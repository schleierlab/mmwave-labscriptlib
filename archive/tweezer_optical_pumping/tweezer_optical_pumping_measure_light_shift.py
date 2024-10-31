# -*- coding: utf-8 -*-
"""
Created on Thu Feb 16 11:33:13 2023

@author: sslab
"""

import sys
root_path = r"C:\Users\sslab\labscript-suite\userlib\labscriptlib"

if root_path not in sys.path:
    sys.path.append(root_path)

import labscript

from connection_table import devices
from getMOT import load_mot
from getMolasses import load_molasses, load_molasses_img_beam
from calibration import ta_freq_calib, repump_freq_calib, biasx_calib, biasy_calib, biasz_calib
from spectrum_manager import spectrum_manager
from labscriptlib.shot_globals import shot_globals
import numpy as np

coil_off_time = 1.4e-3 # minimum time for the MOT coil to be off
min_shutter_off_t = 6.28e-3 # minimum time for shutter to be off and on again

devices.initialize()
ta_vco_ramp_t = 1.2e-4 # minimum TA ramp time to stay locked
ta_vco_stable_t = 1e-4 # stable time waited for lock
mot_detuning = shot_globals.mot_detuning  # -13 # MHz, optimized based on atom number
ta_bm_detuning = shot_globals.ta_bm_detuning  # -100 # MHz, bright molasses detuning
repump_bm_detuning = shot_globals.repump_bm_detuning  # 0 # MHz, bright molasses detuning
ta_pumping_detuning = -251 # MHz 4->4 tansition
repump_pumping_detuning = -201.24 # MHz 3->3 transition
spectrum_card_offset = 52.8e-6 # the offset for the beging of output comparing to the trigger
spectrum_uwave_cable_atten = 4.4 #dB at 300 MHz
spectrum_uwave_power = -1 #-3 # dBm
uwave_clock = 9.192631770e3 # in unit of MHz
local_oscillator_freq_mhz = 9486 # in unit of MHz MKU LO 8-13 PLL setting


def do_MOT(t, dur, coils_bool = shot_globals.do_mot_coil):
    if coils_bool:
        load_mot(t, mot_detuning=mot_detuning)
    else:
        load_mot(t, mot_detuning=mot_detuning, mot_coil_ctrl_voltage=0)


    if shot_globals.do_molasses_img_beam:
        devices.mot_xy_shutter.close(t+dur)
        devices.mot_z_shutter.close(t+dur)

    #MOT coils ramped down in load_molasses

    ta_last_detuning = mot_detuning
    repump_last_detuning = 0

    return t


def do_dipole(t, dur,  dipole_bool = shot_globals.do_dipole_trap):
    #also includes the dipole trap
    if dipole_bool:
        devices.ipg_1064_aom_digital.go_high(t)
        devices.ipg_1064_aom_analog.constant(t, 1)

        devices.ipg_1064_aom_digital.go_low(t+dur)
        devices.ipg_1064_aom_analog.constant(t+dur, 0)
    return t


def do_molasses(t, dur):
    load_molasses(t, ta_bm_detuning, repump_bm_detuning)
    #turn off coil and light for TOF measurement, coil is already off in load_molasses
    devices.ta_aom_digital.go_low(t+dur)
    devices.repump_aom_digital.go_low(t+dur)
    if not(shot_globals.do_optical_pump_MOT) or not(shot_globals.do_optical_depump_MOT):
        devices.mot_xy_shutter.close(t+dur)
        devices.mot_z_shutter.close(t+dur)

    global ta_last_detuning
    global repump_last_detuning
    ta_last_detuning =  ta_bm_detuning
    repump_last_detuning = repump_bm_detuning
    return t


def pre_imaging(t):
    global ta_last_detuning
    global repump_last_detuning

    devices.x_coil_current.constant(t, biasx_calib(0)) # define quantization axis
    devices.y_coil_current.constant(t, biasy_calib(0)) # define quantization axis
    devices.z_coil_current.constant(t, biasz_calib(0)) # define quantization axis

    devices.ta_vco.ramp(
        t,
        duration=ta_vco_ramp_t,
        initial=ta_freq_calib(ta_last_detuning),
        final=ta_freq_calib(shot_globals.ta_img_detuning),
        samplerate=4e5,
    )# ramp back to imaging

    devices.repump_vco.ramp(
            t,
            duration=ta_vco_ramp_t,
            initial=repump_freq_calib(repump_last_detuning),
            final=repump_freq_calib(0),
            samplerate=4e5,
        )# ramp back to imaging

    ta_last_detuning = shot_globals.ta_img_detuning
    repump_last_detuning = 0

    devices.ta_aom_analog.constant(t , shot_globals.ta_img_power) # back to full power for imaging
    devices.repump_aom_analog.constant(t , shot_globals.repump_img_power)

    t += ta_vco_ramp_t
    return t


