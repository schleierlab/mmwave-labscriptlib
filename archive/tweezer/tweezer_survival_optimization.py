# -*- coding: utf-8 -*-
"""
Created on Thu Feb 16 11:33:13 2023

@author: sslab
"""

import sys
root_path = r"X:\userlib\labscriptlib"

if root_path not in sys.path:
    sys.path.append(root_path)

import labscript

from connection_table import devices
from calibration import ta_freq_calib, repump_freq_calib, biasx_calib, biasy_calib, biasz_calib
from spectrum_manager import spectrum_manager
from spectrum_manager_fifo import spectrum_manager_fifo
from labscriptlib.shot_globals import shot_globals
from diagnostics import diagnostics
import numpy as np

spcm_sequence_mode = shot_globals.do_sequence_mode
if __name__ == '__main__':
    devices.initialize()

def robost_loading_pulse_detuning_change(t, ta_last_detuning, repump_last_detuning):
    devices.x_coil_current.constant(t, biasx_calib(0))  # define quantization axis
    devices.y_coil_current.constant(t, biasy_calib(0))  # define quantization axis
    devices.z_coil_current.constant(t, biasz_calib(0)) # define quantization axis

    devices.ta_vco.ramp(
        t,
        duration= diagnostics.CONST_TA_VCO_RAMP_TIME,
        initial=ta_freq_calib(ta_last_detuning),
        final=ta_freq_calib(shot_globals.bm_rlp_ta_detuning),
        samplerate=4e5,
    )# ramp back to imaging

    devices.repump_vco.ramp(
            t,
            duration= diagnostics.CONST_TA_VCO_RAMP_TIME,
            initial=repump_freq_calib(repump_last_detuning),
            final=repump_freq_calib(0),
            samplerate=4e5,
        )# ramp back to imaging

    ta_last_detuning = shot_globals.bm_rlp_ta_detuning
    repump_last_detuning = 0

    devices.ta_aom_analog.constant(t , shot_globals.bm_rlp_ta_power) # back to full power for imaging
    devices.repump_aom_analog.constant(t , shot_globals.bm_rlp_repump_power)

    t += diagnostics.CONST_TA_VCO_RAMP_TIME

    print('robust loading pulse stage')
    print(f'ta_last_detuning = {ta_last_detuning}')
    print(f'repump_last_detuning = {repump_last_detuning}')
    return t, ta_last_detuning, repump_last_detuning


def cooling_between_images(t, ta_last_detuning, repump_last_detuning):
    devices.x_coil_current.constant(t, biasx_calib(0))  # define quantization axis
    devices.y_coil_current.constant(t, biasy_calib(0))  # define quantization axis
    devices.z_coil_current.constant(t, biasz_calib(0)) # define quantization axis

    devices.ta_vco.ramp(
        t,
        duration= diagnostics.CONST_TA_VCO_RAMP_TIME,
        initial=ta_freq_calib(ta_last_detuning),
        final=ta_freq_calib(shot_globals.img_cooling_between_images_ta_detuning),
        samplerate=4e5,
    )# ramp back to imaging

    devices.repump_vco.ramp(
            t,
            duration= diagnostics.CONST_TA_VCO_RAMP_TIME,
            initial=repump_freq_calib(repump_last_detuning),
            final=repump_freq_calib(0),
            samplerate=4e5,
        )# ramp back to imaging

    ta_last_detuning = shot_globals.img_cooling_between_images_ta_detuning
    repump_last_detuning = 0

    devices.ta_aom_analog.constant(t , shot_globals.img_cooling_between_images_ta_power) # back to full power for imaging
    devices.repump_aom_analog.constant(t , shot_globals.img_cooling_between_images_repump_power)

    t += diagnostics.CONST_TA_VCO_RAMP_TIME

    print('robust loading pulse stage')
    print(f'ta_last_detuning = {ta_last_detuning}')
    print(f'repump_last_detuning = {repump_last_detuning}')
    return t, ta_last_detuning, repump_last_detuning

