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

if __name__ == "__main__":
    devices.initialize()

## fixed parameters in the script
coil_off_time = 1.4e-3 # minimum time for the MOT coil to be off
ta_vco_ramp_t = 1.2e-4
min_shutter_off_t = 6.28e-3  # minimum time for shutter to be off and on again
mot_detuning = shot_globals.mot_ta_detuning  # -13 # MHz, optimized based on atom number
ta_bm_detuning = shot_globals.bm_ta_detuning  # -100 # MHz, bright molasses detuning
repump_bm_detuning = shot_globals.bm_repump_detuning  # 0 # MHz, bright molasses detuning

def load_mot(t, mot_detuning, mot_coil_ctrl_voltage=10/6):
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

def load_molasses(t, ta_bm_detuning , repump_bm_detuning): #-100

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

    print('bias x:', biasx_calib(0), '\n bias y:', biasy_calib(0), '\n bias z:', biasz_calib(0))

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
            final= biasz_calib(0),# 0 mG
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

    ta_last_detuning = shot_globals.bm_ta_detuning
    repump_last_detuning = shot_globals.bm_repump_detuning

    print('Molasses stage')
    print(f'ta_last_detuning = {ta_last_detuning}')
    print(f'repump_last_detuning = {repump_last_detuning}')
    return t, ta_last_detuning, repump_last_detuning

def load_molasses_img_beam(t, ta_bm_detuning, repump_bm_detuning ): #-100
    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)
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

    # devices.x_coil_current.constant(t, biasx_calib(0))
    # devices.y_coil_current.constant(t, biasy_calib(0))
    # devices.z_coil_current.constant(t, biasz_calib(0))
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
            final= biasz_calib(0),# 0 mG
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

    ta_last_detuning = shot_globals.bm_img_ta_detuning
    repump_last_detuning = shot_globals.bm_img_repump_detuning

    print('Molasses stage')
    print(f'ta_last_detuning = {ta_last_detuning}')
    print(f'repump_last_detuning = {repump_last_detuning}')
    return t, ta_last_detuning, repump_last_detuning


def do_mot(t, dur, *, use_coil , close_aom = True, close_shutter = True):
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

def do_MOT(t, dur, coils_bool):
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

    devices.manta419b_mot.expose('manta419b', t, 'atoms', exposure_time = shot_globals.mot_exposure_time)

    t += shot_globals.mot_exposure_time


    devices.ta_aom_digital.go_low(t)
    devices.repump_aom_digital.go_low(t)

    if use_shutter:
        devices.mot_xy_shutter.close(t)
        devices.mot_z_shutter.close(t)

    return t

