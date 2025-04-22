from __future__ import annotations

from dataclasses import dataclass
from enum import Flag, auto
from typing import ClassVar, Literal

import labscript
import numpy as np

from labscriptlib.calibration import (
    repump_freq_calib,
    ta_freq_calib,
)
from labscriptlib.connection_table import devices
from labscriptlib.spectrum_manager import spectrum_manager
from labscriptlib.spectrum_manager_fifo import spectrum_manager_fifo
from labscriptlib.shot_globals import shot_globals

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
    def select_imaging_shutters(cls, imaging_label, beam_choice: Literal['mot', 'img'], do_repump=True) -> ShutterConfig:
        '''
        Parameters
        ----------
        imaging_label:
            TODO what does this do?
        beam_choice: {'mot', 'img'}
            Choice of beam for doing imaging
        do_repump: bool
            Whether to use repump beams in the imaging.

        Returns
        -------
        ShutterConfig
            shutter configuration necessary for imaging with the specified params
        '''
        repump_config = cls.REPUMP if do_repump else cls.NONE

        # TODO: change handling of labels to make full default and raise error when not one of the options
        if beam_choice == 'mot':
            if imaging_label == "z":
                return cls.MOT_Z | cls.TA | repump_config
            elif imaging_label == "xy":
                return cls.MOT_XY | cls.TA | repump_config
            else:
                return cls.MOT_TA | repump_config
        elif beam_choice == 'img':
            if imaging_label == "z":
                return cls.IMG_Z | cls.TA | repump_config
            elif imaging_label == "xy":
                return cls.IMG_XY | cls.TA | repump_config
            else:
                return cls.IMG_TA | repump_config
        else:
            return cls.NONE


@dataclass
class D2Config:
    ta_power: float
    ta_detuning: float
    repump_power: float
    repump_detuning: float = 0


@dataclass
class ParityProjectionConfig:
    ta_power: float
    ta_detuning: float


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

    # fixed parameters in the script
    CONST_TA_PUMPING_DETUNING: ClassVar[float] = -251  # MHz 4->4 tansition
    CONST_REPUMP_DEPUMPING_DETUNING: ClassVar[float] = -201.24  # MHz 3->3 transition

    mot_config: D2Config

    # TODO: consider removing this and passing directly to D2Lasers.parity_projection_pulse()
    parity_proj_config: ParityProjectionConfig

    ta_freq: float
    repump_freq: float
    ta_power: float
    repump_power: float
    # TODO add remaining state variables

    # Can we put this somewhere nicer?

    def __init__(
            self,
            t,
            mot_config: D2Config,
            pp_config: ParityProjectionConfig,
    ):
        """Initialize the D2 laser system.

        Sets up initial frequencies and powers for MOT operation, initializes shutter
        configuration, and configures hardware devices.

        Parameters
        ----------
        t: float
            Time to start the D2 laser system
        mot_config, pp_config: MOTConfig, ParityProjectionConfig
            configuration for the MOT and parity projection pulses
        """
        # Tune to MOT frequency, full power
        self.ta_freq = mot_config.ta_detuning
        self.repump_freq = D2Config.repump_detuning
        self.ta_power = mot_config.ta_power
        self.repump_power = mot_config.repump_power

        self.mot_config = mot_config
        self.parity_proj_config = pp_config

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
        #TODO: Double check that this actually still works robustly...
        # if the last shutter is opened and now needs to be closed, close it after CONST_MIN_SHUTTER_ON_TIME
        # subtract CONST_SHUTTER_TURN_OFF_TIME because in do_pulse, shutter time is updated after adding CONST_SHUTTER_TURN_OFF_TIME
        elif any (t - self.CONST_SHUTTER_TURN_OFF_TIME - self.last_shutter_open_t * close_bool_list < self.CONST_MIN_SHUTTER_ON_TIME):
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
        self.ramp_repump_freq(
            t,
            duration=self.CONST_TA_VCO_RAMP_TIME,
            final=self.mot_config.repump_detuning,
        )
        self.ramp_ta_freq(
            t, duration=self.CONST_TA_VCO_RAMP_TIME, final=self.mot_config.ta_detuning
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
        self.ta_aom_on(t, self.mot_config.ta_power)
        self.repump_aom_on(t, self.mot_config.repump_power)
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
            final=self.parity_proj_config.ta_detuning,
        )  # fixed the ramp duration for the parity projection
        t += self.CONST_TA_VCO_RAMP_TIME
        t, t_aom_start = self.do_pulse(
            t,
            dur,
            ShutterConfig.MOT_TA,
            self.parity_proj_config.ta_power,
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

    tweezer_power: float
    spectrum_mode: Literal['sequence', 'fifo']
    tw_y_use_dds: bool

    def __init__(self, t, tweezer_power: float, spectrum_mode: Literal['sequence', 'fifo'], tw_y_use_dds: bool):
        """Initialize the tweezer laser system.

        Args:
            t (float): Time to start the tweezers
        """
        self.tweezer_power = tweezer_power
        self.spectrum_mode = spectrum_mode
        self.tw_y_use_dds = tw_y_use_dds

        # self.intensity_servo_keep_on(t)
        self.start_tweezers(t)

    def start_tweezers(self, t):
        """Initialize and start the optical tweezer system.

        Args:
            t (float): Time to start the tweezers
        """
        if self.spectrum_mode == 'sequence':
            spectrum_manager.start_card()
            spectrum_manager.start_tweezers(t)
        elif self.spectrum_mode == 'fifo':
            spectrum_manager_fifo.start_tweezer_card()
            spectrum_manager_fifo.start_tweezers(t)
            print('global `do_sequence_mode` is currently False, running Fifo mode now. '
                  'Set to True for sequence mode')
        else:
            raise ValueError("The spectrum_mode should only be sequence or fifo mode")

        if self.tw_y_use_dds:
            devices.dds0.synthesize(t+1e-3, freq = shot_globals.TW_y_freqs, amp = 0.95, ph = 0) # unit: MHz
        self.aom_on(t, self.tweezer_power)

    def stop_tweezers(self, t):
        """Safely stop and power down the optical tweezer system.

        Args:
            t (float): Time to stop the tweezers
        """
        if self.spectrum_mode == 'sequence':
            # stop tweezers
            spectrum_manager.stop_tweezers(t)

            # dummy segment, need this to stop tweezers due to spectrum card bug
            spectrum_manager.start_tweezers(t)
            t += 2e-3
            spectrum_manager.stop_tweezers(t)
            spectrum_manager.stop_card(t)
        elif self.spectrum_mode == 'fifo':
            spectrum_manager_fifo.stop_tweezers(t)
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
            self.tweezer_power = const

    def aom_off(self, t, digital_only = False):
        """Turn off the tweezer beam using AOM.

        Args:
            t (float): Time to turn off the AOM
        """
        """Turn off the tweezer beam using aom"""
        devices.tweezer_aom_digital.go_low(t)  # digital off
        if not digital_only:
            devices.tweezer_aom_analog.constant(t, 0)  # analog off
            self.tweezer_power = 0

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
            t, duration=dur, initial=self.tweezer_power, final=final_power, samplerate=1e5
        )
        self.tweezer_power = final_power
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
            dc_offset=self.tweezer_power,
            samplerate=1e5,
        )


