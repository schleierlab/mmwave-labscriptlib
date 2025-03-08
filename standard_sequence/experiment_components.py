from __future__ import annotations

from enum import Flag, auto
from typing import ClassVar, Literal

import labscript
import numpy as np
from labscript import AnalogOut, DigitalOut

from calibration import (
    biasx_calib,
    biasy_calib,
    biasz_calib,
    repump_freq_calib,
    spec_freq_calib,
    ta_freq_calib,
)
from connection_table import devices
from labscriptlib.shot_globals import shot_globals
from spectrum_manager import spectrum_manager

# from shot_globals import shot_globals
# from spectrum_manager_fifo import spectrum_manager_fifo


class ShutterConfig(Flag):
    """Configuration flags for controlling various shutters in the experimental setup.

    This class uses Flag enumeration to represent different shutter configurations that can be
    combined using bitwise operations. Each configuration represents a specific combination of
    shutters for different experimental phases like MOT operation, imaging, and optical pumping.

    Attributes:
        NONE (Flag): No shutters active
        TA (Flag): Tapered Amplifier shutter
        REPUMP (Flag): Repump laser shutter
        MOT_XY (Flag): MOT beams in XY plane shutter
        MOT_Z (Flag): MOT beam in Z direction shutter
        IMG_XY (Flag): Imaging beams in XY plane shutter
        IMG_Z (Flag): Imaging beam in Z direction shutter
        OPTICAL_PUMPING (Flag): Optical pumping beam shutter

        Combinations:
        UPSTREAM: Combined TA and REPUMP shutters
        MOT_FULL: All MOT-related shutters (UPSTREAM | MOT_XY | MOT_Z)
        MOT_TA: TA and MOT directional shutters
        MOT_REPUMP: Repump and MOT directional shutters
        IMG_FULL: All imaging-related shutters
        IMG_TA: TA and imaging directional shutters
        IMG_REPUMP: Repump and imaging directional shutters
        OPTICAL_PUMPING_FULL: All optical pumping shutters
        OPTICAL_PUMPING_TA: TA and optical pumping shutters
        OPTICAL_PUMPING_REPUMP: Repump and optical pumping shutters
    """
    NONE = 0

    TA = auto()
    REPUMP = auto()
    MOT_XY = auto()
    MOT_Z = auto()
    IMG_XY = auto()
    IMG_Z = auto()
    OPTICAL_PUMPING = auto()

    UPSTREAM = TA | REPUMP
    MOT_FULL = UPSTREAM | MOT_XY | MOT_Z
    MOT_TA = TA | MOT_XY | MOT_Z
    MOT_REPUMP = REPUMP | MOT_XY | MOT_Z

    IMG_FULL = UPSTREAM | IMG_XY | IMG_Z
    IMG_TA = TA | IMG_XY | IMG_Z
    IMG_REPUMP = REPUMP | IMG_XY | IMG_Z

    OPTICAL_PUMPING_FULL = UPSTREAM | OPTICAL_PUMPING
    OPTICAL_PUMPING_TA = TA | OPTICAL_PUMPING
    OPTICAL_PUMPING_REPUMP = REPUMP | OPTICAL_PUMPING

    @classmethod
    def select_imaging_shutters(cls, do_repump=True) -> ShutterConfig:
        repump_config = cls.REPUMP if do_repump else cls.NONE
        # print("Repump_config = ", repump_config)
        label = shot_globals.imaging_label

        # TODO: change handling of labels to make full default and raise error when not one of the options
        if shot_globals.do_mot_beams_during_imaging:
            if label == "z":
                shutter_config = cls.MOT_Z | cls.TA | repump_config
            elif label == "xy":
                shutter_config = cls.MOT_XY | cls.TA | repump_config
            else:
                shutter_config = cls.MOT_TA | repump_config

        # If you're trying to do in-situ imaging, you want to image faster than switch shutters allows for,
        # so you can't do imaging beam imaging
        elif (
            shot_globals.do_img_beams_during_imaging
            and not shot_globals.do_molasses_in_situ_check
        ):
            if label == "z":
                shutter_config = cls.IMG_Z | cls.TA | repump_config
            elif label == "xy":
                shutter_config = cls.IMG_XY | cls.TA | repump_config
            else:
                shutter_config = cls.IMG_TA | repump_config

        else:
            shutter_config = cls.NONE

        # print("Shutter config = ", shutter_config)
        return shutter_config