def reset_mot(t, ta_last_detuning):
    print(f"time in diagonistics python {t}")
    t += devices.ta_vco.ramp(
        t,
        duration=ta_vco_ramp_t,
        initial=ta_freq_calib(ta_last_detuning),
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

def do_molasses(t, dur, *, use_img_beam , use_mot_beam , close_shutter = True):
    assert (shot_globals.do_molasses_img_beam or shot_globals.do_molasses_mot_beam), "either do_molasses_img_beam or do_molasses_mot_beam has to be on"

    if use_mot_beam:
        assert shot_globals.bm_ta_detuning != 0, "bright molasses detuning = 0, did you forget to correct for the new case ?"
        _, ta_last_detuning, repump_last_detuning = load_molasses(t, shot_globals.bm_ta_detuning, shot_globals.bm_repump_detuning)

        print(f"molasses detuning is {shot_globals.bm_ta_detuning}")
        #turn off coil and light for TOF measurement, coil is already off in load_molasses
        if close_shutter:
            devices.mot_xy_shutter.close(t+dur)
            devices.mot_z_shutter.close(t+dur)

    if use_img_beam:
        devices.ta_aom_digital.go_low(t)
        devices.repump_aom_digital.go_low(t)
        devices.mot_xy_shutter.close(t)
        devices.mot_z_shutter.close(t)
        devices.img_xy_shutter.open(t)
        devices.img_z_shutter.open(t)
        assert shot_globals.bm_ta_detuning != 0, "bright molasses detuning = 0, did you forget to correct for the new case ?"
        _, ta_last_detuning, repump_last_detuning = load_molasses_img_beam(t, shot_globals.bm_img_ta_detuning, shot_globals.bm_img_repump_detuning)
        if close_shutter:
            devices.img_xy_shutter.close(t+dur)
            devices.img_z_shutter.close(t+dur)

    #turn off coil and light for TOF measurement, coil is already off in load_molasses
    devices.ta_aom_digital.go_low(t+dur)
    devices.repump_aom_digital.go_low(t+dur)

    return ta_last_detuning, repump_last_detuning


def do_molasses_dipole_trap_imaging(t, ta_last_detuning, repump_last_detuning, *, img_ta_detuning = 0, img_repump_detuning = 0, img_ta_power = 1, img_repump_power = 1, exposure = shot_globals.bm_exposure_time, do_repump = True, close_shutter = True):

    devices.x_coil_current.constant(t, biasx_calib(0)) # define quantization axis
    devices.y_coil_current.constant(t, biasy_calib(0)) # define quantization axis
    devices.z_coil_current.constant(t, biasz_calib(0)) # define quantization axis

    devices.ta_shutter.open(t)
    if do_repump:
        devices.repump_shutter.open(t)
    else:
        devices.repump_shutter.close(t)

    if shot_globals.do_molasses_mot_beam:
        devices.ta_vco.ramp(
                t-ta_vco_ramp_t,
                duration=ta_vco_ramp_t,
                initial=ta_freq_calib(ta_last_detuning), #ta_freq_calib(shot_globals.bm_ta_detuning),
                final=ta_freq_calib(img_ta_detuning),
                samplerate=4e5,
            )# ramp back to imaging

        devices.repump_vco.ramp(
                t-ta_vco_ramp_t,
                duration=ta_vco_ramp_t,
                initial=repump_freq_calib(repump_last_detuning),#repump_freq_calib(shot_globals.bm_repump_detuning),
                final=repump_freq_calib(img_repump_detuning),
                samplerate=4e5,
            )# ramp back to imaging

    if shot_globals.do_molasses_img_beam:
        devices.ta_vco.ramp(
                t-ta_vco_ramp_t,
                duration=ta_vco_ramp_t,
                initial=ta_freq_calib(ta_last_detuning),#ta_freq_calib(shot_globals.bm_img_ta_detuning),
                final=ta_freq_calib(img_ta_detuning),
                samplerate=4e5,
            )# ramp back to imaging

        devices.repump_vco.ramp(
                t-ta_vco_ramp_t,
                duration=ta_vco_ramp_t,
                initial=repump_freq_calib(repump_last_detuning), #repump_freq_calib(shot_globals.bm_img_repump_detuning),
                final=repump_freq_calib(img_repump_detuning),
                samplerate=4e5,
            )# ramp back to imaging

    ta_last_detuning = img_ta_detuning
    repump_last_detuning = img_repump_detuning

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
        devices.tweezer_camera_trigger.go_high(t)
        devices.tweezer_camera_trigger.go_low(t+shot_globals.bm_exposure_time)


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
    return t, ta_last_detuning, repump_last_detuning

# def do_imaging_beam_pulse(t, *, img_ta_detuning = 0, img_repump_detuning = 0, img_ta_power = 1, img_repump_power = 1, exposure = shot_globals.bm_exposure_time, close_shutter = True):
def do_imaging_beam_pulse(t, ta_last_detuning, repump_last_detuning):

    blue_detuning = 10

    devices.ta_vco.ramp(
            t-ta_vco_ramp_t,
            duration=ta_vco_ramp_t,
            initial=ta_freq_calib(ta_last_detuning),#ta_freq_calib(shot_globals.bm_img_ta_detuning),
            final=ta_freq_calib(blue_detuning),
            samplerate=4e5,
        )# ramp back to imaging

    devices.repump_vco.ramp(
            t-ta_vco_ramp_t,
            duration=ta_vco_ramp_t,
            initial=repump_freq_calib(repump_last_detuning), #repump_freq_calib(shot_globals.bm_img_repump_detuning),
            final=repump_freq_calib(blue_detuning),
            samplerate=4e5,
        )# ramp back to imaging

    devices.mot_xy_shutter.close(t)
    devices.mot_z_shutter.close(t)
    if shot_globals.do_img_xy_beams_during_imaging:
        devices.img_xy_shutter.open(t)
    if shot_globals.do_img_z_beam_during_imaging:
        devices.img_z_shutter.open(t)

    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)
    # set ta and repump to full power
    devices.ta_aom_analog.constant(t, 1)#0.5)
    devices.repump_aom_analog.constant(t, 1)#0.5)


    t += shot_globals.img_pulse_time
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

    t += 3e-3
    devices.ta_vco.ramp(
            t-ta_vco_ramp_t,
            duration=ta_vco_ramp_t,
            initial=ta_freq_calib(blue_detuning),
            final=ta_freq_calib(shot_globals.bm_img_ta_detuning),
            samplerate=4e5,
        )# ramp back to imaging

    devices.repump_vco.ramp(
            t-ta_vco_ramp_t,
            duration=ta_vco_ramp_t,
            initial=repump_freq_calib(blue_detuning),
            final=repump_freq_calib(shot_globals.bm_img_repump_detuning),
            samplerate=4e5,
        )# ramp back to imaging

    ta_last_detuning = shot_globals.bm_img_ta_detuning
    repump_last_detuning = shot_globals.bm_img_repump_detuning
    return t, ta_last_detuning, repump_last_detuning


