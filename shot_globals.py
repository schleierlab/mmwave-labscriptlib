import re
from importlib import resources as impresources
from types import SimpleNamespace
from typing import Any, TypedDict

import h5py
import yaml

from labscript import compiler
import runmanager

import labscriptlib

# pyyaml doesn't recognize all scientific notation numbers
# fix from https://stackoverflow.com/a/30462009
loader = yaml.SafeLoader
loader.add_implicit_resolver(
    u'tag:yaml.org,2002:float',
    re.compile(u'''^(?:
     [-+]?(?:[0-9][0-9_]*)\\.[0-9_]*(?:[eE][-+]?[0-9]+)?
    |[-+]?(?:[0-9][0-9_]*)(?:[eE][-+]?[0-9]+)
    |\\.[0-9_]+(?:[eE][-+][0-9]+)?
    |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\\.[0-9_]*
    |[-+]?\\.(?:inf|Inf|INF)
    |\\.(?:nan|NaN|NAN))$''', re.X),
    list(u'-+0123456789.'),
)


class ParameterSpec(TypedDict):
    value: Any
    unit: str


class ShotGlobals(SimpleNamespace):
    # declare globals here!
    n_shot: int
    manta_exposure: float

    def __init__(self) -> None:
        super().__init__()
        self._last_loaded_h5 = None

        self._runmanager_globals = dict()
        self._defaults = dict()
        self._loaded_globals = dict()

    def __getattr__(self, name: str) -> Any:
        '''
        Treat any unrecognized attributes as runmanager global names and try to access them.
        '''
        # only load globals once per shot
        # note: we cannot cache globals naively (i.e. fetch once per instance of ShotGlobals)
        # because runmanager caches modules aggressively (in particular, unless the module is
        # edited or one clicks "Restart subprocess"), so one instance of ShotGlobals can persist
        # across multiple shots
        if self._last_loaded_h5 != compiler.hdf5_filename:
            self._runmanager_globals = runmanager.get_shot_globals(compiler.hdf5_filename)

            inp_file = impresources.files(labscriptlib) / 'defaults.yml'
            # with open('defaults.yml', 'r') as f:
            with inp_file.open('r') as f:
                self._defaults: dict[str, dict[str, ParameterSpec]] = yaml.load(f, Loader=loader)

            flattened_defaults = dict()
            for _, groupvars in self._defaults.items():
                for varname, var in groupvars.items():
                    if varname in flattened_defaults:
                        raise ValueError(f'Duplicated name {varname} in defaults')
                    flattened_defaults[varname] = var['value']

            self._loaded_globals = flattened_defaults | self._runmanager_globals
            self._save_defaults_to_h5(flattened_defaults)
            self._last_loaded_h5 = compiler.hdf5_filename

        try:
            return self._loaded_globals[name]
        except KeyError:
            raise AttributeError(f'global {name} defined neither in defaults nor as a runmanager override')

    # pass in flattened defaults so we don't have to flatten a second time
    def _save_defaults_to_h5(self, defaults_flattened):
        '''
        In the h5 file, create the following structure:

        'default_params' (attrs: {global1: value1, ...})
            Group1 (attrs: {global1: value1, ...})
                'units' (attrs: {global1: unit1, ...})
            Group2 (...)
                'units' (...)
            ...

        where:
        - groups:
            Group1, Group2, ... consist of all groups spec'd in runmanager
            together with all groups in the defaults file.
        - group attrs
            The group attributes
        '''
        with h5py.File(compiler.hdf5_filename, 'r+') as f:
            f.create_group('default_params')
            defaults_h5group = f['default_params']

            defaults_h5group.attrs.update(defaults_flattened)
            for groupname, groupvars in self._defaults.items():
                defaults_h5group.create_group(groupname)
                subgroup = defaults_h5group[groupname]

                defaults_values = {varname: vardict['value'] for varname, vardict in groupvars.items()}
                defaults_units = {varname: vardict['unit'] for varname, vardict in groupvars.items()}
                subgroup.attrs.update(defaults_values)
                subgroup.create_group('units')
                subgroup['units'].attrs.update(defaults_units)


shot_globals = ShotGlobals()