# Hardware control classes
# -------------------------------------------------------------------------------
class D2Lasers:
    """Controls for D2 transition lasers including Tapered Amplifier (TA) and repump lasers.

    This class manages the frequency, power, and shutter configurations for D2 transition lasers
    used in the experiment. It provides methods for ramping frequencies, controlling AOMs, and
    managing shutter configurations.

    Attributes:
        CONST_TA_VCO_RAMP_TIME (float): Minimal TA VCO ramp time to maintain beatnote lock (1.2e-4 s)
        CONST_SHUTTER_TURN_OFF_TIME (float): Time for shutter to fully close (2e-3 s)
        CONST_SHUTTER_TURN_ON_TIME (float): Time for shutter to fully open (2e-3 s)
        CONST_MIN_SHUTTER_OFF_TIME (float): Minimum time for shutter off-on cycle (6.28e-3 s)
        CONST_MIN_SHUTTER_ON_TIME (float): Minimum time for shutter to stay on (3.6e-3 s)
    """
    shutter_config: ShutterConfig

    CONST_TA_VCO_RAMP_TIME: ClassVar[float] = (
        1.2e-4
    )
    CONST_SHUTTER_TURN_OFF_TIME: ClassVar[float] = (
        2e-3  # for shutter take from start to open to fully close
    )
    CONST_SHUTTER_TURN_ON_TIME: ClassVar[float] = (
        2e-3  # for shutter take from start to close to fully open
    )

    CONST_MIN_SHUTTER_OFF_TIME: ClassVar[float] = (
        6.28e-3  # minimum time for shutter to be off and on again
    )
    CONST_MIN_SHUTTER_ON_TIME: ClassVar[float] = (
        3.6e-3  # minimum time for shutter to be on
    )


    # Can we put this somewhere nicer?

    def __init__(self, t):
        """Initialize the D2 laser system.

        Sets up initial frequencies and powers for MOT operation, initializes shutter
        configuration, and configures hardware devices.

        Args:
            t (float): Time to start the D2 laser system
        """
        # Tune to MOT frequency, full power
        self.ta_freq = shot_globals.mot_ta_detuning
        self.repump_freq = 0  # shot_globals.mot_repump_detuning
        self.ta_power = shot_globals.mot_ta_power
        self.repump_power = shot_globals.mot_repump_power
        # update_shutters compares with self.shutter_config to decide what
        # changes to make. Do not call self.update_shutters(self.shutter_config),
        # nothing will happen.
        self.shutter_config = ShutterConfig.NONE
        self.last_shutter_open_t = np.zeros(7)
        self.last_shutter_close_t = np.zeros(7)
        _ = self.update_shutters(t + D2Lasers.CONST_SHUTTER_TURN_ON_TIME, ShutterConfig.MOT_FULL)

        # If do_mot is the first thing that is called, these initializations
        # produce a warning in the runmanager output because the MOT powers
        # and frequencies are set twice.
        devices.ta_vco.constant(t, ta_freq_calib(self.ta_freq))
        devices.repump_vco.constant(t, repump_freq_calib(self.repump_freq))
        devices.ta_aom_analog.constant(t, self.ta_power)
        devices.repump_aom_analog.constant(t, self.repump_power)

    def ramp_ta_freq(self, t, duration, final):
        """Ramp the TA laser frequency from current to final value.

        The ramp duration will be at least CONST_TA_VCO_RAMP_TIME to maintain
        beatnote lock. If current and final frequencies are the same, no ramp
        is performed.

        Args:
            t (float): Start time for the frequency ramp
            duration (float): Desired duration of the ramp
            final (float): Target frequency detuning in MHz

        Returns:
            float: End time of the ramp
        """
        # TODO: check that duration statement here is valid for optical pumping
        if self.ta_freq == final:
            print("ta freq is same for initial and final, skip ramp")
            return t
        else:
            duration = max(self.CONST_TA_VCO_RAMP_TIME, duration)
            devices.ta_vco.ramp(
                t,
                duration=duration,
                initial=ta_freq_calib(self.ta_freq),
                final=ta_freq_calib(final),
                samplerate=4e5,
            )
            self.ta_freq = final
            return t + duration

    def ramp_repump_freq(self, t, duration, final):
        """Ramp the repump laser frequency from current to final value.

        The ramp duration will be at least CONST_TA_VCO_RAMP_TIME to maintain
        beatnote lock. If current and final frequencies are the same, no ramp
        is performed.

        Args:
            t (float): Start time for the frequency ramp
            duration (float): Desired duration of the ramp
            final (float): Target frequency detuning in MHz

        Returns:
            float: End time of the ramp
        """
        # TODO: check that duration statement here is valid for optical pumping
        if self.repump_freq == final:
            print("repump freq is same for initial and final, skip ramp")
            return t
        else:
            duration = max(self.CONST_TA_VCO_RAMP_TIME, duration)
            devices.repump_vco.ramp(
                t,
                duration=duration,
                initial=repump_freq_calib(self.repump_freq),
                final=repump_freq_calib(final),
                samplerate=4e5,
            )
            self.repump_freq = final
            return t + duration

    def ta_aom_off(self, t):
        """Turn off the TA beam using AOM.

        Disables both digital and analog controls of the TA AOM to ensure
        complete beam extinction.

        Args:
            t (float): Time to turn off the AOM
        """
        devices.ta_aom_digital.go_low(t)  # digital off
        devices.ta_aom_analog.constant(t, 0)  # analog off
        self.ta_power = 0

    def ta_aom_on(self, t, const):
        """Turn on the TA beam using AOM.

        Enables both digital and analog controls of the TA AOM to activate
        the beam at specified power.

        Args:
            t (float): Time to turn on the AOM
            const (float): Power level for the AOM (0 to 1)
        """
        devices.ta_aom_digital.go_high(t)  # digital on
        devices.ta_aom_analog.constant(t, const)  # analog to const
        self.ta_power = const

    def repump_aom_off(self, t):
        """Turn off the repump beam using AOM.

        Disables both digital and analog controls of the repump AOM to ensure
        complete beam extinction.

        Args:
            t (float): Time to turn off the AOM
        """
        devices.repump_aom_digital.go_low(t)  # digital off
        devices.repump_aom_analog.constant(t, 0)  # analog off
        self.repump_power = 0

    def repump_aom_on(self, t, const):
        """Turn on the repump beam using AOM.

        Enables both digital and analog controls of the repump AOM to activate
        the beam at specified power.

        Args:
            t (float): Time to turn on the AOM
            const (float): Power level for the AOM (0 to 1)
        """
        devices.repump_aom_digital.go_high(t)  # digital on
        devices.repump_aom_analog.constant(t, const)  # analog to const
        self.repump_power = const

    def ramp_ta_aom(self, t, dur, final_power):
        """Ramp the TA AOM power from current to final value.

        Performs a smooth power ramp of the TA beam using the AOM.

        Args:
            t (float): Start time for the power ramp
            dur (float): Duration of the ramp
            final_power (float): Target power level (0 to 1)

        Returns:
            float: End time of the ramp
        """
        devices.ta_aom_analog.ramp(
            t,
            duration=dur,
            initial=self.ta_power,
            final=final_power,
            samplerate=1e5,
        )

    def ramp_repump_aom(self, t, dur, final_power):
        """Ramp the repump AOM power from current to final value.

        Performs a smooth power ramp of the repump beam using the AOM.

        Args:
            t (float): Start time for the power ramp
            dur (float): Duration of the ramp
            final_power (float): Target power level (0 to 1)

        Returns:
            float: End time of the ramp
        """
        devices.repump_aom_analog.ramp(
            t,
            duration=dur,
            initial=self.repump_power,
            final=final_power,
            samplerate=1e5,
        )

    def update_shutters(self, t, new_shutter_config: ShutterConfig):
        """Update the shutter configuration of the laser system.

        Manages the opening and closing of various shutters based on the new configuration.
        Ensures proper timing between shutter operations to maintain system stability.

        Args:
            t (float): Time to update the shutter configuration
            new_shutter_config (ShutterConfig): New shutter configuration to apply

        Returns:
            float: Updated time after all shutter operations are complete
        """
        basic_shutters: list[ShutterConfig] = [
            ShutterConfig.TA,
            ShutterConfig.REPUMP,
            ShutterConfig.MOT_XY,
            ShutterConfig.MOT_Z,
            ShutterConfig.IMG_XY,
            ShutterConfig.IMG_Z,
            ShutterConfig.OPTICAL_PUMPING,
        ]

        shutter_dict: dict[ShutterConfig, labscript.Shutter] = {
            ShutterConfig.TA: devices.ta_shutter,
            ShutterConfig.REPUMP: devices.repump_shutter,
            ShutterConfig.MOT_XY: devices.mot_xy_shutter,
            ShutterConfig.MOT_Z: devices.mot_z_shutter,
            ShutterConfig.IMG_XY: devices.img_xy_shutter,
            ShutterConfig.IMG_Z: devices.img_z_shutter,
            ShutterConfig.OPTICAL_PUMPING: devices.optical_pump_shutter,
        }

        changed_shutters = self.shutter_config ^ new_shutter_config

        shutters_to_open = changed_shutters & new_shutter_config
        open_bool_list = [(shutter in shutters_to_open) for shutter in basic_shutters]
        shutters_to_close = changed_shutters & self.shutter_config
        close_bool_list = [(shutter in shutters_to_close) for shutter in basic_shutters]

        # if the last shutter is closed and now needs to be opened, open it after CONST_MIN_SHUTTER_OFF_TIME
        if any(t - self.last_shutter_close_t * open_bool_list < self.CONST_MIN_SHUTTER_OFF_TIME):
            t = max(self.last_shutter_close_t * open_bool_list) + self.CONST_MIN_SHUTTER_OFF_TIME
        # if the last shutter is opened and now needs to be closed, close it after CONST_MIN_SHUTTER_ON_TIME
        elif any (t - self.last_shutter_open_t * close_bool_list < self.CONST_MIN_SHUTTER_ON_TIME):
            t = max(self.last_shutter_open_t * close_bool_list) + self.CONST_MIN_SHUTTER_ON_TIME + self.CONST_SHUTTER_TURN_OFF_TIME

        for shutter in basic_shutters:
            if shutter in shutters_to_open:
                shutter_dict[shutter].open(t)
                # record the last time the shutter was opened
                self.last_shutter_open_t[basic_shutters.index(shutter)] = t
            if shutter in shutters_to_close:
                shutter_dict[shutter].close(t - self.CONST_SHUTTER_TURN_OFF_TIME)
                # record the last time the shutter was closed
                self.last_shutter_close_t[basic_shutters.index(shutter)] = t - self.CONST_SHUTTER_TURN_OFF_TIME

        self.shutter_config = new_shutter_config
        return t

    def do_pulse(
        self, t, dur, shutter_config, ta_power, repump_power, close_all_shutters=False
    ):
        """Perform a laser pulse with specified parameters.

        Executes a laser pulse by configuring shutters and AOM powers. Can optionally
        close all shutters after the pulse.

        Args:
            t (float): Start time for the pulse
            dur (float): Duration of the pulse
            shutter_config (ShutterConfig): Shutter configuration for the pulse
            ta_power (float): Power level for the TA beam (0 to 1)
            repump_power (float): Power level for the repump beam (0 to 1)
            close_all_shutters (bool, optional): Whether to close all shutters after pulse. Defaults to False.

        Returns:
            tuple[float, float]: (End time after pulse and shutter operations, AOM start time)
        """
        change_shutters = self.shutter_config != shutter_config

        if change_shutters:
            # NOTE: Adding this to t makes it so it doesn't cut the previous pulse
            # short, but rather shifts the time of the next pulse.
            t += self.CONST_SHUTTER_TURN_ON_TIME
            # print("shutter config changed, adding time to account for switching")
            # print("shutter config:", shutter_config, ", t:", t)
            t = self.update_shutters(t, shutter_config)
            # print("****shutter config:", shutter_config, ", t:", t)

            self.ta_aom_off(t - self.CONST_SHUTTER_TURN_ON_TIME)
            self.repump_aom_off(t - self.CONST_SHUTTER_TURN_ON_TIME)

        if ta_power != 0:
            self.ta_aom_on(t, ta_power)
            self.ta_power = ta_power
        if repump_power != 0:
            self.repump_aom_on(t, repump_power)
            self.repump_power = repump_power

        t_aom_start = t
        t += dur
        self.ta_aom_off(t)
        self.repump_aom_off(t)
        # Remember that even if you don't close the shutters, the beam will turn off
        # at the end of the pulse duration. Plan accordingly and don't leave long wait
        # times between pulses accidentally.

        # If doing close_all_shutters, have to make sure that we aren't opening any of the ones we just closed in the next pulse.
        # Otherwise they won't be able to open in time unless there's enough delay between pulses.
        if close_all_shutters:
            # print("closing all shutters")
            t += self.CONST_SHUTTER_TURN_OFF_TIME
            t = self.update_shutters(t, ShutterConfig.NONE)
            self.ta_aom_on(t, 1)
            self.repump_aom_on(t, 1)

        return t, t_aom_start

    def reset_to_mot_freq(self, t):
        """Reset laser frequencies to MOT operation values.

        Ramps both TA and repump laser frequencies back to their MOT operation values.

        Args:
            t (float): Start time for the frequency reset

        Returns:
            float: End time after frequency ramps are complete
        """
        self.ramp_repump_freq(t, duration=self.CONST_TA_VCO_RAMP_TIME, final=0)
        self.ramp_ta_freq(
            t, duration=self.CONST_TA_VCO_RAMP_TIME, final=shot_globals.mot_ta_detuning
        )
        t += self.CONST_TA_VCO_RAMP_TIME
        return t

    def reset_to_mot_on(self, t):
        """Reset the laser system to MOT operation state.

        Configures shutters and powers for MOT operation and ensures proper timing.

        Args:
            t (float): Start time for the MOT reset

        Returns:
            float: End time after reset operations are complete
        """
        self.ta_aom_on(t, shot_globals.mot_ta_power)
        self.repump_aom_on(t, shot_globals.mot_repump_power)
        t = self.update_shutters(t, ShutterConfig.MOT_FULL)
        t += self.CONST_SHUTTER_TURN_ON_TIME

        return t

    def parity_projection_pulse(self, t, dur, close_all_shutters=False):
        """Execute a parity projection pulse sequence.

        Performs a specialized pulse sequence for parity projection measurements,
        using specific shutter configurations and power levels.

        Args:
            t (float): Start time for the parity projection pulse
            dur (float): Duration of the pulse
            close_all_shutters (bool, optional): Whether to close all shutters after pulse. Defaults to False.

        Returns:
            tuple[float, float]: (End time after pulse sequence, AOM start time)
        """
        self.ramp_ta_freq(
            t,
            duration=self.CONST_TA_VCO_RAMP_TIME,
            final=shot_globals.bm_parity_projection_ta_detuning,
        )  # fixed the ramp duration for the parity projection
        t += self.CONST_TA_VCO_RAMP_TIME
        t, t_aom_start = self.do_pulse(
            t,
            dur,
            ShutterConfig.MOT_TA,
            shot_globals.bm_parity_projection_ta_power,
            0,
            close_all_shutters=close_all_shutters,
        )
        return t, t_aom_start