def turn_on_dipole_trap(t):
    devices.ipg_1064_aom_digital.go_high(t)
    devices.ipg_1064_aom_analog.constant(t, 1)


def turn_off_dipole_trap(t):
        devices.ipg_1064_aom_digital.go_low(t)
        devices.ipg_1064_aom_analog.constant(t, 0)


def pre_imaging(t, ta_last_detuning, repump_last_detuning):
    devices.x_coil_current.constant(t, biasx_calib(0))  # define quantization axis
    devices.y_coil_current.constant(t, biasy_calib(0))  # define quantization axis
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

    assert shot_globals.img_ta_power !=0, "Imaging ta power = 0, did you forget to adjust for the case?"
    assert shot_globals.img_repump_power !=0, "Imaging repump power = 0, did you forget to adjust for the case?"
    devices.ta_aom_analog.constant(t , shot_globals.img_ta_power) # back to full power for imaging
    devices.repump_aom_analog.constant(t , shot_globals.img_repump_power)

    t += ta_vco_ramp_t

    print('preimaging stage')
    print(f'ta_last_detuning = {ta_last_detuning}')
    print(f'repump_last_detuning = {repump_last_detuning}')
    return t, ta_last_detuning, repump_last_detuning


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


def do_imaging(t, shot_number, ta_last_detuning, repump_last_detuning):
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
        t += kinetix_readout_time + shot_globals.kinetix_extra_readout_time  # need extra 7 ms for shutter to close on the second shot

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
    assert shot_globals.img_exposure_time !=0, "Imaging expsorue time = 0, did you forget to adjust for the case?"

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
    return t, ta_last_detuning, repump_last_detuning