@dataclass
class PointingConfig:
    '''
    Config class for beam pointing with four picomotors or two mirror mounts.
    '''
    upstream_h: float
    upstream_v: float
    downstream_h: float
    downstream_v: float


class RydLasers:
    """Controls for Rydberg excitation lasers (456nm and 1064nm).

    This class manages the laser systems used for Rydberg excitation, including
    intensity servos, AOM controls, and mirror positioning for both 456nm and 1064nm lasers.
    """
    # Constants for shutter timing
    CONST_SHUTTER_TURN_ON_TIME: ClassVar[float] = 2e-3  # 2ms for shutter to open
    CONST_SHUTTER_TURN_OFF_TIME: ClassVar[float] = 2e-3  # 2ms for shutter to close

    CONST_MIN_SHUTTER_OFF_TIME: ClassVar[float] = 6.28e-3
    """minimum time for shutter to be off and on again"""
    CONST_MIN_SHUTTER_ON_TIME: ClassVar[float] = 3.6e-3
    """minimum time for shutter to be on"""

    CONST_MIN_FREQ_STEP: ClassVar[float] = 2  # MHz
    CONST_DEFAULT_DETUNING_456: ClassVar[float] = 600  # MHz

    # NI analog seems to be responding slower than the pulse blaster digital
    # this is only really a problem for devices that use both (ryd lasers, tweezers, local addressing)
    CONST_NI_ANALOG_DELAY: ClassVar[float] = 0


    def __init__(self, t, blue_pointing: PointingConfig, ir_pointing: PointingConfig, init_blue_detuning: float):
        """Initialize the Rydberg laser system.

        Args:
            t (float): Time to start the Rydberg lasers
        """
        # Can't do any output from NI card until 12e-6
        t = max(t, 12e-6)

        # Keep the intensity servo on, regardless of BLACs settings
        self.servo_456_intensity_keep_on(t)
        self.servo_1064_intensity_keep_on(t)
        # Initialize 456nm laser detuning
        # the initial detuning every ramp start and end to
        self.detuning_456 = init_blue_detuning
        devices.dds1.synthesize(t, freq = self.detuning_456, amp = 0.5, ph = 0)
        # Initialize shutter state
        self.shutter_open = False

        self.blue_pointing = blue_pointing
        self.ir_pointing = ir_pointing

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

    def servo_456_aom_on(self, t: float, power: float):
        """Turn on the 456nm laser servo AOM.

        Parameters
        ----------
        t: float
            Time to turn on the AOM
        power: float
            Power level for the AOM
        """
        devices.servo_456_aom_digital.go_high(t)  # digital on
        devices.servo_456_aom_analog.constant(t, power)  # analog to const
        self.power_456 = power

    def servo_456_aom_off(self, t: float):
        """Turn off the 456nm laser servo AOM.

        Parameters
        ----------
        t: float
            Time to turn off the AOM
        """
        devices.servo_456_aom_digital.go_low(t)  # digital off
        devices.servo_456_aom_analog.constant(t, 0)  # analog off
        self.power_456 = 0

    def pulse_456_aom_on(self, t: float, power: float, digital_only: bool = False):
        """Turn on the 456nm laser pulse AOM.

        Parameters
        ----------
        t: float
            Time to turn on the AOM
        power: float
            Power level for the AOM
        digital_only: bool
            Whether to switch only the digital control. Defaults to False
            (i.e. also use analog control).
        """
        devices.pulse_456_aom_digital.go_high(t)  # digital on
        if not digital_only:
            devices.pulse_456_aom_analog.constant(t - self.CONST_NI_ANALOG_DELAY, power)  # analog to const
            self.power_456 = power

    def pulse_456_aom_off(self, t: float, digital_only: bool = False):
        """Turn off the 456nm laser pulse AOM.

        Parameters
        ----------
        t: float
            Time to turn off the AOM
        digital_only: bool
            Whether to switch only the digital control. Defaults to False
            (i.e. also use analog control).
        """
        devices.pulse_456_aom_digital.go_low(t)  # digital off
        if not digital_only:
            devices.pulse_456_aom_analog.constant(t - self.CONST_NI_ANALOG_DELAY, 0)  # analog off
            self.power_456 = 0

    def servo_1064_aom_on(self, t: float, power: float):
        """Turn on the 1064nm laser servo AOM.

        Parameters
        ----------
        t: float
            Time to turn on the AOM
        power: float
            Power level for the AOM
        """
        devices.servo_1064_aom_digital.go_high(t)  # digital on
        devices.servo_1064_aom_analog.constant(t, power)  # analog to const
        self.power_1064 = power

    def servo_1064_aom_off(self, t: float):
        """Turn off the 1064nm laser servo AOM.

        Parameters
        ----------
        t: float
            Time to turn off the AOM
        """
        devices.servo_1064_aom_digital.go_low(t)  # digital off
        devices.servo_1064_aom_analog.constant(t, 0)  # analog off
        self.power_1064 = 0

    def pulse_1064_aom_on(self, t: float, power: float, digital_only: bool = False):
        """Turn on the 1064nm laser pulse AOM.

        Parameters
        ----------
        t: float
            Time to turn on the AOM
        power: float
            Power level for the AOM
        digital_only: bool
            Whether to switch only the digital control. Defaults to False
            (i.e. also use analog control).
        """
        devices.pulse_1064_aom_digital.go_high(t)  # digital on
        if not digital_only:
            devices.pulse_1064_aom_analog.constant(t, power)  # analog to const
            self.power_1064 = power

    def pulse_1064_aom_off(self, t: float, digital_only: bool = False):
        """Turn off the 1064nm laser pulse AOM.

        Parameters
        ----------
        t: float
            Time to turn off the AOM
        digital_only: bool
            Whether to switch only the digital control. Defaults to False
            (i.e. also use analog control).
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
        devices.mirror_456_1_h.constant(t, self.blue_pointing.upstream_h)
        devices.mirror_456_1_v.constant(t, self.blue_pointing.upstream_v)

    def mirror_456_2_position(self, t):
        """Set the position of the second 456nm laser mirror.

        Args:
            t (float): Time to set the mirror position
        """
        devices.mirror_456_2_h.constant(t, self.blue_pointing.downstream_h)
        devices.mirror_456_2_v.constant(t, self.blue_pointing.downstream_v)

    def mirror_1064_1_position(self, t):
        """Set the position of the first 1064nm laser mirror.

        Args:
            t (float): Time to set the mirror position
        """
        devices.mirror_1064_1_h.constant(t, self.ir_pointing.upstream_h)
        devices.mirror_1064_1_v.constant(t, self.ir_pointing.upstream_v)

    def mirror_1064_2_position(self, t):
        """Set the position of the second 1064nm laser mirror.

        Args:
            t (float): Time to set the mirror position
        """
        devices.mirror_1064_2_h.constant(t, self.ir_pointing.downstream_h)
        devices.mirror_1064_2_v.constant(t, self.ir_pointing.downstream_v)

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
        if not self.shutter_open:
            if power_456 != 0:
                t = self.update_blue_456_shutter(t, "open")
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
                t = self.update_blue_456_shutter(t, "close")
            self.pulse_456_aom_on(t, 1)

        return t

    def do_rydberg_pulse(self, t, dur, power_456, power_1064, close_shutter=False, in_dipole_trap=False):
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
            in_dipole_trap (bool, optional): Whether there is a dipole trap on at subsequence onset.
                Controls end state of 1064 light and allows fully dropping dipole trap during pulse
                by setting power_1064=0

        Returns:
            tuple[float, float]: (End time after pulse and shutter operations)
        """
        if not self.shutter_open:
            if power_456 != 0:
                t = self.update_blue_456_shutter(t, "open")
            # Turn off AOMs while waiting for shutter to fully open
            self.pulse_456_aom_off(t - self.CONST_SHUTTER_TURN_ON_TIME)

        if in_dipole_trap:
            if power_1064 == 0:
                self.pulse_1064_aom_off(t)
            else:
                self.pulse_1064_aom_on(t, power_1064)
        else:
            if power_1064 != 0:
                self.pulse_1064_aom_on(t, power_1064)

        # Turn on AOMs with specified powers
        if power_456 != 0:
            self.pulse_456_aom_on(t, power_456)

        t_aom_start = t
        t += dur

        # Turn off AOMs at the end of the pulse
        self.pulse_456_aom_off(t)

        if in_dipole_trap:
            self.pulse_1064_aom_on(t, 1)
        else:
            self.pulse_1064_aom_off(t)

        if close_shutter:
            if power_456 != 0:
                t = self.update_blue_456_shutter(t, "close")
                t += 1e-3
            self.pulse_456_aom_on(t, 1)

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

    def do_rydberg_pulse_short(
            self,
            t,
            dur: float,
            power_456: float,
            power_1064: float,
            close_shutter: bool = False,
            in_dipole_trap: bool = False,
    ):
        '''
        turn analog on 10 us earlier than the digital so there won't be pulseblaster related errors from the labscript
        '''
        if not dur >= 0:
            raise ValueError(f'duration must be nonnegative, was {dur}')
        if not 0 <= power_456 <= 1:
            raise ValueError(f'456 power out of bounds [0, 1], was {power_456}')
        if not 0 <= power_1064 <= 1:
            raise ValueError(f'1064 power out of bounds [0, 1], was {power_1064}')

        # turn analog on 10 us earlier than the digital
        # workaround for timing limitation on pulseblaster due to labscript
        # https://groups.google.com/g/labscriptsuite/c/QdW6gUGNwQ0
        aom_analog_ctrl_anticipation = 10e-6
        if not self.shutter_open:
            if power_456 != 0:
                t = self.update_blue_456_shutter(t, "open")
            # Turn off AOMs while waiting for shutter to fully open
            self.pulse_456_aom_off(t - self.CONST_SHUTTER_TURN_ON_TIME, digital_only=True)

        if power_456 != 0:
            devices.pulse_456_aom_analog.constant(t - aom_analog_ctrl_anticipation, power_456)
            self.pulse_456_aom_on(t, power_456, digital_only=True)

        if in_dipole_trap:
            if power_1064 == 0:
                self.pulse_1064_aom_off(t, digital_only=True)
            else:
                raise ValueError("Can't switch from dipole trap to nonzero power with a short pulse")
        else:
            if power_1064 != 0:
                devices.pulse_1064_aom_analog.constant(t - aom_analog_ctrl_anticipation, power_1064)
                self.pulse_1064_aom_on(t, power_1064, digital_only=True)

        t_aom_start = t

        t += dur
        self.pulse_456_aom_off(t, digital_only=True)
        devices.pulse_456_aom_analog.constant(t + aom_analog_ctrl_anticipation, 0)

        if in_dipole_trap:
            self.pulse_1064_aom_on(t, 1, digital_only=True)
        else:
            self.pulse_1064_aom_off(t, digital_only=True)
            devices.pulse_1064_aom_analog.constant(t + aom_analog_ctrl_anticipation, 0)

        if close_shutter:
            if power_456 != 0:
                t = self.update_blue_456_shutter(t, "close")
            self.pulse_456_aom_on(t, 1, digital_only=True)

        return t, t_aom_start
