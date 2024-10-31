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
# from imaging import  beam_off_aom, mot_imaging_aom, repump_off, mot_imaging, repump_off_aom, ta_off_aom, repump_on_aom, repump_on_shutter, repump_on, ta_on_aom, ta_off, ta_on, ta_on_shutter
from calibration import ta_freq_calib, biasx_calib, biasy_calib, biasz_calib, repump_freq_calib

def load_mot(t, mot_coil_ctrl_voltage=10/6, mot_detuning = shot_globals.mot_ta_detuning):
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

    # devices.x_coil_current.constant(t, biasx_calib(0))
    # devices.y_coil_current.constant(t, biasy_calib(0))
    # devices.z_coil_current.constant(t, biasz_calib(0))

    return t

def turn_on_dipole_trap(t):
    devices.ipg_1064_aom_digital.go_high(t)
    devices.ipg_1064_aom_analog.constant(t, 1)

def turn_off_dipole_trap(t):
    devices.ipg_1064_aom_digital.go_low(t)
    devices.ipg_1064_aom_analog.constant(t, 0)

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

    return t

def do_molasses_dipole_trap_imaging(t, *, ini_ta_detuning, ini_repump_detuning, img_ta_detuning = 0, img_repump_detuning = 0, img_ta_power = 1, img_repump_power = 1, exposure):

    devices.ta_vco.ramp(
            t-ta_vco_ramp_t,
            duration=ta_vco_ramp_t,
            initial=ta_freq_calib(ini_ta_detuning),
            final=ta_freq_calib(img_ta_detuning),
            samplerate=4e5,
        )# ramp back to imaging

    devices.repump_vco.ramp(
            t-ta_vco_ramp_t,
            duration=ta_vco_ramp_t,
            initial=repump_freq_calib(ini_repump_detuning),
            final=repump_freq_calib(img_repump_detuning),
            samplerate=4e5,
        )# ramp back to imaging



    devices.ta_shutter.open(t) # turn on TA
    devices.ta_aom_digital.go_high(t)
    devices.ta_aom_analog.constant(t, img_ta_power)


    if shot_globals.do_repump:
        devices.repump_shutter.open(t) # turn on TA
        devices.repump_aom_digital.go_high(t)
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


    if shot_globals.do_kinetix_camera:

        devices.kinetix.expose(
            'Kinetix',
            t,
            'atoms',
            exposure_time = exposure,
        )
        print('t after exposure', t)
        print('exposure time', exposure)


    t += exposure

    devices.ta_shutter.close(t) # turn on TA
    devices.ta_aom_digital.go_low(t)

    if shot_globals.do_repump:
        devices.repump_shutter.close(t) # turn on TA
        devices.repump_aom_digital.go_low(t)

    return t

uwave_clock = 9.192631770e3 # in unit of MHz
local_oscillator_freq_mhz = 9486 # in unit of MHz MKU LO 8-13 PLL setting
ta_vco_ramp_t = 1.2e-4 # minimum TA ramp time to stay locked
ta_vco_stable_t = 1e-4 # stable time waited for lock

min_shutter_off_t = 6.28e-3 # minimum time for shutter to be off and on again
min_shutter_on_t = 3.6e-3 # minimum time for shutter to be on and off again
resonance_detuning = 0 # MHz, measured under lower ta power to find the resonance
shutter_ramp_time = 1.5e-3 # time for shutter to start open/close to fully open/close
bias_coil_on_time = 0.5e-3 # minimum time for the bias coil to be on
mot_detuning = shot_globals.mot_ta_detuning #-16 # MHz, optimized based on atom number
ta_bm_detuning = shot_globals.bm_ta_detuning #-100 # bright molasses detuning
ta_pumping_detuning = -251 # MHz 4->4 tansition
kinetix_readout_time = 1800*4.7065e-6 #2400*4.7065e-6

devices.initialize()

t = 0
labscript.start()
if shot_globals.do_mot_coil:
    load_mot(t, mot_detuning=shot_globals.mot_ta_detuning)
else:
    load_mot(t, mot_detuning=shot_globals.mot_ta_detuning, mot_coil_ctrl_voltage=0)

devices.dds0.synthesize(1e-4, local_oscillator_freq_mhz - uwave_clock - shot_globals.uwave_detuning , 0.7, 0) # setup the frequency for the dds


if shot_globals.do_dipole_trap:
    turn_on_dipole_trap(t)
else:
    turn_off_dipole_trap(t)


t += 0.5 # how long MOT last