def optical_pumping(t, ta_last_detuning, repump_last_detuning):
    ta_pumping_detuning = -251 # MHz 4->4 tansition
    ta_vco_stable_t = 1e-4 # stable time waited for lock
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
            final= biasx_calib(shot_globals.ryd_biasx_field),# 0 mG
            samplerate=1e5,
        )

        # devices.y_coil_current.ramp(
        #         t,
        #         duration=100e-6,
        #         initial=biasx_calib(shot_globals.op_biasy_field),
        #         final=  biasy_calib(shot_globals.biasy_field),# 0 mG
        #         samplerate=1e5,
        #     )
        devices.y_coil_current.constant(t, biasy_calib(shot_globals.ryd_biasy_field)) # define quantization axis

        devices.z_coil_current.ramp(
                t,
                duration=100e-6,
                initial=biasz_calib(op_biasz_field),
                final= biasz_calib(shot_globals.ryd_biasz_field),# 0 mG
                samplerate=1e5,
            )

        print(f'OP bias x, y, z voltage = {biasx_calib(op_biasx_field)}, {biasy_calib(op_biasy_field)}, {biasz_calib(op_biasz_field)}')
        ta_last_detuning = ta_pumping_detuning
        repump_last_detuning = repump_last_detuning

    devices.mot_xy_shutter.close(t)
    devices.mot_z_shutter.close(t)
    return t, ta_last_detuning, repump_last_detuning

def do_mot_in_situ_check():
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
    print("Running do_mot_in_situ_check")
    # set back to initial value
    t += 1e-2
    t = reset_mot(t, ta_last_detuning = 0)

    labscript.stop(t + 1e-2)

    return t

def do_mot_tof_check():
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
    t = reset_mot(t, ta_last_detuning = 0)

    labscript.stop(t + 1e-2)

    return t

def do_molasses_in_situ_check():
    labscript.start()

    t = 0
    mot_load_dur = 0.75

    # if shot_globals.do_tweezers:
    #     print("Initializing tweezers")
    #     devices.dds0.synthesize(t+1e-2, shot_globals.TW_y_freqs, 0.95, 0)
    #     spectrum_manager.start_card()
    #     t1 = spectrum_manager.start_tweezers(t) #has to be the first thing in the timing sequence (?)
    #     print('tweezer start time:',t1)
    #     # Turn on the tweezer
    #     devices.tweezer_aom_digital.go_high(t)
    #     devices.tweezer_aom_analog.constant(t, 1) #0.3) #for single tweezer
    if shot_globals.do_dipole_trap:
        turn_on_dipole_trap(t)
    else:
        turn_off_dipole_trap(t)

    do_mot(t, mot_load_dur, use_coil = True, close_aom = False, close_shutter = False)
    t += mot_load_dur  # how long MOT last


    molasses_dur = shot_globals.bm_time
    ta_last_detuning, repump_last_detuning = do_molasses(t, molasses_dur, close_shutter = False, use_img_beam = shot_globals.do_molasses_img_beam, use_mot_beam = shot_globals.do_molasses_mot_beam)
    t += molasses_dur

    t += ta_vco_ramp_t # account for the ramp before imaging

    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(
        t, ta_last_detuning, repump_last_detuning,
        img_ta_detuning=0,
        img_repump_detuning=0,
        img_ta_power=1,
        img_repump_power=1,
        exposure=shot_globals.bm_exposure_time,
        close_shutter=False
        )

    turn_off_dipole_trap(t)

    # Turn off MOT for taking background images
    t += 1e-1
    # devices.ta_aom_digital.go_low(t)
    # devices.repump_aom_digital.go_low(t)
    # devices.mot_xy_shutter.close(t)
    # devices.mot_z_shutter.close(t)

    t +=  ta_vco_ramp_t
    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(t, ta_last_detuning, repump_last_detuning, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=1, img_repump_power=1, exposure= shot_globals.bm_exposure_time, close_shutter= False)


    t += 1e-2
    t = reset_mot(t, ta_last_detuning)

    # if shot_globals.do_tweezers:
    #     # stop tweezers
    #     t2 = spectrum_manager.stop_tweezers(t)
    #     print('tweezer stop time:', t2)
    #     #t += 1e-3

    #     ##### dummy segment ######
    #     t1 = spectrum_manager.start_tweezers(t)
    #     print('tweezer start time:', t1)
    #     t += 2e-3
    #     t2 = spectrum_manager.stop_tweezers(t)
    #     print('tweezer stop time:',t2)
    #     #t += 1e-3################
    #     spectrum_manager.stop_card(t)

    labscript.stop(t + 1e-2)

    return t

