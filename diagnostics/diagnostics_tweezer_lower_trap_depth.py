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

spcm_sequence_mode = shot_globals.do_sequence_mode

def load_mot(t, mot_coil_ctrl_voltage=10/6, mot_detuning = shot_globals.mot_ta_detuning):
    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)
    # devices.mot_camera_trigger.go_low(t)
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

    devices.ta_aom_analog.constant(t, shot_globals.mot_ta_power)
    devices.repump_aom_analog.constant(t, shot_globals.mot_repump_power)

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

def load_molasses(t, ta_bm_detuning = shot_globals.bm_ta_detuning, repump_bm_detuning = shot_globals.bm_repump_detuning): #-100
    devices.ta_vco.ramp(
            t,
            duration=1e-3,
            initial=ta_freq_calib(shot_globals.mot_ta_detuning),
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
            initial=shot_globals.mot_ta_power,
            final=shot_globals.bm_ta_power, #0.16, #0.15, # optimized on both temperature and atom number, too low power will lead to small atom number
            samplerate=1e5,
        )

    devices.repump_aom_analog.ramp(
            t,
            duration=100e-6,
            initial=shot_globals.mot_repump_power,
            final=shot_globals.bm_repump_power, # doesn't play any significant effect
            samplerate=1e5,
        )


    devices.mot_coil_current_ctrl.ramp(
            t,
            duration=100e-6,
            initial=10/6,
            final=0,
            samplerate=1e5,
        )

    # ramp to zero field calibrated by microwaves
    # ramp the bias coil from MOT loading field to molasses field
    # devices.x_coil_current.ramp(
    #         t,
    #         duration=100e-6,
    #         initial=0,
    #         final= 0.46968,#shot_globals.x_coil_voltage,
    #         samplerate=1e5,
    #     )

    # devices.y_coil_current.ramp(
    #         t,
    #         duration=100e-6,
    #         initial=0,
    #         final=0,#shot_globals.y_coil_voltage,
    #         samplerate=1e5,
    #     )

    # devices.z_coil_current.ramp(
    #         t,
    #         duration=100e-6,
    #         initial=0,
    #         final=0.77068,#shot_globals.z_coil_voltage,
    #         samplerate=1e5,
    #     )


    if shot_globals.mot_x_coil_voltage <0:
        devices.x_coil_current.ramp(
            t-4e-3,
            duration=100e-6,
            initial=shot_globals.mot_x_coil_voltage,
            final= biasx_calib(0),# 0 mG
            samplerate=1e5,
        )
    else:
        devices.x_coil_current.ramp(
                t,
                duration=100e-6,
                initial=shot_globals.mot_x_coil_voltage,
                final= biasx_calib(0),# 0 mG
                samplerate=1e5,
            )

    if shot_globals.mot_y_coil_voltage <0:
        devices.y_coil_current.ramp(
            t-4e-3,
            duration=100e-6,
            initial=shot_globals.mot_y_coil_voltage,
            final= biasx_calib(0),# 0 mG
            samplerate=1e5,
        )
    else:
        devices.y_coil_current.ramp(
                t,
                duration=100e-6,
                initial=shot_globals.mot_y_coil_voltage,
                final= biasy_calib(0),# 0 mG
                samplerate=1e5,
            )

    if shot_globals.mot_z_coil_voltage <0:
        devices.z_coil_current.ramp(
            t-4e-3,
            duration=100e-6,
            initial=shot_globals.mot_z_coil_voltage,
            final= biasx_calib(0),# 0 mG
            samplerate=1e5,
        )
    else:
        devices.z_coil_current.ramp(
                t,
                duration=100e-6,
                initial=shot_globals.mot_z_coil_voltage,
                final= biasz_calib(0),# 0 mG
                samplerate=1e5,
            )

    # devices.x_coil_current.constant(t, biasx_calib(0))
    # devices.y_coil_current.constant(t, biasy_calib(0))
    # devices.z_coil_current.constant(t, biasz_calib(0))

    return t

