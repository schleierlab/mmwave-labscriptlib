from __future__ import annotations

from enum import Flag, auto
from typing import ClassVar

import numpy as np

import labscript
from labscriptlib.shot_globals import shot_globals
from connection_table import devices
from calibration import (
    ta_freq_calib,
    repump_freq_calib,
    biasx_calib,
    biasy_calib,
    biasz_calib,
    spec_freq_calib,
)
from spectrum_manager import spectrum_manager
# from shot_globals import shot_globals
# from spectrum_manager_fifo import spectrum_manager_fifo


class ShutterConfig(Flag):
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
    shutter_config: ShutterConfig

    CONST_TA_VCO_RAMP_TIME: ClassVar[float] = 1.2e-4  # minimal ta vco ramp time to stay in beatnote lock
    CONST_SHUTTER_TURN_OFF_TIME: ClassVar[float] = 2e-3  # for shutter take from start to open to fully close
    CONST_SHUTTER_TURN_ON_TIME: ClassVar[float] = 2e-3  # for shutter take from start to close to fully open

    CONST_MIN_SHUTTER_OFF_TIME: ClassVar[float] = 6.28e-3  # minimum time for shutter to be off and on again
    CONST_MIN_SHUTTER_ON_TIME: ClassVar[float] = 3.6e-3  # minimum time for shutter to be on


    def __init__(self, t):
        # Tune to MOT frequency, full power
        self.ta_freq = shot_globals.mot_ta_detuning
        self.repump_freq = 0  # shot_globals.mot_repump_detuning
        self.ta_power = shot_globals.mot_ta_power
        self.repump_power = shot_globals.mot_repump_power
        # update_shutters compares with self.shutter_config to decide what
        # changes to make. Do not call self.update_shutters(self.shutter_config),
        # nothing will happen.
        self.shutter_config = ShutterConfig.NONE
        self.update_shutters(t, ShutterConfig.MOT_FULL)

        # If do_mot is the first thing that is called, these initializations
        # produce a warning in the runmanager output because the MOT powers
        # and frequencies are set twice.
        devices.ta_vco.constant(t, ta_freq_calib(self.ta_freq))
        devices.repump_vco.constant(t, repump_freq_calib(self.repump_freq))
        devices.ta_aom_analog.constant(t, self.ta_power)
        devices.repump_aom_analog.constant(t, self.repump_power)

    # Move freq_calib to a function within here? Probably not needed.
    def ramp_ta_freq(self, t, duration, final):
        # TODO: check that duration statement here is valid for optical pumping
        duration = max(self.CONST_TA_VCO_RAMP_TIME, duration)
        devices.ta_vco.ramp(
            t,
            duration=duration,
            initial=ta_freq_calib(self.ta_freq),
            final=ta_freq_calib(final),
            samplerate=4e5,
        )
        self.ta_freq = final

    def ramp_repump_freq(self, t, duration, final):
        # TODO: check that duration statement here is valid for optical pumping
        duration = max(self.CONST_TA_VCO_RAMP_TIME, duration)
        devices.repump_vco.ramp(
            t,
            duration=duration,
            initial=repump_freq_calib(self.repump_freq),
            final=repump_freq_calib(final),
            samplerate=4e5,
        )
        self.repump_freq = final

    def ta_aom_off(self, t):
        """Turn off the ta beam using aom"""
        devices.ta_aom_digital.go_low(t)  # digital off
        devices.ta_aom_analog.constant(t, 0)  # analog off
        self.ta_power = 0

    def ta_aom_on(self, t, const):
        """Turn on the ta beam using aom"""
        devices.ta_aom_digital.go_high(t)  # digital on
        devices.ta_aom_analog.constant(t, const)  # analog to const
        self.ta_power = const

    def repump_aom_off(self, t):
        """Turn off the repump beam using aom"""
        devices.repump_aom_digital.go_low(t)  # digital off
        devices.repump_aom_analog.constant(t, 0)  # analog off
        self.repump_power = 0

    def repump_aom_on(self, t, const):
        """Turn on the repump beam using aom"""
        devices.repump_aom_digital.go_high(t)  # digital on
        devices.repump_aom_analog.constant(t, const)  # analog to const
        self.repump_power = const

    def ramp_ta_aom(self, t, dur, final_power):
        """ramp ta power from current value to final power"""
        devices.ta_aom_analog.ramp(
            t,
            duration=dur,
            initial=self.ta_power,
            final=final_power,
            samplerate=1e5,
        )

    def ramp_repump_aom(self, t, dur, final_power):
        """ramp repump power from current value to final power"""
        devices.repump_aom_analog.ramp(
            t,
            duration=dur,
            initial=self.repump_power,
            final=final_power,
            samplerate=1e5,
        )

    def update_shutters(self, t, new_shutter_config: ShutterConfig):
        changed_shutters = self.shutter_config ^ new_shutter_config

        shutters_to_open = changed_shutters & new_shutter_config
        shutters_to_close = changed_shutters & self.shutter_config

        # Can we put this somewhere nicer?
        basic_shutters = [
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

        for shutter in basic_shutters:
            if shutter in shutters_to_open:
                shutter_dict[shutter].open(t)
            if shutter in shutters_to_close:
                shutter_dict[shutter].close(t - self.CONST_SHUTTER_TURN_OFF_TIME)

        self.shutter_config = new_shutter_config
        # return t?

    # NOTE: This version makes it so that the previous shutters are fully closed before opening the new shutters
    # def update_shutters(self, t, new_shutter_config: ShutterConfig):
    #     changed_shutters = self.shutter_config ^ new_shutter_config

    #     shutters_to_open = changed_shutters & new_shutter_config
    #     shutters_to_close = changed_shutters & self.shutter_config

    #     for shutter in shutters_to_close:
    #         self.shutter_config.shutter_dict[shutter].close(t)

    #     t += 2*self.CONST_SHUTTER_TURN_OFF_TIME
    #     for shutter in shutters_to_open:
    #         self.shutter_config.shutter_dict[shutter].open(t)

    #     self.shutter_config = new_shutter_config
    #     return t

    # NOTE: If the shutter configuration is changed from the previous pulse, this will cut the previous pulse short
    # with the AOM by self.CONST_SHUTTER_TURN_ON_TIME in order to switch the shutters, and start the next pulse exactly at the t specified.
    # NOTE: The above note should be taken in context with the one below.
    def do_pulse(
        self, t, dur, shutter_config, ta_power, repump_power, close_all_shutters=False
    ):
        change_shutters = self.shutter_config != shutter_config

        if change_shutters:
            # NOTE:Adding this to t makes it so it doesn't cut the previous pulse short, but shifts the time of the next.
            t += self.CONST_SHUTTER_TURN_ON_TIME
            print("shutter config changed, adding time to account for switching")
            self.ta_aom_off(t - self.CONST_SHUTTER_TURN_ON_TIME)
            self.repump_aom_off(t - self.CONST_SHUTTER_TURN_ON_TIME)
            self.update_shutters(t, shutter_config)

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

        if (dur < self.CONST_MIN_SHUTTER_ON_TIME) and change_shutters:
            t += self.CONST_MIN_SHUTTER_ON_TIME - dur

        # If doing close_all_shutters, have to make sure that we aren't opening any of the ones we just closed in the next pulse.
        # Otherwise they won't be able to open in time unless there's enough delay between pulses.
        if close_all_shutters:
            print("closing all shutters")
            t += self.CONST_SHUTTER_TURN_OFF_TIME
            self.update_shutters(t, ShutterConfig.NONE)
            self.ta_aom_on(t, 1)
            self.repump_aom_on(t, 1)

        return t, t_aom_start

    def reset_to_mot_freq(self, t):
        self.ramp_repump_freq(t, duration=self.CONST_TA_VCO_RAMP_TIME, final=0)
        self.ramp_ta_freq(
            t, duration=self.CONST_TA_VCO_RAMP_TIME, final=shot_globals.mot_ta_detuning
        )
        t += self.CONST_TA_VCO_RAMP_TIME
        return t

    def reset_to_mot_on(self, t):
        self.ta_aom_on(t, shot_globals.mot_ta_power)
        self.repump_aom_on(t, shot_globals.mot_repump_power)
        self.update_shutters(t, ShutterConfig.MOT_FULL)
        t += self.CONST_SHUTTER_TURN_ON_TIME

        return t

    def parity_projection_pulse(self, t, dur):
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
            close_all_shutters=True,
        )
        return t, t_aom_start