def do_molasses_tof_check():
    labscript.start()

    t = 0
    mot_load_dur = 0.75

    # if shot_globals.do_tweezers:
    #     print("Initializing tweezers")
    #     devices.dds0.synthesize(t+1e-2, shot_globals.TW_y_freqs, 0.95, 0)
    #     spectrum_manager.start_card()
    #     t1 = spectrum_manager.start_tweezers(t) #has to be the first thing in the timing sequence (?)
    #     print('tweezer start time:',t1)
    #     # Turn on the tweezer
    #     devices.tweezer_aom_digital.go_high(t)
    #     devices.tweezer_aom_analog.constant(t, 1) #0.3) #for single tweezer

    do_mot(t, mot_load_dur, use_coil = True, close_aom = False, close_shutter = False)
    t += mot_load_dur  # how long MOT last


    molasses_dur = shot_globals.bm_time
    ta_last_detuning, repump_last_detuning = do_molasses(t, molasses_dur, close_shutter = True, use_img_beam = shot_globals.do_molasses_img_beam, use_mot_beam = shot_globals.do_molasses_mot_beam)
    t += molasses_dur


    assert shot_globals.bm_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter"
    t += shot_globals.bm_tof_imaging_delay
    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(t, ta_last_detuning, repump_last_detuning, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=1, img_repump_power=1, exposure= shot_globals.bm_exposure_time, close_shutter= True)


    # Turn off MOT for taking background images
    t += 1e-1
    # devices.ta_aom_digital.go_low(t)
    # devices.repump_aom_digital.go_low(t)
    # devices.mot_xy_shutter.close(t)
    # devices.mot_z_shutter.close(t)

    t += shot_globals.bm_tof_imaging_delay
    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(t, ta_last_detuning, repump_last_detuning, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=1, img_repump_power=1, exposure= shot_globals.bm_exposure_time, close_shutter= True)

    t += 1e-2
    t = reset_mot(t, ta_last_detuning)

    # if shot_globals.do_tweezers:
    #     # stop tweezers
    #     t2 = spectrum_manager.stop_tweezers(t)
    #     print('tweezer stop time:', t2)
    #     #t += 1e-3

    #     ##### dummy segment ######
    #     t1 = spectrum_manager.start_tweezers(t)
    #     print('tweezer start time:', t1)
    #     t += 2e-3
    #     t2 = spectrum_manager.stop_tweezers(t)
    #     print('tweezer stop time:',t2)
    #     #t += 1e-3################
    #     spectrum_manager.stop_card(t)

    labscript.stop(t + 1e-2)

    return t