def load_molasses_img_beam(t, ta_bm_detuning = shot_globals.bm_img_ta_detuning, repump_bm_detuning = shot_globals.bm_img_repump_detuning): #-100
    devices.ta_vco.ramp(
            t,
            duration=1e-3,
            initial=ta_freq_calib(shot_globals.mot_ta_detuning),
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
            initial=shot_globals.mot_ta_power,
            final=shot_globals.bm_img_ta_power, #0.16, #0.15, # optimized on both temperature and atom number, too low power will lead to small atom number
            samplerate=1e5,
        )

    devices.repump_aom_analog.ramp(
            t,
            duration=100e-6,
            initial=shot_globals.mot_repump_power,
            final=shot_globals.bm_img_repump_power, # doesn't play any significant effect
            samplerate=1e5,
        )


    devices.mot_coil_current_ctrl.ramp(
            t,
            duration=100e-6,
            initial=10/6,
            final=0,
            samplerate=1e5,
        )

    # ramp to zero field calibrated by microwaves
    # ramp the bias coil from MOT loading field to molasses field
    # devices.x_coil_current.ramp(
    #         t,
    #         duration=100e-6,
    #         initial=0,
    #         final= 0.46968,#shot_globals.x_coil_voltage,
    #         samplerate=1e5,
    #     )

    # devices.y_coil_current.ramp(
    #         t,
    #         duration=100e-6,
    #         initial=0,
    #         final=0,#shot_globals.y_coil_voltage,
    #         samplerate=1e5,
    #     )

    # devices.z_coil_current.ramp(
    #         t,
    #         duration=100e-6,
    #         initial=0,
    #         final=0.77068,#shot_globals.z_coil_voltage,
    #         samplerate=1e5,
    #     )


    # devices.x_coil_current.ramp(
    #         t,
    #         duration=100e-6,
    #         initial=shot_globals.mot_x_coil_voltage,
    #         final= biasx_calib(0),# 0 mG
    #         samplerate=1e5,
    #     )

    # devices.y_coil_current.ramp(
    #         t,
    #         duration=100e-6,
    #         initial=shot_globals.mot_y_coil_voltage,
    #         final= biasy_calib(0),# 0 mG
    #         samplerate=1e5,
    #     )

    # devices.z_coil_current.ramp(
    #         t,
    #         duration=100e-6,
    #         initial=shot_globals.mot_z_coil_voltage,
    #         final= biasz_calib(0),# 0 mG
    #         samplerate=1e5,
    #     )

    devices.x_coil_current.constant(t, biasx_calib(0))
    devices.y_coil_current.constant(t, biasy_calib(0))
    devices.z_coil_current.constant(t, biasz_calib(0))

    return t

## fixed parameters in the script
coil_off_time = 1.4e-3 # minimum time for the MOT coil to be off
ta_vco_ramp_t = 1.2e-4
min_shutter_off_t = 6.28e-3  # minimum time for shutter to be off and on again
mot_detuning = shot_globals.mot_ta_detuning  # -13 # MHz, optimized based on atom number
ta_bm_detuning = shot_globals.bm_ta_detuning  # -100 # MHz, bright molasses detuning
repump_bm_detuning = shot_globals.bm_repump_detuning  # 0 # MHz, bright molasses detuning

devices.initialize()

def do_mot(t, dur, *, use_coil = shot_globals.do_mot_coil, close_aom = True, close_shutter = True):
    if use_coil:
        load_mot(t, mot_detuning=shot_globals.mot_ta_detuning)
        devices.mot_coil_current_ctrl.constant(t + dur, 0) # Turn off coils
    else:
        load_mot(t, mot_detuning=shot_globals.mot_ta_detuning, mot_coil_ctrl_voltage=0)

    if close_aom:
        devices.ta_aom_digital.go_low(t + dur)
        devices.repump_aom_digital.go_low(t + dur)

    if close_shutter:
        devices.mot_xy_shutter.close(t + dur)
        devices.mot_z_shutter.close(t + dur)

    return t

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