def depump_pulse(t, ta_last_detuning, repump_last_detuning):
    #==================== scan for F=4 -> F'=4 for depumping =======================#
    devices.repump_aom_digital.go_low(t)
    devices.repump_shutter.close(t)
    devices.ta_aom_digital.go_low(t)
    devices.ta_shutter.close(t)

    t += devices.ta_vco.ramp(
        t,
        duration=diagnostics.CONST_TA_VCO_RAMP_TIME,
        initial=ta_freq_calib(ta_last_detuning),
        final=ta_freq_calib(shot_globals.tw_depump_pulse_ta_detuning),
        samplerate=4e5,
    )

    t += diagnostics.CONST_MIN_SHUTTER_OFF_TIME
    devices.ta_shutter.open(t)
    devices.optical_pump_shutter.open(t)
    devices.ta_aom_digital.go_high(t)
    devices.ta_aom_analog.constant(t, 1)
    devices.tweezer_aom_analog.constant(t, shot_globals.tw_depump_pulse_power)
    t += shot_globals.tw_depump_pulse_time
    devices.tweezer_aom_analog.constant(t, 1)
    devices.ta_aom_digital.go_low(t)
    devices.optical_pump_shutter.close(t)
    devices.ta_shutter.close(t)

    ta_last_detuning = shot_globals.tw_depump_pulse_ta_detuning
    repump_last_detuning = repump_last_detuning

    return t, ta_last_detuning, repump_last_detuning

def killing_pulse(t, ta_last_detuning, repump_last_detuning):
    #==================== Use a strong killing pulse to kick all atoms in F=4 out =======================#
    devices.repump_aom_digital.go_low(t)
    devices.repump_shutter.close(t)
    devices.ta_aom_digital.go_low(t)
    devices.ta_shutter.close(t)

    devices.ta_vco.ramp(
        t,
        duration=diagnostics.CONST_TA_VCO_RAMP_TIME,
        initial=ta_freq_calib(ta_last_detuning),
        final=ta_freq_calib(0),
        samplerate=4e5,
    )
    t += diagnostics.CONST_TA_VCO_RAMP_TIME

    t += diagnostics.CONST_MIN_SHUTTER_OFF_TIME
    devices.ta_shutter.open(t)
    devices.optical_pump_shutter.open(t)
    devices.ta_aom_digital.go_high(t)
    devices.ta_aom_analog.constant(t, 1)
    if shot_globals.do_tw_off_during_killing:
        devices.tweezer_aom_analog.constant(t, 0)
    t += shot_globals.img_killing_pulse_time
    if shot_globals.do_tw_off_during_killing:
        devices.tweezer_aom_analog.constant(t, 1)
    devices.ta_aom_digital.go_low(t)
    devices.optical_pump_shutter.close(t)
    devices.ta_shutter.close(t)

    ta_last_detuning = 0
    repump_last_detuning = repump_last_detuning

    return t, ta_last_detuning, repump_last_detuning

