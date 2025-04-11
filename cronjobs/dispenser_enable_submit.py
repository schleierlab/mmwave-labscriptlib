from pathlib import Path

import runmanager.remote as rr

current_file = rr.get_labscript_file()

rr.set_labscript_file(Path(__file__).with_name('dispenser_enable.py'))
rr.set_globals({ 'repetition_index': 1 })
if rr.n_shots() != 1:
    raise RuntimeError()
rr.engage()

rr.set_labscript_file(current_file)
