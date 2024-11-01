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
from labscriptlib.shot_globals import shot_globals

coil_off_time = 1.4e-3  # minimum time for the MOT coil to be off
min_shutter_off_t = 6.28e-3  # minimum time for shutter to be off and on again

devices.initialize()
ta_vco_ramp_t = 1.2e-4  # minimum TA ramp time to stay locked
ta_vco_stable_t = 1e-4  # stable time waited for lock
mot_detuning = shot_globals.CONST_MOT_DETUNING  # -13 # MHz, optimized based on atom number
ta_bm_detuning = shot_globals.CONST_TA_BM_DETUNING  # -100 # MHz, bright molasses detuning
repump_bm_detuning = shot_globals.CONST_REPUMP_BM_DETUNING  # 0 # MHz, bright molasses detuning
blue_456_detuning = shot_globals.blue_456_detuning
camera_string = shot_globals.camera_string


def do_MOT(t, dur, use_coils: bool = shot_globals.do_mot_coil):
    if use_coils:
        load_mot(t, mot_detuning=mot_detuning)
    else:
        load_mot(t, mot_detuning=mot_detuning, mot_coil_ctrl_voltage=0)

    if shot_globals.do_molasses_img_beam:
        devices.mot_xy_shutter.close(t+dur)
        devices.mot_z_shutter.close(t+dur)

    # MOT coils ramped down in load_molasses
    return t


def do_dipole(t, dur, dipole_bool = shot_globals.do_dipole_trap):
    # also includes the dipole trap
    if dipole_bool:
        devices.ipg_1064_aom_digital.go_high(t)
        devices.ipg_1064_aom_analog.constant(t, 1)

        devices.ipg_1064_aom_digital.go_low(t+dur)
        devices.ipg_1064_aom_analog.constant(t+dur, 0)
    return t


def do_rydberg_excite(
        t: float,
        dur: float,
        use_blue_light: bool = shot_globals.do_456nm_laser,
        blue_power: float = shot_globals.blue_456nm_power):
    x_field = shot_globals.Ryd_x_field
    y_field = shot_globals.Ryd_y_field
    z_field = shot_globals.Ryd_z_field

    # Starts ramping field early, might not be what we want?
    ramp_duration = 100e-6
    devices.x_coil_current.ramp(
            t - ramp_duration,
            duration=ramp_duration,
            initial=biasx_calib(0),
            final=biasx_calib(x_field),
            samplerate=1e5,
        )

    devices.y_coil_current.ramp(
            t - ramp_duration,
            duration=ramp_duration,
            initial=biasy_calib(0),
            final=biasy_calib(y_field),
            samplerate=1e5,
        )

    devices.z_coil_current.ramp(
            t - ramp_duration,
            duration=ramp_duration,
            initial=biasz_calib(0),
            final=biasz_calib(z_field),
            samplerate=1e5,
        )

    if use_blue_light:
        devices.blue_456_shutter.open(t)
        devices.moglabs_456_aom_analog.constant(t, blue_power)
        devices.moglabs_456_aom_digital.go_high(t)
        devices.moglabs_456_aom_analog.constant(t+dur, 0)
        devices.moglabs_456_aom_digital.go_low(t+dur)
        devices.blue_456_shutter.close(t+dur)
    return t