def optical_pumping(t, ta_last_detuning, repump_last_detuning):
    ######## pump all atom into F=4 using MOT beams ###########
    ta_vco_ramp_t = diagnostics.CONST_TA_VCO_RAMP_TIME
    ta_pumping_detuning = -251 # MHz 4->4 tansition
    repump_pumping_detuning = -201.24 # MHz 3->3 transition
    if shot_globals.do_optical_pump_MOT:
        print("I'm doing optical pumping now using MOT beams")
        devices.mot_xy_shutter.open(t)
        devices.mot_z_shutter.open(t)
        devices.ta_aom_digital.go_low(t)
        devices.ta_shutter.close(t)
        devices.repump_shutter.open(t)
        devices.repump_aom_digital.go_high(t)
        devices.repump_aom_analog.constant(t, 1)
        devices.mot_coil_current_ctrl.constant(t, 0)

        t += shot_globals.op_MOT_op_time
        devices.repump_aom_digital.go_low(t)
        devices.repump_shutter.close(t)

        devices.x_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasx_calib(0),
            final= biasx_calib(shot_globals.mw_biasx_field),# 0 mG
            samplerate=1e5,
        )

        devices.y_coil_current.ramp(
                t,
                duration=100e-6,
                initial=biasx_calib(0),
                final=  biasy_calib(shot_globals.mw_biasy_field),# 0 mG
                samplerate=1e5,
            )

        devices.z_coil_current.ramp(
                t,
                duration=100e-6,
                initial=biasz_calib(0),
                final= biasz_calib(shot_globals.mw_biasz_field),# 0 mG
                samplerate=1e5,
            )

        ta_last_detuning = ta_last_detuning
        repump_last_detuning = repump_last_detuning

    ####### depump all atom into F = 3 level by using MOT beams F = 4 -> F' = 4 resonance #########
    if shot_globals.do_optical_depump_MOT:
        print("I'm doing optical de pumping now using MOT beams")
        devices.repump_aom_digital.go_low(t)
        devices.repump_shutter.close(t)
        devices.ta_aom_digital.go_low(t)

        devices.ta_vco.ramp(
            t,
            duration=ta_vco_ramp_t,
            initial=ta_freq_calib(ta_last_detuning),
            final=ta_freq_calib(ta_pumping_detuning),
            samplerate=4e5,
        )

        ta_last_detuning = ta_pumping_detuning
        repump_last_detuning = repump_last_detuning

        t += ta_vco_ramp_t + ta_vco_stable_t

        devices.mot_xy_shutter.open(t)
        devices.mot_z_shutter.open(t)
        devices.ta_shutter.open(t)
        devices.ta_aom_digital.go_high(t)
        devices.ta_aom_analog.constant(t, 1)
        devices.mot_coil_current_ctrl.constant(t, 0)

        t += shot_globals.op_MOT_odp_time
        devices.ta_aom_digital.go_low(t)
        devices.ta_shutter.close(t)

        devices.x_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasx_calib(0),
            final= biasx_calib(shot_globals.mw_biasx_field),# 0 mG
            samplerate=1e5,
        )

        devices.y_coil_current.ramp(
                t,
                duration=100e-6,
                initial=biasx_calib(0),
                final=  biasy_calib(shot_globals.mw_biasy_field),# 0 mG
                samplerate=1e5,
            )

        devices.z_coil_current.ramp(
                t,
                duration=100e-6,
                initial=biasz_calib(0),
                final= biasz_calib(shot_globals.mw_biasz_field),# 0 mG
                samplerate=1e5,
            )

    ####### depump all atom into F = 3, mF =3 level by using sigma+ beam #########
    if shot_globals.do_optical_depump_sigma_plus:


        op_biasx_field = shot_globals.op_bias_amp * np.cos(shot_globals.op_bias_phi/180*np.pi) * np.sin(shot_globals.op_bias_theta/180*np.pi)
        op_biasy_field = shot_globals.op_bias_amp * np.sin(shot_globals.op_bias_phi/180*np.pi) * np.sin(shot_globals.op_bias_theta/180*np.pi)
        op_biasz_field = shot_globals.op_bias_amp * np.cos(shot_globals.op_bias_theta/180*np.pi)


        devices.x_coil_current.ramp(
                t,
                duration=100e-6,
                initial=biasx_calib(0),
                final= biasx_calib(op_biasx_field),# 0 mG
                samplerate=1e5,
            )

        # devices.y_coil_current.ramp(
        #         t,
        #         duration=100e-6,
        #         initial=biasx_calib(0),
        #         final=  biasy_calib(shot_globals.op_biasy_field),# 0 mG
        #         samplerate=1e5,
        #     )

        devices.y_coil_current.constant(t, biasy_calib(op_biasy_field)) # define quantization axis

        devices.z_coil_current.ramp(
                t,
                duration=100e-6,
                initial=biasz_calib(0),
                final= biasz_calib(op_biasz_field),# 0 mG
                samplerate=1e5,
            )

        devices.ta_vco.ramp(
                t,
                duration=ta_vco_ramp_t,
                initial=ta_freq_calib(ta_last_detuning),
                final=ta_freq_calib(ta_pumping_detuning),
                samplerate=4e5,
            )

        devices.repump_vco.ramp(
            t,
            duration=ta_vco_ramp_t,
            initial=repump_freq_calib(repump_last_detuning),
            final=repump_freq_calib(repump_pumping_detuning),
            samplerate=4e5,
            )

        ta_shutter_off_t = 1.74e-3
        devices.mot_z_shutter.close(t)
        devices.mot_xy_shutter.close(t)
        devices.ta_aom_digital.go_low(t - ta_shutter_off_t)
        devices.repump_aom_digital.go_low(t - ta_shutter_off_t)

        t += max(ta_vco_ramp_t, 100e-6, shot_globals.op_ramp_delay)

        devices.optical_pump_shutter.open(t)
        devices.ta_aom_digital.go_high(t)
        devices.ta_aom_analog.constant(t, shot_globals.odp_ta_power)
        devices.repump_aom_digital.go_high(t)
        devices.repump_aom_analog.constant(t, shot_globals.odp_repump_power)

        devices.ta_aom_digital.go_low(t + shot_globals.odp_ta_time)
        devices.ta_shutter.close(t + shot_globals.odp_ta_time)
        devices.repump_aom_digital.go_low(t + shot_globals.odp_repump_time)
        devices.repump_shutter.close(t + shot_globals.odp_repump_time)

        assert shot_globals.odp_ta_time > shot_globals.odp_repump_time, "TA time should be longer than repump for atom in F = 3"

        t += max(shot_globals.odp_ta_time, shot_globals.odp_repump_time)
        devices.optical_pump_shutter.close(t)

        devices.x_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasx_calib(op_biasx_field),
            final= biasx_calib(shot_globals.mw_biasx_field),# 0 mG
            samplerate=1e5,
        )

        # devices.y_coil_current.ramp(
        #         t,
        #         duration=100e-6,
        #         initial=biasx_calib(shot_globals.op_biasy_field),
        #         final=  biasy_calib(shot_globals.biasy_field),# 0 mG
        #         samplerate=1e5,
        #     )
        devices.y_coil_current.constant(t, biasy_calib(shot_globals.mw_biasy_field)) # define quantization axis

        devices.z_coil_current.ramp(
                t,
                duration=100e-6,
                initial=biasz_calib(op_biasz_field),
                final= biasz_calib(shot_globals.mw_biasz_field),# 0 mG
                samplerate=1e5,
            )

        print(f'OP bias x, y, z voltage = {biasx_calib(op_biasx_field)}, {biasy_calib(op_biasy_field)}, {biasz_calib(op_biasz_field)}')

        ta_last_detuning = ta_pumping_detuning
        repump_last_detuning = repump_pumping_detuning

    ####### pump all atom into F = 4, mF = 4 level by using sigma+ beam #########
    if shot_globals.do_optical_pump_sigma_plus: # use sigma + polarized light for optical pumping
        op_biasx_field = shot_globals.op_bias_amp * np.cos(shot_globals.op_bias_phi/180*np.pi) * np.sin(shot_globals.op_bias_theta/180*np.pi)
        op_biasy_field = shot_globals.op_bias_amp * np.sin(shot_globals.op_bias_phi/180*np.pi) * np.sin(shot_globals.op_bias_theta/180*np.pi)
        op_biasz_field = shot_globals.op_bias_amp * np.cos(shot_globals.op_bias_theta/180*np.pi)


        devices.x_coil_current.ramp(
                t,
                duration=100e-6,
                initial=biasx_calib(0),
                final= biasx_calib(op_biasx_field),# 0 mG
                samplerate=1e5,
            )

        devices.y_coil_current.constant(t, biasy_calib(op_biasy_field)) # define quantization axis

        devices.z_coil_current.ramp(
                t,
                duration=100e-6,
                initial=biasz_calib(0),
                final= biasz_calib(op_biasz_field),# 0 mG
                samplerate=1e5,
            )

        devices.ta_vco.ramp(
                t,
                duration=ta_vco_ramp_t,
                initial=ta_freq_calib(ta_last_detuning),
                final=ta_freq_calib(ta_pumping_detuning),
                samplerate=4e5,
            )


        ta_shutter_off_t = 1.74e-3
        devices.mot_z_shutter.close(t)
        devices.mot_xy_shutter.close(t)
        devices.ta_aom_digital.go_low(t - ta_shutter_off_t)
        devices.repump_aom_digital.go_low(t - ta_shutter_off_t)

        t += max(ta_vco_ramp_t, 100e-6, shot_globals.op_ramp_delay)

        devices.optical_pump_shutter.open(t)
        devices.ta_aom_digital.go_high(t)
        devices.ta_aom_analog.constant(t, shot_globals.op_ta_power)
        devices.repump_aom_digital.go_high(t)
        devices.repump_aom_analog.constant(t, shot_globals.op_repump_power)

        devices.ta_aom_digital.go_low(t + shot_globals.op_ta_time)
        devices.ta_shutter.close(t + shot_globals.op_ta_time)
        devices.repump_aom_digital.go_low(t + shot_globals.op_repump_time)
        devices.repump_shutter.close(t + shot_globals.op_repump_time)

        assert shot_globals.op_ta_time < shot_globals.op_repump_time, "TA time should be shorter than repump for atom in F = 4"

        t += max(shot_globals.op_ta_time, shot_globals.op_repump_time)

        devices.optical_pump_shutter.close(t)


        devices.x_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasx_calib(op_biasx_field),
            final= biasx_calib(0),# 0 mG
            samplerate=1e5,
        )

        # devices.y_coil_current.ramp(
        #         t,
        #         duration=100e-6,
        #         initial=biasx_calib(shot_globals.op_biasy_field),
        #         final=  biasy_calib(shot_globals.biasy_field),# 0 mG
        #         samplerate=1e5,
        #     )
        devices.y_coil_current.constant(t, biasy_calib(0)) # define quantization axis

        devices.z_coil_current.ramp(
                t,
                duration=100e-6,
                initial=biasz_calib(op_biasz_field),
                final= biasz_calib(0),# 0 mG
                samplerate=1e5,
            )

        print(f'OP bias x, y, z voltage = {biasx_calib(op_biasx_field)}, {biasy_calib(op_biasy_field)}, {biasz_calib(op_biasz_field)}')
        ta_last_detuning = ta_pumping_detuning
        repump_last_detuning = repump_last_detuning

    devices.mot_xy_shutter.close(t)
    devices.mot_z_shutter.close(t)
    return t, ta_last_detuning, repump_last_detuning


