# -*- coding: utf-8 -*-
"""
Created on Thu Feb 16 11:33:13 2023

@author: sslab
"""
from __future__ import annotations
import sys
from typing import ClassVar
root_path = r"X:\userlib\labscriptlib"

if root_path not in sys.path:
    sys.path.append(root_path)

import numpy as np
from labscriptlib.shot_globals import shot_globals
#from shot_globals import shot_globals
from spectrum_manager_fifo import spectrum_manager_fifo
from spectrum_manager import spectrum_manager
from calibration import ta_freq_calib, repump_freq_calib, biasx_calib, biasy_calib, biasz_calib
from connection_table import devices
import labscript

spcm_sequence_mode = shot_globals.do_sequence_mode

if __name__ == "__main__":
    devices.initialize()

# fixed parameters in the script
CONST_COIL_OFF_TIME = 1.4e-3  # minimum time for the MOT coil to be off
CONST_TA_VCO_RAMP_TIME = 1.2e-4
CONST_MIN_SHUTTER_OFF_TIME = 6.28e-3  # minimum time for shutter to be off and on again
CONST_MIN_SHUTTER_ON_TIME = 3.6e-3  # minimum time for shutter to be on
CONST_SHUTTER_TURN_ON_TIME  = 2e-3 # for shutter take from start to close to fully close
CONST_SHUTTER_TURN_OFF_TIME = 2e-3 # for shutter take from start to open to fully open
CONST_TA_PUMPING_DETUNING = -251  # MHz 4->4 tansition
CONST_REPUMP_DEPUMPING_DETUNING = -201.24  # MHz 3->3 transition
CONST_BIPOLAR_COIL_FLIP_TIME = 10e-3 # the time takes to flip the polarity of the coil
CONST_COIL_FEEDBACK_OFF_TIME = 4.5e-3 # how long to turn off the feedback of circuit when flipping polarity
CONST_COIL_RAMP_TIME = 100e-6

# lasers_852 =  D2Lasers()
# lasers_852.pulse_imaging(t=300e-6, duration=100e-6)
# lasers_852.pulse_ta(t=450e-6, duration=100e-6, hold_shutter_open = True)
# pulser_ta(t=600e-6, duration=100e-6)


# MOTconfig = {shutter1: True, shutter2: False, shutter3: True}
# imagconfig = {shutter1: False, shutter2: True, }

from enum import Enum, Flag, auto


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
        repump_config = (cls.REPUMP if do_repump else cls.NONE)
        label = shot_globals.imaging_label

        # TODO: change handling of labels to make full default and raise error when not one of the options
        if shot_globals.do_mot_beams_during_imaging:
            if label == "z":
                shutter_config = cls.MOT_Z | repump_config
            elif label == "xy":
                shutter_config = cls.MOT_XY | repump_config
            else:
                shutter_config = cls.MOT_FULL | repump_config

        # If you're trying to do in-situ imaging, you want to image faster than switch shutters allows for,
        # so you can't do imaging beam imaging
        elif shot_globals.do_img_beams_during_imaging and not shot_globals.do_molasses_in_situ_check:
            if label == "z":
                shutter_config = cls.IMG_Z | repump_config
            elif label == "xy":
                shutter_config = cls.IMG_XY | repump_config
            else:
                shutter_config = cls.IMG_FULL | repump_config

        else:
            shutter_config = cls.NONE

        return shutter_config


# Hardware control classes
#-------------------------------------------------------------------------------
class D2Lasers:
    shutter_config: ShutterConfig

    def __init__(self, t):
        # Tune to MOT frequency, full power
        self.ta_freq = shot_globals.mot_ta_detuning
        self.repump_freq = 0# shot_globals.mot_repump_detuning
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

    #Move freq_calib to a function within here? Probably not needed.
    def ramp_ta_freq(self, t, duration, final):
        # TODO: check that duration statement here is valid for optical pumping
        duration = max(CONST_TA_VCO_RAMP_TIME, duration)
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
        duration = max(CONST_TA_VCO_RAMP_TIME, duration)
        devices.repump_vco.ramp(
            t,
            duration=duration,
            initial=repump_freq_calib(self.repump_freq),
            final=repump_freq_calib(final),
            samplerate=4e5,
        )
        self.repump_freq = final

    def ta_aom_off(self, t):
        """ Turn off the ta beam using aom """
        devices.ta_aom_digital.go_low(t)  # digital off
        devices.ta_aom_analog.constant(t, 0)  # analog off
        self.ta_power = 0

    def ta_aom_on(self, t, const):
        """ Turn on the ta beam using aom """
        devices.ta_aom_digital.go_high(t)  # digital on
        devices.ta_aom_analog.constant(t, const)  # analog to const
        self.ta_power = const

    def repump_aom_off(self, t):
        """ Turn off the repump beam using aom """
        devices.repump_aom_digital.go_low(t)  # digital off
        devices.repump_aom_analog.constant(t, 0)  # analog off
        self.repump_power = 0

    def repump_aom_on(self, t, const):
        """ Turn on the repump beam using aom """
        devices.repump_aom_digital.go_high(t)  # digital on
        devices.repump_aom_analog.constant(t, const)  # analog to const
        self.repump_power = const

    def ramp_ta_aom(self, t, dur, final_power):
        """ ramp ta power from current value to final power """
        devices.ta_aom_analog.ramp(
            t,
            duration=dur,
            initial=self.ta_power,
            final=final_power,
            samplerate=1e5,)

    def ramp_repump_aom(self, t, dur, final_power):
        """ ramp repump power from current value to final power """
        devices.repump_aom_analog.ramp(
            t,
            duration=dur,
            initial=self.repump_power,
            final=final_power,
            samplerate=1e5,)

    def update_shutters(self, t, new_shutter_config: ShutterConfig):
        changed_shutters = self.shutter_config ^ new_shutter_config

        shutters_to_open = changed_shutters & new_shutter_config
        shutters_to_close = changed_shutters & self.shutter_config

        # Can we put this somewhere nicer?
        basic_shutters = [ShutterConfig.TA, ShutterConfig.REPUMP, ShutterConfig.MOT_XY,
                          ShutterConfig.MOT_Z, ShutterConfig.IMG_XY, ShutterConfig.IMG_Z,
                          ShutterConfig.OPTICAL_PUMPING]

        shutter_dict: dict[ShutterConfig, labscript.Shutter] = {
            ShutterConfig.TA: devices.ta_shutter,
            ShutterConfig.REPUMP: devices.repump_shutter,
            ShutterConfig.MOT_XY: devices.mot_xy_shutter,
            ShutterConfig.MOT_Z: devices.mot_z_shutter,
            ShutterConfig.IMG_XY: devices.img_xy_shutter,
            ShutterConfig.IMG_Z: devices.img_z_shutter,
            ShutterConfig.OPTICAL_PUMPING: devices.optical_pump_shutter,}

        for shutter in basic_shutters:
            if shutter in shutters_to_open:
                shutter_dict[shutter].open(t)
            if shutter in shutters_to_close:
                shutter_dict[shutter].close(t)

        self.shutter_config = new_shutter_config
        #return t?