def do_dipole_trap_imaging(t):
    devices.ta_shutter.open(t)
    devices.repump_shutter.open(t)
    devices.mot_xy_shutter.open(t)
    devices.mot_z_shutter.open(t)
    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)

    kinetix_readout_time = shot_globals.kinetix_roi_row[1]*4.7065e-6
    devices.kinetix.expose(
        'Kinetix',
        t - kinetix_readout_time,
        'atoms',
        exposure_time=shot_globals.kinetix_exposure
    )
    t += shot_globals.kinetix_exposure
    devices.repump_aom_digital.go_low(t)
    devices.ta_aom_digital.go_low(t)
    devices.mot_xy_shutter.close(t)
    devices.mot_z_shutter.close(t)
    devices.ta_shutter.close(t)
    devices.repump_shutter.close(t)

    return t


def do_imaging_no_camera(t, shot_number):
    global ta_last_detuning
    global repump_last_detuning
    devices.ta_shutter.open(t)
    #devices.repump_shutter.open(t)
    if shot_number ==1:
        if shot_globals.do_mot_beams_during_imaging:
            if shot_globals.do_mot_xy_beams_during_imaging:
                devices.mot_xy_shutter.open(t)
            if shot_globals.do_mot_z_beam_during_imaging:
                devices.mot_z_shutter.open(t)
        if shot_globals.do_img_beams_during_imaging:
            if shot_globals.do_img_xy_beams_during_imaging:
                devices.img_xy_shutter.open(t)
            if shot_globals.do_img_z_beam_during_imaging:
                devices.img_z_shutter.open(t)
    elif shot_number ==2:
        # pulse for the second shots and wait for the first shot to finish the first reading
        kinetix_readout_time = shot_globals.kinetix_roi_row[1]*4.7065e-6
        print('kinetix readout time:', kinetix_readout_time)
        t += kinetix_readout_time + shot_globals.kinetix_extra_readout_time #need extra 7 ms for shutter to close on the second shot

        if shot_globals.do_shutter_close_on_second_shot:
            if shot_globals.do_mot_beams_during_imaging:
                if shot_globals.do_mot_xy_beams_during_imaging:
                    devices.mot_xy_shutter.open(t)
                if shot_globals.do_mot_z_beam_during_imaging:
                    devices.mot_z_shutter.open(t)
            if shot_globals.do_img_beams_during_imaging:
                if shot_globals.do_img_xy_beams_during_imaging:
                    devices.img_xy_shutter.open(t)
                if shot_globals.do_img_z_beam_during_imaging:
                    devices.img_z_shutter.open(t)

    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)

    # if shot_globals.do_tweezer_camera:
    #     devices.manta419b_tweezer.expose(
    #         'manta419b',
    #         t,
    #         'atoms',
    #         exposure_time=max(shot_globals.manta_exposure, 50e-6),
    #     )

    #     t +=  shot_globals.manta_exposure
    #     devices.repump_aom_digital.go_low(t)
    #     devices.ta_aom_digital.go_low(t)

    if shot_globals.do_kinetix_camera:

        # devices.kinetix.expose(
        #     'Kinetix',
        #     t,
        #     'atoms',
        #     exposure_time=max(shot_globals.kinetix_exposure, 1e-3),
        # )
        # # do this when not using kinetix server (take picture locally)
        # # devices.kinetix_camera_trigger.go_high(t)
        # # devices.kinetix_camera_trigger.go_low(t+shot_globals.kinetix_exposure)

        t +=  shot_globals.kinetix_exposure
        devices.repump_aom_digital.go_low(t)
        devices.ta_aom_digital.go_low(t)


    if shot_number ==1:
        if shot_globals.do_shutter_close_on_second_shot:
            if shot_globals.do_mot_beams_during_imaging:
                if shot_globals.do_mot_xy_beams_during_imaging:
                    devices.mot_xy_shutter.close(t)
                if shot_globals.do_mot_z_beam_during_imaging:
                    devices.mot_z_shutter.close(t)
            if shot_globals.do_img_beams_during_imaging:
                if shot_globals.do_img_xy_beams_during_imaging:
                    devices.img_xy_shutter.close(t)
                if shot_globals.do_img_z_beam_during_imaging:
                    devices.img_z_shutter.close(t)
    elif shot_number ==2:
        if shot_globals.do_mot_beams_during_imaging:
            if shot_globals.do_mot_xy_beams_during_imaging:
                devices.mot_xy_shutter.close(t)
            if shot_globals.do_mot_z_beam_during_imaging:
                devices.mot_z_shutter.close(t)
        if shot_globals.do_img_beams_during_imaging:
            if shot_globals.do_img_xy_beams_during_imaging:
                devices.img_xy_shutter.close(t)
            if shot_globals.do_img_z_beam_during_imaging:
                devices.img_z_shutter.close(t)
    return t


