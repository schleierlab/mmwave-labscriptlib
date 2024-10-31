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
from calibration import ta_freq_calib, repump_freq_calib
from spectrum_manager import spectrum_manager
from labscriptlib.shot_globals import shot_globals

coil_off_time = 1.4e-3 # minimum time for the MOT coil to be off
min_shutter_off_t = 6.28e-3 # minimum time for shutter to be off and on again

devices.initialize()
ta_vco_ramp_t = 1.2e-4 # minimum TA ramp time to stay locked
ta_vco_stable_t = 1e-4 # stable time waited for lock
mot_detuning = shot_globals.mot_detuning  # -13 # MHz, optimized based on atom number
ta_bm_detuning = shot_globals.ta_bm_detuning  # -100 # MHz, bright molasses detuning
repump_bm_detuning = shot_globals.repump_bm_detuning  # 0 # MHz, bright molasses detuning

if shot_globals.do_tweezers:
    spectrum_manager.start_card()

labscript.start()

t = 0

devices.moglabs_456_aom_analog.constant(t, shot_globals.blue_456nm_power)
devices.moglabs_456_aom_digital.go_high(t)

if shot_globals.do_tweezers:
    t1 = spectrum_manager.start_tweezers(t) #has to be the first thing in the timing sequence (?)
    print('tweezer start time:',t1)


if shot_globals.do_mot_coil:
    load_mot(t, mot_detuning=mot_detuning)
else:
    load_mot(t, mot_detuning=mot_detuning, mot_coil_ctrl_voltage=0)

# Turn on the dipole trap
if shot_globals.do_dipole_trap:
    devices.ipg_1064_aom_digital.go_high(t)
    devices.ipg_1064_aom_analog.constant(t, 1)

# Turn on the tweezer
if shot_globals.do_tweezers:
    devices.tweezer_aom_digital.go_high(t)
    devices.tweezer_aom_analog.constant(t, 1) #0.3) #for single tweezer

t += 2 #2 #0.5  # how long MOT last

# Bright molasses stage
if shot_globals.do_molasses_mot_beam:
    load_molasses(t)

    if shot_globals.do_456nm_laser:
        devices.moglabs_456_aom_analog.constant(t, shot_globals.blue_456nm_power)
        devices.moglabs_456_aom_digital.go_high(t)

    t += shot_globals.molasses_time*1e-3  # how long bright molasses last
    #turn off coil and light for TOF measurement, coil is already off in load_molasses
    devices.ta_aom_digital.go_low(t)
    devices.repump_aom_digital.go_low(t)

    # devices.ta_shutter.close(t)
    # devices.repump_shutter.close(t)
    # devices.mot_xy_shutter.close(t)
    # devices.mot_z_shutter.close(t)


if shot_globals.do_molasses_img_beam:
    devices.mot_xy_shutter.close(t)
    devices.mot_z_shutter.close(t)
    devices.img_xy_shutter.open(t)
    devices.img_z_shutter.open(t)
    load_molasses_img_beam(t)

    if shot_globals.do_456nm_laser:
        devices.moglabs_456_aom_analog.constant(t, shot_globals.blue_456nm_power)
        devices.moglabs_456_aom_digital.go_high(t)

    t += shot_globals.molasses_time*1e-3  # how long bright molasses last
    #turn off coil and light for TOF measurement, coil is already off in load_molasses
    devices.ta_aom_digital.go_low(t)
    devices.repump_aom_digital.go_low(t)

    # devices.ta_shutter.close(t)
    # devices.repump_shutter.close(t)
    # devices.img_xy_shutter.close(t)
    # devices.img_z_shutter.close(t)




# assert shot_globals.tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter'"

# t += shot_globals.tof_imaging_delay-ta_vco_ramp_t-ta_vco_stable_t

if shot_globals.do_molasses_img_beam or shot_globals.do_molasses_mot_beam:
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
            final=ta_freq_calib(shot_globals.ta_img_detuning),
            samplerate=4e5,
        )# ramp back to imaging

    devices.repump_vco.ramp(
            t,
            duration=ta_vco_ramp_t,
            initial=repump_freq_calib(0),
            final=repump_freq_calib(0),
            samplerate=4e5,
        )# ramp back to imaging



devices.ta_aom_analog.constant(t , shot_globals.ta_img_power) # back to full power for imaging
devices.repump_aom_analog.constant(t , shot_globals.repump_img_power)


t += shot_globals.tof_imaging_delay

# t += ta_vco_ramp_t + ta_vco_stable_t
# devices.ta_shutter.open(t)
# devices.repump_shutter.open(t)
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

if shot_globals.do_MOT_camera:
    devices.manta419b_mot.expose(
        'manta419b',
        t,
        'atoms',
        exposure_time=max(shot_globals.manta_exposure, 50e-6),
    )

    t +=  shot_globals.manta_exposure
    devices.repump_aom_digital.go_low(t)
    devices.ta_aom_digital.go_low(t)