def do_field_calib_in_molasses_check():
    labscript.start()

    t = 0
    mot_load_dur = 0.75
    spectrum_uwave_cable_atten = 4.4 #dB at 300 MHz
    spectrum_uwave_power = -1 #-3 # dBm
    #================================================================================
    # Spectrum card related for microwaves
    #================================================================================
    devices.spectrum_uwave.set_mode(replay_mode=b'sequence',
                                    channels=[{'name': 'microwaves', 'power': spectrum_uwave_power + spectrum_uwave_cable_atten, 'port': 0, 'is_amplified': False, 'amplifier': None, 'calibration_power': 12, 'power_mode': 'constant_total', 'max_pulses': 1},
                                            {'name': 'mmwaves', 'power': -11, 'port': 1, 'is_amplified': False, 'amplifier': None, 'calibration_power': 12, 'power_mode': 'constant_total', 'max_pulses': 1}],
                                    clock_freq=625,
                                    use_ext_clock=True,
                                    ext_clock_freq=10)

    do_mot(t, mot_load_dur, use_coil = True, close_aom = False, close_shutter = False)
    t += mot_load_dur  # how long MOT last


    molasses_dur = shot_globals.bm_time
    do_molasses(t, molasses_dur, close_shutter = True, use_img_beam = shot_globals.do_molasses_img_beam, use_mot_beam = shot_globals.do_molasses_mot_beam)
    t += molasses_dur

    ta_last_detuning = shot_globals.bm_ta_detuning
    repump_last_detuning = shot_globals.bm_repump_detuning
    t, ta_last_detuning, repump_last_detuning = optical_pumping(t, ta_last_detuning, repump_last_detuning)

    devices.x_coil_current.constant(t, biasx_calib(shot_globals.mw_biasx_field))   # define quantization axis
    devices.y_coil_current.constant(t, biasy_calib(shot_globals.mw_biasy_field))   # define quantization axis
    devices.z_coil_current.constant(t, biasz_calib(shot_globals.mw_biasz_field))   # define quantization axis

    # Turn on microwave
    # wait until the bias coils are on and the shutter is fullly closed
    bias_coil_on_time = 0.5e-3 # minimum time for the bias coil to be on
    shutter_ramp_time = 1.5e-3 # time for shutter to start open/close to fully open/close
    t += max(bias_coil_on_time, shutter_ramp_time, min_shutter_off_t)
    if shot_globals.do_mw:
        spectrum_card_offset = 52.8e-6 # the offset for the beging of output comparing to the trigger
        uwave_clock = 9.192631770e3 # in unit of MHz
        local_oscillator_freq_mhz = 9486 # in unit of MHz MKU LO 8-13 PLL setting
        t += spectrum_card_offset
        devices.uwave_absorp_switch.go_high(t)
        devices.spectrum_uwave.single_freq(t - spectrum_card_offset, duration=shot_globals.uwave_time, freq=(local_oscillator_freq_mhz - uwave_clock - shot_globals.uwave_detuning)*1e6, amplitude=0.99, phase=0, ch=0, loops=1)
        print(f'Spectrum card freq = {local_oscillator_freq_mhz - uwave_clock - shot_globals.uwave_detuning}')
        devices.uwave_absorp_switch.go_low(t + shot_globals.uwave_time)
        t += shot_globals.uwave_time


    # assert shot_globals.bm_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter"
    # t += shot_globals.bm_tof_imaging_delay
    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(t, ta_last_detuning, repump_last_detuning, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=0.1, img_repump_power=1, exposure= 10e-3, do_repump=shot_globals.mw_imaging_do_repump, close_shutter= True)


    # Turn off MOT for taking background images
    t += 1e-1
    # devices.ta_aom_digital.go_low(t)
    # devices.repump_aom_digital.go_low(t)
    # devices.mot_xy_shutter.close(t)
    # devices.mot_z_shutter.close(t)

    # t += shot_globals.bm_tof_imaging_delay
    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(t, ta_last_detuning, repump_last_detuning, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=0.1, img_repump_power=1, exposure= 10e-3, do_repump=shot_globals.mw_imaging_do_repump, close_shutter= True)

    t += 1e-2
    t = reset_mot(t, ta_last_detuning)

    labscript.stop(t + 1e-2)

    return t



