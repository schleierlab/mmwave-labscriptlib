import labscript
from labscriptlib.connection_table import devices
from labscriptlib.shot_globals import shot_globals


if shot_globals.get_n_runs() != 1:
    raise ValueError('Remove all runmanager scans before proceeding!')

devices.initialize()
labscript.start()
devices.dispenser_off_trigger.go_high(t=0.1)
devices.mot_coil_current_ctrl.constant(t=0.1, value=0)
labscript.stop(t=0.2)
