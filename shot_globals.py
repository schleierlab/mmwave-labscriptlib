from types import SimpleNamespace
from typing import Any, TypedDict

import h5py
import yaml

from labscript import compiler
import runmanager


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
        self.from_yaml()

    def from_yaml(self) -> None:
        """Load default values from defaults.yml file."""
        try:
            with open('defaults.yml', 'r') as f:
                self._defaults = yaml.safe_load(f)
        except FileNotFoundError:
            self._defaults = dict()
        except yaml.YAMLError as e:
            raise ValueError(f'Error parsing defaults.yml: {e}')

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
            self._defaults: dict[str, dict[str, ParameterSpec]] = dict()

            flattened_defaults = dict()
            for _, groupvars in self._defaults.items():
                for varname, var in groupvars.items():
                    if varname in flattened_defaults:
                        raise ValueError(f'Duplicated name {varname} in defaults')
                    flattened_defaults[varname] = var['value']

            self._loaded_globals = flattened_defaults | self._runmanager_globals
            self.save_to_h5()
            self._last_loaded_h5 = compiler.hdf5_filename

        try:
            return self._loaded_globals[name]
        except KeyError:
            raise AttributeError(f'global {name} defined neither in defaults nor as a runmanager override')

    def save_to_h5(self):
        '''
        In the h5 file, create the following structure:

        'shot_parameters' (attrs: {global1: value1, ...})
            Group1 (attrs: {global1: runmanager_value1, ...})
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
            f.create_group('shot_parameters')
            params_h5group = f['shot_parameters']

            for key, value in self._loaded_globals.items():
                params_h5group.attrs[key] = value

            # runmgr groups + default groups
            groupnames = set(self._defaults) | set(f['globals'])
            for groupname in groupnames:
                params_h5group.create_group(groupname)
                paramsgroup_h5group = params_h5group[groupname]

                paramsgroup_h5group.create_group('units')
                units_h5group = paramsgroup_h5group['units']

                if groupname in self._defaults:
                    for varname, vardict in self._defaults[groupname].items():
                        paramsgroup_h5group.attrs[varname] = vardict['value']
                        units_h5group.attrs[varname] = vardict['unit']
                if groupname in f['globals']:
                    for varname in f['globals'][groupname].attrs:
                        paramsgroup_h5group.attrs[varname] = f['globals'][groupname].attrs[varname]
                        units_h5group.attrs[varname] = f['globals'][groupname]['units'].attrs[varname]


shot_globals = ShotGlobals()