def do_imaging(t, shot_number):
    global ta_last_detuning
    global repump_last_detuning
    devices.ta_shutter.open(t)
    devices.repump_shutter.open(t)
    if shot_number ==1:
        if shot_globals.do_mot_beams_during_imaging:
            if shot_globals.do_mot_xy_beams_during_imaging:
                devices.mot_xy_shutter.open(t)
            if shot_globals.do_mot_z_beam_during_imaging:
                devices.mot_z_shutter.open(t)
        if shot_globals.do_img_beams_during_imaging:
            if shot_globals.do_img_xy_beams_during_imaging:
                devices.img_xy_shutter.open(t)
            if shot_globals.do_img_z_beam_during_imaging:
                devices.img_z_shutter.open(t)
    elif shot_number ==2:
        # pulse for the second shots and wait for the first shot to finish the first reading
        kinetix_readout_time = shot_globals.kinetix_roi_row[1]*4.7065e-6
        print('kinetix readout time:', kinetix_readout_time)
        t += kinetix_readout_time + shot_globals.kinetix_extra_readout_time #need extra 7 ms for shutter to close on the second shot

        if shot_globals.do_shutter_close_on_second_shot:
            if shot_globals.do_mot_beams_during_imaging:
                if shot_globals.do_mot_xy_beams_during_imaging:
                    devices.mot_xy_shutter.open(t)
                if shot_globals.do_mot_z_beam_during_imaging:
                    devices.mot_z_shutter.open(t)
            if shot_globals.do_img_beams_during_imaging:
                if shot_globals.do_img_xy_beams_during_imaging:
                    devices.img_xy_shutter.open(t)
                if shot_globals.do_img_z_beam_during_imaging:
                    devices.img_z_shutter.open(t)

    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)

    # if shot_globals.do_tweezer_camera:
    #     devices.manta419b_tweezer.expose(
    #         'manta419b',
    #         t,
    #         'atoms',
    #         exposure_time=max(shot_globals.manta_exposure, 50e-6),
    #     )

    #     t +=  shot_globals.manta_exposure
    #     devices.repump_aom_digital.go_low(t)
    #     devices.ta_aom_digital.go_low(t)

    if shot_globals.do_kinetix_camera:

        devices.kinetix.expose(
            'Kinetix',
            t,
            'atoms',
            exposure_time=max(shot_globals.kinetix_exposure, 1e-3),
        )
        # do this when not using kinetix server (take picture locally)
        # devices.kinetix_camera_trigger.go_high(t)
        # devices.kinetix_camera_trigger.go_low(t+shot_globals.kinetix_exposure)

        t +=  shot_globals.kinetix_exposure
        devices.repump_aom_digital.go_low(t)
        devices.ta_aom_digital.go_low(t)


    if shot_number ==1:
        if shot_globals.do_shutter_close_on_second_shot:
            if shot_globals.do_mot_beams_during_imaging:
                if shot_globals.do_mot_xy_beams_during_imaging:
                    devices.mot_xy_shutter.close(t)
                if shot_globals.do_mot_z_beam_during_imaging:
                    devices.mot_z_shutter.close(t)
            if shot_globals.do_img_beams_during_imaging:
                if shot_globals.do_img_xy_beams_during_imaging:
                    devices.img_xy_shutter.close(t)
                if shot_globals.do_img_z_beam_during_imaging:
                    devices.img_z_shutter.close(t)
    elif shot_number ==2:
        if shot_globals.do_mot_beams_during_imaging:
            if shot_globals.do_mot_xy_beams_during_imaging:
                devices.mot_xy_shutter.close(t)
            if shot_globals.do_mot_z_beam_during_imaging:
                devices.mot_z_shutter.close(t)
        if shot_globals.do_img_beams_during_imaging:
            if shot_globals.do_img_xy_beams_during_imaging:
                devices.img_xy_shutter.close(t)
            if shot_globals.do_img_z_beam_during_imaging:
                devices.img_z_shutter.close(t)
    return t


