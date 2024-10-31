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
from labscriptlib.shot_globals import shot_globals
from getMOT import load_mot
# from imaging import  beam_off_aom, mot_imaging_aom, repump_off, mot_imaging, repump_off_aom, ta_off_aom, repump_on_aom, repump_on_shutter, repump_on, ta_on_aom, ta_off, ta_on, ta_on_shutter
from calibration import ta_freq_calib, biasx_calib, biasy_calib, biasz_calib

uwave_clock = 9.192631770e3 # in unit of MHz
local_oscillator_freq_mhz = 9486 # in unit of MHz MKU LO 8-13 PLL setting
ta_vco_ramp_t = 1.2e-4 # minimum TA ramp time to stay locked
ta_vco_stable_t = 1e-4 # stable time waited for lock

min_shutter_off_t = 6.28e-3 # minimum time for shutter to be off and on again
min_shutter_on_t = 3.6e-3 # minimum time for shutter to be on and off again
resonance_detuning = 0 # MHz, measured under lower ta power to find the resonance
shutter_ramp_time = 1.5e-3 # time for shutter to start open/close to fully open/close
bias_coil_on_time = 0.5e-3 # minimum time for the bias coil to be on
mot_detuning = -16 # MHz, optimized based on atom number
ta_pumping_detuning = -251 # MHz 4->4 tansition

devices.initialize()

t = 0
labscript.start()
load_mot(t)
# devices.img_xy_shutter.go_high(t) # for monitoring the optical power using photodiode
devices.dds0.synthesize(1e-4, local_oscillator_freq_mhz - uwave_clock - shot_globals.uwave_detuning , 0.7, 0) # setup the frequency  for the dds

t += 0.1 # load atom for 100 ms

if shot_globals.do_optical_pump: ######## Doing optical pumping to pump all atom into F=4 ###########
    devices.ta_aom_digital.go_low(t)
    devices.ta_shutter.close(t)
    devices.repump_aom_analog.constant(t, 1)


    devices.mot_coil_current_ctrl.constant(t, 0)

    t += shot_globals.pump_time
    devices.repump_aom_digital.go_low(t)
    devices.repump_shutter.close(t)



if shot_globals.do_optical_depump: ####### depump all atom into F = 3 level by using F = 4 -> F' = 4 resonance
    #devices.digital_out_ch12.go_high(t)
    devices.ta_vco.ramp(
        t,
        duration=ta_vco_ramp_t,
        initial=ta_freq_calib(mot_detuning),
        # final=ta_freq_calib(resonance_detuning),
        final=ta_freq_calib(resonance_detuning + ta_pumping_detuning),
        samplerate=4e5,
    )
    t += ta_vco_ramp_t + ta_vco_stable_t
    devices.repump_aom_digital.go_low(t)
    devices.repump_shutter.close(t)
    devices.ta_aom_analog.constant(t, 1)
    #devices.digital_out_ch12.go_low(t)

    devices.mot_coil_current_ctrl.constant(t, 0)

    t += shot_globals.depump_time
    devices.ta_aom_digital.go_low(t)
    devices.ta_shutter.close(t)










devices.digital_out_ch12.go_high(t)
# devices.x_coil_current.constant(t, shot_globals.x_coil_voltage) # define quantization axis
# devices.y_coil_current.constant(t, shot_globals.y_coil_voltage) # define quantization axis
# devices.z_coil_current.constant(t, shot_globals.z_coil_voltage) # define quantization axis

devices.x_coil_current.constant(t, biasx_calib(shot_globals.biasx_field)) # define quantization axis
devices.y_coil_current.constant(t, biasy_calib(shot_globals.biasy_field)) # define quantization axis
devices.z_coil_current.constant(t, biasz_calib(shot_globals.biasz_field)) # define quantization axis

# Turn on microwave
# wait until the bias coils are on and the shutter is fullly closed
t += max(bias_coil_on_time, shutter_ramp_time, min_shutter_off_t)
if shot_globals.do_mw:
    devices.uwave_absorp_switch.go_high(t)
    devices.uwave_absorp_switch.go_low(t + shot_globals.uwave_time)