def do_tweezer_check():


    MOT_load_dur = 0.5
    molasses_dur = shot_globals.bm_time
    labscript.start()

    t = 0

    if shot_globals.do_tweezers:
        print("Initializing tweezers")
        devices.dds0.synthesize(t+1e-2, shot_globals.TW_y_freqs, 0.95, 0)
        spectrum_manager.start_card()
        t1 = spectrum_manager.start_tweezers(t) #has to be the first thing in the timing sequence (?)
        print('tweezer start time:',t1)
        # Turn on the tweezer
        devices.tweezer_aom_digital.go_high(t)
        devices.tweezer_aom_analog.constant(t, shot_globals.tweezer_loading_power) #0.3) #for single tweezer

    if shot_globals.do_dipole_trap:
        diagnostics.turn_on_dipole_trap(t)
    else:
        diagnostics.turn_off_dipole_trap(t)

    diagnostics.do_MOT(t, MOT_load_dur, shot_globals.do_mot_coil)
    t += MOT_load_dur # how long MOT last

    _, ta_last_detuning, repump_last_detuning = diagnostics.load_molasses(t, diagnostics.CONST_TA_BM_DETUNING, diagnostics.CONST_REPUMP_BM_DETUNING)
    t += molasses_dur
    # ta_last_detuning =  ta_bm_detuning
    # repump_last_detuning = repump_bm_detuning


    devices.mot_xy_shutter.close(t)
    devices.mot_z_shutter.close(t)

    t += 7e-3

    #t, ta_last_detuning, repump_last_detuning = robost_loading_pulse_detuning_change(t, ta_last_detuning, repump_last_detuning)
    t, ta_last_detuning, repump_last_detuning = diagnostics.pre_imaging(t, ta_last_detuning, repump_last_detuning)

    if shot_globals.do_trap_increase_during_imaging:
        devices.tweezer_aom_analog.constant(t, 1)
    if shot_globals.do_robust_loading_pulse:
        diagnostics.robust_loading_pulse(t, dur = shot_globals.robust_loading_pulse_dur)
        t += shot_globals.robust_loading_pulse_dur
    if shot_globals.do_trap_increase_during_imaging:
        devices.tweezer_aom_analog.constant(t, shot_globals.tweezer_loading_power) #0.3) #for single tweezer

    t += diagnostics.CONST_MIN_SHUTTER_OFF_TIME

    t, ta_last_detuning, repump_last_detuning = diagnostics.pre_imaging(t, ta_last_detuning, repump_last_detuning)

    assert shot_globals.img_tof_imaging_delay > diagnostics.CONST_MIN_SHUTTER_OFF_TIME, "time of flight too short for shutter'"
    t += shot_globals.img_tof_imaging_delay

    if shot_globals.do_trap_increase_during_imaging:
        devices.tweezer_aom_analog.constant(t, shot_globals.tweezer_imaging_power) #0.3) #for single tweezer

    t, ta_last_detuning, repump_last_detuning = diagnostics.do_imaging(t, 1, ta_last_detuning, repump_last_detuning)
    t += 7e-3 # make sure sutter fully closed after 1st imaging

    # t, ta_last_detuning, repump_last_detuning = optical_pumping(t, ta_last_detuning, repump_last_detuning)

    if shot_globals.do_cooling_between_images:
        t, ta_last_detuning, repump_last_detuning = cooling_between_images(t, ta_last_detuning, repump_last_detuning)
        diagnostics.robust_loading_pulse(t, dur = shot_globals.cooling_between_images_dur)
        t += shot_globals.cooling_between_images_dur
        t += 7e-3


    if shot_globals.do_trap_increase_during_imaging:
        devices.tweezer_aom_analog.constant(t, shot_globals.tweezer_loading_power) #0.3) #for single tweezer

    if shot_globals.do_depump_pulse:
        t, ta_last_detuning, repump_last_detuning = depump_pulse(t, ta_last_detuning, repump_last_detuning)

    t += 7e-3

    if shot_globals.do_killing_pulse:
        t, ta_last_detuning, repump_last_detuning = killing_pulse(t, ta_last_detuning, repump_last_detuning)


    # second shot
    t, ta_last_detuning, repump_last_detuning = diagnostics.pre_imaging(t, ta_last_detuning, repump_last_detuning)
    t += 10e-3 #100e-3
    if shot_globals.do_trap_increase_during_imaging:
        devices.tweezer_aom_analog.constant(t, shot_globals.tweezer_imaging_power) #0.3) #for single tweezer
    t, ta_last_detuning, repump_last_detuning = diagnostics.do_imaging(t, 2, ta_last_detuning, repump_last_detuning)
    if shot_globals.do_trap_increase_during_imaging:
        devices.tweezer_aom_analog.constant(t, shot_globals.tweezer_loading_power) #0.3) #for single tweezer
    t += 1e-2
    print(f"time to reset mot = {t}")
    diagnostics.reset_mot(t, ta_last_detuning)
    # make sure tweezer AOM has full rf power
    if shot_globals.do_tweezers:
        # stop tweezers
        t2 = spectrum_manager.stop_tweezers(t)
        print('tweezer stop time:', t2)
        #t += 1e-3

        ##### dummy segment ######
        t1 = spectrum_manager.start_tweezers(t)
        print('tweezer start time:', t1)
        t += 2e-3
        t2 = spectrum_manager.stop_tweezers(t)
        print('tweezer stop time:',t2)
        #t += 1e-3################
        spectrum_manager.stop_card(t)

    labscript.stop(t + 1e-2)

    return t

if __name__ == "__main__":
    if shot_globals.do_mot_in_situ_check:
        diagnostics.do_mot_in_situ_check()

    if shot_globals.do_mot_tof_check:
        diagnostics.do_mot_tof_check()

    if shot_globals.do_molasses_in_situ_check:
        diagnostics.do_molasses_in_situ_check()

    if shot_globals.do_molasses_tof_check:
        diagnostics.do_molasses_tof_check()

    if shot_globals.do_dipole_trap_tof_check:
        diagnostics.do_dipole_trap_tof_check()

    if shot_globals.do_img_beam_alignment_check:
        diagnostics.do_img_beam_alignment_check()

    if shot_globals.do_tweezer_position_check:
        diagnostics.do_tweezer_position_check()

    if shot_globals.do_tweezer_check:
        # diagnostics.do_tweezer_check()
        do_tweezer_check()
