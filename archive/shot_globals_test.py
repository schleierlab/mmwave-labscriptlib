
import labscript

from labscriptlib.connection_table import devices
from labscriptlib.shot_globals import shot_globals

devices.initialize()

print(shot_globals.n_shot)
print(shot_globals)

t = 0
labscript.start()
labscript.stop(t + 1e-2)
