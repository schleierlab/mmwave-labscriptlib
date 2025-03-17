import labscript
from labscriptlib.connection_table import devices

devices.initialize()
labscript.start()
devices.dispenser_off_trigger.go_low(t=0.1)
labscript.stop(t=0.2)