# NOTE: This version makes it so that the previous shutters are fully closed before opening the new shutters
    # def update_shutters(self, t, new_shutter_config: ShutterConfig):
    #     changed_shutters = self.shutter_config ^ new_shutter_config

    #     shutters_to_open = changed_shutters & new_shutter_config
    #     shutters_to_close = changed_shutters & self.shutter_config

    #     for shutter in shutters_to_close:
    #         self.shutter_config.shutter_dict[shutter].close(t)

    #     t += 2*CONST_SHUTTER_TURN_OFF_TIME
    #     for shutter in shutters_to_open:
    #         self.shutter_config.shutter_dict[shutter].open(t)

    #     self.shutter_config = new_shutter_config
    #     return t

    # NOTE: If the shutter configuration is changed from the previous pulse, this will cut the previous pulse short
    # with the AOM by CONST_SHUTTER_TURN_ON_TIME in order to switch the shutters, and start the next pulse exactly at the t specified.
    # NOTE: The above note should be taken in context with the one below.
    def do_pulse(self, t, dur, shutter_config, ta_power, repump_power, close_all_shutters=False):
        change_shutters = self.shutter_config != shutter_config

        if change_shutters:
            # NOTE:Adding this to t makes it so it doesn't cut the previous pulse short, but shifts the time of the next.
            t += CONST_SHUTTER_TURN_ON_TIME
            print("shutter config changed, adding time to account for switching")
            self.ta_aom_off(t - CONST_SHUTTER_TURN_ON_TIME)
            self.repump_aom_off(t - CONST_SHUTTER_TURN_ON_TIME)
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

        if (dur < CONST_MIN_SHUTTER_ON_TIME) and change_shutters:
            t += CONST_MIN_SHUTTER_ON_TIME - dur

        # If doing close_all_shutters, have to make sure that we aren't opening any of the ones we just closed in the next pulse.
        # Otherwise they won't be able to open in time unless there's enough delay between pulses.
        if close_all_shutters:
            print("closing all shutters")
            self.update_shutters(t, ShutterConfig.NONE)
            t += CONST_SHUTTER_TURN_OFF_TIME
            self.ta_aom_on(t, 1)
            self.repump_aom_on(t, 1)

        return t, t_aom_start

    def reset_to_mot_freq(self, t):
        self.ramp_repump_freq(t, duration=CONST_TA_VCO_RAMP_TIME,
                              final=0)
        self.ramp_ta_freq(t, duration=CONST_TA_VCO_RAMP_TIME,
                          final=shot_globals.mot_ta_detuning)
        t += CONST_TA_VCO_RAMP_TIME
        return t

    def reset_to_mot_on(self, t):
        self.ta_aom_on(t, shot_globals.mot_ta_power)
        self.repump_aom_on(t, shot_globals.mot_repump_power)
        self.update_shutters(t, ShutterConfig.MOT_FULL)
        t += CONST_SHUTTER_TURN_ON_TIME

        return t

    def parity_projection_pulse(self, t, dur):
        self.ramp_ta_freq(t, duration=0, final=shot_globals.bm_parity_projection_ta_detuning)
        t += CONST_TA_VCO_RAMP_TIME
        # TODO: is this a TA pulse only? Or is repump also supposed to be on?
        # TODO: if so, is shot_globals.bm_parity_projection_repump_power ever used. Perhaps it should be deleted
        t, t_aom_start = self.do_pulse(t, dur, ShutterConfig.MOT_TA,
                      shot_globals.bm_parity_projection_ta_power,
                      0,
                      close_all_shutters=True)
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
        print('tweezer start time:', t1)
        self.aom_on(t, self.tw_power)

    def stop_tweezers(self, t):
        # stop tweezers
        t2 = spectrum_manager.stop_tweezers(t)
        print('tweezer stop time:', t2)

        # TODO: explain what this does
        ##### dummy segment ######
        t1 = spectrum_manager.start_tweezers(t)
        print('tweezer start time:', t1)
        t += 2e-3
        t2 = spectrum_manager.stop_tweezers(t)
        print('tweezer stop time:',t2)
        spectrum_manager.stop_card(t)
        return t

    def intensity_servo_keep_on(self, t):
        ''' keep the AOM digital high for intensity servo '''
        self.aom_on(t, 1)

    def aom_on(self, t, const):
        """ Turn on the tweezer beam using aom """
        devices.tweezer_aom_digital.go_high(t)  # digital off
        devices.tweezer_aom_analog.constant(t, const)  # analog off
        self.tw_power = const

    def aom_off(self, t):
        """ Turn off the tweezer beam using aom """
        devices.tweezer_aom_digital.go_low(t)  # digital off
        devices.tweezer_aom_analog.constant(t, 0)  # analog off
        self.tw_power = 0

    def ramp_power(self, t, dur, final_power):
        devices.tweezer_aom_analog.ramp(
            t,
            duration=dur,
            initial=self.tw_power,
            final=final_power,
            samplerate=1e5
        )

    def sine_mod_power(self, t, dur, amp, freq):
        devices.tweezer_aom_analog.sine(
            t,
            duration=dur,
            amplitude=amp,
            angfreq=2*np.pi*freq,
            phase=0,
            dc_offset=self.tw_power,
            samplerate=1e5
        )