def robust_loading_pulse(t, dur):
    devices.ta_shutter.open(t)
    devices.repump_shutter.open(t)
    devices.img_xy_shutter.open(t)
    devices.img_z_shutter.open(t)
    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)
    t += dur
    devices.repump_aom_digital.go_low(t)
    devices.ta_aom_digital.go_low(t)
    devices.img_xy_shutter.close(t)
    devices.img_z_shutter.close(t)
    devices.ta_shutter.close(t)
    devices.repump_shutter.close(t)
    return t


def reset_shot(t):
    global ta_last_detuning
    global repump_last_detuning
    # set ta detuning back to initial value
    devices.ta_vco.ramp(
        t,
        duration=ta_vco_ramp_t,
        # initial=ta_freq_calib(ta_pumping_detuning),
        initial=ta_freq_calib(ta_last_detuning),
        final=ta_freq_calib(mot_detuning),
        samplerate=1e5,
    )
    # set the default value into MOT loading value
    if shot_globals.do_mot_coil:
        load_mot(t,mot_detuning=mot_detuning)
    else:
        load_mot(t,mot_detuning=mot_detuning, mot_coil_ctrl_voltage=0)


def optical_pump(t):
    global ta_last_detuning
    global repump_last_detuning
    ######## pump all atom into F=4 using MOT beams ###########
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

    ####### pump all atom into F = 4, mF = $ level by using sigma+ beam #########
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
        repump_last_detuning = repump_last_detuning

    devices.mot_xy_shutter.close(t)
    devices.mot_z_shutter.close(t)
    return t

def optical_dempump(t):
    global ta_last_detuning
    global repump_last_detuning
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
            final=ta_freq_calib(ta_pumping_detuning + shot_globals.odp_ta_detuning),
            samplerate=4e5,
        )

        ta_last_detuning = ta_pumping_detuning + shot_globals.odp_ta_detuning
        repump_last_detuning = repump_last_detuning

        t += ta_vco_ramp_t + ta_vco_stable_t

        devices.mot_xy_shutter.open(t)
        devices.mot_z_shutter.open(t)
        devices.ta_shutter.open(t)
        devices.ta_aom_digital.go_high(t)
        devices.ta_aom_analog.constant(t, shot_globals.odp_MOT_ta_power)
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

    devices.mot_xy_shutter.close(t)
    devices.mot_z_shutter.close(t)
    return t

def killing_pulse(t):
    #==================== Use a strong killing pulse to kick all atoms in F=4 out =======================#
    global ta_last_detuning
    global repump_last_detuning
    devices.repump_aom_digital.go_low(t)
    devices.repump_shutter.close(t)
    devices.ta_aom_digital.go_low(t)
    devices.ta_shutter.close(t)

    devices.ta_vco.ramp(
        t,
        duration=ta_vco_ramp_t,
        initial=ta_freq_calib(ta_last_detuning),
        final=ta_freq_calib(0),#-45), #ta_bm_detuning),
        samplerate=4e5,
    )
    t += ta_vco_ramp_t

    t += min_shutter_off_t
    devices.ta_shutter.open(t)
    devices.optical_pump_shutter.open(t)
    devices.ta_aom_digital.go_high(t)
    devices.ta_aom_analog.constant(t, 1)
    t += shot_globals.img_killing_pulse_time
    devices.ta_aom_digital.go_low(t)
    devices.optical_pump_shutter.close(t)
    devices.ta_shutter.close(t)

    ta_last_detuning = 0 #-45
    repump_last_detuning = repump_last_detuning

    return t


