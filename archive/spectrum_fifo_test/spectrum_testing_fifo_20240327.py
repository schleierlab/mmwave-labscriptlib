
# import os
import sys

import labscript_devices.FunctionRunner
import labscript_devices.FunctionRunner.labscript_devices
root_path = r"C:\Users\sslab\labscript-suite\userlib\labscriptlib"

if root_path not in sys.path:
    sys.path.append(root_path)

import labscript
import labscript_devices as labscript_devices
import time
from connection_table import devices
from spectrum_manager_fifo import spectrum_manager_fifo

def generate_txt_file(shot_context, t, empty = False):
    file_path = r"X:\userlib\user_devices\kinetix\tweezer_atom_positions.txt"
        # Open the file in write mode
    if empty == True:
        atom_site_lst = [] # empty file for bkg shots to run
    else:
        atom_site_lst = [0,2,3,5,6] # for testing
        # atom_site_lst = [0,3,5,6,9]
        # atom_site_lst = [0,2,3,5,6,9]
    with open(file_path, 'w') as file:
        for item in atom_site_lst:
            file.write(str(item) + ' ')
    if empty == True:
        print(f'an empty file has been created as {file_path}.')
    else:
        print(f'The list has been saved to {file_path}.')
    # end_time = time.time()
    # return end_time
# generate_txt_file(empty = False)
devices.initialize()

### SET MODE ##################################################################

spectrum_manager_fifo.start_tweezer_card()

labscript.start()
t = 0

start_time = time.time()
print("start time:",start_time)
devices.runner.add_function(t='start', function=generate_txt_file)
print(f'start generating txt file at time {t}')

# t += 10e-3
# devices.blue_456_shutter.open(t)
# t+=10e-3
# devices.moglabs_456_aom_analog.constant(t,1)
# devices.moglabs_456_aom_digital.go_high(t)
# t += 10e-6
# devices.moglabs_456_aom_analog.constant(t,0)
# devices.moglabs_456_aom_digital.go_low(t)


devices.digital_out_ch26.go_high(t)
# t += 3e-6
t1 = spectrum_manager_fifo.start_tweezers(t) #has to be the first thing in the timing sequence (?)
print('tweezer start time:',t1)
# t += 2e-3 #lower than 1e-3 will cause server to close automatically before reaching transition to static
# t +=2

# generate_txt_file(empty = False)
# end_time = generate_txt_file(empty = False)

# devices.tweezer_aom_digital.go_high(t)
# devices.tweezer_aom_analog.constant(t, 1)
# time_difference = end_time - start_time
# print("Time taken to generate the txt file:", time_difference, "seconds")

t += 0.5 #900e-3#1#200e-3#1#200e-3#200e-3 #100

# Stop cards

t2 = spectrum_manager_fifo.stop_tweezers(t)
print('tweezer stop time:',t2)
#t += 1e-3

##### dummy segment ######
# t1 = spectrum_manager_fifo.start_tweezers(t)
# print('tweezer start time:',t1)
# t += 2e-3
# t2 = spectrum_manager_fifo.stop_tweezers(t)
# print('tweezer stop time:',t2)

devices.digital_out_ch26.go_low(t)

spectrum_manager_fifo.stop_tweezer_card()

labscript.stop(t+1e-3)