class Microwave:
    def __init__(self, t):
        # Shutoff microwaves?
        devices.uwave_dds_switch.go_high(t)
        devices.uwave_absorp_switch.go_low(t)

class RydLasers:
    def __init__(self, t):
        # Keep the intensity servo on, regardless of BLACs settings
        self.blue_intensity_servo_keep_on(t)
        self.red_intensity_servo_keep_on(t)

    def blue_intensity_servo_keep_on(self, t):
        ''' keep the AOM digital high for intensity servo '''
        self.blue_servo_aom_on(t, 0)

    def red_intensity_servo_keep_on(self, t):
        ''' keep the AOM digital high for intensity servo '''
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
        devices.mirror_1_horizontal.constant(t, shot_globals.ryd_456_mirror_1_h_position)
        devices.mirror_1_vertical.constant(t, shot_globals.ryd_456_mirror_1_v_position)

    def blue_mirror_2_position(self, t):
        devices.mirror_2_horizontal.constant(t, shot_globals.ryd_456_mirror_2_h_position)
        devices.mirror_2_vertical.constant(t, shot_globals.ryd_456_mirror_2_v_position)

    def red_mirror_1_position(self, t):
        devices.mirror_3_horizontal.constant(t, shot_globals.ryd_1064_mirror_1_h_position)
        devices.mirror_3_vertical.constant(t, shot_globals.ryd_1064_mirror_1_v_position)

    def red_mirror_2_position(self, t):
        devices.mirror_4_horizontal.constant(t, shot_globals.ryd_1064_mirror_2_h_position)
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
    def __init__(self, t):
        self.bias_x_voltage = shot_globals.mot_x_coil_voltage
        self.bias_y_voltage = shot_globals.mot_y_coil_voltage
        self.bias_z_voltage = shot_globals.mot_z_coil_voltage
        self.mot_coils_on = shot_globals.do_mot_coil
        self.mot_coils_on_current = 10/6

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

    def _x_coil_flip_polarity(self, t, final):
        coil_voltage_mid_abs = 0.03
        coil_voltage_mid = np.sign(final) * coil_voltage_mid_abs
        total_coil_flip_ramp_time = CONST_BIPOLAR_COIL_FLIP_TIME + CONST_COIL_RAMP_TIME
        t += devices.x_coil_current.ramp(
            t,
            duration=CONST_COIL_RAMP_TIME/2,
            initial=self.bias_x_voltage,
            final=coil_voltage_mid,  # sligtly negative voltage to trigger the polarity change
            samplerate=1e5,
        )
        devices.x_coil_feedback_off.go_high(t)
        devices.x_coil_feedback_off.go_low(t + CONST_COIL_FEEDBACK_OFF_TIME)
        devices.x_coil_current.constant(t, coil_voltage_mid)
        t += CONST_BIPOLAR_COIL_FLIP_TIME

        t += devices.x_coil_current.ramp(
            t,
            duration=CONST_COIL_RAMP_TIME/2,
            initial=coil_voltage_mid,
            final=final,  # 0 mG
            samplerate=1e5,
        )

        t -= total_coil_flip_ramp_time # subtract to the begining tp set other coils

        # Update internal state
        self.bias_x_voltage = final

        return t

    def _y_coil_flip_polarity(self, t, final):
        coil_voltage_mid_abs = 0.03
        coil_voltage_mid = np.sign(final) * coil_voltage_mid_abs
        total_coil_flip_ramp_time = CONST_BIPOLAR_COIL_FLIP_TIME + CONST_COIL_RAMP_TIME
        t += devices.y_coil_current.ramp(
            t,
            duration=CONST_COIL_RAMP_TIME/2,
            initial=self.bias_y_voltage,
            final=coil_voltage_mid,  # sligtly negative voltage to trigger the polarity change
            samplerate=1e5,
        )
        devices.y_coil_feedback_off.go_high(t)
        print('turn coil feedback off at time t = ', t)
        devices.y_coil_feedback_off.go_low(t + CONST_COIL_FEEDBACK_OFF_TIME)
        print('turn coil feedback back on at time t = ', t + CONST_COIL_FEEDBACK_OFF_TIME)
        devices.y_coil_current.constant(t, coil_voltage_mid)
        t += CONST_BIPOLAR_COIL_FLIP_TIME

        t += devices.y_coil_current.ramp(
            t,
            duration=CONST_COIL_RAMP_TIME/2,
            initial=coil_voltage_mid,
            final=final,  # 0 mG
            samplerate=1e5,
        )

        t -= total_coil_flip_ramp_time # subtract to the begining tp set other coils

        # Update internal state
        self.bias_y_voltage = final

        return t

    def _z_coil_flip_polarity(self, t, final):
        coil_voltage_mid_abs = 0.03
        coil_voltage_mid = np.sign(final) * coil_voltage_mid_abs
        total_coil_flip_ramp_time = CONST_BIPOLAR_COIL_FLIP_TIME + CONST_COIL_RAMP_TIME
        t += devices.z_coil_current.ramp(
            t,
            duration=CONST_COIL_RAMP_TIME/2,
            initial=self.bias_z_voltage,
            final=coil_voltage_mid,  # sligtly negative voltage to trigger the polarity change
            samplerate=1e5,
        )
        devices.z_coil_feedback_off.go_high(t)
        devices.z_coil_feedback_off.go_low(t + CONST_COIL_FEEDBACK_OFF_TIME)
        devices.z_coil_current.constant(t, coil_voltage_mid)
        t += CONST_BIPOLAR_COIL_FLIP_TIME

        t += devices.z_coil_current.ramp(
            t,
            duration=CONST_COIL_RAMP_TIME/2,
            initial=coil_voltage_mid,
            final=final,  # 0 mG
            samplerate=1e5,
        )

        t -= total_coil_flip_ramp_time # subtract to the begining tp set other coils

        # Update internal state
        self.bias_z_voltage = final

        return t

    def ramp_bias_field(self, t, bias_field_vector=None, voltage_vector=None):
        # bias_field_vector should be a tuple of the form (x,y,z)
        # Need to start the ramp earlier if the voltage changes sign
        if bias_field_vector is not None:
            voltage_vector = [biasx_calib(bias_field_vector[0]),
                              biasy_calib(bias_field_vector[1]),
                              biasz_calib(bias_field_vector[2])]

        t_x_coil, t_y_coil, t_z_coil = (t - CONST_BIPOLAR_COIL_FLIP_TIME*int(self.bias_x_voltage * voltage_vector[0] < 0),
                                        t - CONST_BIPOLAR_COIL_FLIP_TIME*int(self.bias_y_voltage * voltage_vector[1] < 0),
                                        t - CONST_BIPOLAR_COIL_FLIP_TIME*int(self.bias_z_voltage * voltage_vector[2] < 0))

        if np.sign(self.bias_x_voltage * voltage_vector[0]) > 0:
            devices.x_coil_current.ramp(
                t_x_coil,
                duration=CONST_COIL_RAMP_TIME,
                initial=self.bias_x_voltage,
                final=voltage_vector[0],
                samplerate=1e5,
            )
        else: # coil flip the control voltage sign
            t = self._x_coil_flip_polarity(t_x_coil, voltage_vector[0])

        if np.sign(self.bias_y_voltage * voltage_vector[1]) > 0:
            devices.y_coil_current.ramp(
                t_y_coil,
                duration=CONST_COIL_RAMP_TIME,
                initial=self.bias_y_voltage,
                final=voltage_vector[1],  # 0 mG
                samplerate=1e5,
            )
        else: # coil flip the control voltage sign
            t = self._y_coil_flip_polarity(t_y_coil, voltage_vector[1])

        if np.sign(self.bias_z_voltage * voltage_vector[2]) > 0:
            devices.z_coil_current.ramp(
                t_z_coil,
                duration=CONST_COIL_RAMP_TIME,
                initial=self.bias_z_voltage,
                final=voltage_vector[2],  # 0 mG
                samplerate=1e5,
            )
        else: # coil flip the control voltage sign
            t = self._z_coil_flip_polarity(t_z_coil, voltage_vector[2])

        # check if any of the bias coil polarity/sign is flipped
        cond_x = (np.sign(voltage_vector[0]*biasx_calib(self.bias_x_voltage)) < 0)
        cond_y = (np.sign(voltage_vector[1]*biasy_calib(self.bias_y_voltage)) < 0)
        cond_z = (np.sign(voltage_vector[2]*biasz_calib(self.bias_z_voltage)) < 0)
        if cond_x or cond_y or cond_z:
            # if any bias coils are flipped, add extra time to account for the settling time
            t += CONST_BIPOLAR_COIL_FLIP_TIME

        # TODO: add the inverse function of bias_i_calib
        # otherwise, if only voltage vector is provided on input, the bias field will not be updated
        # if bias_field_vector is not None:
        #     self.bias_field = bias_field_vector
        self.bias_x_voltage = voltage_vector[0]
        self.bias_y_voltage = voltage_vector[1]
        self.bias_z_voltage = voltage_vector[2]

        t += CONST_COIL_RAMP_TIME
        return t

    # def ramp_bias_field_voltage(self, t, voltage_vector):
    #     #B_field_vector should be a tuple of the form (x,y,z)
    #     # Need to start the ramp earlier if the voltage changes sign
    #     t_x_coil, t_y_coil, t_z_coil = (t - 4e-3*int(self.bias_x_voltage * voltage_vector[0] < 0),
    #                                     t - 4e-3*int(self.bias_y_voltage * voltage_vector[1] < 0),
    #                                     t - 4e-3*int(self.bias_z_voltage * voltage_vector[2] < 0))

    #     devices.x_coil_current.ramp(
    #         t_x_coil,
    #         duration=CONST_COIL_RAMP_TIME,
    #         initial=self.bias_x_voltage,
    #         final=voltage_vector[0],
    #         samplerate=1e5,
    #     )

    #     devices.y_coil_current.ramp(
    #         t_y_coil,
    #         duration=CONST_COIL_RAMP_TIME,
    #         initial=self.bias_y_voltage,
    #         final=voltage_vector[1],
    #         samplerate=1e5,
    #     )

    #     devices.z_coil_current.ramp(
    #         t_z_coil,
    #         duration=CONST_COIL_RAMP_TIME,
    #         initial=self.bias_z_voltage,
    #         final=voltage_vector[2],
    #         samplerate=1e5,
    #     )
    #     # TODO: add the inverse function of bias_i_calib
    #     # self.B_field = B_field_vector
    #     self.bias_x_voltage = voltage_vector[0]
    #     self.bias_y_voltage = voltage_vector[1]
    #     self.bias_z_voltage = voltage_vector[2]

    #     t += CONST_COIL_RAMP_TIME
    #     return t

    def switch_mot_coils(self, t):
        if self.mot_coils_on:
            devices.mot_coil_current_ctrl.ramp(
                t,
                duration=CONST_COIL_RAMP_TIME,
                initial= self.mot_coils_on_current,
                final=0,
                samplerate=1e5,
            )
            self.mot_coils_on = False
        else:
            devices.mot_coil_current_ctrl.ramp(
                t,
                duration=CONST_COIL_RAMP_TIME,
                initial=0,
                final = self.mot_coils_on_current,
                samplerate=1e5,
            )
            self.mot_coils_on = True

        t += CONST_COIL_RAMP_TIME
        t += CONST_COIL_OFF_TIME
        return t

    def get_op_bias_fields(self):
        """ Compute the proper bias fields for a given quantization angle from shot globals """
        op_biasx_field = shot_globals.op_bias_amp * np.cos(shot_globals.op_bias_phi / 180 * np.pi) * np.sin(shot_globals.op_bias_theta / 180 * np.pi)
        op_biasy_field = shot_globals.op_bias_amp * np.sin(shot_globals.op_bias_phi / 180 * np.pi) * np.sin(shot_globals.op_bias_theta / 180 * np.pi)
        op_biasz_field = shot_globals.op_bias_amp * np.cos(shot_globals.op_bias_theta / 180 * np.pi)

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
                'manta419b',
                t,
                'atoms',
                exposure_time=exposure_time)

        if self.type == "tweezer_manta":
            devices.manta419b_tweezer.expose(
                'manta419b',
                t,
                'atoms',
                exposure_time=exposure_time,
            )

        if self.type == "kinetix":
            devices.kinetix.expose(
                'Kinetix',
                t,
                'atoms',
                exposure_time=exposure_time,
            )