def do_mot_imaging(t, *, use_shutter = True):
    devices.ta_vco.ramp(
        t - ta_vco_ramp_t ,
        duration=ta_vco_ramp_t,
        initial=ta_freq_calib(shot_globals.mot_ta_detuning),
        final=ta_freq_calib(0),
        samplerate=4e5,
    ) # ramp to imaging

    # set ta and repump to full power
    devices.ta_aom_analog.constant(t, 1)
    devices.repump_aom_analog.constant(t, 1)


    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)

    if use_shutter:
        devices.mot_xy_shutter.open(t)
        devices.mot_z_shutter.open(t)

    devices.manta419b_mot.expose('manta419b', t, 'atoms', exposure_time=shot_globals.mot_exposure_time)

    t += shot_globals.mot_exposure_time


    devices.ta_aom_digital.go_low(t)
    devices.repump_aom_digital.go_low(t)

    if use_shutter:
        devices.mot_xy_shutter.close(t)
        devices.mot_z_shutter.close(t)

    return t

def reset_mot(t):
    devices.ta_vco.ramp(
        t,
        duration=ta_vco_ramp_t,
        initial=ta_freq_calib(0),
        final=ta_freq_calib(shot_globals.mot_ta_detuning),
        samplerate=4e5,
    )# ramp to MOT loading

    # set the default value into MOT loading value
    if shot_globals.do_mot_coil:
        load_mot(t, mot_detuning=shot_globals.mot_ta_detuning)
    else:
        load_mot(t, mot_detuning=shot_globals.mot_ta_detuning, mot_coil_ctrl_voltage=0)
    # devices.uv_switch.go_low(t)
    return t

def do_molasses(t, dur, *, use_img_beam = shot_globals.do_molasses_img_beam, use_mot_beam = shot_globals.do_molasses_mot_beam, close_shutter = True):
    assert (shot_globals.do_molasses_img_beam or shot_globals.do_molasses_mot_beam), "either do_molasses_img_beam or do_molasses_mot_beam has to be on"

    if use_mot_beam:
        load_molasses(t, shot_globals.bm_ta_detuning, shot_globals.bm_repump_detuning)
        #turn off coil and light for TOF measurement, coil is already off in load_molasses
        if close_shutter:
            devices.mot_xy_shutter.close(t+dur)
            devices.mot_z_shutter.close(t+dur)


    if use_img_beam:
        devices.mot_xy_shutter.close(t)
        devices.mot_z_shutter.close(t)
        devices.img_xy_shutter.open(t)
        devices.img_z_shutter.open(t)
        load_molasses_img_beam(t, shot_globals.bm_img_ta_detuning, shot_globals.bm_img_repump_detuning)
        if close_shutter:
            devices.img_xy_shutter.close(t+dur)
            devices.img_z_shutter.close(t+dur)

    #turn off coil and light for TOF measurement, coil is already off in load_molasses
    devices.ta_aom_digital.go_low(t+dur)
    devices.repump_aom_digital.go_low(t+dur)

