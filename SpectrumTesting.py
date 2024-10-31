# -*- coding: utf-8 -*-
"""
Created on Fri Dec 28 18:06:03 2018

@author: Quantum Engineer
"""

import os
import sys
root_path = r"C:\labscript-suite\userlib\labscriptlib"

if root_path not in sys.path:
    sys.path.append(root_path)

from labscript import *
from pulses import MWPulseSpectrum

computer_name = os.environ['COMPUTERNAME']

if computer_name == 'RYD-EXPTCTRL':
    print('Importing from RYD-EXPTCTRL')
    from SetUpLab import SetUpLab
    from connectiontable import do_connectiontable
else:
    from connectiontable_sandbox import do_connectiontable
    from SetUpLab_testcomputer import SetUpLab

from SpectrumFunctions import SpectrumPulse, SpectrumSweep


if __name__ == '__main__':

    do_connectiontable()

### SET MODE ##################################################################
    if CT_haveSpectrum6621:
        Spectrum6621.set_mode(replay_mode=b'sequence', 

                           channels = [{'name': 'Tweezer_X', 'power': 7, 'port': 0, 'is_amplified':False,
                                        'amplifier': None, 'calibration_power': 0, 'power_mode': 'passive', 'max_pulses':1},
                                        {'name': 'Tweezer_Y', 'power': 7, 'port': 1, 'is_amplified':False,
                                        'amplifier': None, 'calibration_power': 0, 'power_mode': 'passive', 'max_pulses':1},
                                       ],
                           clock_freq = 625,
                           use_ext_clock = True,
                           export_data = True,
                           export_path = r'Z:\Experiments\rydberglab')
    if CT_haveSpectrum6622:
        Spectrum6622.set_mode(replay_mode=b'sequence', 
                           channels = [
                                       {'name': 'Tweezer_X', 'power': S_6622_0_power, 'port': 0, 'is_amplified':True,
                                        'amplifier': 1, 'calibration_power': 0, 'power_mode': 'passive', 'max_pulses':10},
                                       {'name': 'Tweezer_Y', 'power': S_6622_1_power, 'port': 1, 'is_amplified':True,
                                        'amplifier': 2, 'calibration_power': 0, 'power_mode': 'passive', 'max_pulses':10},
                                       {'name': 'MW1', 'power': S_6622_2_power, 'port': 2, 'is_amplified':False},
                                       {'name': 'MW2', 'power': S_6622_3_power, 'port': 3, 'is_amplified':False}
                                       ],
                           clock_freq = 625,
                           use_ext_clock = True,
                           export_data = True,
                           export_path = r'Z:\Experiments\rydberglab')
    
    if CT_haveSpectrum6631:
        Spectrum6631.set_mode(replay_mode=b'sequence', 
                           channels = [
                                       {'name': 'Tweezer_X', 'power': S_6631_0_power, 'port': 0, 'is_amplified':True,
                                        'amplifier': 1, 'calibration_power': 0, 'power_mode': 'passive', 'max_pulses':2},
                                       {'name': 'Tweezer_Y', 'power': S_6631_1_power, 'port': 1, 'is_amplified':True,
                                        'amplifier': 2, 'calibration_power': 0, 'power_mode': 'passive', 'max_pulses':2},
                                       ],
                           clock_freq = 625,
                           use_ext_clock = True,
                           export_data = True,
                           export_path = r'G:\Shared drives\Rydberg Drive\Jacob\Spectrum Testing')
    
    start()
    t = 0
    t = SetUpLab(t)
    t += 1
    
    RunTrigger.go_high(t)
    RunTrigger.go_low(t+1e-3)
    
### SINGLE FREQUENCY #########################################################
    # duration = 1e-3
    # resonance = 293.36823e6
    # reference = 150e6
    # tuning = resonance - reference
    # half = resonance/2
    
    # freq_0 = half
    # freq_1 = half
    # amplitude = 0.99
    # loops=5/duration
    # phase=0

    # RunTrigger.go_high(t)
    # RunTrigger.go_low(t+1e-3)

    # Spectrum6621.single_freq(t, duration, freq_0, amplitude, phase, 0, loops)
    # Spectrum6621.single_freq(t, duration, freq_1, amplitude, phase, 1, loops)

    # t += loops*duration
        

### FLEXIBLE LOOPS ############################################################
    # kwargs = {'duration': S_testDuration,
    #           'freq': S_testFreq,
    #           'amplitude': S_testAmplitude, 
    #           'phase': 0,
    #           'ch': 0}
    
    # output_key = 'test_loop'
    
    # Spectrum6631.start_flexible_loop(t, Spectrum6631.single_freq, output_key, **kwargs)
    
    # t += 5
    
    # Spectrum6631.stop_flexible_loop(t, output_key)

### FLEXIBLE COMB #############################################################
    # duration = 120e-6
    # # freqs = np.arange(60, 90, 3)*1e6
    # freqs = [f*1e6 for f in TW_x_freqs]
    # amps = [1 for i in range(len(freqs)) ]
    # phases = [0 for i in range(len(freqs))]

    # kwargs = {'duration': duration,
    #           'freqs': freqs,
    #           'amplitudes': amps, 
    #           'phases': phases,
    #           'ch': 0}
    
    # output_key = 'test_loop'
    
    # Spectrum6631.start_flexible_loop(t, Spectrum6631.comb, output_key, **kwargs)
    
    # t += 10
    
    # Spectrum6631.stop_flexible_loop(t, output_key)
    
    
### MICROWAVE PULSE ###########################################################
    microwave_start_time = t
    
    calibration_pulse_number = 4
    calibration_delay = 0
    calibration_pulse_length = MW1_Pulse1_Length
    # frequency = MW_Resonance_Freq+MW1_Detuning
    frequency = 150
    
    for i in range(calibration_pulse_number):
        t+= calibration_delay/2
        
        phase = -7.25*i*0
        t = MWPulseSpectrum(t, calibration_pulse_length, frequency,
                             0.5, -phase, delay=0, microwave_start_time=microwave_start_time)
        
        t+= calibration_delay/2

    # added because calibration pulses were clashing with something later
    t += 5e-3
    


### STOP ######################################################################    
    if CT_haveSpectrum6621:
        Spectrum6621.stop()
    if CT_haveSpectrum6622:
        Spectrum6622.stop()
    if CT_haveSpectrum6631:
        Spectrum6631.stop()

    t += 1
    stop(t)