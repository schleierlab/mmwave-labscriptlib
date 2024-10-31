# -*- coding: utf-8 -*-
"""
Modified from Rydberg lab spectrum_manager_fifo.py

Created on March 25th 2024
"""
import labscript
from connection_table import devices
import numpy as np
from tweezers_phaseAmplitudeAdjustment import trap_phase, trap_amplitude
from labscriptlib.shot_globals import shot_globals

devices.initialize()
#Note 20230327: can only use one channel for fifo mode for now.

def dbm_to_vpeak(power):
    # Converts power in dbm to peak voltage (not Vpp or Vrms)
    r = 50 # Ohms
    exponent = (power - 10) / 20
    return 10**exponent

class SpectrumManagerFifo():
    x_kwargs = None
    x_key = None
    # y_kwargs = None
    # y_key = None
    started_tw = False
    outputting_tw = False

    def start_tweezer_card(self):
        self.started_tw = False
        self.outputting_tw = False

        # we need to declare some runmanager variables as global so that we can reference them later
        TW_x_freqs = shot_globals.TW_x_freqs
        TW_x_power = shot_globals.TW_x_power
        TW_x_amplitude = shot_globals.TW_x_amplitude
        # TW_y_freqs = shot_globals.TW_y_freqs
        # TW_y_power = shot_globals.TW_y_power
        # TW_y_amplitude = shot_globals.TW_y_amplitude
        # if shot_globals.do_rearrangement_single_shot == True:
        #     b_rearrangement = True
        # else:
        #     b_rearrangement = shot_globals.do_mot_coil

        # set the card mode
        devices.spectrum_0.set_mode(
            replay_mode= b'fifo_single',
            channels = [
                        {'name': 'Tweezer_X', 'power': TW_x_power, 'port': 0, 'is_amplified':True,
                         'amplifier': 1, 'calibration_power': 15, 'power_mode': 'constant_total', 'max_pulses': 1}#'do_rearrangement': b_rearrangement} #, 'static_atten': 12}
                        # {'name': 'Tweezer_Y', 'power': TW_y_power, 'port': 0, 'is_amplified':False,
                        #  'amplifier': 2, 'calibration_power': 15, 'power_mode': 'constant_total', 'max_pulses': 1}
                          # power_mode and max_pulses are not included in power calculation here.
                          # calibration_power is only used to identify which calibration to use.
                          # It is set to 15 here because 15 dBm is the max output from the spectrum card (w/o any attenuation) but it can be set to any number as long as it is distinguishable from other calibrations.
                          # We have 12 dB attenuation for both chaneels of spectrum card 19620 (spectrum_0)
                        ],
            clock_freq = 625,#350,#625,
            use_ext_clock = True,
            # export_data = True, #export data function not yet exists in fifo mode
            # export_path = r'Z:\spectrum_testing_fifo_20240327',
            smart_programming= True, #True,
            )
        # set the output settings
        SpectrumPhase = 0
        # SpectrumDuration = TW_loopDuration

        # if only a single frequency is entered, convert it to an array with one entry
        if type(TW_x_freqs)==np.int32 or type(TW_x_freqs)==np.float64:
            TW_x_freqs = np.array([TW_x_freqs])
        # if type(TW_y_freqs)==np.int32 or type(TW_y_freqs)==np.float64:
        #     TW_y_freqs = np.array([TW_y_freqs])
            # round the y frequencies since we vary them sometimes
            # TW_x_freqs = np.round(TW_x_freqs* 1e6 * SpectrumDuration) / SpectrumDuration / 1e6 #FIXME: this is bad mojo without phase optimization
            # TW_y_freqs = np.round(TW_y_freqs* 1e6 * SpectrumDuration) / SpectrumDuration / 1e6


        if len(TW_x_freqs)==1: # TW_x single freq input
            TW_x_phases  = [SpectrumPhase for i in TW_x_freqs]
            TW_x_amps = [TW_x_amplitude for i in TW_x_freqs]
        else: # TW_x multi-freq input
            TW_x_phases = trap_phase(TW_x_freqs)
            TW_x_amps = TW_x_amplitude * trap_amplitude(TW_x_freqs) # amplitude set to 0.99 to aviod calculation error

        # if len(TW_y_freqs)==1: # TW_y single freq input
        #     TW_y_phases  = [SpectrumPhase for i in TW_y_freqs]
        #     TW_y_amps = [TW_y_amplitude for i in TW_y_freqs]
        # else: # TW_y multi-freq input
        #     TW_y_phases = trap_phase(TW_y_freqs)
        #     TW_y_amps = TW_y_amplitude * trap_amplitude(TW_y_freqs) # amplitude set to 0.99 to aviod calculation error

        # instantiate dictionary to carry tweezer options
        self.x_kwargs = {'freq': TW_x_freqs*1e6,
                          'output_voltage': dbm_to_vpeak(TW_x_power),
                          'amplitude': TW_x_amps,
                          'phase': TW_x_phases,
                          'ch': 0}

        self.x_key = 'x_fifo'

        # self.y_kwargs = {'freq': TW_y_freqs*1e6,
        #                   'output_voltage': dbm_to_vpeak(TW_y_power),
        #                   'amplitude': TW_y_amps,
        #                   'phase': TW_y_phases,
        #                   'ch': 0}

        # self.y_key = 'y_fifo'

        self.started_tw = True

        return

    def stop_tweezer_card(self):
        assert not self.outputting_tw, 'SpectrumManager: output must be stopped before card is stopped'
        devices.spectrum_0.stop()

        # fifo_single_freq(t_start, total_time, freq, output_voltage, amplitude, phase, ch)
    def start_tweezers(self, t):
        assert self.started_tw, 'SpectrumManager: must run prepare() before start()'
        assert not self.outputting_tw, 'SpectrumManager: output has already been started'
        devices.spectrum_0.start_flexible_loop(t, devices.spectrum_0.fifo_multi_freq, self.x_key, **self.x_kwargs)
        # devices.spectrum_0.start_flexible_loop(t, devices.spectrum_0.fifo_single_freq, self.x_key, **self.x_kwargs)
        # devices.spectrum_0.start_flexible_loop(t, devices.spectrum_0.fifo_single_freq, self.y_key, **self.y_kwargs)
        self.outputting_tw = True
        return t

    def stop_tweezers(self, t):
        assert self.outputting_tw, 'SpectrumManager: must run start() before stop()'
        print(f'Ending last static period at time t = {t}')
        devices.spectrum_0.stop_flexible_loop(t, self.x_key, fifo=True)
        # devices.spectrum_0.stop_flexible_loop(t, self.y_key, fifo=True)
        self.outputting_tw = False
        # self.x_key = self.x_key + "0"
        # self.y_key = self.y_key + "0"
        return t

    def start_mw_card(self):
        print('Microwave not implemented in FIFO.')

        return

    # Note: This function assumes CP used for cubic transport sweep
    def start_cp_card(self):
        self.started_cp = False
        self.outputting_cp = False

        # set the card mode
        # TO DO: Potentially change for FIFO
        Spectrum6631.set_mode(
            replay_mode= b'fifo_single',
            channels = [
                        {'name': 'cp_spectrum', 'power': CP_spectrum_power, 'port': 0, 'is_amplified':True,
                         'amplifier': 3, 'power_mode': 'constant_total', 'max_pulses': 1, 'calibration_power': 15, 'static_atten': 23}
                          # {'name': 'cp_dummy2', 'power': 0, 'port': 1, 'is_amplified':False,
                          # 'amplifier': None, 'power_mode': 'constant_total', 'max_pulses': 1} # 'calibration_power': 0
                         # {'name': 'cp_dummy3', 'power': 0, 'port': 3, 'is_amplified':False,
                         # 'amplifier': None, 'power_mode': 'passive', 'max_pulses': 1}
                        ],
            clock_freq = 400,
            use_ext_clock = True,
            export_data = False,
            export_path = r'Z:\Experiments\rydberglab',
            smart_programming=False,
            )
        # Estimate min and max frequency based on detuning, distance and duration
        self.baseline_freq = (110 ) * 1e6 + T_cp_relative_freq
        max_speed = 1.5 * (T_cp_distance / 100) / T_transportTime
        self.peak_freq = 2 * max_speed/ 1064e-9 + self.baseline_freq #cp  - 10e6
        print(f"Peak frequency is calculated to be : {self.peak_freq}")
        self.cp_key = 'cp_key'
        self.started_cp = True

        return

    # Starts CP output at time t, single frequency. End time tbd by stop_flexible
    def start_cp(self, t):
        assert self.started_cp, 'SpectrumManager: must run prepare() before start()'
        # if CP_spectrum_power > 14:
        #     raise LabscriptError('The programmed power is higher than your calibration power of 13. Please fix this')
        if CP_spectrum_amplitude < 0 or CP_spectrum_amplitude > 1:
            raise LabscriptError('Amplitude must be between 0 and 1')

        cp_static_kwargs = {'freq': self.baseline_freq,
                          'output_voltage': dbm_to_vpeak(CP_spectrum_power),
                          'amplitude': CP_spectrum_amplitude,
                          'phase': 0,
                          'ch': 0}
        Spectrum6631.start_flexible_loop(t, Spectrum6631.fifo_single_freq, self.cp_key, **cp_static_kwargs)
        self.outputting_cp = True
        return t

    def stop_cp(self, t):
        assert self.outputting_cp, 'SpectrumManager: must run start() before stop()'
        print(f'Ending last static period at time t = {t}')
        Spectrum6631.stop_flexible_loop(t, self.cp_key, fifo=True)
        self.outputting_cp = False
        return t

    def quadratic_sweep(self, t):
        # Stop static sweep
        t = Spectrum6631.stop_flexible_loop(t, self.cp_key, fifo=True)

        # Quadratic sweep for transport
        cp_quad_kwargs = {'start_freq': self.baseline_freq,
                          'peak_freq': self.peak_freq,
                          'output_voltage': dbm_to_vpeak(CP_spectrum_power),
                          'amplitude': CP_spectrum_amplitude,
                          'phase': 0,
                          'ch': 0}
        t = Spectrum6631.fifo_quad(t_start=t, total_time=T_transportTime, **cp_quad_kwargs)

        # Back to static sweep
        cp_static_kwargs = {'freq': self.baseline_freq,
                          'output_voltage': dbm_to_vpeak(CP_spectrum_power),
                          'amplitude': CP_spectrum_amplitude,
                          'phase': 0,
                          'ch': 0}
        Spectrum6631.start_flexible_loop(t, Spectrum6631.fifo_single_freq, self.cp_key, **cp_static_kwargs)
        return t

    def sin_frequency_modulation(self, t):
        # Stop static sweep
        t = Spectrum6631.stop_flexible_loop(t, self.cp_key, fifo=True)

        # Quadratic sweep for transport
        cp_sine_kwargs = {'base_freq': self.baseline_freq,
                          'mod_freq': CP_mod_freq * 1e3,
                          'mod_amplitude': CP_mod_amplitude * 1e3,
                          'output_voltage': dbm_to_vpeak(CP_spectrum_power),
                          'amplitude': CP_spectrum_amplitude,
                          'phase': 0,
                          'ch': 0}
        t = Spectrum6631.fifo_sin_modulation(t_start=t, total_time=CP_mod_duration, **cp_sine_kwargs)

        # Back to static sweep
        cp_static_kwargs = {'freq': self.baseline_freq,
                          'output_voltage': dbm_to_vpeak(CP_spectrum_power),
                          'amplitude': CP_spectrum_amplitude,
                          'phase': 0,
                          'ch': 0}
        Spectrum6631.start_flexible_loop(t, Spectrum6631.fifo_single_freq, self.cp_key, **cp_static_kwargs)
        return t

    def stop_cp_card(self, t):
        assert not self.outputting_cp, 'SpectrumManager: output must be stopped before card is stopped'
        Spectrum6631.stop()



    def start_dummy_mw(self, t):
        self.x_kwargs = {'duration': SpectrumDuration,
                                'freqs': TW_x_freqs*1e6,
                                'amplitudes': TW_x_amps,
                                'phases': TW_x_phases,
                                'ch': 0}

        self.x_key = 'x_comb'

    def spectrum_pulse(self, t, freq, duration, delay=0, microwave_start_time=0, phase=0, loops=1, mw_switch=False, switch_delay=0):

        """
        Schedule a fixed frequency pulse at time t
        freq: frequency of the pulse in MHz
        duration: Length of the pulse in s
        delay: Delay
        """

        t += delay
        print(f"Requested frequency is {freq}")
        # global phase of each channel since the start of microwaves
        global_phase = 360 * freq * (t - switch_delay - microwave_start_time)
        global_phase = np.mod(global_phase, 360)


        # print(global_phase)
        # print(loops)
        # actual phase is the sum of relative and global phases
        phase_final = np.mod(phase + global_phase, 360)
        # print(phase_final)
        Spectrum6631.single_freq(t - switch_delay, duration + switch_delay, freq,
                                 S_6631_0_amplitude, phase_final, 0, loops)

        if mw_switch:
            MicrowaveSwitch.go_high(t)

        dt = duration*loops
        t += max(dt, 0) #TODO: update for pulseblaster, previously max cf 2.5e-6

        if mw_switch:
            MicrowaveSwitch.go_low(t)

        return t


    def spectrum_sweep(self, t, freq_start, freq_end, duration, delay=0, phase=0, loops=1, ramp_type='linear', mw_switch=False):

        t += delay

        if mw_switch:
            MicrowaveSwitch.go_high(t)


        Spectrum6631.sweep(t, duration, freq_start, freq_end, S_6631_0_amplitude, phase, 0, ramp_type, loops=loops)

        dt = duration*loops
        t += max(dt, 0)

        if mw_switch:
            MicrowaveSwitch.go_low(t)

        return t


spectrum_manager_fifo = SpectrumManagerFifo()