class TweezerLaser:
    """Controls for the optical tweezer laser system.

    This class manages the optical tweezer laser system, including power control,
    intensity servo operation, and modulation capabilities.

    Attributes:
        CONST_TWEEZER_RAMPING_TIME (float): Standard ramping time for tweezer power changes (10e-3 s)
    """

    CONST_TWEEZER_RAMPING_TIME: ClassVar[float] = 10e-3

    def __init__(self, t):
        """Initialize the tweezer laser system.

        Args:
            t (float): Time to start the tweezers
        """
        self.tw_power = shot_globals.tw_power

        # self.intensity_servo_keep_on(t)
        self.start_tweezers(t)

    def start_tweezers(self, t):
        """Initialize and start the optical tweezer system.

        Args:
            t (float): Time to start the tweezers
        """
        assert shot_globals.do_sequence_mode, "shot_globals.do_sequence_mode is False, running Fifo mode now. Set to True for sequence mode"
        spectrum_manager.start_card()
        t1 = spectrum_manager.start_tweezers(t)
        # print("tweezer start time:", t1)
        self.aom_on(t, self.tw_power)

    def stop_tweezers(self, t):
        """Safely stop and power down the optical tweezer system.

        Args:
            t (float): Time to stop the tweezers
        """
        # stop tweezers
        t2 = spectrum_manager.stop_tweezers(t)
        # print("tweezer stop time:", t2)

        # dummy segment, need this to stop tweezers due to spectrum card bug
        t1 = spectrum_manager.start_tweezers(t)
        # print("tweezer start time:", t1)
        t += 2e-3
        t2 = spectrum_manager.stop_tweezers(t)
        # print("tweezer stop time:", t2)
        spectrum_manager.stop_card(t)
        # print("tweezers have been stopped... for good...")
        return t

    def intensity_servo_keep_on(self, t):
        """Maintain the intensity servo in active state.

        Args:
            t (float): Time to ensure servo remains active
        """
        """keep the AOM digital high for intensity servo"""
        self.aom_on(t, 1)

    def aom_on(self, t, const, digital_only = False):
        """Turn on the tweezer beam using AOM.

        Args:
            t (float): Time to turn on the AOM
            const (float): Power level for the AOM
        """
        """Turn on the tweezer beam using aom"""
        devices.tweezer_aom_digital.go_high(t)  # digital on
        if not digital_only:
            devices.tweezer_aom_analog.constant(t, const)  # analog on
            self.tw_power = const

    def aom_off(self, t, digital_only = False):
        """Turn off the tweezer beam using AOM.

        Args:
            t (float): Time to turn off the AOM
        """
        """Turn off the tweezer beam using aom"""
        devices.tweezer_aom_digital.go_low(t)  # digital off
        if not digital_only:
            devices.tweezer_aom_analog.constant(t, 0)  # analog off
            self.tw_power = 0

    def ramp_power(self, t, dur, final_power):
        """Ramp the tweezer power from current to final value.

        Args:
            t (float): Start time for the power ramp
            dur (float): Duration of the ramp
            final_power (float): Target power level

        Returns:
            float: End time of the ramp
        """
        devices.tweezer_aom_analog.ramp(
            t, duration=dur, initial=self.tw_power, final=final_power, samplerate=1e5
        )
        self.tw_power = final_power
        return t + dur

    def sine_mod_power(self, t, dur, amp, freq):
        """Apply sinusoidal modulation to the tweezer power.

        Args:
            t (float): Start time for modulation
            dur (float): Duration of modulation
            amp (float): Amplitude of the modulation
            freq (float): Frequency of the modulation in Hz
        """
        devices.tweezer_aom_analog.sine(
            t,
            duration=dur,
            amplitude=amp,
            angfreq=2 * np.pi * freq,
            phase=0,
            dc_offset=self.tw_power,
            samplerate=1e5,
        )


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

    def __init__(self, t):
        """Initialize the microwave system.

        Sets up the spectrum card configuration for microwave
        channels, including power levels, clock settings, and switch states.

        Args:
            t (float): Time to initialize the microwave system
        """

        self.mw_detuning = shot_globals.mw_detuning  # tune the microwave detuning here
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