def killing_repump_pulse(t):
    global ta_last_detuning
    global repump_last_detuning
    #==================== Use a strong killing pulse to kick all atoms in F=3 out =======================#
    devices.ta_aom_digital.go_low(t)
    devices.ta_shutter.close(t)

    t += min_shutter_off_t
    devices.optical_pump_shutter.open(t)
    devices.repump_aom_digital.go_high(t)
    devices.repump_aom_analog.constant(t, 1)
    t += shot_globals.img_killing_pulse_time
    devices.repump_aom_digital.go_low(t)
    devices.optical_pump_shutter.close(t)
    devices.repump_shutter.close(t)

    ta_last_detuning = ta_last_detuning
    repump_last_detuning = repump_last_detuning

    return t

def spectrum_microwave_sweep(t):
    if shot_globals.do_mw_sweep_starttoend:
        mw_freq_start = local_oscillator_freq_mhz - uwave_clock - shot_globals.mw_detuning_start
        mw_freq_end = local_oscillator_freq_mhz - uwave_clock - shot_globals.mw_detuning_end
        mw_sweep_range = abs(mw_freq_end - mw_freq_start)
        if shot_globals.do_mw_sweep_duration:
            mw_sweep_duration = shot_globals.mw_sweep_duration
        else:
            mw_sweep_duration = mw_sweep_range/shot_globals.mw_sweep_rate
        devices.spectrum_uwave.sweep(t - spectrum_card_offset, duration=mw_sweep_duration, start_freq=mw_freq_start*1e6, end_freq=mw_freq_end*1e6, amplitude=0.99, phase=0, ch=0, freq_ramp_type='linear')
        print(f'Start the sweep from {shot_globals.mw_detuning_start} MHz to {shot_globals.mw_detuning_end} MHz within {mw_sweep_duration}s ')
    else:
        mw_sweep_range = shot_globals.mw_sweep_range
        mw_detuning_center = shot_globals.mw_detuning_center
        mw_freq_center = local_oscillator_freq_mhz - uwave_clock - mw_detuning_center
        mw_freq_start = mw_freq_center - mw_sweep_range/2
        mw_freq_end = mw_freq_center + mw_sweep_range/2
        if shot_globals.do_mw_sweep_duration:
            mw_sweep_duration = shot_globals.mw_sweep_duration
        else:
            mw_sweep_duration = mw_sweep_range/shot_globals.mw_sweep_rate
        devices.spectrum_uwave.sweep(t - spectrum_card_offset, duration=mw_sweep_duration, start_freq=mw_freq_start*1e6, end_freq=mw_freq_end*1e6, amplitude=0.99, phase=0, ch=0, freq_ramp_type='linear')
        print(f'Sweep around center {shot_globals.mw_sweep_range} MHz for a range of {shot_globals.mw_detuning_end} MHz within {mw_sweep_duration}s ')

    return mw_sweep_duration


labscript.start()

t = 0
MOT_load_dur = 0.5
molasses_dur = shot_globals.molasses_time*1e-3
# ryd_excitation_dur = shot_globals.ryd_excitation_dur

devices.spectrum_uwave.set_mode(replay_mode=b'sequence',
                                channels=[{'name': 'microwaves', 'power': spectrum_uwave_power + spectrum_uwave_cable_atten, 'port': 0, 'is_amplified': False, 'amplifier': None, 'calibration_power': 12, 'power_mode': 'constant_total', 'max_pulses': 1},
                                          {'name': 'mmwaves', 'power': -11, 'port': 1, 'is_amplified': False, 'amplifier': None, 'calibration_power': 12, 'power_mode': 'constant_total', 'max_pulses': 1}],
                                clock_freq=625,
                                use_ext_clock=True,
                                ext_clock_freq=10)

if shot_globals.do_dipole_trap:
    devices.ipg_1064_aom_digital.go_high(t)
    devices.ipg_1064_aom_analog.constant(t, 1)

if shot_globals.do_tweezers:
    devices.dds0.synthesize(t+1e-2, shot_globals.TW_y_freqs, 0.95, 0)
    spectrum_manager.start_card()
    t1 = spectrum_manager.start_tweezers(t) #has to be the first thing in the timing sequence (?)
    print('tweezer start time:',t1)
    # Turn on the tweezer
    devices.tweezer_aom_digital.go_high(t)
    devices.tweezer_aom_analog.constant(t, 1) #0.3) #for single tweezer