def do_dipole_trap_tof_check():
    labscript.start()

    t = 0
    if shot_globals.do_dipole_trap:
        turn_on_dipole_trap(t)
    else:
        turn_off_dipole_trap(t)

    if shot_globals.do_tweezers:
        devices.dds0.synthesize(t+1e-2, shot_globals.TW_y_freqs, 0.95, 0)
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
    ta_last_detuning, repump_last_detuning = do_molasses(t, molasses_dur, close_shutter = True, use_img_beam = shot_globals.do_molasses_img_beam, use_mot_beam = shot_globals.do_molasses_mot_beam)
    t += molasses_dur


    assert shot_globals.img_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter"
    t += shot_globals.img_tof_imaging_delay
    assert shot_globals.img_exposure_time !=0, "Imaging expsorue time = 0, did you forget to adjust for the case?"
    assert shot_globals.img_ta_power !=0, "Imaging ta power = 0, did you forget to adjust for the case?"
    assert shot_globals.img_repump_power !=0, "Imaging repump power = 0, did you forget to adjust for the case?"
    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(
        t, ta_last_detuning, repump_last_detuning,
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
    assert shot_globals.img_exposure_time !=0, "Imaging expsorue time = 0, did you forget to adjust for the case?"
    assert shot_globals.img_ta_power !=0, "Imaging ta power = 0, did you forget to adjust for the case?"
    assert shot_globals.img_repump_power !=0, "Imaging repump power = 0, did you forget to adjust for the case?"
    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(
        t, ta_last_detuning, repump_last_detuning,
        img_ta_detuning = shot_globals.img_ta_detuning,
        img_repump_detuning = 0 ,
        img_ta_power = shot_globals.img_ta_power,
        img_repump_power = shot_globals.img_repump_power,
        exposure = shot_globals.img_exposure_time,
        close_shutter = True
        )


    t += 1e-2
    t = reset_mot(t, ta_last_detuning)

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

    return t

def do_img_beam_alignment_check():
    labscript.start()

    t = 0
    if shot_globals.do_dipole_trap:
        turn_on_dipole_trap(t)
    else:
        turn_off_dipole_trap(t)

    if shot_globals.do_tweezers:
        devices.dds0.synthesize(t+1e-2, shot_globals.TW_y_freqs, 0.95, 0)
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
    ta_last_detuning, repump_last_detuning = do_molasses(t, molasses_dur, close_shutter = True, use_img_beam = shot_globals.do_molasses_img_beam, use_mot_beam = shot_globals.do_molasses_mot_beam)
    t += molasses_dur

    assert shot_globals.img_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter"
    t += shot_globals.img_tof_imaging_delay

    if shot_globals.do_img_pulse:
        t, ta_last_detuning, repump_last_detuning = do_imaging_beam_pulse(t, ta_last_detuning, repump_last_detuning)
            # t,
            # img_ta_detuning = shot_globals.img_ta_detuning,
            # img_repump_detuning = 0,
            # img_ta_power = shot_globals.img_ta_power,
            # img_repump_power = shot_globals.img_repump_power,
            # exposure = shot_globals.img_exposure_time,
            # close_shutter = True
            # )
    else:
        t += shot_globals.img_pulse_time + 3e-3 + ta_vco_ramp_t*2

    t += 7e-3

    assert shot_globals.img_exposure_time !=0, "Imaging expsorue time = 0, did you forget to adjust for the case?"
    assert shot_globals.img_ta_power !=0, "Imaging ta power = 0, did you forget to adjust for the case?"
    assert shot_globals.img_repump_power !=0, "Imaging repump power = 0, did you forget to adjust for the case?"
    t, ta_last_detuning, repump_last_detuning, = do_molasses_dipole_trap_imaging(
        t, ta_last_detuning, repump_last_detuning,
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
    assert shot_globals.img_exposure_time !=0, "Imaging expsorue time = 0, did you forget to adjust for the case?"
    assert shot_globals.img_ta_power !=0, "Imaging ta power = 0, did you forget to adjust for the case?"
    assert shot_globals.img_repump_power !=0, "Imaging repump power = 0, did you forget to adjust for the case?"
    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(
        t, ta_last_detuning, repump_last_detuning,
        img_ta_detuning = shot_globals.img_ta_detuning,
        img_repump_detuning = 0 ,
        img_ta_power = shot_globals.img_ta_power,
        img_repump_power = shot_globals.img_repump_power,
        exposure = shot_globals.img_exposure_time,
        close_shutter = True
        )


    t += 1e-2
    t = reset_mot(t, ta_last_detuning)

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

    return t

def do_tweezer_position_check():
    # look at the trap intensity distribution on the tweezer camera
    # look at it's relative position to the molasses
    labscript.start()
    t = 0
    t += 1e-3

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
        devices.tweezer_aom_analog.constant(t, 0.3) #0.3) #for single tweezer


    t += 1e-3 #10 #1e-1

    ta_last_detuning = 0
    repump_last_detuning = 0

    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(t, ta_last_detuning, repump_last_detuning, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=0, img_repump_power=0, exposure= 50e-6, close_shutter= False)

    t += 7e-2

    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(t, ta_last_detuning, repump_last_detuning, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=0, img_repump_power=0, exposure= 50e-6, close_shutter= False)

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
            spectrum_manager_fifo.stop_tweezer_card()
        print('tweezer stop time:',t2)


    labscript.stop(t + 1e-2)

    return t

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
        devices.tweezer_aom_analog.constant(t, 1) #0.3) #for single tweezer

    if shot_globals.do_dipole_trap:
        turn_on_dipole_trap(t)
    else:
        turn_off_dipole_trap(t)

    do_MOT(t, MOT_load_dur, shot_globals.do_mot_coil)
    t += MOT_load_dur # how long MOT last

    #_, ta_last_detuning, repump_last_detuning = load_molasses(t, ta_bm_detuning, repump_bm_detuning)
    ta_last_detuning, repump_last_detuning = do_molasses(t, molasses_dur, close_shutter = True, use_img_beam = shot_globals.do_molasses_img_beam, use_mot_beam = shot_globals.do_molasses_mot_beam)
    t += molasses_dur
    # ta_last_detuning =  ta_bm_detuning
    # repump_last_detuning = repump_bm_detuning

    # devices.mot_xy_shutter.close(t)
    # devices.mot_z_shutter.close(t)

    t += 7e-3

    t, ta_last_detuning, repump_last_detuning = pre_imaging(t, ta_last_detuning, repump_last_detuning)

    if shot_globals.do_robust_loading_pulse:
        robust_loading_pulse(t, dur = shot_globals.robust_loading_pulse_dur)
        t += shot_globals.robust_loading_pulse_dur

    assert shot_globals.img_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter'"
    t += shot_globals.img_tof_imaging_delay

    t, ta_last_detuning, repump_last_detuning = do_imaging(t, 1, ta_last_detuning, repump_last_detuning)
    t += 7e-3 # make sure sutter fully closed after 1st imaging

    # second shot
    t, ta_last_detuning, repump_last_detuning = pre_imaging(t, ta_last_detuning, repump_last_detuning)
    t += 10e-3 #100e-3
    t, ta_last_detuning, repump_last_detuning = do_imaging(t, 2, ta_last_detuning, repump_last_detuning)

    t += 1e-2
    t = reset_mot(t, ta_last_detuning)
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
        do_mot_in_situ_check()

    if shot_globals.do_mot_tof_check:
        do_mot_tof_check()

    if shot_globals.do_molasses_in_situ_check:
        do_molasses_in_situ_check()

    if shot_globals.do_molasses_tof_check:
        do_molasses_tof_check()

    if shot_globals.do_field_calib_in_molasses_check:
        do_field_calib_in_molasses_check()

    if shot_globals.do_dipole_trap_tof_check:
        do_dipole_trap_tof_check()

    if shot_globals.do_img_beam_alignment_check:
        do_img_beam_alignment_check()

    if shot_globals.do_tweezer_position_check:
        do_tweezer_position_check()

    if shot_globals.do_tweezer_check:
        do_tweezer_check()