class RydLasers:
    """Controls for Rydberg excitation lasers (456nm and 1064nm).

    This class manages the laser systems used for Rydberg excitation, including
    intensity servos, AOM controls, and mirror positioning for both 456nm and 1064nm lasers.
    """
    # Constants for shutter timing
    CONST_SHUTTER_TURN_ON_TIME: ClassVar[float] = 2e-3  # 2ms for shutter to open
    CONST_SHUTTER_TURN_OFF_TIME: ClassVar[float] = 2e-3  # 2ms for shutter to close
    CONST_MIN_SHUTTER_OFF_TIME: ClassVar[float] = (
        6.28e-3  # minimum time for shutter to be off and on again
    )
    CONST_MIN_SHUTTER_ON_TIME: ClassVar[float] = (
        3.6e-3  # minimum time for shutter to be on
    )

    CONST_MIN_FREQ_STEP = 2 # MHz
    CONST_MIN_T_STEP = 100e-6 # 10us
    CONST_DEFAULT_DETUNING_456 = 600 #MHz


    def __init__(self, t):
        """Initialize the Rydberg laser system.

        Args:
            t (float): Time to start the Rydberg lasers
        """
        # Can't do any output from NI card until 12e-6
        t += 12e-6 if t < 12e-6 else 0
        # Keep the intensity servo on, regardless of BLACs settings
        self.servo_456_intensity_keep_on(t)
        self.servo_1064_intensity_keep_on(t)
        # Initialize 456nm laser detuning
        # the initial detuning every ramp start and end to
        self.detuning_456 = shot_globals.ryd_456_detuning #self.CONST_DEFAULT_DETUNING_456 #MHz
        devices.dds1.synthesize(t, freq = self.detuning_456, amp = 0.5, ph = 0)
        # Initialize shutter state
        self.shutter_open = False
        # Mirrors go to initial positions
        self.mirror_456_1_position(t)
        self.mirror_456_2_position(t)
        self.mirror_1064_1_position(t)
        self.mirror_1064_2_position(t)
        self.last_shutter_close_t = 0
        self.last_shutter_open_t = 0

    def do_456_freq_sweep(self, t, end_freq):
        """Perform a frequency sweep of 456nm laser.

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
        start_freq = self.detuning_456
        if start_freq == end_freq:
            return t

        num_steps = 4 #int(np.abs(start_freq - end_freq)/self.CONST_MIN_FREQ_STEP)
        dur = num_steps*self.CONST_MIN_T_STEP
        t_step = np.linspace(t - dur, t, num_steps)
        freq_step = np.linspace(start_freq, end_freq, num_steps)
        for i in np.arange(num_steps):
            devices.dds1.synthesize(t_step[i], freq = freq_step[i], amp = 0.7, ph = 0)

        self.detuning_456 = end_freq
        return t

    def servo_456_intensity_keep_on(self, t):
        """Maintain the 456nm laser intensity servo in active state.

        Args:
            t (float): Time to ensure servo remains active
        """
        """keep the AOM digital high for intensity servo"""
        self.servo_456_aom_on(t, 0)

    def servo_1064_intensity_keep_on(self, t):
        """Maintain the 1064nm laser intensity servo in active state.

        Args:
            t (float): Time to ensure servo remains active
        """
        """keep the AOM digital high for intensity servo"""
        self.servo_1064_aom_on(t, 0)

    def servo_456_aom_on(self, t, const):
        """Turn on the 456nm laser servo AOM.

        Args:
            t (float): Time to turn on the AOM
            const (float): Power level for the AOM
        """
        devices.servo_456_aom_digital.go_high(t)  # digital on
        devices.servo_456_aom_analog.constant(t, const)  # analog to const
        self.power_456 = const

    def servo_456_aom_off(self, t):
        """Turn off the 456nm laser servo AOM.

        Args:
            t (float): Time to turn off the AOM
        """
        devices.servo_456_aom_digital.go_low(t)  # digital off
        devices.servo_456_aom_analog.constant(t, 0)  # analog off
        self.power_456 = 0

    def pulse_456_aom_on(self, t, const, digital_only = False):
        """Turn on the 456nm laser pulse AOM.

        Args:
            t (float): Time to turn on the AOM
            const (float): Power level for the AOM
        """
        devices.pulse_456_aom_digital.go_high(t)  # digital on
        if not digital_only:
            devices.pulse_456_aom_analog.constant(t, const)  # analog to const
            self.power_456 = const

    def pulse_456_aom_off(self, t, digital_only = False):
        """Turn off the 456nm laser pulse AOM.

        Args:
            t (float): Time to turn off the AOM
        """
        devices.pulse_456_aom_digital.go_low(t)  # digital off
        if not digital_only:
            devices.pulse_456_aom_analog.constant(t, 0)  # analog off
            self.power_456 = 0

    def servo_1064_aom_on(self, t, const):
        """Turn on the 1064nm laser servo AOM.

        Args:
            t (float): Time to turn on the AOM
            const (float): Power level for the AOM
        """
        devices.servo_1064_aom_digital.go_high(t)  # digital on
        devices.servo_1064_aom_analog.constant(t, const)  # analog to const
        self.power_1064 = const

    def servo_1064_aom_off(self, t):
        """Turn off the 1064nm laser servo AOM.

        Args:
            t (float): Time to turn off the AOM
        """
        devices.servo_1064_aom_digital.go_low(t)  # digital off
        devices.servo_1064_aom_analog.constant(t, 0)  # analog off
        self.power_1064 = 0

    def pulse_1064_aom_on(self, t, const, digital_only = False):
        """Turn on the 1064nm laser pulse AOM.

        Args:
            t (float): Time to turn on the AOM
            const (float): Power level for the AOM
        """
        devices.pulse_1064_aom_digital.go_high(t)  # digital on
        if not digital_only:
            devices.pulse_1064_aom_analog.constant(t, const)  # analog to const
            self.power_1064 = const

    def pulse_1064_aom_off(self, t, digital_only = False):
        """Turn off the 1064nm laser pulse AOM.

        Args:
            t (float): Time to turn off the AOM
        """
        devices.pulse_1064_aom_digital.go_low(t)  # digital off
        if not digital_only:
            devices.pulse_1064_aom_analog.constant(t, 0)  # analog off
            self.power_1064 = 0

    def mirror_456_1_position(self, t):
        """Set the position of the first 456nm laser mirror.

        Args:
            t (float): Time to set the mirror position
        """
        devices.mirror_456_1_h.constant(
            t, shot_globals.ryd_456_mirror_1_h
        )
        devices.mirror_456_1_v.constant(t, shot_globals.ryd_456_mirror_1_v)

    def mirror_456_2_position(self, t):
        """Set the position of the second 456nm laser mirror.

        Args:
            t (float): Time to set the mirror position
        """
        devices.mirror_456_2_h.constant(
            t, shot_globals.ryd_456_mirror_2_h
        )
        devices.mirror_456_2_v.constant(t, shot_globals.ryd_456_mirror_2_v)

    def mirror_1064_1_position(self, t):
        """Set the position of the first 1064nm laser mirror.

        Args:
            t (float): Time to set the mirror position
        """
        devices.mirror_1064_1_h.constant(
            t, shot_globals.ryd_1064_mirror_1_h
        )
        devices.mirror_1064_1_v.constant(t, shot_globals.ryd_1064_mirror_1_v)

    def mirror_1064_2_position(self, t):
        """Set the position of the second 1064nm laser mirror.

        Args:
            t (float): Time to set the mirror position
        """
        devices.mirror_1064_2_h.constant(
            t, shot_globals.ryd_1064_mirror_2_h
        )
        devices.mirror_1064_2_v.constant(t, shot_globals.ryd_1064_mirror_2_v)

    def update_blue_456_shutter(self, t, config):
        """ perform the shutter update for the 456nm laser
        This help tracks when the last time the shutter is closed and open
        make sure to add the minium time for the shutter open and close
        before turn the aom back on for thermalization"""
        if config == "open":
            if t - self.last_shutter_close_t < self.CONST_MIN_SHUTTER_OFF_TIME:
                t = self.last_shutter_close_t + self.CONST_MIN_SHUTTER_OFF_TIME
            devices.blue_456_shutter.open(t) # shutter fully open
            self.last_shutter_open_t = t
            self.shutter_open = True
            return t
        elif config == "close":
            if t - self.last_shutter_open_t  < self.CONST_MIN_SHUTTER_ON_TIME:
                t = self.last_shutter_open_t + self.CONST_MIN_SHUTTER_ON_TIME
            self.last_shutter_close_t = t
            devices.blue_456_shutter.close(t) #shutter start to close
            t += self.CONST_SHUTTER_TURN_OFF_TIME
            self.shutter_open = False
            return t

    def do_456_pulse(self, t, dur, power_456, close_shutter=False):
        """Perform a Rydberg excitation pulse with specified parameters.

        Executes a laser pulse by configuring the shutter and AOM powers for both 456nm and 1064nm lasers.
        The servo AOMs remain unchanged during the pulse.

        # TODO: Check that this explanation is clear, @Sam, @Lin, @Michelle.
        Note that this routine is a little different from the D2Lasers do_pulse routine.
        In D2Lasers do_pulse, there is automatic time added if shutters need to be changed,
        so the input t is not necessarily the start time of the pulse. In contrast, here, t
        is the start time of the pulse, and the shutter is opened in time for the
        start of the pulse.

        Args:
            t (float): Start time for the aom part of the pulse
            dur (float): Duration of the pulse
            power_456 (float): Power level for the 456nm beam (0 to 1)
            power_1064 (float): Power level for the 1064nm beam (0 to 1)
            close_shutter (bool, optional): Whether to close shutter after pulse. Defaults to False.

        Returns:
            tuple[float]: (End time after pulse and shutter operations)
        """
        # t = self.do_456_freq_sweep(t, shot_globals.ryd_456_detuning)

        if not self.shutter_open:
            if power_456 != 0:
                t = self.update_blue_456_shutter(t,"open")
            # Turn off AOMs while waiting for shutter to fully open
            self.pulse_456_aom_off(t - self.CONST_SHUTTER_TURN_ON_TIME)

        # Turn on AOMs with specified powers
        if power_456 != 0:
            self.pulse_456_aom_on(t, power_456)


        t += dur

        # Turn off AOMs at the end of the pulse
        self.pulse_456_aom_off(t)

        if close_shutter:
            if power_456 != 0:
                t = self.update_blue_456_shutter(t,"close")
            self.pulse_456_aom_on(t, 1)

        return t



    def do_rydberg_pulse(self, t, dur, power_456, power_1064, close_shutter=False):
        """Perform a Rydberg excitation pulse with specified parameters.

        Executes a laser pulse by configuring the shutter and AOM powers for both 456nm and 1064nm lasers.
        The servo AOMs remain unchanged during the pulse.

        # TODO: Check that this explanation is clear, @Sam, @Lin, @Michelle.
        Note that this routine is a little different from the D2Lasers do_pulse routine.
        In D2Lasers do_pulse, there is automatic time added if shutters need to be changed,
        so the input t is not necessarily the start time of the pulse. In contrast, here, t
        is the start time of the pulse, and the shutter is opened in time for the
        start of the pulse.

        Args:
            t (float): Start time for the aom part of the pulse
            dur (float): Duration of the pulse
            power_456 (float): Power level for the 456nm beam (0 to 1)
            power_1064 (float): Power level for the 1064nm beam (0 to 1)
            close_shutter (bool, optional): Whether to close shutter after pulse. Defaults to False.

        Returns:
            tuple[float]: (End time after pulse and shutter operations)
        """
        # t = self.do_456_freq_sweep(t, shot_globals.ryd_456_detuning)

        if not self.shutter_open:
            if power_456 != 0:
                t = self.update_blue_456_shutter(t,"open")
            # Turn off AOMs while waiting for shutter to fully open
            self.pulse_456_aom_off(t - self.CONST_SHUTTER_TURN_ON_TIME)
            if power_1064 != 0:
                self.pulse_1064_aom_on(t , power_1064)
                # self.pulse_1064_aom_on(t- self.CONST_SHUTTER_TURN_ON_TIME, power_1064)

        # Turn on AOMs with specified powers
        if power_456 != 0:
            self.pulse_456_aom_on(t, power_456)

        t_aom_start = t
        t += dur


        # Turn off AOMs at the end of the pulse
        self.pulse_456_aom_off(t)
        self.pulse_1064_aom_off(t)

        if close_shutter:
            if power_456 != 0:
                t = self.update_blue_456_shutter(t,"close")
                t += 1e-3
            self.pulse_456_aom_on(t, 1)
            # self.pulse_1064_aom_on(t,1)

        # t = self.do_456_freq_sweep(t, self.CONST_DEFAULT_DETUNING_456)

        return t, t_aom_start


    def do_rydberg_multipulses(self, t, n_pulses, pulse_dur, pulse_wait_dur, power_456, power_1064, just_456=False, close_shutter=False):

        pulse_start_times = []

        # turn analog on 10 us earlier than the digital
        # workaround for timing limitation on pulseblaster due to labscript
        # https://groups.google.com/g/labscriptsuite/c/QdW6gUGNwQ0
        aom_analog_ctrl_anticipation = 1e-5

        if not self.shutter_open:
            if power_1064 != 0:
                devices.pulse_1064_aom_analog.constant(t - aom_analog_ctrl_anticipation, power_1064)
            if power_456 != 0:
                devices.pulse_456_aom_analog.constant(t - aom_analog_ctrl_anticipation, power_456)
                t = self.update_blue_456_shutter(t,"open")
            # Turn off AOMs while waiting for shutter to fully open
            self.pulse_456_aom_off(t - self.CONST_SHUTTER_TURN_ON_TIME, digital_only=True)
            if power_1064 != 0:
                self.pulse_1064_aom_on(t , power_1064, digital_only=True)
                # self.pulse_1064_aom_on(t- self.CONST_SHUTTER_TURN_ON_TIME, power_1064)

        for i in range(n_pulses):
            if just_456:
                self.pulse_456_aom_on(t, power_456, digital_only=True)
                # print(i, ' pulse start time:', t)
                t += pulse_dur
                self.pulse_456_aom_off(t, digital_only=True)
                t+= pulse_wait_dur
            else:
                self.pulse_456_aom_on(t, power_456, digital_only=True)
                self.pulse_1064_aom_on(t, power_1064, digital_only=True)
                t += pulse_dur
                self.pulse_456_aom_off(t, digital_only=True)
                self.pulse_1064_aom_off(t, digital_only=True)
                t += pulse_wait_dur

            pulse_start_times.append(t - pulse_wait_dur-pulse_dur)

        self.pulse_1064_aom_off(t)
        if close_shutter:
            if power_456 != 0:
                t = self.update_blue_456_shutter(t,"close")
            self.pulse_456_aom_on(t, 1)
            # self.pulse_1064_aom_on(t,1)
            t_end = t

        return t_end, pulse_start_times

    def do_rydberg_pulse_short(self, t, dur, power_456, power_1064, close_shutter=False):
        '''
        turn analog on 10 us earlier than the digital so there won't be pulseblaster related errors from the labscript
        '''

        # turn analog on 10 us earlier than the digital
        # workaround for timing limitation on pulseblaster due to labscript
        # https://groups.google.com/g/labscriptsuite/c/QdW6gUGNwQ0
        aom_analog_ctrl_anticipation = 1e-5
        if not self.shutter_open:
            if power_1064 != 0:
                devices.pulse_1064_aom_analog.constant(t - aom_analog_ctrl_anticipation, power_1064)
            if power_456 != 0:
                devices.pulse_456_aom_analog.constant(t - aom_analog_ctrl_anticipation, power_456)
                t = self.update_blue_456_shutter(t, "open")

            # Turn off AOMs while waiting for shutter to fully open
            self.pulse_456_aom_off(t - self.CONST_SHUTTER_TURN_ON_TIME, digital_only=True)

            if power_456!=0:
                self.pulse_456_aom_on(t, power_456, digital_only=True)
            if power_1064 !=0:
                self.pulse_1064_aom_on(t, power_1064, digital_only=True)

            print(f"t for aom on time {t}")
            pulse_times = [t]
            t += dur
            pulse_times.append(t)
            print(f"t for aom off time {t}")
            self.pulse_456_aom_off(t, digital_only=True)
            self.pulse_1064_aom_off(t, digital_only=True)

        if close_shutter:
            if power_456 != 0:
                t = self.update_blue_456_shutter(t, "close")
            # self.pulse_456_aom_on(t, 1, digital_only=True)

        return t, pulse_times


class UVLamps:
    """Controls for UV LED lamps used in the experiment.

    This class manages the UV LED lamps, which are typically used for MOT loading
    enhancement through light-induced atom desorption.
    """

    def __init__(self, t):
        """Initialize the UV lamp system.

        Args:
            t (float): Time to start the UV lamps
        """
        # Turn off UV lamps
        devices.uv_switch.go_low(t)

    def uv_pulse(self, t, dur):
        """Flash the UV LED lamps for a specified duration.

        Args:
            t (float): Start time for the UV pulse
            dur (float): Duration of the UV pulse

        Returns:
            float: End time of the UV pulse
        """
        devices.uv_switch.go_high(t)
        t += dur
        devices.uv_switch.go_low(t)
        return t


class BField:
    """Controls for magnetic field generation and manipulation.

    This class manages the magnetic field coils used in the experiment, including MOT coils
    and bias field coils. It provides methods for switching coils, ramping fields, and
    converting between spherical and Cartesian coordinates for field control.

    Attributes:
        CONST_COIL_OFF_TIME (float): Time required for coils to turn off (1.4e-3 s)
        CONST_COIL_RAMP_TIME (float): Standard time for ramping coil currents (100e-6 s)
        CONST_BIPOLAR_COIL_FLIP_TIME (float): Time required to flip coil polarity (10e-3 s)
        CONST_COIL_FEEDBACK_OFF_TIME (float): Time for coil feedback to turn off (4.5e-3 s)
    """
    CONST_COIL_OFF_TIME: ClassVar[float] = 1.4e-3
    CONST_COIL_RAMP_TIME: ClassVar[float] = 100e-6
    CONST_BIPOLAR_COIL_FLIP_TIME: ClassVar[float] = 10e-3
    CONST_COIL_FEEDBACK_OFF_TIME: ClassVar[float] = 4.5e-3

    bias_voltages = tuple[float]
    mot_coils_on: bool
    mot_coils_on_current: float
    current_outputs = tuple[AnalogOut, AnalogOut, AnalogOut]
    feedback_disable_ttls = tuple[DigitalOut, DigitalOut, DigitalOut]


    def __init__(self, t: float):
        """Initialize the magnetic field system.

        Args:
            t (float): Time to start the magnetic field
        """
        self.bias_voltages = (
            shot_globals.mot_x_coil_voltage,
            shot_globals.mot_y_coil_voltage,
            shot_globals.mot_z_coil_voltage,
        )
        self.mot_coils_on = shot_globals.mot_do_coil
        self.mot_coils_on_current = 10 / 6

        self.t_last_change = 0

        self.current_outputs = (
            devices.x_coil_current,
            devices.y_coil_current,
            devices.z_coil_current,
        )

        self.feedback_disable_ttls = (
            devices.x_coil_feedback_off,
            devices.y_coil_feedback_off,
            devices.z_coil_feedback_off,
        )

        for current_output, bias_voltage_cmpnt in zip(
            self.current_outputs, self.bias_voltages
        ):
            current_output.constant(t, bias_voltage_cmpnt)

        if self.mot_coils_on:
            devices.mot_coil_current_ctrl.constant(t, self.mot_coils_on_current)
        else:
            devices.mot_coil_current_ctrl.constant(
                t, 0
            )  # when changing bias field make sure the magnetic field gradient is off

    def flip_coil_polarity(
        self, t: float, final_voltage: float, component: Literal[0, 1, 2]
    ):
        """
        Flip the polarity of a specified magnetic field coil.

        Performs a controlled polarity flip of a magnetic field coil by ramping through
        an intermediate voltage state. The process involves:
        1. Ramping to a small intermediate voltage
        2. Disabling feedback during the polarity change
        3. Waiting for the flip to complete
        4. Ramping to the final voltage

        Args:
            t (float): Time to begin coil polarity flipping
            final_voltage (float): Target control voltage for the coil after polarity flip
            component (Literal[0, 1, 2]): Field component to flip (0=x, 1=y, 2=z)

        Returns:
            float: Start time for parallel operations (accounts for flip duration)

        Note:
            The method returns the start time instead of end time to allow parallel
            operations on other coils. Total operation time is CONST_BIPOLAR_COIL_FLIP_TIME
            plus CONST_COIL_RAMP_TIME.
        """
        coil_voltage_mid_abs = 0.03
        coil_voltage_mid = np.sign(final_voltage) * coil_voltage_mid_abs
        total_coil_flip_ramp_time = (
            self.CONST_BIPOLAR_COIL_FLIP_TIME + self.CONST_COIL_RAMP_TIME
        )

        current_output = self.current_outputs[component]
        feedback_disable_ttl = self.feedback_disable_ttls[component]

        t += current_output.ramp(
            t,
            duration=self.CONST_COIL_RAMP_TIME / 2,
            initial=self.bias_voltages[component],
            final=coil_voltage_mid,  # sligtly negative voltage to trigger the polarity change
            samplerate=1e5,
        )
        # print(f"feed_disable_ttl in coil {component}")
        feedback_disable_ttl.go_high(t)
        feedback_disable_ttl.go_low(t + self.CONST_COIL_FEEDBACK_OFF_TIME)
        self.current_outputs[component].constant(t, coil_voltage_mid)
        t += self.CONST_BIPOLAR_COIL_FLIP_TIME

        t += current_output.ramp(
            t,
            duration=self.CONST_COIL_RAMP_TIME / 2,
            initial=coil_voltage_mid,
            final=final_voltage,  # 0 mG
            samplerate=1e5,
        )

        t -= total_coil_flip_ramp_time  # subtract to the begining to set other coils

        # Update internal state
        bias_voltages = [voltage for voltage in self.bias_voltages]
        bias_voltages[component] = final_voltage
        self.bias_voltages = tuple(bias_voltages)
        return t

    def ramp_bias_field(self, t, dur = 100e-6,  bias_field_vector=None, voltage_vector=None, polar = False):
        """Ramp the bias field to new values.

        Args:
            t (float): Start time for the ramp
            dur (float, optional): Duration of the ramp. Defaults to 100e-6 s
            bias_field_vector (tuple, optional): Target bias field values in Gauss
            voltage_vector (tuple, optional): Target voltage values for coils
            polar (boolean): using the spherical coordinate for the magnetic fields or cartiesain

        Returns:
            float: End time of the ramp
        """
        # bias_field_vector should be a tuple of the form (x,y,z)
        # Need to start the ramp earlier if the voltage changes sign
        if polar:
            field_vector = (
                self.convert_bias_fields_sph_to_cart(
                    bias_field_vector[0],
                    bias_field_vector[1],
                    bias_field_vector[2],
                )
            )
        else:
            field_vector = bias_field_vector


        dur = np.max([dur, self.CONST_COIL_RAMP_TIME])
        if field_vector is not None:
            voltage_vector = np.array(
                [
                    biasx_calib(field_vector[0]),
                    biasy_calib(field_vector[1]),
                    biasz_calib(field_vector[2]),
                ]
            )

        if np.all(self.bias_voltages == voltage_vector):
            print("bias field initial and final are the same, skip ramp")
            return t

        sign_flip_in_ramp = voltage_vector * np.asarray(self.bias_voltages) < 0
        coil_ramp_start_times = (
            t - self.CONST_BIPOLAR_COIL_FLIP_TIME * sign_flip_in_ramp
        )

        # print(coil_ramp_start_times)

        for i in range(3):
            if sign_flip_in_ramp[i]:
                coil_ramp_start_times[i] = np.max(
                    [self.t_last_change + 100e-6, coil_ramp_start_times[i]]
                )
                _ = self.flip_coil_polarity(
                    coil_ramp_start_times[i], voltage_vector[i], component=i
                )
            else:
                self.current_outputs[i].ramp(
                    coil_ramp_start_times[i],
                    duration= dur,
                    initial=self.bias_voltages[i],
                    final=voltage_vector[i],
                    samplerate=1e5,
                )
        # print(coil_ramp_start_times)
        end_time = (
            np.min(coil_ramp_start_times)
            + dur
            + self.CONST_BIPOLAR_COIL_FLIP_TIME
        )
        self.t_last_change = end_time
        # print(coil_ramp_start_times)

        # TODO: add the inverse function of bias_i_calib
        # otherwise, if only voltage vector is provided on input, the bias field will not be updated
        # if bias_field_vector is not None:

        self.bias_voltages = tuple(voltage_vector)

        return t + dur

    def switch_mot_coils(self, t):
        """Switch the MOT coils on or off.

        Args:
            t (float): Time to switch the coils

        Returns:
            float: End time after switching operation is complete
        """
        if self.mot_coils_on:
            devices.mot_coil_current_ctrl.ramp(
                t,
                duration=self.CONST_COIL_RAMP_TIME,
                initial=self.mot_coils_on_current,
                final=0,
                samplerate=1e5,
            )
            self.mot_coils_on = False
        else:
            devices.mot_coil_current_ctrl.ramp(
                t,
                duration=self.CONST_COIL_RAMP_TIME,
                initial=0,
                final=self.mot_coils_on_current,
                samplerate=1e5,
            )
            self.mot_coils_on = True

        endtime = t + self.CONST_COIL_RAMP_TIME + self.CONST_COIL_OFF_TIME
        return endtime

    def convert_bias_fields_sph_to_cart(self, bias_amp, bias_phi, bias_theta):
        """Convert spherical coordinates to Cartesian for bias field control.

        Args:
            bias_amp (float): Amplitude of the bias field
            bias_phi (float): Azimuthal angle in radians
            bias_theta (float): Polar angle in radians

        Returns:
            tuple: Cartesian coordinates (x, y, z) for the bias field
        """
        biasx_field = (
            bias_amp
            * np.cos(np.deg2rad(bias_phi))
            * np.sin(np.deg2rad(bias_theta))
        )
        biasy_field = (
            bias_amp
            * np.sin(np.deg2rad(bias_phi))
            * np.sin(np.deg2rad(bias_theta))
        )
        biasz_field = bias_amp * np.cos(
            np.deg2rad(bias_theta),
        )

        return biasx_field, biasy_field, biasz_field

class EField:
    """Control for electric field generation and manipulation.

    This class manages the 8 electrodes in the glass cell to zero electric field or generate requested field
    """
    def __init__(self, t):

        self.Efield_voltage = [
            shot_globals.zero_Efield_Vx,
            shot_globals.zero_Efield_Vy,
            shot_globals.zero_Efield_Vz
        ]

        self.electrodes = [devices.electrode_T1,
                           devices.electrode_T2,
                           devices.electrode_T3,
                           devices.electrode_T4,
                           devices.electrode_B1,
                           devices.electrode_B2,
                           devices.electrode_B3,
                           devices.electrode_B4,]

        self.set_electric_field(t, self.Efield_voltage)

    def convert_electrodes_voltages(self, voltage_diff_vector):
        """
        convert voltage difference into electrode voltages
        """
        Vx = voltage_diff_vector[0]
        Vy = voltage_diff_vector[1]
        Vz = voltage_diff_vector[2]

        electrode_voltages=[Vx + Vy,
                            Vy,
                            Vx + Vy + Vz,
                            Vy + Vz,
                            Vx,
                            0,
                            Vx + Vz,
                            Vz]

        return electrode_voltages

    def set_electric_field(self, t, voltage_diff_vector):
        """
        set electrodes to constant voltages. No ramp.
        """
        print(type(voltage_diff_vector))
        print(voltage_diff_vector)
        electrode_voltages = self.convert_electrodes_voltages(voltage_diff_vector)

        for voltage, electrode in zip(electrode_voltages, self.electrodes):
            electrode.constant(t, voltage)

        self.Efield_voltage = voltage_diff_vector




class Camera:
    """Controls for experimental imaging cameras.

    This class manages the camera systems used for imaging atoms in the experiment,
    including exposure timing and triggering.
    """

    def __init__(self, t):
        """Initialize the camera system.

        Args:
            t (float): Time to start the camera
        """
        self.type = None

    def set_type(self, type):
        """Set the type of imaging to be performed.

        Args:
            type (str): Type of imaging configuration to use, "MOT_manta" or
            "tweezer_manta" or "kinetix"
        """
        self.type = type

    def expose(self, t, exposure_time, trigger_local_manta=False):
        """Trigger camera exposure.

        Args:
            t (float): Start time for the exposure
            exposure_time (float): Duration of the exposure
            trigger_local_manta (bool, optional): Whether to trigger local Manta camera
        """
        if trigger_local_manta:
            devices.mot_camera_trigger.go_high(t)
            devices.mot_camera_trigger.go_low(t + exposure_time)

        if self.type == "MOT_manta":
            devices.manta419b_mot.expose(
                "manta419b", t, "atoms", exposure_time=exposure_time
            )

        if self.type == "tweezer_manta":
            devices.manta419b_tweezer.expose(
                "manta419b",
                t,
                "atoms",
                exposure_time=exposure_time,
            )

        if self.type == "kinetix":
            devices.kinetix.expose(
                "Kinetix",
                t,
                "atoms",
                exposure_time=exposure_time,
            )