def do_molasses_dipole_trap_imaging(t, *, img_ta_detuning = 0, img_repump_detuning = 0, img_ta_power = 1, img_repump_power = 1, exposure = shot_globals.bm_exposure_time, close_shutter = True):

    if shot_globals.do_molasses_mot_beam:
        devices.ta_vco.ramp(
                t-ta_vco_ramp_t,
                duration=ta_vco_ramp_t,
                initial=ta_freq_calib(shot_globals.bm_ta_detuning),
                final=ta_freq_calib(img_ta_detuning),
                samplerate=4e5,
            )# ramp back to imaging

        devices.repump_vco.ramp(
                t-ta_vco_ramp_t,
                duration=ta_vco_ramp_t,
                initial=repump_freq_calib(shot_globals.bm_repump_detuning),
                final=repump_freq_calib(img_repump_detuning),
                samplerate=4e5,
            )# ramp back to imaging

    if shot_globals.do_molasses_img_beam:
        devices.ta_vco.ramp(
                t-ta_vco_ramp_t,
                duration=ta_vco_ramp_t,
                initial=ta_freq_calib(shot_globals.bm_img_ta_detuning),
                final=ta_freq_calib(img_ta_detuning),
                samplerate=4e5,
            )# ramp back to imaging

        devices.repump_vco.ramp(
                t-ta_vco_ramp_t,
                duration=ta_vco_ramp_t,
                initial=repump_freq_calib(shot_globals.bm_img_repump_detuning),
                final=repump_freq_calib(img_repump_detuning),
                samplerate=4e5,
            )# ramp back to imaging

    if shot_globals.do_molasses_in_situ_check:
        if shot_globals.do_mot_beams_during_imaging:
            if shot_globals.do_mot_xy_beams_during_imaging:
                devices.mot_xy_shutter.open(t)
            if shot_globals.do_mot_z_beam_during_imaging:
                devices.mot_z_shutter.open(t)
    else:
        if shot_globals.do_mot_beams_during_imaging:
            devices.img_xy_shutter.close(t)
            devices.img_z_shutter.close(t)
            if shot_globals.do_mot_xy_beams_during_imaging:
                devices.mot_xy_shutter.open(t)
            if shot_globals.do_mot_z_beam_during_imaging:
                devices.mot_z_shutter.open(t)
        if shot_globals.do_img_beams_during_imaging:
            devices.mot_xy_shutter.close(t)
            devices.mot_z_shutter.close(t)
            if shot_globals.do_img_xy_beams_during_imaging:
                devices.img_xy_shutter.open(t)
            if shot_globals.do_img_z_beam_during_imaging:
                devices.img_z_shutter.open(t)

    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)
    # set ta and repump to full power
    devices.ta_aom_analog.constant(t, img_ta_power)
    devices.repump_aom_analog.constant(t, img_repump_power)

    if shot_globals.do_mot_camera:
        devices.manta419b_mot.expose(
            'manta419b',
            t,
            'atoms',
            exposure_time=max(exposure, 50e-6),
        )


    if shot_globals.do_tweezer_camera:
        devices.manta419b_tweezer.expose(
            'manta419b',
            t,
            'atoms',
            exposure_time=max(exposure, 50e-6),
        )

        # send a trigger to a local manta camera: (mot camera or blue laser camera)
        devices.mot_camera_trigger.go_high(t)
        devices.mot_camera_trigger.go_low(t+shot_globals.bm_exposure_time)

    if shot_globals.do_kinetix_camera:

        devices.kinetix.expose(
            'Kinetix',
            t,
            'atoms',
            exposure_time = max(exposure, 1e-3),
        )
        print('t after exposure', t)
        print('exposure time', max(exposure, 1e-3))


    t += exposure
    devices.repump_aom_digital.go_low(t)
    devices.ta_aom_digital.go_low(t)


    if close_shutter:
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

def turn_on_dipole_trap(t):
    devices.ipg_1064_aom_digital.go_high(t)
    devices.ipg_1064_aom_analog.constant(t, 1)

def turn_off_dipole_trap(t):
        devices.ipg_1064_aom_digital.go_low(t)
        devices.ipg_1064_aom_analog.constant(t, 0)

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
        final=ta_freq_calib(shot_globals.img_ta_detuning),
        samplerate=4e5,
    )# ramp back to imaging

    devices.repump_vco.ramp(
            t,
            duration=ta_vco_ramp_t,
            initial=repump_freq_calib(repump_last_detuning),
            final=repump_freq_calib(0),
            samplerate=4e5,
        )# ramp back to imaging

    ta_last_detuning = shot_globals.img_ta_detuning
    repump_last_detuning = 0

    devices.ta_aom_analog.constant(t , shot_globals.img_ta_power) # back to full power for imaging
    devices.repump_aom_analog.constant(t , shot_globals.img_repump_power)

    t += ta_vco_ramp_t
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
            exposure_time=max(shot_globals.img_exposure_time, 1e-3),
        )
        # do this when not using kinetix server (take picture locally)
        # devices.kinetix_camera_trigger.go_high(t)
        # devices.kinetix_camera_trigger.go_low(t+shot_globals.img_exposure_time)

        t +=  shot_globals.img_exposure_time
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