class EField:
    def __init__(self, t):
        pass

#Sequence Classes
#-------------------------------------------------------------------------------

class MOTSequence:
    def __init__(self, t):
        # Standard initialization for hardware objects puts everything in
        # correct state/tuning to start loading the MOT
        self.D2Lasers_obj = D2Lasers(t)
        self.BField_obj = BField(t)
        self.Microwave_obj = Microwave(t)
        self.UVLamps_obj = UVLamps(t)
        self.Camera_obj = Camera(t)

    def do_mot(self, t, dur, close_all_shutters=False):
        if shot_globals.do_uv:
            _ = self.UVLamps_obj.uv_pulse(t, dur=shot_globals.uv_duration)
            # the uv duration should be determined for each dispenser current
            # generally, get superior loading in the 10s of milliseconds

        # if using a long UV duration, want to make sure that the MOT doesn't finish
        # loading leaving the UV is still on for imaging.
        dur = max(dur, shot_globals.uv_duration)
        t, _ = self.D2Lasers_obj.do_pulse(t, dur,
                                          ShutterConfig.MOT_FULL,
                                          shot_globals.mot_ta_power,
                                          shot_globals.mot_repump_power,
                                          close_all_shutters=close_all_shutters)

        return t

    def reset_mot(self, t):
        #B fields
        if not self.BField_obj.mot_coils_on:
            t = self.BField_obj.switch_mot_coils(t)

        mot_bias_voltages = (shot_globals.mot_x_coil_voltage,
                             shot_globals.mot_y_coil_voltage,
                             shot_globals.mot_z_coil_voltage)

        t = self.BField_obj.ramp_bias_field(t, voltage_vector=mot_bias_voltages)

        # Reset laser frequency and configuration
        t = self.D2Lasers_obj.reset_to_mot_freq(t)
        t = self.D2Lasers_obj.reset_to_mot_on(t)

        t += 1e-2

        return t

    def image_mot(self, t, close_all_shutters=False):
        # Move to on resonance, make sure AOM is off
        self.D2Lasers_obj.ramp_ta_freq(t, CONST_TA_VCO_RAMP_TIME, ta_freq_calib(0))
        t += CONST_TA_VCO_RAMP_TIME

        # Make sure coils are off
        if self.BField_obj.mot_coils_on:
            t = self.BField_obj.switch_mot_coils(t)

        self.Camera_obj.set_type("MOT_manta")
        self.Camera_obj.expose(t, shot_globals.mot_exposure_time)

        t, _ = self.D2Lasers_obj.do_pulse(t, shot_globals.mot_exposure_time, ShutterConfig.MOT_FULL, shot_globals.mot_ta_power,
                                        shot_globals.mot_repump_power, close_all_shutters = close_all_shutters)

        return t

    def _do_mot_in_situ_sequence(self, t, reset_mot=False):
        print("Running _do_mot_in_situ_sequence")

        print("MOT coils = ", self.BField_obj.mot_coils_on)
        # MOT loading time 500 ms
        mot_load_dur = 0.5
        t += CONST_SHUTTER_TURN_ON_TIME
        t = self.do_mot(t, mot_load_dur)

        t = self.image_mot(t)
        # Shutter does not need to be held open

        # Wait until the MOT disappear for background image
        t += 0.1
        t = self.image_mot(t)

        # Reset laser frequency so lasers do not jump frequency and come unlocked
        t = self.D2Lasers_obj.reset_to_mot_freq(t)

        if reset_mot:
            t = self.reset_mot(t)

        return t

    # TODO: Needs more experimental debugging. When should the shutter close? What timescales should we expect the MOT to disperse in?
    def _do_mot_tof_sequence(self, t, reset_mot = False):
        print("Running _do_mot_tof_sequence")

        print("MOT coils = ", self.BField_obj.mot_coils_on)
        # MOT loading time 500 ms
        mot_load_dur = 0.5

        t += CONST_SHUTTER_TURN_ON_TIME

        t = self.do_mot(t, mot_load_dur)

        # assert shot_globals.mot_tof_imaging_delay > CONST_MIN_SHUTTER_OFF_TIME, "time of flight too short for shutter"
        t += shot_globals.mot_tof_imaging_delay

        t = self.image_mot(t)
        # Shutter does not need to be held open

        # Wait until the MOT disappear for background image
        t += 0.1
        t = self.image_mot(t)

        # Reset laser frequency so lasers do not jump frequency and come unlocked
        t = self.D2Lasers_obj.reset_to_mot_freq(t)

        if reset_mot:
            t = self.reset_mot(t)

        return t

    # Molasses sequences
    def ramp_to_molasses(self, t):
        # detuning is ramped slowly here (duration = 1e-3) because atoms
        # see the light during the frequency ramp.
        self.D2Lasers_obj.ramp_ta_freq(t, 1e-3, shot_globals.bm_ta_detuning)
        self.D2Lasers_obj.ramp_repump_freq(t, 1e-3, shot_globals.bm_repump_detuning)

        self.BField_obj.switch_mot_coils(t)
        self.BField_obj.ramp_bias_field(t, bias_field_vector=(0, 0, 0))

        return t

    def do_molasses(self, t, dur, close_all_shutters=False):
        assert (shot_globals.do_molasses_img_beam or shot_globals.do_molasses_mot_beam), \
            "either do_molasses_img_beam or do_molasses_mot_beam has to be on"
        assert shot_globals.bm_ta_detuning != 0, \
            "bright molasses detuning = 0. TA detuning should be non-zero for bright molasses."
        print(f"molasses detuning is {shot_globals.bm_ta_detuning}")

        _ = self.ramp_to_molasses(t)

        if shot_globals.do_molasses_mot_beam:
            t, _ = self.D2Lasers_obj.do_pulse(t, dur, ShutterConfig.MOT_FULL, shot_globals.bm_ta_power,
                                shot_globals.bm_repump_power, close_all_shutters=close_all_shutters)

        if shot_globals.do_molasses_img_beam:
            t, _ = self.D2Lasers_obj.do_pulse(t, dur, ShutterConfig.IMG_FULL, shot_globals.bm_ta_power,
                                shot_globals.bm_repump_power, close_all_shutters=close_all_shutters)
        return t

    #Which arguments are actually necessary to pass or even set as a defualt?
    #How many of them can just be set to globals?
    # TODO: Maybe pass the shutter config into here? This would get rid of all the if statements?
    def do_molasses_dipole_trap_imaging(self, t, do_repump=True,
                                        close_all_shutters=False):
        # zero the field
        _ = self.BField_obj.ramp_bias_field(t, bias_field_vector=(0,0,0))

        # Ramp to imaging frequencies
        self.D2Lasers_obj.ramp_ta_freq(t, CONST_TA_VCO_RAMP_TIME, ta_freq_calib(0))
        self.D2Lasers_obj.ramp_repump_freq(t, CONST_TA_VCO_RAMP_TIME, repump_freq_calib(0))
        t += CONST_TA_VCO_RAMP_TIME

        shutter_config = ShutterConfig.select_imaging_shutters(do_repump=do_repump)

        # full power ta and repump pulse
        t_pulse_end, t_aom_start = self.D2Lasers_obj.do_pulse(t, shot_globals.bm_exposure_time,
                                                                shutter_config, 1, 1,
                                                                close_all_shutters=close_all_shutters)

        # TODO: ask Lin and Michelle and max() logic and if we always want it there
        self.Camera_obj.set_type(shot_globals.camera_type)
        if self.Camera_obj.type =="MOT_manta" or "tweezer_manta":
            exposure = max(shot_globals.bm_exposure_time, 50e-6)
        if self.Camera_obj.type == "kinetix":
            exposure = max(shot_globals.bm_exposure_time, 1e-3)

        # expose the camera
        self.Camera_obj.expose(t_aom_start, exposure)

        # Closes the aom and the specified shutters
        t += exposure
        t = max(t, t_pulse_end)

        return t

    def _do_molasses_in_situ_sequence(self, t, reset_mot=False):
        # MOT loading time 500 ms
        mot_load_dur = 0.5

        t += CONST_SHUTTER_TURN_ON_TIME

        t = self.do_mot(t, mot_load_dur)
        t = self.do_molasses(t, shot_globals.bm_time)
        t = self.do_molasses_dipole_trap_imaging(t, close_all_shutters=True)

        # Turn off MOT for taking background images
        t += 1e-1

        t = self.do_molasses_dipole_trap_imaging(t, close_all_shutters=True)
        t += 1e-2

        if reset_mot:
            t = self.reset_mot(t)

        return t

    def _do_molasses_tof_sequence(self, t, reset_mot=False):

        mot_load_dur = 0.5
        t += CONST_SHUTTER_TURN_ON_TIME

        t = self.do_mot(t, mot_load_dur)

        t = self.do_molasses(t, shot_globals.bm_time)

        assert shot_globals.bm_tof_imaging_delay > CONST_MIN_SHUTTER_OFF_TIME, "time of flight too short for shutter"
        t += shot_globals.bm_tof_imaging_delay
        t = self.do_molasses_dipole_trap_imaging(t, close_all_shutters=True)

        # Turn off MOT for taking background images
        t += 1e-1

        t = self.do_molasses_dipole_trap_imaging(t)

        t += 1e-2
        if reset_mot:
            t = self.reset_mot(t)

        return t

