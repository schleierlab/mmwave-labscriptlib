from pathlib import Path
import time

import runmanager.remote as rr

current_file = rr.get_labscript_file()

rr.set_labscript_file(Path(__file__).with_name('dispenser_enable.py'))

n_shots = rr.n_shots()
rr.engage()

# only need to queue up one shot, and definitely don't want to queue up a bunch
# so just abort shot compilation if we're running more
if n_shots > 1:
    time.sleep(0.2)  # tested 2025-04-16, queues up three shots
    rr.abort()

rr.set_labscript_file(current_file)
