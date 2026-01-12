from pathlib import Path
from typing import ClassVar, Optional

from labscript import compiler as ls_compiler
from labscriptlib.calibration import spec_freq_calib
from labscriptlib.connection_table import devices
from labscriptlib.shot_globals import shot_globals
import numpy as np


class Microwave:
    """Controls for microwave wave generation and manipulation.

    This class manages the microwave system used for driving transitions between hyperfine
    states and Rydberg levels. It handles both single-frequency pulses and frequency sweeps
    using a spectrum card, and includes controls for switches and power levels.

    Attributes:
        CONST_SPECTRUM_CARD_OFFSET (float): Delay time between spectrum card output and trigger (52.8µs)
        CONST_SPECTRUM_UWAVE_CABLE_ATTEN (float): Attenuation in dB for the microwave output at 300 MHz (4.4)
    """

    CONST_SPECTRUM_CARD_OFFSET: ClassVar[float] = 52.8e-6
    CONST_SPECTRUM_UWAVE_CABLE_ATTEN: ClassVar[float] = 4.4

    def __init__(self, t, init_detuning, init_mmwave_detuning):
        """Initialize the microwave system.

        Sets up the spectrum card configuration for microwave
        channels, including power levels, clock settings, and switch states.

        Parameters
        ----------
        t: float
            Time to initialize the microwave system
        initial_detuning: float
            Initial detuning of the microwave frequency from the cesium clock transition, in MHz
        """

        self.mw_detuning = init_detuning
        self.mmwave_spcm_freq = init_mmwave_detuning
        self.uwave_dds_switch_on = True
        self.uwave_absorp_switch_on = False
        self.spectrum_uwave_power = -1
        # dBm power set at the input of dds switch, this power is set
        # to below the amplifier damage threshold
        devices.uwave_dds_switch.go_high(t)
        # dds_switch always on, can be off if need further higher
        # extinction ratio
        devices.uwave_absorp_switch.go_low(
            t
        )  # absorp switch only on when sending pulse
        devices.mmwave_switch.go_high(t)

        hdf5_path = Path(ls_compiler.hdf5_filename)

        # spectrum setup for microwaves & mmwaves
        # Channel 0 for 9.2 GHz microwaves (lower-sideband mixed with ~9.4 GHz LO)
        # Channel 1 for mm-waves (upper-sideband mixed with mm-wave LO)
        devices.spectrum_uwave.set_mode(
            replay_mode="sequence",
            channels=[
                {
                    "name": "microwaves",
                    "power": self.spectrum_uwave_power + self.CONST_SPECTRUM_UWAVE_CABLE_ATTEN,
                    "port": 0,
                    "is_amplified": False,
                    "amplifier": None,
                    "calibration_power": 12,
                    "power_mode": "constant_total",
                    "max_pulses": 1,
                },
                {
                    "name": "mmwaves",
                    "power": 16,
                    "port": 1,
                    "is_amplified": False,
                    "amplifier": None,
                    "calibration_power": 12,
                    "power_mode": "constant_total",
                    "max_pulses": 1,
                },
            ],
            clock_freq=1250,
            use_ext_clock=True,
            ext_clock_freq=10,
            export_data=shot_globals.mmwave_export_spectrum_segments,
            export_path=str(hdf5_path.parent),
        )

    def do_pulse(self, t, dur, detuning: Optional[float] = None):
        """Generate a single-frequency microwave pulse.

        Produces a microwave pulse at the current detuning frequency with specified duration.
        Handles timing offsets and switch control automatically.

        Args:
            t (float): Start time for the pulse
            dur (float): Duration of the pulse
            detuning (float, optional):
                Detuning of the pulse from the cesium clock transition, in MHz.
                Defaults to default detuning of this object if not specified.

        Returns:
            float: End time after the pulse is complete
        """
        t += self.CONST_SPECTRUM_CARD_OFFSET
        devices.uwave_absorp_switch.go_high(t)
        self.uwave_absorp_switch_on = True

        pulse_detuning = self.mw_detuning if detuning is None else detuning
        devices.spectrum_uwave.single_freq(
            t - self.CONST_SPECTRUM_CARD_OFFSET,
            duration=dur,
            freq=spec_freq_calib(pulse_detuning),
            amplitude=0.99,  # the amplitude cannot be 1 due to bug in spectrum card server
            phase=0,  # initial phase = 0
            ch=0,
            loops=1,
        )

        t += dur
        devices.uwave_absorp_switch.go_low(t)
        self.uwave_absorp_switch_on = False

        return t
    
    def do_mmwave_pulse(
            self,
            t0: float,
            duration: float,
            detuning: Optional[list] = None,
            phase: Optional[list] = None,
            keep_switch_on: bool = False,
            switch_offset: float = 0
    ):
        """Generate a single-frequency microwave pulse.

        Produces a microwave pulse at the current detuning frequency with specified duration.
        Handles timing offsets and switch control automatically.

        The output IF waveform will be of the form cos(phase + omega * (t - t0)).

        Parameters
        ----------
        t0: float
            Start time for the pulse
        dur: float
            Duration of the pulse
        detuning: float, optional
            Output frequency (IF) from the Spectrum card, in Hz.
            The final mm-wave frequency is then mm-wave LO frequency + IF frequency
        phase: float
            Phase of the waveform at the beginning of the pulse, in degrees.
            For phase coherence between pulses, one must manually compute
            the accumulated phase between the pulses.

        Returns
        -------
        float
            End time of the pulse
        """
        def ensure_list(param):
            if np.isscalar(param):
                return [param]
            else:
                return list(param)
            
        turn_on_buffer_time = shot_globals.mmwave_switch_turn_on_buffer_time #1.15e-6 #0.75e-6
        turn_off_buffer_time = 0.1e-6
        switch_spectrum_offset = switch_offset + 2.5e-7
        devices.mmwave_switch.go_low(t0 + switch_spectrum_offset - turn_on_buffer_time)
        self.mmwave_switch_on = True

        pulse_detuning = self.mmwave_spcm_freq if detuning is None else detuning
        pulse_detuning = ensure_list(pulse_detuning)
        phase = [0]*len(pulse_detuning) if phase is None else phase
        if len(pulse_detuning) == 1:
            amplitude = 0.965
        elif len(pulse_detuning) == 2:
            amplitude = [0.5,0.5]
        else:
            raise ValueError("This function cannot handle more than two tones now. Need optimized phases and duration for that. ")
    
        if shot_globals.do_mmwave_pulse:
            devices.spectrum_uwave.comb(
                t0,
                duration=duration,
                freqs=pulse_detuning,
                amplitudes= ensure_list(amplitude),#0.965,#0.98,  # the amplitude cannot be 1 due to bug in spectrum card server, at most 0.99
                phases= ensure_list(phase),
                ch=1,
                loops=1,
            )

        t0 += duration
        if not keep_switch_on:
            devices.mmwave_switch.go_high(t0 + switch_spectrum_offset + turn_off_buffer_time)
            self.mmwave_switch_on = False

        return t0

    # TODO: This function is not tested yet
    def do_ramsey_pulse(self, t, dur, dur_between_pulse):
        """Generate a single-frequency microwave pulse.

        Produces a microwave pulse at the current detuning frequency with specified duration.
        Handles timing offsets and switch control automatically.

        Args:
            t (float): Start time for the pulse
            dur (float): Duration of the pulse

        Returns:
            float: End time after the pulse is complete
        """
        t += self.CONST_SPECTRUM_CARD_OFFSET
        devices.uwave_absorp_switch.go_high(t)
        self.uwave_absorp_switch_on = True

        total_dur = dur + dur_between_pulse
        devices.spectrum_uwave.single_freq(
            t - self.CONST_SPECTRUM_CARD_OFFSET,
            duration=total_dur,
            freq=spec_freq_calib(self.mw_detuning),
            amplitude=0.99,  # the amplitude can not be 1 due to the bug in spectrum card server
            phase=0,  # initial phase = 0
            ch=0,  # using channel 0
            loops=1,  # doing 1 loop
        )

        t += dur/2
        devices.uwave_absorp_switch.go_low(t)

        t += dur_between_pulse
        devices.uwave_absorp_switch.go_high(t)

        t += dur/2
        devices.uwave_absorp_switch.go_low(t)
        self.uwave_absorp_switch_on = False

        return t

    def do_sweep(self, t, start_freq, end_freq, dur):
        """Perform a frequency sweep of the microwave signal.

        Generates a linear frequency sweep between specified start and end frequencies.
        Controls switches and timing for proper sweep execution.

        Args:
            t (float): Start time for the sweep
            start_freq (float): Starting frequency for the sweep
            end_freq (float): Ending frequency for the sweep
            dur (float): Duration of the sweep

        Returns:
            float: End time after the sweep is complete
        """
        # print("I'm doing microwave sweep")
        t += self.CONST_SPECTRUM_CARD_OFFSET
        devices.uwave_absorp_switch.go_high(t)
        self.uwave_absorp_switch_on = True
        devices.spectrum_uwave.sweep(
            t - self.CONST_SPECTRUM_CARD_OFFSET,
            duration=dur,
            start_freq=spec_freq_calib(start_freq),
            end_freq=spec_freq_calib(end_freq),
            amplitude=0.99,  # the amplitude can not be 1 due to the bug in spectrum card server
            phase=0,  # initial phase = 0
            ch=0,  # using channel 0
            loops=1,  # doing 1 loop
            freq_ramp_type = "linear",
        )

        t += dur
        devices.uwave_absorp_switch.go_low(t)
        self.uwave_absorp_switch_on = False

        return t

    def reset_spectrum(self, t):
        """Reset the spectrum card by sending a dummy segment.

        Due to spectrum card behavior, two pulses are required to properly stop
        the card. This method sends a dummy segment and stops the card.

        Args:
            t (float): Time to perform the reset

        Returns:
            float: End time after reset is complete
        """
        # dummy segment ####
        devices.spectrum_uwave.single_freq(
            t, duration=100e-6, freq=10**6, amplitude=0.99, phase=0, ch=0, loops=1
        )
        devices.spectrum_uwave.single_freq(
            t, duration=100e-6, freq=10**6, amplitude=0.99, phase=0, ch=1, loops=1
        )
        # dummy segment
        devices.spectrum_uwave.stop()

        return t