if shot_globals.do_mot_in_situ_check:


    labscript.start()
    t = 0
    mot_load_dur = 0.5

    do_mot(t, mot_load_dur, use_coil = True, close_aom = True, close_shutter = False)
    t += mot_load_dur # MOT loading time 500 ms

    t += coil_off_time # wait for the coil fully off

    t = do_mot_imaging(t, use_shutter = False)

    # Turn off MOT for taking background images
    t += 0.1 # Wait until the MOT disappear
    t = do_mot_imaging(t, use_shutter = False)

    # set back to initial value
    t += 1e-2
    reset_mot(t)

    labscript.stop(t + 1e-2)

if shot_globals.do_mot_tof_check:


    labscript.start()
    t = 0
    mot_load_dur = 0.5


    do_mot(t, mot_load_dur, use_coil = True, close_aom = True, close_shutter = False)
    t += mot_load_dur # MOT loading time 500 ms

    assert shot_globals.mot_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter"
    t += shot_globals.mot_tof_imaging_delay

    t = do_mot_imaging(t, use_shutter = True)

    # Turn off MOT for taking background images
    t += 0.1 # Wait until the MOT disappear
    t = do_mot_imaging(t, use_shutter = True)

    # set back to initial value
    t += 1e-2
    reset_mot(t)

    labscript.stop(t + 1e-2)

if shot_globals.do_molasses_in_situ_check:
    labscript.start()

    t = 0
    mot_load_dur = 0.75
    do_mot(t, mot_load_dur, use_coil = True, close_aom = False, close_shutter = False)
    t += mot_load_dur  # how long MOT last


    molasses_dur = shot_globals.bm_time
    do_molasses(t, molasses_dur, close_shutter = False)
    t += molasses_dur

    t += ta_vco_ramp_t # account for the ramp before imaging
    t = do_molasses_dipole_trap_imaging(t, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=1, img_repump_power=1, exposure= shot_globals.bm_exposure_time, close_shutter= False)

    # Turn off MOT for taking background images
    t += 1e-1
    # devices.ta_aom_digital.go_low(t)
    # devices.repump_aom_digital.go_low(t)
    # devices.mot_xy_shutter.close(t)
    # devices.mot_z_shutter.close(t)

    t +=  ta_vco_ramp_t
    t = do_molasses_dipole_trap_imaging(t, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=1, img_repump_power=1, exposure= shot_globals.bm_exposure_time, close_shutter= False)


    t += 1e-2
    reset_mot(t)

    labscript.stop(t + 1e-2)

if shot_globals.do_molasses_tof_check:
    labscript.start()

    t = 0
    mot_load_dur = 0.75
    do_mot(t, mot_load_dur, use_coil = True, close_aom = False, close_shutter = False)
    t += mot_load_dur  # how long MOT last


    molasses_dur = shot_globals.bm_time
    do_molasses(t, molasses_dur, close_shutter = True)
    t += molasses_dur


    assert shot_globals.bm_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter"
    t += shot_globals.bm_tof_imaging_delay
    t = do_molasses_dipole_trap_imaging(t, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=1, img_repump_power=1, exposure= shot_globals.bm_exposure_time, close_shutter= True)


    # Turn off MOT for taking background images
    t += 1e-1
    # devices.ta_aom_digital.go_low(t)
    # devices.repump_aom_digital.go_low(t)
    # devices.mot_xy_shutter.close(t)
    # devices.mot_z_shutter.close(t)

    t += shot_globals.bm_tof_imaging_delay
    t = do_molasses_dipole_trap_imaging(t, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=1, img_repump_power=1, exposure= shot_globals.bm_exposure_time, close_shutter= True)


    t += 1e-2
    reset_mot(t)

    labscript.stop(t + 1e-2)

