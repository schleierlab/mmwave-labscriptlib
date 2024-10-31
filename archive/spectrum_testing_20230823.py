import sys
root_path = r"C:\Users\sslab\labscript-suite\userlib\labscriptlib"

if root_path not in sys.path:
    sys.path.append(root_path)

import labscript
from connection_table import devices
from spectrum_manager import spectrum_manager
import numpy as np
from tweezers_phaseAmplitudeAdjustment import trap_phase, trap_amplitude
from labscriptlib.shot_globals import shot_globals

devices.initialize()

### SET MODE ##################################################################
# TW_x_freqs = shot_globals.TW_x_freqs
# TW_x_power = shot_globals.TW_x_power
# TW_x_amplitude = shot_globals.TW_x_amplitude
TW_y_freqs = shot_globals.TW_y_freqs
TW_y_power = shot_globals.TW_y_power
TW_y_amplitude = shot_globals.TW_y_amplitude
TW_maxPulses = shot_globals.TW_maxPulses
TW_loopDuration = shot_globals.TW_loopDuration

devices.spectrum_0.set_mode(
        replay_mode=b'sequence',
        channels = [
                    # {'name': 'Tweezer_X', 'power': TW_x_power, 'port': 0, 'is_amplified':False,
                    #  'amplifier': None, 'calibration_power': 0, 'power_mode': 'constant_total', 'max_pulses':TW_maxPulses},
                    {'name': 'Tweezer_Y', 'power': TW_y_power, 'port': 1, 'is_amplified':False,
                    'amplifier': None, 'calibration_power': 0, 'power_mode': 'constant_total', 'max_pulses':TW_maxPulses}
                    ],
        clock_freq = 625,
        use_ext_clock = True,
        export_data = False,
        export_path = r'Z:\spectrum_testing_20230801',
        smart_programming=False,
        )

# set the output settings
SpectrumPhase = 0
SpectrumDuration = TW_loopDuration


# if only a single frequency is entered, convert it to an array with one entry
if type(TW_y_freqs)==np.int32 or type(TW_y_freqs)==np.float64:
    TW_y_freqs = np.array([TW_y_freqs])

# round the y frequencies since we vary them sometimes
# TW_x_freqs = np.round(TW_x_freqs* 1e6 * SpectrumDuration) / SpectrumDuration / 1e6 #FIXME: this is bad mojo without phase optimization
TW_y_freqs = np.round(TW_y_freqs* 1e6 * SpectrumDuration) / SpectrumDuration / 1e6
TW_y_phases  = [SpectrumPhase for i in TW_y_freqs]
TW_y_amps = [TW_y_amplitude for i in TW_y_freqs]

y_kwargs = {
    'duration': SpectrumDuration,
    'freqs': TW_y_freqs*1e6,
    'amplitudes': TW_y_amps,
    'phases': TW_y_phases,
    'ch': 1
    }

y_key = 'y_comb'

labscript.start()
t = 0

devices.spectrum_0.start_flexible_loop(t, devices.spectrum_0.comb, y_key, **y_kwargs)

t += 5

devices.spectrum_0.stop_flexible_loop(t, y_key)

devices.spectrum_0.stop()
labscript.stop(t)