if shot_globals.do_tweezer_camera:
    devices.manta419b_tweezer.expose(
        'manta419b',
        t,
        'atoms',
        exposure_time=max(shot_globals.manta_exposure, 50e-6),
    )

    if shot_globals.do_blue_laser_camera_local:
        print('blue laser camera triggered!')
        devices.mot_camera_trigger.go_high(t)

    t +=  shot_globals.manta_exposure
    devices.repump_aom_digital.go_low(t)
    devices.ta_aom_digital.go_low(t)

if shot_globals.do_blue_laser_camera:
    devices.manta419b_blue_laser.expose(
        'manta419b',
        t,
        'atoms',
        exposure_time=max(shot_globals.manta_exposure, 50e-6),
    )

    t +=  shot_globals.manta_exposure
    devices.repump_aom_digital.go_low(t)
    devices.ta_aom_digital.go_low(t)

if shot_globals.do_kinetix_camera:

    if shot_globals.kinetix_exp_res == 0:
        kinetix_exp_time = max(shot_globals.kinetix_exposure, 1e-3)
    elif shot_globals.kinetix_exp_res == 1:
        kinetix_exp_time = max(shot_globals.kinetix_exposure*1e-3, 1e-6)

    devices.kinetix.expose(
            'Kinetix',
            t,
            'atoms',
            exposure_time = kinetix_exp_time,
        )

    if shot_globals.do_blue_laser_camera_local:
        print('blue laser camera triggered!')
        devices.mot_camera_trigger.go_high(t)

    t += kinetix_exp_time

    devices.repump_aom_digital.go_low(t)
    devices.ta_aom_digital.go_low(t)

    # do this when not using kinetix server and lyse
    # devices.kinetix_camera_trigger.go_high(t)
    # devices.kinetix_camera_trigger.go_low(t+shot_globals.kinetix_exposure)



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
# devices.ta_shutter.close(t)
# devices.repump_shutter.close(t)


# Turn off MOT for taking background images
t += 1e-1

devices.ta_aom_digital.go_low(t)
devices.repump_aom_digital.go_low(t)
# devices.ta_shutter.close(t)
# devices.repump_shutter.close(t)
devices.mot_xy_shutter.close(t)
devices.mot_z_shutter.close(t)

t += shot_globals.tof_imaging_delay
# devices.ta_shutter.open(t)
# devices.repump_shutter.open(t)
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


if shot_globals.do_MOT_camera:
    devices.manta419b_mot.expose(
        'manta419b',
        t,
        'atoms',
        exposure_time=max(shot_globals.manta_exposure, 50e-6),
    )

    t +=  shot_globals.manta_exposure
    devices.repump_aom_digital.go_low(t)
    devices.ta_aom_digital.go_low(t)

if shot_globals.do_tweezer_camera:
    devices.manta419b_tweezer.expose(
        'manta419b',
        t,
        'atoms',
        exposure_time=max(shot_globals.manta_exposure, 50e-6),
    )

    t +=  shot_globals.manta_exposure
    devices.repump_aom_digital.go_low(t)
    devices.ta_aom_digital.go_low(t)

if shot_globals.do_blue_laser_camera:
    devices.manta419b_blue_laser.expose(
        'manta419b',
        t,
        'atoms',
        exposure_time=max(shot_globals.manta_exposure, 50e-6),
    )

    t +=  shot_globals.manta_exposure
    devices.repump_aom_digital.go_low(t)
    devices.ta_aom_digital.go_low(t)

if shot_globals.do_kinetix_camera:

    if shot_globals.kinetix_exp_res == 0:
        kinetix_exp_time = max(shot_globals.kinetix_exposure, 1e-3)
    elif shot_globals.kinetix_exp_res == 1:
        kinetix_exp_time = max(shot_globals.kinetix_exposure*1e-3, 1e-6)

    devices.kinetix.expose(
            'Kinetix',
            t,
            'atoms',
            exposure_time = kinetix_exp_time,
        )

    t += kinetix_exp_time


    devices.repump_aom_digital.go_low(t)
    devices.ta_aom_digital.go_low(t)

    # do this when not using kinetix server and lyse
    # devices.kinetix_camera_trigger.go_high(t)
    # devices.kinetix_camera_trigger.go_low(t+shot_globals.kinetix_exposure)

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
# devices.ta_shutter.close(t)
# devices.repump_shutter.close(t)

# set ta detuning back to initial value
t += 1e-2
devices.ta_vco.ramp(
    t,
    duration=ta_vco_ramp_t,
    # initial=ta_freq_calib(ta_pumping_detuning),
    initial=ta_freq_calib(shot_globals.ta_img_detuning),
    final=ta_freq_calib(mot_detuning),
    samplerate=1e5,
)


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

if shot_globals.do_456nm_laser:
    devices.moglabs_456_aom_analog.constant(t,0)
    devices.moglabs_456_aom_digital.go_low(t)

# set the default value into MOT loading value
if shot_globals.do_mot_coil:
    load_mot(t,mot_detuning=mot_detuning)
else:
    load_mot(t,mot_detuning=mot_detuning, mot_coil_ctrl_voltage=0)

if shot_globals.do_blue_laser_camera_local:
    devices.mot_camera_trigger.go_low(t)

labscript.stop(t + 1e-2)