if shot_globals.do_dipole_trap_tof_check:
    labscript.start()


    t = 0
    if shot_globals.do_dipole_trap:
        turn_on_dipole_trap(t)
    else:
        turn_off_dipole_trap(t)

    if shot_globals.do_tweezers:
        spectrum_manager.start_card()
        t1 = spectrum_manager.start_tweezers(t) #has to be the first thing in the timing sequence (?)
        print('tweezer start time:',t1)
        # Turn on the tweezer
        devices.tweezer_aom_digital.go_high(t)
        devices.tweezer_aom_analog.constant(t, 1) #0.3) #for single tweezer

    mot_load_dur = 0.75
    do_mot(t, mot_load_dur, use_coil = True, close_aom = False, close_shutter = False)
    t += mot_load_dur  # how long MOT last


    molasses_dur = shot_globals.bm_time
    do_molasses(t, molasses_dur, close_shutter = True)
    t += molasses_dur


    assert shot_globals.img_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter"
    t += shot_globals.img_tof_imaging_delay
    t = do_molasses_dipole_trap_imaging(
        t,
        img_ta_detuning = shot_globals.img_ta_detuning,
        img_repump_detuning = 0,
        img_ta_power = shot_globals.img_ta_power,
        img_repump_power = shot_globals.img_repump_power,
        exposure = shot_globals.img_exposure_time,
        close_shutter = True
        )


    turn_off_dipole_trap(t)

    # Turn off MOT for taking background images
    t += 1e-1
    # devices.ta_aom_digital.go_low(t)
    # devices.repump_aom_digital.go_low(t)
    # devices.mot_xy_shutter.close(t)
    # devices.mot_z_shutter.close(t)

    t += shot_globals.img_tof_imaging_delay
    t = do_molasses_dipole_trap_imaging(
        t,
        img_ta_detuning = shot_globals.img_ta_detuning,
        img_repump_detuning = 0 ,
        img_ta_power = shot_globals.img_ta_power,
        img_repump_power = shot_globals.img_repump_power,
        exposure = shot_globals.img_exposure_time,
        close_shutter = True
        )


    t += 1e-2
    reset_mot(t)

    if shot_globals.do_tweezers:
        # stop tweezers
        t2 = spectrum_manager.stop_tweezers(t)
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

if shot_globals.do_tweezer_position_check:
    # look at the trap intensity distribution on the tweezer camera
    # look at it's relative position to the molasses
    labscript.start()

    t = 0
    mot_load_dur = 0.5
    if shot_globals.do_tweezers:
        if spcm_sequence_mode:
            spectrum_manager.start_card()
            t1 = spectrum_manager.start_tweezers(t)
        else:
            spectrum_manager_fifo.start_tweezer_card()
            t1 = spectrum_manager_fifo.start_tweezers(t) #has to be the first thing in the timing sequence (?)
        devices.dds0.synthesize(t+1e-3, freq = TW_y_freqs, amp = 0.95, ph = 0) # unit: MHz
        print('tweezer x start time:',t1)
        # Turn on the tweezer
        devices.tweezer_aom_digital.go_high(t)
        devices.tweezer_aom_analog.constant(t, 0.1) #0.3) #for single tweezer

    do_mot(t, mot_load_dur, use_coil = True, close_aom = False, close_shutter = False)
    t += mot_load_dur  # how long MOT last


    molasses_dur = shot_globals.bm_time
    do_molasses(t, molasses_dur, close_shutter = False)
    t += molasses_dur

    t += ta_vco_ramp_t # account for the ramp before imaging
    t = do_molasses_dipole_trap_imaging(t, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=1, img_repump_power=1, exposure= shot_globals.bm_exposure_time, close_shutter= False)

    # Turn off MOT for taking background images
    t += 1e-1
    # devices.ta_aom_digital.go_low(t)
    # devices.repump_aom_digital.go_low(t)
    # devices.mot_xy_shutter.close(t)
    # devices.mot_z_shutter.close(t)

    t +=  ta_vco_ramp_t
    t = do_molasses_dipole_trap_imaging(t, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=1, img_repump_power=1, exposure= shot_globals.bm_exposure_time, close_shutter= False)


    t += 1e-2
    reset_mot(t)

    if shot_globals.do_tweezers:
        # stop tweezers
        devices.tweezer_aom_digital.go_low(t)
        if spcm_sequence_mode:
            t2 = spectrum_manager.stop_tweezers(t)
            ##### dummy segment ######
            t1 = spectrum_manager.start_tweezers(t)
            print('tweezer start time:',t1)
            t += 2e-3
            t2 = spectrum_manager.stop_tweezers(t)
            print('tweezer stop time:',t2)
            #################
            spectrum_manager.stop_card(t)
        else:
            t2 = spectrum_manager_fifo.stop_tweezers(t)
        print('tweezer stop time:',t2)

    spectrum_manager_fifo.stop_tweezer_card()

    labscript.stop(t + 1e-2)

