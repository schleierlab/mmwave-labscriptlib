
#import os
import sys
root_path = r"C:\Users\sslab\labscript-suite\userlib\labscriptlib"

if root_path not in sys.path:
    sys.path.append(root_path)

import labscript
from connection_table import devices
from spectrum_manager import spectrum_manager
from labscriptlib.shot_globals import shot_globals

devices.initialize()

### SET MODE ##################################################################

spectrum_manager.start_card()

labscript.start()
t = 0
devices.dds0.synthesize(t+1e-2, shot_globals.TW_y_freqs , 0.95, 0) # control for AOD Y
# devices.digital_out_ch13.go_high(t)
# for i in range(3):
#     t1 = spectrum_manager.start_tweezers(t)
#     print('tweezer start time:',t1)
#     t += 2e-3

#     # Stop cards

#     t2 = spectrum_manager.stop_tweezers(t)
#     print('tweezer stop time:',t2)
#     t+=1e-3

# devices.moglabs_456_aom_analog.constant(t,0.4)
# devices.moglabs_456_aom_digital.go_high(t)

# devices.ipg_1064_aom_analog.constant(t,1)
# devices.ipg_1064_aom_digital.go_high(t)

t1 = spectrum_manager.start_tweezers(t) #has to be the first thing in the timing sequence (?)
print('tweezer start time:',t1)
t += 1e-5

devices.tweezer_aom_digital.go_high(t)
devices.tweezer_aom_analog.constant(t, 0.32)

t += 100 #100

# Stop cards

t2 = spectrum_manager.stop_tweezers(t)
print('tweezer stop time:',t2)
#t += 1e-3

##### dummy segment ######
t1 = spectrum_manager.start_tweezers(t)
print('tweezer start time:',t1)
t += 2e-3
t2 = spectrum_manager.stop_tweezers(t)
print('tweezer stop time:',t2)
#t += 1e-3

# devices.digital_out_ch13.go_low(t)

spectrum_manager.stop_card(t)

labscript.stop(t)