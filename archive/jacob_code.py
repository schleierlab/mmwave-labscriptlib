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
                {'name': 'Tweezer_Y', 'power': 0, 'port': 1, 'is_amplified':False,
                    'amplifier': None, 'calibration_power': 0, 'power_mode': 'constant_single', 'max_pulses':1},
                ],
    clock_freq = 1000,
    use_ext_clock = False,
    export_data = False,
    export_path = r'C:\Users\sslab\labscript-suite\userlib\labscriptlib',
    smart_programming=False,
)

# spectrum card output options
total_duration = 2e-3
loop_duration = 1e-3

flexible = False

frequency = 1e3
amplitude = 0.1
loops = int(total_duration // loop_duration)
phase = 0

x_key = 'x_comb'
y_key = 'y_comb'

x_kwargs = {
    'duration': loop_duration,
    'freqs': [frequency],
    'amplitudes': [amplitude],
    'phases': [phase],
    'ch': 0
    }

y_kwargs = {
    'duration': loop_duration,
    'freqs': [frequency],
    'amplitudes': [amplitude],
    'phases': [phase],
    'ch': 1
    }

print(f'Loops: {loops}')

labscript.start()
t = 0

if flexible:
    devices.spectrum_0.start_flexible_loop(t, devices.spectrum_0.comb, x_key, **x_kwargs)
    devices.spectrum_0.start_flexible_loop(t, devices.spectrum_0.comb, y_key, **y_kwargs)
else:
    devices.spectrum_0.single_freq(t, loop_duration, frequency, amplitude, phase, 0, loops)
    devices.spectrum_0.single_freq(t, loop_duration, frequency, amplitude, phase, 1, loops)

t += total_duration

if flexible:
    devices.spectrum_0.stop_flexible_loop(t, x_key)
    devices.spectrum_0.stop_flexible_loop(t, y_key)

devices.spectrum_0.stop()
labscript.stop(t + 1e-2)