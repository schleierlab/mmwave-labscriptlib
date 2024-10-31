# -*- coding: utf-8 -*-
"""
Created on Fri Feb 9 5:32:13 2024

@author: sslab
"""

import sys
root_path = r"C:\Users\sslab\labscript-suite\userlib\labscriptlib"

if root_path not in sys.path:
    sys.path.append(root_path)

import labscript

from connection_table import devices
from calibration import ta_freq_calib, repump_freq_calib, biasx_calib, biasy_calib, biasz_calib
from labscriptlib.shot_globals import shot_globals


mot_detuning = shot_globals.mot_detuning # MHz, optimized based on atom number
# ta_bm_detuning = shot_globals.ta_bm_detuning
# repump_bm_detuning = shot_globals.repump_bm_detuning


def mot_beam_molasses(t, ta_bm_detuning = shot_globals.ta_bm_detuning, repump_bm_detuning = shot_globals.repump_bm_detuning): #-100
    devices.ta_vco.ramp(
            t,
            duration=1e-3,
            initial=ta_freq_calib(mot_detuning),
            final=ta_freq_calib(ta_bm_detuning), #-190 MHz from Rydberg lab, -100 MHz from Aidelsburger's group, optimized around -200 MHz
            samplerate=1e5,
        )

    devices.repump_vco.ramp(
            t,
            duration=1e-3,
            initial=repump_freq_calib(0),
            final=repump_freq_calib(repump_bm_detuning), # doesn't play any significant effect
            samplerate=1e5,
        )

    devices.ta_aom_analog.ramp(
            t,
            duration=100e-6,
            initial=shot_globals.ta_power,
            final=shot_globals.ta_bm_power, #0.16, #0.15, # optimized on both temperature and atom number, too low power will lead to small atom number
            samplerate=1e5,
        )

    devices.repump_aom_analog.ramp(
            t,
            duration=100e-6,
            initial=shot_globals.repump_power,
            final=shot_globals.repump_bm_power, # doesn't play any significant effect
            samplerate=1e5,
        )

    devices.mot_coil_current_ctrl.ramp(
            t,
            duration=100e-6,
            initial=10/6,
            final=0,
            samplerate=1e5,
        )


    devices.x_coil_current.ramp(
            t,
            duration=100e-6,
            initial=shot_globals.mot_x_coil_voltage,
            final= biasx_calib(0),# 0 mG
            samplerate=1e5,
        )

    devices.y_coil_current.ramp(
            t,
            duration=100e-6,
            initial=shot_globals.mot_y_coil_voltage,
            final= biasy_calib(0),# 0 mG
            samplerate=1e5,
        )

    devices.z_coil_current.ramp(
            t,
            duration=100e-6,
            initial=shot_globals.mot_z_coil_voltage,
            final= biasz_calib(0),# 0 mG
            samplerate=1e5,
        )


    return t


def img_beam_molasses(t, ta_bm_detuning = shot_globals.img_ta_bm_detuning, repump_bm_detuning = shot_globals.img_repump_bm_detuning): #-100
    
    devices.ta_vco.ramp(
            t,
            duration=1e-3,
            initial=ta_freq_calib(mot_detuning),
            final=ta_freq_calib(ta_bm_detuning), #-190 MHz from Rydberg lab, -100 MHz from Aidelsburger's group, optimized around -200 MHz
            samplerate=1e5,
        )

    devices.repump_vco.ramp(
            t,
            duration=1e-3,
            initial=repump_freq_calib(0),
            final=repump_freq_calib(repump_bm_detuning), # doesn't play any significant effect
            samplerate=1e5,
        )

    devices.ta_aom_analog.ramp(
            t,
            duration=100e-6,
            initial=shot_globals.ta_power,
            final=shot_globals.img_ta_bm_power, #0.16, #0.15, # optimized on both temperature and atom number, too low power will lead to small atom number
            samplerate=1e5,
        )

    devices.repump_aom_analog.ramp(
            t,
            duration=100e-6,
            initial=shot_globals.repump_power,
            final=shot_globals.img_repump_bm_power, # doesn't play any significant effect
            samplerate=1e5,
        )


    devices.mot_coil_current_ctrl.ramp(
            t,
            duration=100e-6,
            initial=10/6,
            final=0,
            samplerate=1e5,
        )

    devices.x_coil_current.constant(t, biasx_calib(0))
    devices.y_coil_current.constant(t, biasy_calib(0))
    devices.z_coil_current.constant(t, biasz_calib(0))

    return t