if shot_globals.do_tweezer_check:
    labscript.start()

    t = 0

    if shot_globals.do_tweezers:
        devices.dds0.synthesize(t+1e-2, shot_globals.TW_y_freqs, 0.95, 0)
        spectrum_manager.start_card()
        t1 = spectrum_manager.start_tweezers(t) #has to be the first thing in the timing sequence (?)
        print('tweezer start time:',t1)
        # Turn on the tweezer
        devices.tweezer_aom_digital.go_high(t)
        devices.tweezer_aom_analog.constant(t, 1) #0.3) #for single tweezer

    MOT_load_dur = 0.5
    do_MOT(t, MOT_load_dur)
    t += MOT_load_dur # how long MOT last


    molasses_dur = shot_globals.bm_time
    load_molasses(t, ta_bm_detuning, repump_bm_detuning)
    t += molasses_dur
    ta_last_detuning =  ta_bm_detuning
    repump_last_detuning = repump_bm_detuning

    print('Molasses stage')
    print(f'ta_last_detuning = {ta_last_detuning}')
    print(f'repump_last_detuning = {repump_last_detuning}')


    devices.mot_xy_shutter.close(t)
    devices.mot_z_shutter.close(t)

    t += 7e-3

    t = pre_imaging(t)

    if shot_globals.do_robust_loading_pulse:
        robust_loading_pulse(t, dur = shot_globals.robust_loading_pulse_dur)
        t += shot_globals.robust_loading_pulse_dur

    assert shot_globals.img_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter'"
    t += shot_globals.img_tof_imaging_delay

    t = do_imaging(t, 1)

    if do_tw_cooling_while_ramp:
        t += min_shutter_off_t
        devices.ta_aom_digital.go_high(t)
        devices.repump_aom_digital.go_high(t)
        devices.img_xy_shutter.open(t)
        devices.img_z_shutter.open(t)
    else:
        t += 7e-3 # make sure sutter fully closed after 1st imaging

    if do_tw_power_ramp == True:
        t += devices.tweezer_aom_analog.ramp(
            t,
            duration=shot_globals.tw_ramp_dur,
            initial= 1,
            final=shot_globals.tw_ramp_power,
            samplerate=4e5,
        )

    if do_tw_cooling_while_ramp: # need at least 2 ms to fully close the shutters. At time t shutter start to close
        assert shot_globals.tw_ramp_dur > 2e-3, "ramp time too short for shutter to close"
        devices.ta_aom_digital.go_low(t)
        devices.repump_aom_digital.go_low(t)
        devices.img_xy_shutter.close(t-2e-3)
        devices.img_z_shutter.close(t-2e-3)

    # turn trap off
    devices.tweezer_aom_digital.go_low(t)
    devices.tweezer_aom_analog.constant(0,t)
    t+= shot_globals.tw_turn_off_time
    devices.tweezer_aom_digital.go_high(t)

    if do_tw_power_ramp == True:
        t += devices.tweezer_aom_analog.ramp(
            t,
            duration=shot_globals.tw_ramp_dur,
            initial= shot_globals.tw_ramp_power,
            final=1,
            samplerate=4e5,
        )

    # second shot
    t = pre_imaging(t)
    t += 10e-3 #100e-3
    t = do_imaging(t, 2)

    t += 1e-2
    reset_mot(t)

    if shot_globals.do_tweezers:
        # stop tweezers
        t2 = spectrum_manager.stop_tweezers(t)
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