### Bright molasses stage
if shot_globals.do_bm:
    load_molasses(t)
    t += 4e-3 # how long bright molasses last

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
    if shot_globals.do_bm:
        devices.ta_vco.ramp(
            t,
            duration=ta_vco_ramp_t,
            initial=ta_freq_calib(ta_bm_detuning),
            final=ta_freq_calib(resonance_detuning + ta_pumping_detuning),
            samplerate=4e5,
        )
    else:
        devices.ta_vco.ramp(
            t,
            duration=ta_vco_ramp_t,
            initial=ta_freq_calib(mot_detuning),
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

# devices.x_coil_current.constant(t, 0) # define quantization axis
# devices.y_coil_current.constant(t, 0) # define quantization axis
# devices.z_coil_current.constant(t, 0) # define quantization axis

devices.x_coil_current.constant(t, biasx_calib(0)) # define quantization axis
devices.y_coil_current.constant(t, biasy_calib(0)) # define quantization axis
devices.z_coil_current.constant(t, biasz_calib(0)) # define quantization axis


t += max(ta_vco_ramp_t + ta_vco_stable_t, shot_globals.img_tof_imaging_delay)



devices.ta_aom_analog.constant(t, shot_globals.img_ta_power) #0.1) # for better exposure of the F=4 atom
devices.repump_aom_analog.constant(t, shot_globals.img_repump_power)

if shot_globals.do_repump:  # Turn on the repump during imaging depending on the global variable
    devices.ta_aom_digital.go_high(t)
    devices.ta_shutter.open(t)
    devices.repump_aom_digital.go_high(t)
    devices.repump_shutter.open(t)


    if shot_globals.do_mot_camera:
        devices.manta419b_mot.expose('manta419b', t, 'atoms', exposure_time=max(shot_globals.img_exposure,50e-6))
    if shot_globals.do_kinetix_camera:
        devices.kinetix.expose(
            'Kinetix',
            t - kinetix_readout_time,
            'atoms',
            exposure_time= shot_globals.img_exposure,
        )

    t += shot_globals.img_exposure
    devices.repump_aom_digital.go_low(t)
    devices.repump_shutter.close(t)
    devices.ta_aom_digital.go_low(t)
    devices.ta_shutter.close(t)
else: # Turn off the repump during imaging depending on the global variable
    devices.ta_aom_digital.go_high(t)
    devices.ta_shutter.open(t)

    if shot_globals.do_mot_camera:
        devices.manta419b_mot.expose('manta419b', t, 'atoms', exposure_time=max(shot_globals.img_exposure,50e-6))
    if shot_globals.do_kinetix_camera:
        devices.kinetix.expose(
            'Kinetix',
            t - kinetix_readout_time,
            'atoms',
            exposure_time= shot_globals.img_exposure,
        )

    t += shot_globals.img_exposure
    devices.ta_aom_digital.go_low(t)
    devices.ta_shutter.close(t)

turn_off_dipole_trap(t)
# Wait until the MOT disappear and then take a background
t += 1e-1

if shot_globals.do_repump:  # Turn on the repump during imaging depending on the global variable
    devices.ta_aom_digital.go_high(t)
    devices.ta_shutter.open(t)
    devices.repump_aom_digital.go_high(t)
    devices.repump_shutter.open(t)

    if shot_globals.do_mot_camera:
        devices.manta419b_mot.expose('manta419b', t, 'atoms', exposure_time=max(shot_globals.img_exposure,50e-6))
    if shot_globals.do_kinetix_camera:
        devices.kinetix.expose(
            'Kinetix',
            t - kinetix_readout_time,
            'atoms',
            exposure_time= shot_globals.img_exposure,
        )

    t += shot_globals.img_exposure
    devices.repump_aom_digital.go_low(t)
    devices.repump_shutter.close(t)
    devices.ta_aom_digital.go_low(t)
    devices.ta_shutter.close(t)
else: # Turn off the repump during imaging depending on the global variable
    devices.ta_aom_digital.go_high(t)
    devices.ta_shutter.open(t)

    if shot_globals.do_mot_camera:
        devices.manta419b_mot.expose('manta419b', t, 'atoms', exposure_time=max(shot_globals.img_exposure,50e-6))
    if shot_globals.do_kinetix_camera:
        devices.kinetix.expose(
            'Kinetix',
            t - kinetix_readout_time,
            'atoms',
            exposure_time= shot_globals.img_exposure,
        )

    t += shot_globals.img_exposure
    devices.ta_aom_digital.go_low(t)
    devices.ta_shutter.close(t)


# set ta detuning back to initial value
t += 1e-1
devices.ta_vco.ramp(
    t,
    duration=ta_vco_ramp_t,
    # initial=ta_freq_calib(ta_pumping_detuning),
    initial=ta_freq_calib(resonance_detuning),
    final=ta_freq_calib(mot_detuning),
    samplerate=1e5,
)
load_mot(t) # set the default value into MOT loading value

labscript.stop(t + 1e-2)