def load_mot(t, mot_coil_ctrl_voltage=10/6, mot_detuning = shot_globals.mot_detuning):
    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)
    devices.mot_camera_trigger.go_low(t)
    devices.uwave_dds_switch.go_high(t)
    devices.uwave_absorp_switch.go_low(t)
    devices.ta_shutter.go_high(t)
    devices.repump_shutter.go_high(t)
    devices.mot_xy_shutter.go_high(t)
    devices.mot_z_shutter.go_high(t)
    devices.img_xy_shutter.go_low(t)
    devices.img_z_shutter.go_low(t)
    if shot_globals.do_uv:
        devices.uv_switch.go_high(t)
    devices.uv_switch.go_low(t+1e-2) # longer time will lead to the overall MOT atom number decay during the cycle

    devices.ta_aom_analog.constant(t, shot_globals.ta_power)
    devices.repump_aom_analog.constant(t, shot_globals.repump_power)

    devices.ta_vco.constant(t, ta_freq_calib(mot_detuning))  # 16 MHz red detuned
    devices.repump_vco.constant(t, repump_freq_calib(0))  # on resonance

    devices.mot_coil_current_ctrl.constant(t, mot_coil_ctrl_voltage) # 1/6 V/A, do not change to too high which may burn the coil

    devices.x_coil_current.constant(t, shot_globals.mot_x_coil_voltage)
    devices.y_coil_current.constant(t, shot_globals.mot_y_coil_voltage)
    devices.z_coil_current.constant(t, shot_globals.mot_z_coil_voltage)

    # devices.x_coil_current.constant(t, biasx_calib(0))
    # devices.y_coil_current.constant(t, biasy_calib(0))
    # devices.z_coil_current.constant(t, biasz_calib(0))

    # devices.x_coil_current.constant(t, biasx_calib(shot_globals.mot_biasx))
    # devices.y_coil_current.constant(t, biasy_calib(shot_globals.mot_biasy))
    # devices.z_coil_current.constant(t, biasz_calib(shot_globals.mot_biasz))
    return t


def do_MOT(t, coils_bool = shot_globals.do_mot_coil, dipole_bool = shot_globals.do_dipole_trap):
    if coils_bool:
        load_mot(t, mot_detuning=mot_detuning)
    else:
        load_mot(t, mot_detuning=mot_detuning, mot_coil_ctrl_voltage=0)
    
    #also includes the dipole trap
    if dipole_bool:
        devices.ipg_1064_aom_digital.go_high(t)
        devices.ipg_1064_aom_analog.constant(t, 1)
    
    return t


#does not step time
def do_blue_push(t, dur, blue_bool = shot_globals.do_456nm_laser, blue_power = shot_globals.blue_456nm_power):
    if blue_bool:
        devices.blue_456_shutter.open(t)
        devices.moglabs_456_aom_analog.constant(t, blue_power)
        devices.moglabs_456_aom_digital.go_high(t)
        devices.moglabs_456_aom_analog.constant(t+dur,0)
        devices.moglabs_456_aom_digital.go_low(t+dur)
    return t