do_MOT(t, MOT_load_dur)


t += MOT_load_dur # how long MOT last
load_molasses(t, ta_bm_detuning, repump_bm_detuning)
#turn off coil and light for TOF measurement, coil is already off in load_molasses
t += molasses_dur
# devices.ta_aom_digital.go_low(t)
# devices.repump_aom_digital.go_low(t)
ta_last_detuning =  ta_bm_detuning
repump_last_detuning = repump_bm_detuning

print('Molasses stage')
print(f'ta_last_detuning = {ta_last_detuning}')
print(f'repump_last_detuning = {repump_last_detuning}')


devices.mot_xy_shutter.close(t)
devices.mot_z_shutter.close(t)
devices.img_xy_shutter.close(t)
devices.img_z_shutter.close(t)

print('OP stage')
print(f'ta_last_detuning = {ta_last_detuning}')
print(f'repump_last_detuning = {repump_last_detuning}')

t += 7e-3

t = pre_imaging(t)

if shot_globals.do_robust_loading_pulse:
    robust_loading_pulse(t, dur = shot_globals.robust_loading_pulse_dur)
    t += shot_globals.robust_loading_pulse_dur

assert shot_globals.tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter'"
t += shot_globals.tof_imaging_delay

t = do_imaging(t, 1)

t += 7e-3

t = optical_pump(t)

t+= 7e-3

# lower trap depth for optical depumping
devices.tweezer_aom_analog.constant(t,0.15)#1)
# t+=50e-6
t = optical_dempump(t)

#================================================================================
# Spectrum card related for microwaves
#================================================================================

# if shot_globals.do_mw_sweep:
#     devices.uwave_absorp_switch.go_high(t)
#     mw_sweep_duration = spectrum_microwave_sweep(t)
#     devices.uwave_absorp_switch.go_low(t + mw_sweep_duration)
#     t += mw_sweep_duration

# if shot_globals.do_mw:
#     t += spectrum_card_offset
#     devices.uwave_absorp_switch.go_high(t)
#     devices.spectrum_uwave.single_freq(t - spectrum_card_offset, duration=shot_globals.mw_time, freq=(local_oscillator_freq_mhz - uwave_clock - shot_globals.uwave_detuning)*1e6, amplitude=0.99, phase=0, ch=0, loops=1)
#     print(f'Spectrum card freq = {local_oscillator_freq_mhz - uwave_clock - shot_globals.mw_detuning}')
#     devices.uwave_absorp_switch.go_low(t + shot_globals.mw_time)
#     t += shot_globals.mw_time

# change the tweezer power back
devices.tweezer_aom_analog.constant(t,1)

t += 10e-3
if shot_globals.do_killing_pulse:
    devices.tweezer_aom_analog.constant(t,1)
    t = killing_pulse(t)
    devices.tweezer_aom_analog.constant(t,1)


t += 10e-3

# if shot_globals.do_killing_pulse:
#     devices.tweezer_aom_analog.constant(t,0.25)
#     t = killing_pulse(t)
#     devices.tweezer_aom_analog.constant(t,1)
# if shot_globals.do_killing_repump_pulse:
#     devices.tweezer_aom_analog.constant(t,0.25)
#     t += shot_globals.img_killing_pulse_time
#     devices.tweezer_aom_analog.constant(t,1)


# second shot
t = pre_imaging(t)
t += 10e-3 #100e-3
t = do_imaging(t, 2)


t += 1e-2
reset_shot(t)

devices.spectrum_uwave.single_freq(t, duration=100e-6, freq=10**6, amplitude=0.99, phase=0, ch=0, loops=1)
devices.spectrum_uwave.stop()

if shot_globals.do_dipole_trap:
    devices.ipg_1064_aom_digital.go_low(t)

if shot_globals.do_tweezers:
    # stop tweezers
    t2 = spectrum_manager.stop_tweezers(t)
    devices.tweezer_aom_digital.go_low(t)
    print('tweezer stop time:',t2)
    #t += 1e-3

    ##### dummy segment ######
    t1 = spectrum_manager.start_tweezers(t)
    print('tweezer start time:',t1)
    t += 2e-3
    t2 = spectrum_manager.stop_tweezers(t)
    print('tweezer stop time:',t2)
    #t += 1e-3################
    spectrum_manager.stop_card(t)

labscript.stop(t + 1e-2)












