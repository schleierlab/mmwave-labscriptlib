# -*- coding: utf-8 -*-
"""
Modified from Rydberg lab spectrum_manager.py

Created on Aug 1st 2023

@author: Michelle Wu
"""
from typing import Any
import numpy as np

from labscriptlib.tweezers_phaseAmplitudeAdjustment import trap_phase, trap_amplitude
from labscriptlib.connection_table import devices
from labscriptlib.shot_globals import shot_globals

if not shot_globals.TW_y_use_dds:
    TW_y_channel = True # use spectrum card instead of dds for tweezer y channel
else:
    TW_y_channel = False
devices.initialize()

class SpectrumManager():
    x_kwargs = None
    x_key = None
    y_kwargs = None
    y_key = None
    started = False
    outputting = False

    def start_card(self):
        # reset state variables
        self.started = False
        self.outputting = False

        # we need to declare some runmanager variables as global so that we can reference them later
        TW_x_freqs = np.asarray(shot_globals.TW_x_freqs)

        #print(f"TW_x_freqs = {TW_x_freqs}")
        TW_x_power = 33 # Translated from old runmanager settings
        TW_x_amplitude = 0.99 # Translated from old runmanager settings
        TW_maxPulses = shot_globals.TW_maxPulses
        TW_loopDuration = shot_globals.TW_loopDuration

        if TW_y_channel:
            TW_y_freqs = np.asarray(shot_globals.TW_y_freqs)
            TW_y_freqs = np.array([TW_y_freqs])
            TW_y_power = shot_globals.TW_y_power
            TW_y_amplitude = shot_globals.TW_y_amplitude
            channel_setting = [
                        {'name': 'Tweezer_X', 'power': TW_x_power, 'port': 0, 'is_amplified':True,
                         'amplifier': 1, 'calibration_power': 12, 'power_mode': 'constant_total', 'max_pulses':TW_maxPulses},
                        {'name': 'Tweezer_Y', 'power': TW_y_power, 'port': 1, 'is_amplified':True,
                         'amplifier': 2, 'calibration_power': 12, 'power_mode': 'constant_total', 'max_pulses':TW_maxPulses}
                        ]
        else:
            channel_setting = [
                        {'name': 'Tweezer_X', 'power': TW_x_power, 'port': 0, 'is_amplified':True,
                         'amplifier': 1, 'calibration_power': 12, 'power_mode': 'constant_total', 'max_pulses':TW_maxPulses},
                        ]


        # set the card mode
        devices.spectrum_0.set_mode(
            replay_mode=b'sequence',
            channels = channel_setting,
            clock_freq = 625,#625,
            use_ext_clock = True,
            export_data = False,
            export_path = r'Z:\spectrum_testing_20230801',
            smart_programming=True,
            )

        # set the output settings
        SpectrumPhase = 0
        SpectrumDuration = TW_loopDuration

        def is_np_int_float(x: Any) -> bool:
            return isinstance(x, np.int32) or isinstance(x, np.float64)

        # if only a single frequency is entered, convert it to an array with one entry
        if is_np_int_float(TW_x_freqs):
            TW_x_freqs = np.array([TW_x_freqs])

        if TW_y_channel:
            if is_np_int_float(TW_y_freqs):
                TW_y_freqs = np.array([TW_y_freqs])
                # round the y frequencies since we vary them sometimes
                # TW_x_freqs = np.round(TW_x_freqs* 1e6 * SpectrumDuration) / SpectrumDuration / 1e6 #FIXME: this is bad mojo without phase optimization
                TW_y_freqs = np.round(TW_y_freqs* 1e6 * SpectrumDuration) / SpectrumDuration / 1e6



        if len(TW_x_freqs)==1: # TW_x single freq input
            TW_x_phases  = [SpectrumPhase for i in TW_x_freqs]
            TW_x_amps = [TW_x_amplitude for i in TW_x_freqs]
        else: # TW_x multi-freq input
            print(f"TW_x_freqs = {TW_x_freqs}")
            TW_x_phases = trap_phase(TW_x_freqs)
            TW_x_amps = TW_x_amplitude * trap_amplitude(TW_x_freqs) # amplitude set to 0.99 to aviod calculation error

        if TW_y_channel:
            if len(TW_y_freqs)==1: # TW_y single freq input
                TW_y_phases  = [SpectrumPhase for i in TW_y_freqs]
                TW_y_amps = [TW_y_amplitude for i in TW_y_freqs]
            else: # TW_y multi-freq input
                TW_y_phases = trap_phase(TW_y_freqs)
                TW_y_amps = TW_y_amplitude * trap_amplitude(TW_y_freqs) # amplitude set to 0.99 to aviod calculation error

        # instantiate dictionary to carry tweezer options
        self.x_kwargs = {'duration': SpectrumDuration,
                                'freqs': TW_x_freqs*1e6,
                                'amplitudes': TW_x_amps,
                                'phases': TW_x_phases,
                                'ch': 0}
        self.x_key = 'x_comb'

        if TW_y_channel:
            self.y_kwargs = {'duration': SpectrumDuration,
                                'freqs': TW_y_freqs*1e6,
                                'amplitudes': TW_y_amps,
                                'phases': TW_y_phases,
                                'ch': 1}
            self.y_key = 'y_comb'

        self.started = True


        return

    def start_tweezers(self, t):
        assert self.started, 'SpectrumManager: must run prepare() before start()'
        assert not self.outputting, 'SpectrumManager: output has already been started'
        devices.spectrum_0.start_flexible_loop(t, devices.spectrum_0.comb, self.x_key, **self.x_kwargs)
        if TW_y_channel:
            devices.spectrum_0.start_flexible_loop(t, devices.spectrum_0.comb, self.y_key, **self.y_kwargs)
        self.outputting = True
        return t

    def stop_tweezers(self, t):
        assert self.outputting, 'SpectrumManager: must run start() before stop()'
        devices.spectrum_0.stop_flexible_loop(t, self.x_key)
        self.x_key = self.x_key + "0"
        if TW_y_channel:
            devices.spectrum_0.stop_flexible_loop(t, self.y_key)
            self.y_key = self.y_key + "0"
        self.outputting = False
        return t

    def stop_card(self, t):
        assert not self.outputting, 'SpectrumManager: output must be stopped before card is stopped'
        devices.spectrum_0.stop()

    # def move_tweezers(self, t, loops=1):
    #     #add 0-64 ns variable delay here
    #     # Stop original tweezer position frequencies

    #     freq_ramp_type = TW_ramp_type_freqs
    #     amp_ramp_type = TW_ramp_type_amps
    #     phase_ramp_type = TW_ramp_type_phases
    #     devices.spectrum_0.stop_flexible_loop(t, self.y_key, extend=TW_extend_waveform_before_ramp)
    #     print(f"t before stopping loop {t}")
    #     t = devices.spectrum_0.stop_flexible_loop(t, self.x_key, extend=TW_extend_waveform_before_ramp)
    #     print(f"t after stopping loop {t}")
    #     # x stuff

    #     freqs1 = self.x_kwargs['freqs']
    #     freqs2 = self.x2_kwargs['freqs']
    #     phases_init = self.x_kwargs['phases']
    #     phases_final = self.x2_kwargs['phases']
    #     phases = [(phases_init[i], phases_final[i]) for i in range(len(freqs1))]
    #     amplitudes_init = self.x_kwargs['amplitudes']
    #     amplitudes_final = self.x2_kwargs['amplitudes']
    #     amplitudes = [(amplitudes_init[i], amplitudes_final[i]) for i in range(len(freqs1))]
    #     # amplitudes=amplitudes_final
    #     # phases = phases_final
    #     # y stuff
    #     phases_y = self.y_kwargs['phases']
    #     amplitudes_y = self.y_kwargs['amplitudes']
    #     freqs_y = self.y_kwargs['freqs']


    #     # Sweep x and y tweezers (y sweep is not needed but we do it to keep x and y symmetric)
    #     devices.spectrum_0.sweep_comb(t,
    #                             TW_sweep_time,
    #                             freqs_y,
    #                             freqs_y,
    #                             amplitudes_y,
    #                             phases_y,
    #                             loops=1,
    #                             ch=1,
    #                             freq_ramp_type=freq_ramp_type,
    #                             amp_ramp_type=amp_ramp_type,
    #                             phase_ramp_type=phase_ramp_type)

    #     t = devices.spectrum_0.sweep_comb(t,
    #                                 TW_sweep_time,
    #                                 freqs1,
    #                                 freqs2,
    #                                 amplitudes,
    #                                 phases ,
    #                                 loops=1,
    #                                 ch=0,
    #                                 freq_ramp_type=freq_ramp_type,
    #                                 amp_ramp_type=amp_ramp_type,
    #                                 phase_ramp_type=phase_ramp_type)

    #     # Set final waveforms
    #     self.y_key = 'y_final'
    #     self.x_key = 'x_final'
    #     devices.spectrum_0.start_flexible_loop(t, devices.spectrum_0.comb, self.y_key, **self.y_kwargs)
    #     devices.spectrum_0.start_flexible_loop(t, devices.spectrum_0.comb, self.x_key, **self.x2_kwargs)
    #     self.outputting = True

    #     return t

