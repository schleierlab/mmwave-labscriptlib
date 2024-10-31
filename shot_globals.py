from types import SimpleNamespace
from typing import Any

from labscript import compiler
import runmanager


class ShotGlobals(SimpleNamespace):
    # declare globals here!
    n_shot: int
    manta_exposure: float

    def __init__(self) -> None:
        super().__init__()
        self._last_loaded_h5 = None
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
            self._loaded_globals = runmanager.get_shot_globals(compiler.hdf5_filename)
            self._last_loaded_h5 = compiler.hdf5_filename

        try:
            return self._loaded_globals[name]
        except KeyError:
            raise AttributeError(f'runmanager global {name} not defined. Did you forget to call load()?')


shot_globals = ShotGlobals()