class OpticalPumpingSequence(MOTSequence):

    def __init__(self, t):
        super(OpticalPumpingSequence, self).__init__(t)

    def pump_to_F4(self, t, label=None):
        if self.BField_obj.mot_coils_on:
            _ = self.BField_obj.mot_coils_off(t)
        if label == "mot":
            # Use the MOT beams for optical pumping
            # define quantization axis
            t = self.BField_obj.ramp_bias_field(t, bias_field_vector=(shot_globals.mw_biasx_field,
                                                 shot_globals.mw_biasy_field,
                                                 shot_globals.mw_biasz_field))
            # Do a repump pulse
            t, _ = self.D2Lasers_obj.do_pulse(t, shot_globals.op_MOT_op_time,
                                    ShutterConfig.MOT_REPUMP, 0, 1, close_all_shutters=True)
            return t

        elif label == "sigma":
            # Use the sigma+ beam for optical pumping
            # TODO: do we want shutters always closed for this ramping?
            op_biasx_field, op_biasy_field, op_biasz_field = self.BField_obj.get_op_bias_fields()
            _ = self.BField_obj.ramp_bias_field(t, bias_field_vector=(op_biasx_field,
                                                 op_biasy_field,
                                                 op_biasz_field))
            # ramp detuning to 4 -> 4, 3 -> 4
            self.D2Lasers_obj.ramp_ta_freq(t, 0, CONST_TA_PUMPING_DETUNING)
            self.D2Lasers_obj.ramp_repump_freq(t, 0, shot_globals.op_repump_pumping_detuning)
            # Do a sigma+ pulse
            # TODO: is shot_globals.op_ramp_delay just extra fudge time? can it be eliminated?
            t += max(CONST_TA_VCO_RAMP_TIME, shot_globals.op_ramp_delay)
            t, _ = self.D2Lasers_obj.do_pulse(t - CONST_SHUTTER_TURN_ON_TIME,
                                       shot_globals.op_repump_time,
                                       ShutterConfig.OPTICAL_PUMPING_FULL,
                                       shot_globals.op_ta_power,
                                       shot_globals.op_repump_power,)
            # Need to turn off the TA before repump, Sam claims this timing should work
            assert shot_globals.op_ta_time < shot_globals.op_repump_time, "TA time should be shorter than repump for pumping to F=4"
            # TODO: test this timing
            self.D2Lasers_obj.ta_aom_off(t + shot_globals.op_ta_time - shot_globals.op_repump_time)
            # Close the shutters
            self.D2Lasers_obj.update_shutters(t, ShutterConfig.NONE)
            t += CONST_SHUTTER_TURN_OFF_TIME

            return t

        else:
            raise NotImplementedError("This optical pumping method is not implemented")

    def depump_to_F3(self, t, label):
        # This method should be quite similar to pump_to_F4, but trying to call pump_to_F4 with
        # different parameters would produce a very long argument list
        if self.BField_obj.mot_coils_on:
            _ = self.BField_obj.mot_coils_off(t)
        if label == "mot":
            # Use the MOT beams for optical depumping
            # define quantization axis
            t = self.BField_obj.ramp_bias_field(t, bias_field_vector=(shot_globals.mw_biasx_field,
                                                 shot_globals.mw_biasy_field,
                                                 shot_globals.mw_biasz_field))
            # ramp detuning to 4 -> 4 for TA
            self.D2Lasers_obj.ramp_ta_freq(t, 0, CONST_TA_PUMPING_DETUNING)
            # Do a repump pulse
            t, _ = self.D2Lasers_obj.do_pulse(t, shot_globals.op_MOT_odp_time,
                                    ShutterConfig.MOT_REPUMP, 1, 0, close_all_shutters=True)
            return t

        elif label == "sigma":
            # Use the sigma+ beam for optical pumping
            # TODO: do we want shutters always closed for this ramping?
            op_biasx_field, op_biasy_field, op_biasz_field = self.BField_obj.get_op_bias_fields()
            _ = self.BField_obj.ramp_bias_field(t, bias_field_vector=(op_biasx_field,
                                                 op_biasy_field,
                                                 op_biasz_field))
            # ramp detuning to 4 -> 4, 3 -> 3
            self.D2Lasers_obj.ramp_ta_freq(t, 0, CONST_TA_PUMPING_DETUNING)
            self.D2Lasers_obj.ramp_repump_freq(t, 0, CONST_REPUMP_DEPUMPING_DETUNING)
            # Do a sigma+ pulse
            # TODO: is shot_globals.op_ramp_delay just extra fudge time? can it be eliminated?
            t += max(CONST_TA_VCO_RAMP_TIME, shot_globals.op_ramp_delay)
            t, _ = self.D2Lasers_obj.do_pulse(t - CONST_SHUTTER_TURN_ON_TIME,
                                       shot_globals.odp_repump_time,
                                       ShutterConfig.OPTICAL_PUMPING_FULL,
                                       shot_globals.odp_ta_power,
                                       shot_globals.odp_repump_power,)
            # Need to turn off the TA before repump, Sam claims this timing should work
            assert shot_globals.odp_ta_time > shot_globals.odp_repump_time, "TA time should be longer than repump for depumping to F = 3"
            # TODO: test this timing
            self.D2Lasers_obj.ta_aom_off(t + shot_globals.odp_ta_time - shot_globals.odp_repump_time)
            # Close the shutters
            self.D2Lasers_obj.update_shutters(t, ShutterConfig.NONE)
            t += CONST_SHUTTER_TURN_OFF_TIME

            return t

        else:
            raise NotImplementedError("This optical depumping method is not implemented")

    def kill_F4(self, t):
        ''' Push away atoms in F = 4 '''
        # tune to resonance
        self.D2Lasers_obj.ramp_ta_freq(t, 0, 0)
        t += CONST_TA_VCO_RAMP_TIME
        # do a ta pulse via optical pumping path
        t, _ = self.D2Lasers_obj.do_pulse(t, shot_globals.op_killing_killing_pulse_time,
                                    ShutterConfig.OPTICAL_PUMPING_FULL,
                                    shot_globals.op_killing_ta_power, 0, close_all_shutters=True)

    def kill_F3(self, t):
        pass

