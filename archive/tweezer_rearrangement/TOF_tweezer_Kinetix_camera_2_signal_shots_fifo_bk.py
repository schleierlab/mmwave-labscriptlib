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
from spectrum_manager_fifo import spectrum_manager_fifo
from spectrum_manager import spectrum_manager
from labscriptlib.shot_globals import shot_globals

spcm_sequence_mode = shot_globals.do_sequence_mode
#=============== Note (20240402) ===============
# Use specturm card fifo mode for the tweezer X
# Use dds for tweezer Y (because fifo mode only support one channel for now)
#===============================================

coil_off_time = 1.4e-3 # minimum time for the MOT coil to be off
min_shutter_off_t = 6.28e-3 # minimum time for shutter to be off and on again

devices.initialize()
ta_vco_ramp_t = 1.2e-4 # minimum TA ramp time to stay locked
ta_vco_stable_t = 1e-4 # stable time waited for lock
mot_detuning = shot_globals.CONST_MOT_DETUNING  # -13 # MHz, optimized based on atom number
ta_bm_detuning = shot_globals.CONST_TA_BM_DETUNING  # -100 # MHz, bright molasses detuning
repump_bm_detuning = shot_globals.CONST_REPUMP_BM_DETUNING  # 0 # MHz, bright molasses detuning

TW_y_freqs = shot_globals.TW_y_freqs
# TW_y_amplitude = shot_globals.TW_y_amplitude


def do_MOT(t, dur, coils_bool = shot_globals.do_mot_coil):
    if coils_bool:
        load_mot(t, mot_detuning=mot_detuning)
    else:
        load_mot(t, mot_detuning=mot_detuning, mot_coil_ctrl_voltage=0)


    if shot_globals.do_molasses_img_beam:
        devices.mot_xy_shutter.close(t+dur)
        devices.mot_z_shutter.close(t+dur)

    #MOT coils ramped down in load_molasses

    return t

def do_dipole(t, dur,  dipole_bool = shot_globals.do_dipole_trap):
    #also includes the dipole trap
    if dipole_bool:
        devices.ipg_1064_aom_digital.go_high(t)
        devices.ipg_1064_aom_analog.constant(t, 1)

        devices.ipg_1064_aom_digital.go_low(t+dur)
        devices.ipg_1064_aom_analog.constant(t+dur, 0)
    return t

def do_molasses(t, dur, img_beam_bool = shot_globals.do_molasses_img_beam, mot_beam_bool = shot_globals.do_molasses_mot_beam):
    if mot_beam_bool:
        load_molasses(t, ta_bm_detuning, repump_bm_detuning)
        #turn off coil and light for TOF measurement, coil is already off in load_molasses
        devices.ta_aom_digital.go_low(t+dur)
        devices.repump_aom_digital.go_low(t+dur)
        devices.mot_xy_shutter.close(t+dur)
        devices.mot_z_shutter.close(t+dur)

    if img_beam_bool:
        devices.img_xy_shutter.open(t)
        devices.img_z_shutter.open(t)
        load_molasses_img_beam(t, ta_bm_detuning, repump_bm_detuning)

        #turn off coil and light for TOF measurement, coil is already off in load_molasses
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
                final=ta_freq_calib(shot_globals.ta_img_detuning),
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

def do_imaging(t, shot_number):
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

def reset_shot(t):
    # set ta detuning back to initial value
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

def robust_loading_pulse(t, dur):
    devices.img_xy_shutter.open(t)
    devices.img_z_shutter.open(t)
    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)
    t += dur
    devices.repump_aom_digital.go_low(t)
    devices.ta_aom_digital.go_low(t)
    devices.img_xy_shutter.close(t)
    devices.img_z_shutter.close(t)
    return t

MOT_load_dur = 0.5
molasses_dur = shot_globals.molasses_time*1e-3
duration = 100e-3 #robust loading pulse duration

labscript.start()

t = 0

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
    devices.tweezer_aom_analog.constant(t, 1) #0.3) #for single tweezer

do_MOT(t, MOT_load_dur)
# devices.dds1.synthesize(t+1e-3, blue_456_detuning , 0.2, 0)
do_dipole(t+1e-3, MOT_load_dur + molasses_dur + shot_globals.tof_imaging_delay)

t += MOT_load_dur # how long MOT last
do_molasses(t, molasses_dur)

t+=molasses_dur

devices.ta_aom_analog.constant(t , shot_globals.ta_img_power) # back to full power for imaging
devices.repump_aom_analog.constant(t , shot_globals.repump_img_power)

assert shot_globals.tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter'"
t+=shot_globals.tof_imaging_delay


if shot_globals.do_robust_loading_pulse:
    robust_loading_pulse(t, duration)
    t += duration


t = do_imaging(t, 1)
devices.digital_out_ch26.go_high(t)

# do_rydberg_excite(t, ryd_excitation_dur)
# t+=ryd_excitation_dur

# second shot
t += 100e-3#1.01#200e-3
t = do_imaging(t, 2)

devices.digital_out_ch26.go_low(t)

t += 1e-2
reset_shot(t)

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