def do_molasses(t, dur, img_beam_bool = shot_globals.do_molasses_img_beam, mot_beam_bool = shot_globals.do_molasses_mot_beam):
    if mot_beam_bool:
        load_molasses(t, ta_bm_detuning, repump_bm_detuning)
        # turn off coil and light for TOF measurement, coil is already off in load_molasses
        devices.ta_aom_digital.go_low(t+dur)
        devices.repump_aom_digital.go_low(t+dur)
        devices.mot_xy_shutter.close(t+dur)
        devices.mot_z_shutter.close(t+dur)

    if img_beam_bool:
        devices.img_xy_shutter.open(t)
        devices.img_z_shutter.open(t)
        load_molasses_img_beam(t, ta_bm_detuning, repump_bm_detuning)

        # turn off coil and light for TOF measurement, coil is already off in load_molasses
        devices.ta_aom_digital.go_low(t+dur)
        devices.repump_aom_digital.go_low(t+dur)
        devices.img_xy_shutter.close(t+dur)
        devices.img_z_shutter.close(t+dur)

    if img_beam_bool or mot_beam_bool:
        devices.ta_vco.ramp(
                t+dur,
                duration=ta_vco_ramp_t,
                initial=ta_freq_calib(ta_bm_detuning),
                final=ta_freq_calib(shot_globals.ta_img_detuning),
                samplerate=4e5,
            )# ramp back to imaging

        devices.repump_vco.ramp(
                t+dur,
                duration=ta_vco_ramp_t,
                initial=repump_freq_calib(repump_bm_detuning),
                final=repump_freq_calib(0),
                samplerate=4e5,
            )# ramp back to imaging
    else:
        print('no molasses')
        devices.ta_vco.ramp(
                t+dur,
                duration=ta_vco_ramp_t,
                initial=ta_freq_calib(mot_detuning),
                final=ta_freq_calib(shot_globals.CONST_MOT_DETUNING),
                samplerate=4e5,
            )# ramp back to imaging

        devices.repump_vco.ramp(
                t+dur,
                duration=ta_vco_ramp_t,
                initial=repump_freq_calib(0),
                final=repump_freq_calib(0),
                samplerate=4e5,
            )# ramp back to imaging

    return t


def do_imaging(t, camera):
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

        t += shot_globals.manta_exposure
        devices.repump_aom_digital.go_low(t)
        devices.ta_aom_digital.go_low(t)
    elif camera == "tweezer":
        devices.manta419b_tweezer.expose(
            'manta419b',
            t,
            'atoms',
            exposure_time=max(shot_globals.manta_exposure, 50e-6),
        )

        t += shot_globals.manta_exposure
        devices.repump_aom_digital.go_low(t)
        devices.ta_aom_digital.go_low(t)
    elif camera == "kinetix":

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

        t += shot_globals.kinetix_exposure

        print('t after exposure', t)

        print('exposure time', max(shot_globals.kinetix_exposure, 1e-3))

        devices.repump_aom_digital.go_low(t)
        devices.ta_aom_digital.go_low(t)
    else:
        raise ValueError('Unsupported camera!')

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


labscript.start()

t = 0
mot_load_dur = 0.75
molasses_dur = shot_globals.molasses_time*1e-3
ryd_excitation_dur = shot_globals.ryd_excitation_dur

do_MOT(t, mot_load_dur)
devices.dds1.synthesize(t+1e-3, blue_456_detuning, 0.2, 0)
do_dipole(t+1e-3, mot_load_dur + molasses_dur + shot_globals.molasses_tof_delay + ryd_excitation_dur + 0.1)


t += mot_load_dur  # 2 #0.5  # how long MOT last
do_molasses(t, molasses_dur)


t += molasses_dur


t += shot_globals.molasses_tof_delay
do_rydberg_excite(t, ryd_excitation_dur)


t += ryd_excitation_dur
devices.ta_aom_analog.constant(t, shot_globals.ta_img_power)  # back to full power for imaging
devices.repump_aom_analog.constant(t, shot_globals.repump_img_power)
t = do_imaging(t, camera_string)

# img_duration = take_image(t, camera_string)
# t += (img_duration + 0.1)


# Turn off MOT for taking background images
t += 1e-1
devices.ta_aom_digital.go_low(t)
devices.repump_aom_digital.go_low(t)
devices.mot_xy_shutter.close(t)
devices.mot_z_shutter.close(t)

t += shot_globals.molasses_tof_delay
t = do_imaging(t, camera_string)


t += 0.2
reset_shot(t)

labscript.stop(t + 1e-2)