class TweezerSequence(OpticalPumpingSequence):

    def __init__(self, t):
        super(TweezerSequence, self).__init__(t)
        self.TweezerLaser_obj = TweezerLaser(t)

    def ramp_to_imaging_parameters(self, t):
        # ramping to imaging detuning and power, previously referred to as "pre_imaging"
        # also used for additional cooling
        self.BField_obj.ramp_bias_field(t, bias_field_vector=(0,0,0))
        self.D2Lasers_obj.ramp_ta_freq(t, 0, shot_globals.img_ta_detuning)
        self.D2Lasers_obj.ramp_repump_freq(t, 0, 0)
        assert shot_globals.img_ta_power != 0, "img_ta_power should not be zero"
        assert shot_globals.img_repump_power != 0, "img_repump_power should not be zero"
        self.D2Lasers_obj.ramp_ta_aom(t, 0, shot_globals.img_ta_power)
        self.D2Lasers_obj.ramp_repump_aom(t, 0, shot_globals.img_repump_power)

        return t

    def load_tweezers(self, t):
        t = self.do_mot(t, dur=0.5)
        t = self.do_molasses(t, dur=shot_globals.bm_time, close_all_shutters=True)
        # TODO: does making this delay longer make the background better when using UV?
        t += 7e-3
        # ramp to full power and parity projection
        if shot_globals.do_parity_projection_pulse:
            _, t_aom_start = self.D2Lasers_obj.parity_projection_pulse(t, dur=shot_globals.bm_parity_projection_pulse_dur)
            # if doing parity projection, synchronize with power ramp
            t = t_aom_start

        self.TweezerLaser_obj.ramp_power(t,
                                         dur=shot_globals.bm_parity_projection_pulse_dur,
                                         final_power=1)
        # TODO: Does it make sense that parity projection and tweezer ramp should have same duration?

        t += shot_globals.bm_parity_projection_pulse_dur

        # t = self.do_molasses(t, dur=shot_globals.bm_time, close_all_shutters=True)
        # t += shot_globals.bm_time

        t = self.ramp_to_imaging_parameters(t)

        if shot_globals.do_robust_loading_pulse:
            # additional cooling, previously referred to as "robust_loading"
            # sometimes don't use this when tweezer debugging is needed?
            t, _ = self.D2Lasers_obj.do_pulse(t, shot_globals.bm_robust_loading_pulse_dur,
                                            ShutterConfig.IMG_FULL,
                                            shot_globals.img_ta_power,
                                            shot_globals.img_repump_power,
                                            close_all_shutters=True)

        assert shot_globals.img_tof_imaging_delay > CONST_MIN_SHUTTER_OFF_TIME, \
            "time of flight needs to be greater than CONST_MIN_SHUTTER_OFF_TIME"
        t += shot_globals.img_tof_imaging_delay

        return t

    def tweezer_modulation(self, t, label='sine'):
        pass

    def rearrange_to_dense(self, t):
        pass

    def image_tweezers(self, t, shot_number):
        if shot_number == 1:
            t = self.do_kinetix_imaging(t, close_all_shutters=shot_globals.do_shutter_close_after_first_shot)
        if shot_number == 2:
            # pulse for the second shots and wait for the first shot to finish the
            # first reading
            kinetix_readout_time = shot_globals.kinetix_roi_row[1] * 4.7065e-6
            # need extra 7 ms for shutter to close on the second shot
            # TODO: is shot_globals.kinetix_extra_readout_time always zero? Delete if so.
            t += kinetix_readout_time + shot_globals.kinetix_extra_readout_time
            t = self.do_kinetix_imaging(t, close_all_shutters = True)
        return t

    def do_kinetix_imaging(self, t, close_all_shutters=False):
        shutter_config = ShutterConfig.select_imaging_shutters(do_repump=True)

        t_pulse_end, t_aom_start = self.D2Lasers_obj.do_pulse(t, shot_globals.img_exposure_time,
                                                                shutter_config, shot_globals.img_ta_power,
                                                                shot_globals.img_repump_power,
                                                                close_all_shutters = close_all_shutters)

        self.Camera_obj.set_type("kinetix")
        exposure_time = max(shot_globals.img_exposure_time, 1e-3)

        # expose the camera
        self.Camera_obj.expose(t_aom_start, exposure_time)

        # Closes the aom and the specified shutters
        t += exposure_time
        t = max(t, t_pulse_end)

        return t

    def _do_tweezer_check_sequence(self, t):
        t = self.load_tweezers(t)
        t = self.image_tweezers(t, shot_number=1)
        # TODO: add tweezer modulation here, or in a separate sequence?
        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
        t = self.reset_mot(t)
        t = self.TweezerLaser_obj.stop_tweezers(t)

        return t

    def _tweezer_release_recapture_sequence(self, t):
        pass

    def _tweezer_modulation_sequence(self, t):
        pass

    def _tweezer_basic_pump_kill_sequence(self, t):
        t = self.load_tweezers(t)
        t = self.image_tweezers(t, shot_number=1)

        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
        t = self.reset_mot(t)
        t = self.TweezerLaser_obj.stop_tweezers(t)

        return t