#steps time
def do_molasses(t, dur = shot_globals.molasses_time*1e-3, img_beam_bool = shot_globals.do_molasses_img_beam, mot_beam_bool = shot_globals.do_molasses_mot_beam):
    if mot_beam_bool:
        load_molasses(t, ta_bm_detuning, repump_bm_detuning)
        t += dur # how long bright molasses last
        #turn off coil and light for TOF measurement, coil is already off in load_molasses
        devices.ta_aom_digital.go_low(t)
        devices.repump_aom_digital.go_low(t)

    if img_beam_bool:
        devices.mot_xy_shutter.close(t)
        devices.mot_z_shutter.close(t)
        devices.img_xy_shutter.open(t)
        devices.img_z_shutter.open(t)
        load_molasses_img_beam(t, ta_bm_detuning, repump_bm_detuning)

        t += dur  # how long bright molasses last
        #turn off coil and light for TOF measurement, coil is already off in load_molasses
        devices.ta_aom_digital.go_low(t)
        devices.repump_aom_digital.go_low(t)
    return t


def do_imaging(t, camera):
    did_molasses = shot_globals.do_molasses_img_beam or shot_globals.do_molasses_mot_beam
    if did_molasses:
        devices.ta_vco.ramp(
                t,
                duration=ta_vco_ramp_t,
                initial=ta_freq_calib(ta_bm_detuning),
                final=ta_freq_calib(shot_globals.ta_img_detuning),
                samplerate=4e5,
            )# ramp back to imaging

        devices.repump_vco.ramp(
                t,
                duration=ta_vco_ramp_t,
                initial=repump_freq_calib(repump_bm_detuning),
                final=repump_freq_calib(0),
                samplerate=4e5,
            )# ramp back to imaging
    else:
        print('no molasses')
        devices.ta_vco.ramp(
                t,
                duration=ta_vco_ramp_t,
                initial=ta_freq_calib(mot_detuning),
                final=ta_freq_calib(shot_globals.mot_detuning),
                samplerate=4e5,
            )# ramp back to imaging

        devices.repump_vco.ramp(
                t,
                duration=ta_vco_ramp_t,
                initial=repump_freq_calib(0),
                final=repump_freq_calib(0),
                samplerate=4e5,
            )# ramp back to imaging
    
    
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

    if camera == "mot":
        devices.manta419b_mot.expose(
            'manta419b',
            t,
            'atoms',
            exposure_time=max(shot_globals.manta_exposure, 50e-6),
        )

        t +=  shot_globals.manta_exposure
        devices.repump_aom_digital.go_low(t)
        devices.ta_aom_digital.go_low(t)
    
    if camera == "tweezer":
        devices.manta419b_tweezer.expose(
            'manta419b',
            t,
            'atoms',
            exposure_time=max(shot_globals.manta_exposure, 50e-6),
        )

        t +=  shot_globals.manta_exposure
        devices.repump_aom_digital.go_low(t)
        devices.ta_aom_digital.go_low(t)
    
    if shot_globals.do_kinetix_camera:

        # if shot_globals.kinetix_exp_res == 0:
        #     kinetix_exp_time = max(shot_globals.kinetix_exposure, 1e-3)
        # if shot_globals.kinetix_exp_res == 1:
        #     kinetix_exp_time = max(shot_globals.kinetix_exposure*1e-3, 1e-6)


        devices.kinetix.expose(
                'Kinetix',
                t,
                'atoms',
                exposure_time = max(shot_globals.kinetix_exposure, 1e-3),
            )

        print('t before exposure', t)

        t += shot_globals.kinetix_exposure

        print('t after exposure', t)

        print('exposure time', max(shot_globals.kinetix_exposure, 1e-3))

        devices.repump_aom_digital.go_low(t)
        devices.ta_aom_digital.go_low(t)

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


def reset_shot(t):
    devices.ta_vco.ramp(
        t,
        duration=ta_vco_ramp_t,
        # initial=ta_freq_calib(ta_pumping_detuning),
        initial=ta_freq_calib(shot_globals.ta_img_detuning),
        final=ta_freq_calib(mot_detuning),
        samplerate=1e5,
    )

    # set the default value into MOT loading value
    if shot_globals.do_mot_coil:
        load_mot(t,mot_detuning=mot_detuning)
    else:
        load_mot(t,mot_detuning=mot_detuning, mot_coil_ctrl_voltage=0)
    
    return t