spectrum_manager = SpectrumManager()


'''
def SpectrumPulse(t, freq, duration, delay=0, phase=0, loops=1, mw_switch=False):

    t += delay

    if mw_switch:
        MicrowaveSwitch.go_high(t)

    freq_s = round(0.5*freq*1e+6)
    spectrum_0.single_freq(t, duration, freq_s,
                             S_6631_0_amplitude, phase, 0, loops)
    spectrum_0.single_freq(t, duration, freq_s,
                             S_6631_1_amplitude, phase, 1, loops)

    dt = duration*loops
    t += max(dt, 0) #TODO: update for pulseblaster, previously max cf 2.5e-6

    if mw_switch:
        MicrowaveSwitch.go_low(t)

    return t


def SpectrumSweep(t, freq_start, freq_end, duration, delay=0, phase=0, loops=1, ramp_type='linear', mw_switch=False):

    t += delay

    if mw_switch:
        MicrowaveSwitch.go_high(t)

    freq_start_s = round(0.5*freq_start*1e+6)
    freq_end_s = round(0.5*freq_end*1e+6)

    spectrum_0.sweep(t, duration, freq_start_s, freq_end_s, S_6631_0_amplitude, phase, 0, ramp_type, loops=loops)
    spectrum_0.sweep(t, duration, freq_start_s, freq_end_s, S_6631_1_amplitude, phase, 1, ramp_type, loops=loops)

    dt = duration*loops
    t += max(dt, 0)

    if mw_switch:
        MicrowaveSwitch.go_low(t)

    return t
'''