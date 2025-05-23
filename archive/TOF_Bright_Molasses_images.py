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
from getMolasses import load_molasses
from calibration import ta_freq_calib, repump_freq_calib
from labscriptlib.shot_globals import shot_globals

coil_off_time = 1.4e-3 # minimum time for the MOT coil to be off
min_shutter_off_t = 6.28e-3 # minimum time for shutter to be off and on again

devices.initialize()
ta_vco_ramp_t = 1.2e-4 # minimum TA ramp time to stay locked
ta_vco_stable_t = 1e-4 # stable time waited for lock
mot_detuning = shot_globals.CONST_MOT_DETUNING #-13# MHz, optimized based on atom number
ta_bm_detuning = shot_globals.CONST_TA_BM_DETUNING # MHz, bright molasses detuning
repump_bm_detuning = shot_globals.CONST_REPUMP_BM_DETUNING # MHz, bright molasses detuning

t = 0
labscript.start()

load_mot(t)

t += 0.5  # how long MOT last

# Bright molasses stage
load_molasses(t, ta_bm_detuning, repump_bm_detuning)

t += 4e-3  # how long bright molasses last

#turn off coil and light for TOF measurement, coil is already off in load_molasses
devices.ta_aom_digital.go_low(t)
devices.repump_aom_digital.go_low(t)

devices.ta_shutter.close(t)
devices.repump_shutter.close(t)

assert shot_globals.tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter'"

# t += shot_globals.tof_imaging_delay-ta_vco_ramp_t-ta_vco_stable_t


devices.ta_vco.ramp(
        t,
        duration=ta_vco_ramp_t,
        initial=ta_freq_calib(ta_bm_detuning),
        final=ta_freq_calib(0),
        samplerate=4e5,
    )# ramp back to imaging

devices.repump_vco.ramp(
        t,
        duration=ta_vco_ramp_t,
        initial=repump_freq_calib(repump_bm_detuning),
        final=repump_freq_calib(0),
        samplerate=4e5,
    )# ramp back to imaging

devices.ta_aom_analog.constant(t , 1) # back to full power for imaging
devices.repump_aom_analog.constant(t , 1)

t += shot_globals.tof_imaging_delay

# t += ta_vco_ramp_t + ta_vco_stable_t
devices.ta_shutter.open(t)
devices.repump_shutter.open(t)
devices.ta_aom_digital.go_high(t)
devices.repump_aom_digital.go_high(t)
devices.manta419b_mot.expose('manta419b', t, 'atoms', exposure_time=max(shot_globals.manta_exposure,50e-6))
t += shot_globals.manta_exposure
devices.repump_aom_digital.go_low(t)
devices.ta_aom_digital.go_low(t)
devices.ta_shutter.close(t)
devices.repump_shutter.close(t)


# Turn off MOT for taking background images
t += 3e-1

devices.ta_aom_digital.go_low(t)
devices.repump_aom_digital.go_low(t)
devices.ta_shutter.close(t)
devices.repump_shutter.close(t)

t += shot_globals.tof_imaging_delay
devices.ta_shutter.open(t)
devices.repump_shutter.open(t)
devices.ta_aom_digital.go_high(t)
devices.repump_aom_digital.go_high(t)
devices.manta419b_mot.expose('manta419b', t, 'atoms', exposure_time=max(shot_globals.manta_exposure,50e-6))
t += shot_globals.manta_exposure
devices.repump_aom_digital.go_low(t)
devices.ta_aom_digital.go_low(t)
devices.ta_shutter.close(t)
devices.repump_shutter.close(t)

# set ta detuning back to initial value
t += 1e-2
devices.ta_vco.ramp(
    t,
    duration=ta_vco_ramp_t,
    # initial=ta_freq_calib(ta_pumping_detuning),
    initial=ta_freq_calib(0),
    final=ta_freq_calib(mot_detuning),
    samplerate=1e5,
)
# set the default value into MOT loading value
# load_mot(t)

labscript.stop(t + 1e-2)
