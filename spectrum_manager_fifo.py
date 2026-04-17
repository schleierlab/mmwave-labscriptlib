# -*- coding: utf-8 -*-
"""
Modified from Rydberg lab spectrum_manager_fifo.py

Created on March 25th 2024
"""
import logging
import numpy as np

from labscriptlib.connection_table import devices
from labscriptlib.tweezers_phaseAmplitudeAdjustment import trap_phase, trap_amplitude
from labscriptlib.shot_globals import shot_globals

# Note 20230327: can only use one channel for fifo mode for now.

logger = logging.getLogger(__name__)


def dbm_to_vpeak(power):
    # Converts power in dbm to peak voltage (not Vpp or Vrms)
    # r = 50 # Ohms
    exponent = (power - 10) / 20
    return 10**exponent


class SpectrumManagerFifo:
    def __init__(self):
        # current armed waveform (what start_tweezers will start)
        self.x_kwargs = None
        self.x_key = None

        # state flags
        self.started_tw = False
        self.outputting_tw = False

        # cached defaults for tweezers
        self.TW_x_power = 33.2
        self.TW_x_amplitude = 1.0
        self.SpectrumPhase = 0.0  # degrees

        # key counter to avoid "Flexible output key already in use."
        self._key_counter = 0

    # ------------------------
    # Internal helpers
    # ------------------------
    def _new_key(self, prefix="x_fifo"):
        k = f"{prefix}_{self._key_counter}"
        self._key_counter += 1
        return k

    @staticmethod
    def _as_1d_array(x):
        x = np.asarray(x)
        if x.ndim == 0:
            x = x[None]
        return x

    def _tweezer_comb_parameters(self, freqs_MHz, amp_scale=None, base_phase_deg=None):
        """
        For a tweezer comb:
          phases = trap_phase(freqs)
          amps   = amp_scale * trap_amplitude(freqs)
        For a single tone:
          phases = base_phase_deg
          amps   = amp_scale

        Returns (freqs_MHz_array, amps_array, phases_deg_array)
        """
        freqs_MHz = self._as_1d_array(freqs_MHz).astype(float)

        if amp_scale is None:
            amp_scale = float(self.TW_x_amplitude)
        if base_phase_deg is None:
            base_phase_deg = float(self.SpectrumPhase)

        if freqs_MHz.size == 1:
            phases = np.array([base_phase_deg], dtype=float)
            amps = np.array([amp_scale], dtype=float)
        else:
            phases = np.asarray(trap_phase(freqs_MHz), dtype=float) + base_phase_deg
            amps = amp_scale * np.asarray(trap_amplitude(freqs_MHz), dtype=float)

        phases = np.mod(phases, 360.0)
        return freqs_MHz, amps, phases

    def _build_x_kwargs_from_comb(self, freqs_MHz, amps, phases_deg, power_dbm=None, ch=0):
        freqs_MHz = self._as_1d_array(freqs_MHz)
        amps = self._as_1d_array(amps)
        phases_deg = self._as_1d_array(phases_deg)

        if not (len(freqs_MHz) == len(amps) == len(phases_deg)):
            raise ValueError(
                f"freqs/amps/phases length mismatch: {len(freqs_MHz)=}, {len(amps)=}, {len(phases_deg)=}"
            )

        if power_dbm is None:
            power_dbm = float(self.TW_x_power)

        return {
            "freq": freqs_MHz * 1e6,  # Hz
            "output_voltage": dbm_to_vpeak(power_dbm),
            "amplitude": amps,
            "phase": phases_deg,      # degrees (as used in your current code)
            "ch": ch,
        }

    # ------------------------
    # Public tweezer API
    # ------------------------
    def start_tweezer_card(self):
        """
        Configure the spectrum card and arm the DEFAULT tweezer comb from shot_globals.TW_x_freqs.
        Does not start output yet.
        """
        self.started_tw = False
        self.outputting_tw = False
        self._key_counter = 0

        # Default comb frequencies from runmanager globals
        TW_x_freqs = np.asarray(shot_globals.TW_x_freqs)

        # Card configuration (same as your current code)
        devices.spectrum_0.set_mode(
            replay_mode="fifo_single",
            channels=[
                {
                    "name": "Tweezer_X",
                    "power": self.TW_x_power,
                    "port": 0,
                    "is_amplified": True,
                    "amplifier": 1,
                    "calibration_power": 15,
                    "power_mode": "constant_total",
                    "max_pulses": 1,
                },
            ],
            clock_freq=625,
            use_ext_clock=True,
            smart_programming=True,
        )

        # Arm default waveform using the comb calibration logic:
        self.set_tweezer_comb(TW_x_freqs, key="x_fifo_default")

        self.started_tw = True
        return

    def stop_tweezer_card(self):
        if self.outputting_tw:
            raise RuntimeError("SpectrumManager: output must be stopped before card is stopped")
        devices.spectrum_0.stop()

    def set_tweezer_comb(self, freqs_MHz, *, amp_scale=None, base_phase_deg=None,
                         power_dbm=None, ch=0, key=None):
        """
        Arm a tweezer comb (multi-frequency static waveform) so that start_tweezers(t)
        will output THIS comb.
        """
        freqs_MHz, amps, phases = self._tweezer_comb_parameters(
            freqs_MHz,
            amp_scale=amp_scale,
            base_phase_deg=base_phase_deg,
        )
        self.x_kwargs = self._build_x_kwargs_from_comb(freqs_MHz, amps, phases, power_dbm=power_dbm, ch=ch)
        self.x_key = key if key is not None else self._new_key("x_fifo")

    def start_tweezers(self, t):
        if not self.started_tw:
            raise RuntimeError("SpectrumManager: must run start_tweezer_card() before start_tweezers()")
        if self.outputting_tw:
            raise RuntimeError("SpectrumManager: output has already been started")
        if self.x_kwargs is None or self.x_key is None:
            raise RuntimeError("SpectrumManager: call set_tweezer_comb(...) before start_tweezers()")

        devices.spectrum_0.start_flexible_loop(t, devices.spectrum_0.fifo_multi_freq, self.x_key, **self.x_kwargs)
        self.outputting_tw = True
        return t

    def stop_tweezers(self, t):
        if not self.outputting_tw:
            raise ValueError("SpectrumManager: must run start_tweezers() before stop_tweezers()")

        logger.info(f"Ending last static period at time t = {t:.9f}")
        devices.spectrum_0.stop_flexible_loop(t, self.x_key, fifo=True)
        self.outputting_tw = False
        return t

    def switch_tweezer_comb(self, t, freqs_MHz, *, amp_scale=None, base_phase_deg=None,
                            power_dbm=None, ch=0, key=None):
        """
        Switch from the currently-outputting comb to a new comb at exactly time t:
          - old comb ends at t
          - new comb begins at t
        """
        if self.outputting_tw:
            self.stop_tweezers(t)

        self.set_tweezer_comb(
            freqs_MHz,
            amp_scale=amp_scale,
            base_phase_deg=base_phase_deg,
            power_dbm=power_dbm,
            ch=ch,
            key=key,  # usually None -> auto unique key
        )
        self.start_tweezers(t)
        return t

    # ------------------------
    # Rydberg lab functions, but we don't use them for now
    # ------------------------
    # def start_mw_card(self):
    #     raise NotImplementedError("Microwave not implemented in FIFO.")

    # # Note: This function assumes CP used for cubic transport sweep
    # def start_cp_card(self):
    #     self.started_cp = False
    #     self.outputting_cp = False

    #     # set the card mode
    #     # TO DO: Potentially change for FIFO
    #     Spectrum6631.set_mode(
    #         replay_mode=b"fifo_single",
    #         channels=[
    #             {
    #                 "name": "cp_spectrum",
    #                 "power": CP_spectrum_power,
    #                 "port": 0,
    #                 "is_amplified": True,
    #                 "amplifier": 3,
    #                 "power_mode": "constant_total",
    #                 "max_pulses": 1,
    #                 "calibration_power": 15,
    #                 "static_atten": 23,
    #             }
    #         ],
    #         clock_freq=400,
    #         use_ext_clock=True,
    #         export_data=False,
    #         export_path=r"Z:\Experiments\rydberglab",
    #         smart_programming=False,
    #     )
    #     # Estimate min and max frequency based on detuning, distance and duration
    #     self.baseline_freq = (110) * 1e6 + T_cp_relative_freq
    #     max_speed = 1.5 * (T_cp_distance / 100) / T_transportTime
    #     self.peak_freq = 2 * max_speed / 1064e-9 + self.baseline_freq
    #     print(f"Peak frequency is calculated to be : {self.peak_freq}")
    #     self.cp_key = "cp_key"
    #     self.started_cp = True

    #     return

    # # Starts CP output at time t, single frequency. End time tbd by stop_flexible
    # def start_cp(self, t):
    #     assert self.started_cp, "SpectrumManager: must run prepare() before start()"
    #     if CP_spectrum_amplitude < 0 or CP_spectrum_amplitude > 1:
    #         raise LabscriptError("Amplitude must be between 0 and 1")

    #     cp_static_kwargs = {
    #         "freq": self.baseline_freq,
    #         "output_voltage": dbm_to_vpeak(CP_spectrum_power),
    #         "amplitude": CP_spectrum_amplitude,
    #         "phase": 0,
    #         "ch": 0,
    #     }
    #     Spectrum6631.start_flexible_loop(t, Spectrum6631.fifo_single_freq, self.cp_key, **cp_static_kwargs)
    #     self.outputting_cp = True
    #     return t

    # def stop_cp(self, t):
    #     assert self.outputting_cp, "SpectrumManager: must run start() before stop()"
    #     logger.info(f"Ending last static period at time t = {t:.9f}")
    #     Spectrum6631.stop_flexible_loop(t, self.cp_key, fifo=True)
    #     self.outputting_cp = False
    #     return t

    # def quadratic_sweep(self, t):
    #     # Stop static sweep
    #     t = Spectrum6631.stop_flexible_loop(t, self.cp_key, fifo=True)

    #     # Quadratic sweep for transport
    #     cp_quad_kwargs = {
    #         "start_freq": self.baseline_freq,
    #         "peak_freq": self.peak_freq,
    #         "output_voltage": dbm_to_vpeak(CP_spectrum_power),
    #         "amplitude": CP_spectrum_amplitude,
    #         "phase": 0,
    #         "ch": 0,
    #     }
    #     t = Spectrum6631.fifo_quad(t_start=t, total_time=T_transportTime, **cp_quad_kwargs)

    #     # Back to static sweep
    #     cp_static_kwargs = {
    #         "freq": self.baseline_freq,
    #         "output_voltage": dbm_to_vpeak(CP_spectrum_power),
    #         "amplitude": CP_spectrum_amplitude,
    #         "phase": 0,
    #         "ch": 0,
    #     }
    #     Spectrum6631.start_flexible_loop(t, Spectrum6631.fifo_single_freq, self.cp_key, **cp_static_kwargs)
    #     return t

    # def sin_frequency_modulation(self, t):
    #     # Stop static sweep
    #     t = Spectrum6631.stop_flexible_loop(t, self.cp_key, fifo=True)

    #     # Quadratic sweep for transport
    #     cp_sine_kwargs = {
    #         "base_freq": self.baseline_freq,
    #         "mod_freq": CP_mod_freq * 1e3,
    #         "mod_amplitude": CP_mod_amplitude * 1e3,
    #         "output_voltage": dbm_to_vpeak(CP_spectrum_power),
    #         "amplitude": CP_spectrum_amplitude,
    #         "phase": 0,
    #         "ch": 0,
    #     }
    #     t = Spectrum6631.fifo_sin_modulation(t_start=t, total_time=CP_mod_duration, **cp_sine_kwargs)

    #     # Back to static sweep
    #     cp_static_kwargs = {
    #         "freq": self.baseline_freq,
    #         "output_voltage": dbm_to_vpeak(CP_spectrum_power),
    #         "amplitude": CP_spectrum_amplitude,
    #         "phase": 0,
    #         "ch": 0,
    #     }
    #     Spectrum6631.start_flexible_loop(t, Spectrum6631.fifo_single_freq, self.cp_key, **cp_static_kwargs)
    #     return t

    # def stop_cp_card(self, t):
    #     assert not self.outputting_cp, "SpectrumManager: output must be stopped before card is stopped"
    #     Spectrum6631.stop()

    # def start_dummy_mw(self, t):
    #     self.x_kwargs = {
    #         "duration": SpectrumDuration,
    #         "freqs": TW_x_freqs * 1e6,
    #         "amplitudes": TW_x_amps,
    #         "phases": TW_x_phases,
    #         "ch": 0,
    #     }
    #     self.x_key = "x_comb"

    # def spectrum_pulse(self, t, freq, duration, delay=0, microwave_start_time=0, phase=0, loops=1,
    #                    mw_switch=False, switch_delay=0):
    #     """
    #     Schedule a fixed frequency pulse at time t
    #     freq: frequency of the pulse in MHz
    #     duration: Length of the pulse in s
    #     delay: Delay
    #     """
    #     t += delay
    #     print(f"Requested frequency is {freq}")
    #     global_phase = 360 * freq * (t - switch_delay - microwave_start_time)
    #     global_phase = np.mod(global_phase, 360)
    #     phase_final = np.mod(phase + global_phase, 360)

    #     Spectrum6631.single_freq(
    #         t - switch_delay, duration + switch_delay, freq,
    #         S_6631_0_amplitude, phase_final, 0, loops
    #     )

    #     if mw_switch:
    #         MicrowaveSwitch.go_high(t)

    #     dt = duration * loops
    #     t += max(dt, 0)

    #     if mw_switch:
    #         MicrowaveSwitch.go_low(t)

    #     return t

    # def spectrum_sweep(self, t, freq_start, freq_end, duration, delay=0, phase=0, loops=1,
    #                    ramp_type="linear", mw_switch=False):
    #     t += delay

    #     if mw_switch:
    #         MicrowaveSwitch.go_high(t)

    #     Spectrum6631.sweep(t, duration, freq_start, freq_end, S_6631_0_amplitude, phase, 0, ramp_type, loops=loops)

    #     dt = duration * loops
    #     t += max(dt, 0)

    #     if mw_switch:
    #         MicrowaveSwitch.go_low(t)

    #     return t


spectrum_manager_fifo = SpectrumManagerFifo()