# I think we should leave both 456 and 1064 stuff here because really the only debugging
# we would need to do is checking their overlap or looking for a Rydberg loss signal in the dipole trap
class RydSequence(TweezerSequence):

    def __init__(self):
        super(RydSequence, self).__init__()
        self.RydLasers_obj = RydLasers()

    def pulse_blue(self, t, dur):
        pass
    def pulse_1064(self, t, dur):
        pass



#Full Sequences, we'll see if we really want all these in a class or just separate sequence files?
class ScienceSequence(RydSequence):

    def __init__(self):
        super(ScienceSequence, self).__init__()

#Should we separate this from ScienceSequence?
class DiagnosticSequence(RydSequence):

    def __init__(self):
        super(DiagnosticSequence, self).__init__()



if __name__ == "__main__":
    labscript.start()
    t = 0

    # Insert "stay on" statements for alignment here...

    if shot_globals.do_mot_in_situ_check:
        MOTSeq_obj = MOTSequence(t)
        t = MOTSeq_obj._do_mot_in_situ_sequence(t, reset_mot=True)

    if shot_globals.do_mot_tof_check:
        MOTSeq_obj = MOTSequence(t)
        t = MOTSeq_obj._do_mot_tof_sequence(t, reset_mot=True)

    if shot_globals.do_molasses_in_situ_check:
        MOTSeq_obj = MOTSequence(t)
        t = MOTSeq_obj._do_molasses_in_situ_sequence(t, reset_mot=True)

    if shot_globals.do_molasses_tof_check:
        MOTSeq_obj = MOTSequence(t)
        t = MOTSeq_obj._do_molasses_tof_sequence(t, reset_mot=True)

    # if shot_globals.do_field_calib_in_molasses_check:
    #     t = do_field_calib_in_molasses_check(t)

    # if shot_globals.do_dipole_trap_tof_check:
    #     t = do_dipole_trap_tof_check(t)

    # if shot_globals.do_img_beam_alignment_check:
    #     t = do_img_beam_alignment_check(t)

    # if shot_globals.do_tweezer_position_check:
    #     t = do_tweezer_position_check(t)

    if shot_globals.do_tweezer_check:
        TweezerSequence_obj = TweezerSequence(t)
        t = TweezerSequence_obj._do_tweezer_check_sequence(t)

    # if shot_globals.do_tweezer_check_fifo:
    #     t = do_tweezer_check_fifo(t)

    # if shot_globals.do_optical_pump_in_tweezer_check:
    #     t = do_optical_pump_in_tweezer_check(t)

    # if shot_globals.do_optical_pump_in_microtrap_check:
    #     t = do_optical_pump_in_microtrap_check(t)

    labscript.stop(t + 1e-2)
