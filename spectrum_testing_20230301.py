import sys
root_path = r"C:\Users\sslab\labscript-suite\userlib\labscriptlib"

if root_path not in sys.path:
    sys.path.append(root_path)

import labscript
from connection_table import devices

devices.initialize()

# set the card mode
devices.spectrum_0.set_mode(
    replay_mode=b'sequence',
    channels = [
                {'name': 'Tweezer_X', 'power': 0, 'port': 0, 'is_amplified':False,
                    'amplifier': None, 'calibration_power': 0, 'power_mode': 'constant_single', 'max_pulses':1},
                # {'name': 'Tweezer_Y', 'power': 0, 'port': 1, 'is_amplified':False,
                #     'amplifier': 2, 'calibration_power': 0, 'power_mode': 'passive', 'max_pulses':1}
                ],
    clock_freq = 625,
    use_ext_clock = True,
    export_data = False,
    export_path = r'Z:\spectrum_testing_20230301',
    smart_programming=True,
)


labscript.start()
t = 0

#t += 1e-2


#spectrum_0.triggerDO.go_high(t)
#spectrum_0.triggerDO.go_low(t)
#t += 5

### SINGLE FREQUENCY #########################################################
duration = 9e-2
# resonance = 293.36823e6
# reference = 150e6
# tuning = resonance - reference
# half = resonance/2

freq_0 = 1e6
# freq_1 = half
amplitude = 0.99 # max = 1, actual power = power (in dBm)*amplitude
loops=2 #5/duration
phase=0

# RunTrigger.go_high(t)
# RunTrigger.go_low(t+1e-3)

devices.digital_out_ch13.go_high(t)
#devices.spectrum_0.single_freq(t, duration, freq_0, amplitude, phase, 0, loops)
devices.spectrum_0.single_freq(t, duration, freq_0, amplitude, phase, 0, loops)
#Spectrum6621.single_freq(t, duration, freq_1, amplitude, phase, 1, loops)


t += loops*duration

devices.digital_out_ch13.go_low(t)

#devices.spectrum_0.stop()
devices.spectrum_0.stop()

labscript.stop(t + 1e-2)