t += shot_globals.uwave_time



if shot_globals.do_optical_pump: ### ramp back to be on resonance for imaging
    devices.ta_vco.ramp(
        t,
        duration = ta_vco_ramp_t,
        initial = ta_freq_calib(mot_detuning),
        final = ta_freq_calib(resonance_detuning),
        samplerate = 4e5
    )

if shot_globals.do_optical_depump: ### ramp back to be on resonance for imaging
    devices.ta_vco.ramp(
        t,
        duration = ta_vco_ramp_t,
        # initial = ta_freq_calib(resonance_detuning),
        # initial = ta_freq_calib(mot_detuning),
        initial = ta_freq_calib(resonance_detuning + ta_pumping_detuning),
        final = ta_freq_calib(resonance_detuning),
        samplerate = 4e5
    )

devices.x_coil_current.constant(t, 0) # define quantization axis
devices.y_coil_current.constant(t, 0) # define quantization axis
devices.z_coil_current.constant(t, 0) # define quantization axis
devices.digital_out_ch12.go_low(t)

t += ta_vco_ramp_t + ta_vco_stable_t


# Fluroscence imaging
devices.ta_aom_analog.constant(t, 0.1) # for better exposure of the F=4 atom
devices.repump_aom_analog.constant(t, 1)

if shot_globals.mw_dorepump:  # Turn on the repump during imaging depending on the global variable
    devices.ta_aom_digital.go_high(t)
    devices.ta_shutter.open(t)
    devices.repump_aom_digital.go_high(t)
    devices.repump_shutter.open(t)
    devices.manta419b_mot.expose('manta419b', t, 'atoms', exposure_time=max(shot_globals.manta_exposure,50e-6))
    t += shot_globals.manta_exposure
    devices.repump_aom_digital.go_low(t)
    devices.repump_shutter.close(t)
    devices.ta_aom_digital.go_low(t)
    devices.ta_shutter.close(t)
else: # Turn off the repump during imaging depending on the global variable
    devices.ta_aom_digital.go_high(t)
    devices.ta_shutter.open(t)
    devices.manta419b_mot.expose('manta419b', t, 'atoms', exposure_time=max(shot_globals.manta_exposure,50e-6))
    t += shot_globals.manta_exposure
    devices.ta_aom_digital.go_low(t)
    devices.ta_shutter.close(t)


# Wait until the MOT disappear and then take a background
t += 1e-1
if shot_globals.mw_dorepump:  # Turn on the repump during imaging depending on the global variable
    devices.ta_aom_digital.go_high(t)
    devices.ta_shutter.open(t) # turn on TA
    devices.repump_aom_digital.go_high(t)
    devices.repump_shutter.open(t)
    devices.manta419b_mot.expose('manta419b', t, 'atoms', exposure_time=max(shot_globals.manta_exposure,50e-6))
    t += shot_globals.manta_exposure
    devices.repump_aom_digital.go_low(t)
    devices.repump_shutter.close(t)
    devices.ta_aom_digital.go_low(t)
    devices.ta_shutter.close(t) # turn off TA
else: # Turn off the repump during imaging depending on the global variable
    devices.ta_aom_digital.go_high(t)
    devices.ta_shutter.open(t) # turn on TA
    devices.manta419b_mot.expose('manta419b', t, 'atoms', exposure_time=max(shot_globals.manta_exposure,50e-6))
    t += shot_globals.manta_exposure
    devices.ta_aom_digital.go_low(t)
    devices.ta_shutter.close(t) # turn off TA


# set ta detuning back to initial value
t += 1e-2
devices.ta_vco.ramp(
    t,
    duration=ta_vco_ramp_t,
    # initial=ta_freq_calib(ta_pumping_detuning),
    initial=ta_freq_calib(resonance_detuning),
    final=ta_freq_calib(mot_detuning),
    samplerate=1e5,
)
# load_mot(t) # set the default value into MOT loading value

labscript.stop(t + 1e-2)