class TweezerLaser:
    def __init__(self, t):
        self.tw_power = shot_globals.tw_power
        # self.intensity_servo_keep_on(t)
        self.start_tweezers(t)

    def start_tweezers(self, t):
        assert shot_globals.do_sequence_mode, "shot_globals.do_sequence_mode is False, running Fifo mode now. Set to True for sequence mode"
        spectrum_manager.start_card()
        t1 = spectrum_manager.start_tweezers(t)
        print("tweezer start time:", t1)
        self.aom_on(t, self.tw_power)

    def stop_tweezers(self, t):
        # stop tweezers
        t2 = spectrum_manager.stop_tweezers(t)
        print("tweezer stop time:", t2)

        # TODO: explain what this does, Answer: only when there is a dummy segment the spectrum card will actually output waveform, a bug related to the spectrum card server

        # dummy segment
        t1 = spectrum_manager.start_tweezers(t)
        print("tweezer start time:", t1)
        t += 2e-3
        t2 = spectrum_manager.stop_tweezers(t)
        print("tweezer stop time:", t2)
        spectrum_manager.stop_card(t)
        return t

    def intensity_servo_keep_on(self, t):
        """keep the AOM digital high for intensity servo"""
        self.aom_on(t, 1)

    def aom_on(self, t, const):
        """Turn on the tweezer beam using aom"""
        devices.tweezer_aom_digital.go_high(t)  # digital on
        devices.tweezer_aom_analog.constant(t, const)  # analog on
        self.tw_power = const

    def aom_off(self, t):
        """Turn off the tweezer beam using aom"""
        devices.tweezer_aom_digital.go_low(t)  # digital off
        devices.tweezer_aom_analog.constant(t, 0)  # analog off
        self.tw_power = 0

    def ramp_power(self, t, dur, final_power):
        devices.tweezer_aom_analog.ramp(
            t, duration=dur, initial=self.tw_power, final=final_power, samplerate=1e5
        )

    def sine_mod_power(self, t, dur, amp, freq):
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
    def __init__(self, t):
        CONST_SPECTRUM_UWAVE_CABLE_ATTEN = (
            4.4  # cable attenutation, dB  meausred at 300 MHz
        )
        self.mw_detuning = shot_globals.mw_detuning  # tune the microwave detuning here
        self.uwave_dds_switch_on = True
        self.uwave_absorp_switch_on = False
        self.spectrum_uwave_power = -1  # dBm power set at the input of dds switch, this power is set to below the amplifier damage threshold
        devices.uwave_dds_switch.go_high(
            t
        )  # dds_switch always on, can be off if need further higher distinguishing ratio
        devices.uwave_absorp_switch.go_low(
            t
        )  # absorp switch only on when sending pulse
        devices.spectrum_uwave.set_mode(
            replay_mode=b"sequence",
            channels=[
                {
                    "name": "microwaves",
                    "power": self.spectrum_uwave_power
                    + CONST_SPECTRUM_UWAVE_CABLE_ATTEN,
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
        )  # spectrum setup for microwaves & mmwaves, 1st channel for Hyperfine splitting of ground state, 2nd channel for mmwaves on Rydberg levels

    def do_pulse(self, t, dur):
        """do microwave pulse"""
        CONST_SPECTRUM_CARD_OFFSET = (
            52.8e-6  # the delay time between spectrum card output and trigger
        )

        t += CONST_SPECTRUM_CARD_OFFSET
        devices.uwave_absorp_switch.go_high(t)
        self.uwave_absorp_switch_on = True
        devices.spectrum_uwave.single_freq(
            t - CONST_SPECTRUM_CARD_OFFSET,
            duration=dur,
            freq=spec_freq_calib(self.mw_detuning),
            amplitude=0.99,
            phase=0,
            ch=0,
            loops=1,
        )

        t += dur
        devices.uwave_absorp_switch.go_low(t)
        self.uwave_absorp_switch_on = False

        return t

    def reset_spectrum(self, t):
        """stop microwave using dummy segment because of spectrum card, you have to send two pulses to make it work"""
        # dummy segment ####
        devices.spectrum_uwave.single_freq(
            t, duration=100e-6, freq=10**6, amplitude=0.99, phase=0, ch=0, loops=1
        )  # dummy segment
        devices.spectrum_uwave.stop()

        return t + 100e-6


class RydLasers:
    def __init__(self, t):
        # Keep the intensity servo on, regardless of BLACs settings
        self.blue_intensity_servo_keep_on(t)
        self.red_intensity_servo_keep_on(t)

    def blue_intensity_servo_keep_on(self, t):
        """keep the AOM digital high for intensity servo"""
        self.blue_servo_aom_on(t, 0)

    def red_intensity_servo_keep_on(self, t):
        """keep the AOM digital high for intensity servo"""
        self.red_servo_aom_on(t, 0)

    def blue_servo_aom_on(self, t, const):
        devices.moglabs_456_aom_digital.go_high(t)  # digital on
        devices.moglabs_456_aom_analog.constant(t, const)  # analog to const
        self.blue_power = const

    def blue_servo_aom_off(self, t):
        devices.moglabs_456_aom_digital.go_low(t)  # digital off
        devices.moglabs_456_aom_analog.constant(t, 0)  # analog off
        self.blue_power = 0

    def blue_pulse_aom_on(self, t, const):
        devices.octagon_456_aom_digital.go_high(t)  # digital on
        devices.octagon_456_aom_analog.constant(t, const)  # analog to const
        self.blue_power = const

    def blue_pulse_aom_off(self, t):
        devices.octagon_456_aom_digital.go_low(t)  # digital off
        devices.octagon_456_aom_analog.constant(t, 0)  # analog off
        self.blue_power = 0

    def red_servo_aom_on(self, t, const):
        devices.ipg_1064_aom_digital.go_high(t)  # digital on
        devices.ipg_1064_aom_analog.constant(t, const)  # analog to const
        self.red_power = const

    def red_servo_aom_off(self, t):
        devices.ipg_1064_aom_digital.go_low(t)  # digital off
        devices.ipg_1064_aom_analog.constant(t, 0)  # analog off
        self.red_power = 0

    def red_pulse_aom_on(self, t, const):
        devices.pulse_1064_digital.go_high(t)  # digital on
        devices.pulse_1064_analog.constant(t, const)  # analog to const
        self.red_power = const

    def red_pulse_aom_off(self, t):
        devices.pulse_1064_digital.go_low(t)  # digital off
        devices.pulse_1064_analog.constant(t, 0)  # analog off
        self.red_power = 0

    def blue_mirror_1_position(self, t):
        devices.mirror_1_horizontal.constant(
            t, shot_globals.ryd_456_mirror_1_h_position
        )
        devices.mirror_1_vertical.constant(t, shot_globals.ryd_456_mirror_1_v_position)

    def blue_mirror_2_position(self, t):
        devices.mirror_2_horizontal.constant(
            t, shot_globals.ryd_456_mirror_2_h_position
        )
        devices.mirror_2_vertical.constant(t, shot_globals.ryd_456_mirror_2_v_position)

    def red_mirror_1_position(self, t):
        devices.mirror_3_horizontal.constant(
            t, shot_globals.ryd_1064_mirror_1_h_position
        )
        devices.mirror_3_vertical.constant(t, shot_globals.ryd_1064_mirror_1_v_position)

    def red_mirror_2_position(self, t):
        devices.mirror_4_horizontal.constant(
            t, shot_globals.ryd_1064_mirror_2_h_position
        )
        devices.mirror_4_vertical.constant(t, shot_globals.ryd_1064_mirror_2_v_position)


class UVLamps:
    def __init__(self, t):
        # Turn off UV lamps
        devices.uv_switch.go_low(t)

    def uv_pulse(self, t, dur):
        """Flash the UV LED lamps for dur seconds"""
        devices.uv_switch.go_high(t)
        t += dur
        devices.uv_switch.go_low(t)
        return t


class BField:
    CONST_COIL_OFF_TIME: ClassVar[float] = 1.4e-3  # minimum time for the MOT coil to be off
    CONST_COIL_RAMP_TIME: ClassVar[float] = 100e-6  # ramp time from initial field to final field
    CONST_BIPOLAR_COIL_FLIP_TIME: ClassVar[float] = 10e-3  # the time takes to flip the polarity of the coil
    CONST_COIL_FEEDBACK_OFF_TIME: ClassVar[float] = (
        4.5e-3  # how long to turn off the feedback of circuit when flipping polarity
    )
    def __init__(self, t):
        self.bias_x_voltage = shot_globals.mot_x_coil_voltage
        self.bias_y_voltage = shot_globals.mot_y_coil_voltage
        self.bias_z_voltage = shot_globals.mot_z_coil_voltage
        self.mot_coils_on = shot_globals.do_mot_coil
        self.mot_coils_on_current = 10 / 6

        # Same question as for Dline_lasers, should we automatically initialize the hardware here or in a separate function we can call?

        # initialize bias_field variable to None
        # self.bias_field = None

        devices.x_coil_current.constant(t, self.bias_x_voltage)
        devices.y_coil_current.constant(t, self.bias_y_voltage)
        devices.z_coil_current.constant(t, self.bias_z_voltage)

        if self.mot_coils_on:
            devices.mot_coil_current_ctrl.constant(t, self.mot_coils_on_current)
        else:
            devices.mot_coil_current_ctrl.constant(t, 0)

        # coil_dict: dict[str, labscript.Analogout] = {
        #     "x": devices.x_coil_current,
        #     "y": devices.y_coil_current,
        #     "z": devices.z_coil_current,
        # }
        # coil_feedback_dict: dict[str, labscript.Digitalout] = {
        #     "x": devices.x_coil_feedback_off,
        #     "y": devices.y_coil_feedback_off,
        #     "z": devices.z_coil_feedback_off,
        # }
        # TODO: make the flip polarity a single function for all 3 coils instead of 3 functions

    def _x_coil_flip_polarity(self, t, final):
        coil_voltage_mid_abs = 0.03
        coil_voltage_mid = np.sign(final) * coil_voltage_mid_abs
        total_coil_flip_ramp_time = self.CONST_BIPOLAR_COIL_FLIP_TIME + self.CONST_COIL_RAMP_TIME
        t += devices.x_coil_current.ramp(
            t,
            duration=self.CONST_COIL_RAMP_TIME / 2,
            initial=self.bias_x_voltage,
            final=coil_voltage_mid,  # sligtly negative voltage to trigger the polarity change
            samplerate=1e5,
        )
        devices.x_coil_feedback_off.go_high(t)
        devices.x_coil_feedback_off.go_low(t + self.CONST_COIL_FEEDBACK_OFF_TIME)
        devices.x_coil_current.constant(t, coil_voltage_mid)
        t += self.CONST_BIPOLAR_COIL_FLIP_TIME

        t += devices.x_coil_current.ramp(
            t,
            duration=self.CONST_COIL_RAMP_TIME / 2,
            initial=coil_voltage_mid,
            final=final,  # 0 mG
            samplerate=1e5,
        )

        t -= total_coil_flip_ramp_time  # subtract to the begining tp set other coils

        # Update internal state
        self.bias_x_voltage = final

        return t

    def _y_coil_flip_polarity(self, t, final):
        coil_voltage_mid_abs = 0.03
        coil_voltage_mid = np.sign(final) * coil_voltage_mid_abs
        total_coil_flip_ramp_time = self.CONST_BIPOLAR_COIL_FLIP_TIME + self.CONST_COIL_RAMP_TIME
        t += devices.y_coil_current.ramp(
            t,
            duration=self.CONST_COIL_RAMP_TIME / 2,
            initial=self.bias_y_voltage,
            final=coil_voltage_mid,  # sligtly negative voltage to trigger the polarity change
            samplerate=1e5,
        )
        devices.y_coil_feedback_off.go_high(t)
        print("turn coil feedback off at time t = ", t)
        devices.y_coil_feedback_off.go_low(t + self.CONST_COIL_FEEDBACK_OFF_TIME)
        print(
            "turn coil feedback back on at time t = ", t + self.CONST_COIL_FEEDBACK_OFF_TIME
        )
        devices.y_coil_current.constant(t, coil_voltage_mid)
        t += self.CONST_BIPOLAR_COIL_FLIP_TIME

        t += devices.y_coil_current.ramp(
            t,
            duration=self.CONST_COIL_RAMP_TIME / 2,
            initial=coil_voltage_mid,
            final=final,  # 0 mG
            samplerate=1e5,
        )

        t -= total_coil_flip_ramp_time  # subtract to the begining tp set other coils

        # Update internal state
        self.bias_y_voltage = final

        return t

    def _z_coil_flip_polarity(self, t, final):
        coil_voltage_mid_abs = 0.03
        coil_voltage_mid = np.sign(final) * coil_voltage_mid_abs
        total_coil_flip_ramp_time = self.CONST_BIPOLAR_COIL_FLIP_TIME + self.CONST_COIL_RAMP_TIME
        t += devices.z_coil_current.ramp(
            t,
            duration=self.CONST_COIL_RAMP_TIME / 2,
            initial=self.bias_z_voltage,
            final=coil_voltage_mid,  # sligtly negative voltage to trigger the polarity change
            samplerate=1e5,
        )
        devices.z_coil_feedback_off.go_high(t)
        devices.z_coil_feedback_off.go_low(t + self.CONST_COIL_FEEDBACK_OFF_TIME)
        devices.z_coil_current.constant(t, coil_voltage_mid)
        t += self.CONST_BIPOLAR_COIL_FLIP_TIME

        t += devices.z_coil_current.ramp(
            t,
            duration=self.CONST_COIL_RAMP_TIME / 2,
            initial=coil_voltage_mid,
            final=final,  # 0 mG
            samplerate=1e5,
        )

        t -= total_coil_flip_ramp_time  # subtract to the begining tp set other coils

        # Update internal state
        self.bias_z_voltage = final

        return t

    def ramp_bias_field(self, t, bias_field_vector=None, voltage_vector=None):
        # bias_field_vector should be a tuple of the form (x,y,z)
        # Need to start the ramp earlier if the voltage changes sign
        if bias_field_vector is not None:
            voltage_vector = [
                biasx_calib(bias_field_vector[0]),
                biasy_calib(bias_field_vector[1]),
                biasz_calib(bias_field_vector[2]),
            ]

        t_x_coil, t_y_coil, t_z_coil = (
            t
            - self.CONST_BIPOLAR_COIL_FLIP_TIME
            * int(self.bias_x_voltage * voltage_vector[0] < 0),
            t
            - self.CONST_BIPOLAR_COIL_FLIP_TIME
            * int(self.bias_y_voltage * voltage_vector[1] < 0),
            t
            - self.CONST_BIPOLAR_COIL_FLIP_TIME
            * int(self.bias_z_voltage * voltage_vector[2] < 0),
        )

        if np.sign(self.bias_x_voltage * voltage_vector[0]) > 0:
            devices.x_coil_current.ramp(
                t_x_coil,
                duration=self.CONST_COIL_RAMP_TIME,
                initial=self.bias_x_voltage,
                final=voltage_vector[0],
                samplerate=1e5,
            )
        else:  # coil flip the control voltage sign
            t = self._x_coil_flip_polarity(t_x_coil, voltage_vector[0])

        if np.sign(self.bias_y_voltage * voltage_vector[1]) > 0:
            devices.y_coil_current.ramp(
                t_y_coil,
                duration=self.CONST_COIL_RAMP_TIME,
                initial=self.bias_y_voltage,
                final=voltage_vector[1],  # 0 mG
                samplerate=1e5,
            )
        else:  # coil flip the control voltage sign
            t = self._y_coil_flip_polarity(t_y_coil, voltage_vector[1])

        if np.sign(self.bias_z_voltage * voltage_vector[2]) > 0:
            devices.z_coil_current.ramp(
                t_z_coil,
                duration=self.CONST_COIL_RAMP_TIME,
                initial=self.bias_z_voltage,
                final=voltage_vector[2],  # 0 mG
                samplerate=1e5,
            )
        else:  # coil flip the control voltage sign
            t = self._z_coil_flip_polarity(t_z_coil, voltage_vector[2])

        # check if any of the bias coil polarity/sign is flipped
        cond_x = np.sign(voltage_vector[0] * biasx_calib(self.bias_x_voltage)) < 0
        cond_y = np.sign(voltage_vector[1] * biasy_calib(self.bias_y_voltage)) < 0
        cond_z = np.sign(voltage_vector[2] * biasz_calib(self.bias_z_voltage)) < 0
        if cond_x or cond_y or cond_z:
            # if any bias coils are flipped, add extra time to account for the settling time
            t += self.CONST_BIPOLAR_COIL_FLIP_TIME

        # TODO: add the inverse function of bias_i_calib
        # otherwise, if only voltage vector is provided on input, the bias field will not be updated
        # if bias_field_vector is not None:
        #     self.bias_field = bias_field_vector
        self.bias_x_voltage = voltage_vector[0]
        self.bias_y_voltage = voltage_vector[1]
        self.bias_z_voltage = voltage_vector[2]

        t += self.CONST_COIL_RAMP_TIME
        return t

    # def ramp_bias_field_voltage(self, t, voltage_vector):
    #     #B_field_vector should be a tuple of the form (x,y,z)
    #     # Need to start the ramp earlier if the voltage changes sign
    #     t_x_coil, t_y_coil, t_z_coil = (t - 4e-3*int(self.bias_x_voltage * voltage_vector[0] < 0),
    #                                     t - 4e-3*int(self.bias_y_voltage * voltage_vector[1] < 0),
    #                                     t - 4e-3*int(self.bias_z_voltage * voltage_vector[2] < 0))

    #     devices.x_coil_current.ramp(
    #         t_x_coil,
    #         duration=self.CONST_COIL_RAMP_TIME,
    #         initial=self.bias_x_voltage,
    #         final=voltage_vector[0],
    #         samplerate=1e5,
    #     )

    #     devices.y_coil_current.ramp(
    #         t_y_coil,
    #         duration=self.CONST_COIL_RAMP_TIME,
    #         initial=self.bias_y_voltage,
    #         final=voltage_vector[1],
    #         samplerate=1e5,
    #     )

    #     devices.z_coil_current.ramp(
    #         t_z_coil,
    #         duration=self.CONST_COIL_RAMP_TIME,
    #         initial=self.bias_z_voltage,
    #         final=voltage_vector[2],
    #         samplerate=1e5,
    #     )
    #     # TODO: add the inverse function of bias_i_calib
    #     # self.B_field = B_field_vector
    #     self.bias_x_voltage = voltage_vector[0]
    #     self.bias_y_voltage = voltage_vector[1]
    #     self.bias_z_voltage = voltage_vector[2]

    #     t += self.CONST_COIL_RAMP_TIME
    #     return t

    def switch_mot_coils(self, t):
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

        t += self.CONST_COIL_RAMP_TIME
        t += self.CONST_COIL_OFF_TIME
        return t

    def get_op_bias_fields(self):
        """Compute the proper bias fields for a given quantization angle from shot globals"""
        op_biasx_field = (
            shot_globals.op_bias_amp
            * np.cos(shot_globals.op_bias_phi / 180 * np.pi)
            * np.sin(shot_globals.op_bias_theta / 180 * np.pi)
        )
        op_biasy_field = (
            shot_globals.op_bias_amp
            * np.sin(shot_globals.op_bias_phi / 180 * np.pi)
            * np.sin(shot_globals.op_bias_theta / 180 * np.pi)
        )
        op_biasz_field = shot_globals.op_bias_amp * np.cos(
            shot_globals.op_bias_theta / 180 * np.pi
        )

        return op_biasx_field, op_biasy_field, op_biasz_field


class Camera:
    def __init__(self, t):
        self.type = None

    def set_type(self, type):
        # type = "MOT_manta" or "tweezer_manta" or "kinetix"
        self.type = type

    def expose(self, t, exposure_time, trigger_local_manta=False):
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


class EField:
    def __init__(self, t):
        pass
