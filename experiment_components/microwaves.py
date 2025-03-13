from typing import ClassVar

from labscriptlib.calibration import spec_freq_calib
from labscriptlib.connection_table import devices


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

    def __init__(self, t, init_detuning):
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

        # spectrum setup for microwaves & mmwaves, 1st channel for
        # Hyperfine splitting of ground state, 2nd channel for mmwaves on Rydberg levels
        devices.spectrum_uwave.set_mode(
            replay_mode=b"sequence",
            channels=[
                {
                    "name": "microwaves",
                    "power": self.spectrum_uwave_power
                    + self.CONST_SPECTRUM_UWAVE_CABLE_ATTEN,
                    "port": 0,
                    "is_amplified": False,
                    "amplifier": None,
                    "calibration_power": 12,
                    "power_mode": "constant_total",
                    "max_pulses": 1,
                },
                {
                    "name": "mmwaves",
                    "power": -11,
                    "port": 1,
                    "is_amplified": False,
                    "amplifier": None,
                    "calibration_power": 12,
                    "power_mode": "constant_total",
                    "max_pulses": 1,
                },
            ],
            clock_freq=625,
            use_ext_clock=True,
            ext_clock_freq=10,
        )

    def do_pulse(self, t, dur):
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
        devices.spectrum_uwave.single_freq(
            t - self.CONST_SPECTRUM_CARD_OFFSET,
            duration=dur,
            freq=spec_freq_calib(self.mw_detuning),
            amplitude=0.99,  # the amplitude can not be 1 due to the bug in spectrum card server
            phase=0,  # initial phase = 0
            ch=0,  # using channel 0
            loops=1,  # doing 1 loop
        )

        t += dur
        devices.uwave_absorp_switch.go_low(t)
        self.uwave_absorp_switch_on = False

        return t

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
        )  # dummy segment
        devices.spectrum_uwave.stop()

        return t
