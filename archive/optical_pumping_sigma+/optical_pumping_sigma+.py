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
import numpy as np
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

def start_dds(t):
    if shot_globals.do_mw:
        devices.dds0.synthesize(t, local_oscillator_freq_mhz - uwave_clock - shot_globals.uwave_detuning , 0.7, 0)

    elif shot_globals.do_mw_sweep:
        if shot_globals.do_mw_sweep_starttoend:
            if shot_globals.mw_detuning_start < shot_globals.mw_detuning_end:
                mw_sweep_range = shot_globals.mw_detuning_end - shot_globals.mw_detuning_start
            else:
                mw_sweep_range = shot_globals.mw_detuning_start - shot_globals.mw_detuning_end
            mw_detuning_center = (shot_globals.mw_detuning_end + shot_globals.mw_detuning_start)/2
        else:
            mw_sweep_range = shot_globals.mw_sweep_range
            mw_detuning_center = shot_globals.mw_detuning_center

        mw_freq_center = local_oscillator_freq_mhz - uwave_clock - mw_detuning_center
        mw_sweepduration = mw_sweep_range / shot_globals.mw_sweep_rate
        mw_freq_start = mw_freq_center - mw_sweep_range/2
        mw_freq_end = mw_freq_center + mw_sweep_range/2

        print(f'mw_freq_start = {mw_freq_start}, mw_freq_end = {mw_freq_end}, mw_sweepduration = {mw_sweepduration}')

        devices.dds0.setupSweep('freq', mw_freq_start, mw_freq_end, mw_sweepduration, mw_sweepduration, None, 0.7)

        return mw_sweepduration


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
    print(f'mw_freq_start = {mw_freq_start} MHz, mw_freq_end = {mw_freq_end} MHz, mw_sweepduration = {mw_sweep_duration} s')

    return mw_sweep_duration




def dds_microwave_sweep(
    t: float,
    duration: float,
    freq: float, range: float, amplitude: float,
    phase: float = 0,  offset:float = None, loops:int = 1)->float:
    """Do a microwave sweep or pulse

    Parameters:
    t - labscript time to do sweep (s)
    duration - length of sweep (s)
    freq - center frequency of sweep, specified in Hz, NOT MHz
    range - range of sweep, specified in Hz
    amplitude - Spectrum amplitude
    phase - spectrum card phase
    offset - the SpectrumTimeOffset (s)
    loops - number of times to loop the sweep
    """
    assert offset is not None, "Bad style, but w/e, make sure the spectrum offset is non-zero"
    assert amplitude < 0.21, f"Microwave amplitude seems a little too high.  Should be less than 0.2, but is set to {amplitude}"

    if duration > 0:
        devices.uwave_absorp_switch.go_high(t)
        devices.spectrum_uwave.sweep(
          t - offset,
          duration=duration,
          start_freq=freq - 0.5 * range,
          end_freq=freq + 0.5 * range,
          amplitude=amplitude, phase=phase, ch=0, ramp_type='linear', loops=loops)
        t = t + duration * loops
        devices.uwave_absorp_switch.go_low(t)
        t+=3e-6
    return t


def imaging_sequence(t, do_repump = True):
    devices.ta_aom_analog.constant(t, shot_globals.img_ta_power) #0.1) # for better exposure of the F=4 atom
    devices.repump_aom_analog.constant(t, shot_globals.img_repump_power)
    if do_repump:  # Turn on the repump during imaging depending on the global variable
        devices.ta_aom_digital.go_high(t)
        devices.repump_aom_digital.go_high(t)
        devices.ta_shutter.open(t)
        devices.repump_shutter.open(t)
        devices.mot_xy_shutter.open(t)
        devices.mot_z_shutter.open(t)

        if shot_globals.do_mot_camera:
            devices.manta419b_mot.expose('manta419b', t, 'atoms', exposure_time=max(shot_globals.img_exposure,50e-6))
        if shot_globals.do_kinetix_camera:
            devices.kinetix.expose(
                'Kinetix',
                t - kinetix_readout_time,
                'atoms',
                exposure_time= shot_globals.img_exposure + kinetix_readout_time,
            )

        t += shot_globals.img_exposure
        devices.repump_aom_digital.go_low(t)
        devices.ta_aom_digital.go_low(t)
        #devices.repump_shutter.close(t)
        #devices.ta_shutter.close(t)
        devices.mot_xy_shutter.close(t)
        devices.mot_z_shutter.close(t)


    else: # Turn off the repump during imaging depending on the global variable
        devices.ta_aom_digital.go_high(t)
        devices.ta_shutter.open(t)
        devices.mot_xy_shutter.open(t)
        devices.mot_z_shutter.open(t)

        if shot_globals.do_mot_camera:
            devices.manta419b_mot.expose('manta419b', t, 'atoms', exposure_time=max(shot_globals.img_exposure,50e-6))
        if shot_globals.do_kinetix_camera:
            devices.kinetix.expose(
                'Kinetix',
                t - kinetix_readout_time,
                'atoms',
                exposure_time= shot_globals.img_exposure + kinetix_readout_time,
            )
        t += shot_globals.img_exposure
        devices.ta_aom_digital.go_low(t)
        # devices.ta_shutter.close(t)
        devices.mot_xy_shutter.close(t)
        devices.mot_z_shutter.close(t)


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
repump_pumping_detuning = -201.24 # MHz 3->3 transition
kinetix_readout_time = (shot_globals.kinetix_roi_row[1])*4.7065e-6 #1800*4.7065e-6 #2400*4.7065e-6
spectrum_card_offset = 52.8e-6 # the offset for the beging of output comparing to the trigger
spectrum_uwave_cable_atten = 4.4 #dB at 300 MHz
spectrum_uwave_power = -1 #-3 # dBm

devices.initialize()

t = 0
labscript.start()

#================================================================================
# DDS related for microwaves
#================================================================================
# dds0_PS0.go_high(t)
# dds0_PS1.go_high(t+1e-3)
# dds0_PS2.go_high(t+2e-3)
# mw_sweepduration = start_dds(t+1e-4)

#================================================================================
# Spectrum card related for microwaves
#================================================================================
devices.spectrum_uwave.set_mode(replay_mode=b'sequence',
                                channels=[{'name': 'microwaves', 'power': spectrum_uwave_power + spectrum_uwave_cable_atten, 'port': 0, 'is_amplified': False, 'amplifier': None, 'calibration_power': 12, 'power_mode': 'constant_total', 'max_pulses': 1},
                                          {'name': 'mmwaves', 'power': -11, 'port': 1, 'is_amplified': False, 'amplifier': None, 'calibration_power': 12, 'power_mode': 'constant_total', 'max_pulses': 1}],
                                clock_freq=625,
                                use_ext_clock=True,
                                ext_clock_freq=10)


if shot_globals.do_mot_coil:
    load_mot(t, mot_detuning=shot_globals.mot_ta_detuning)
else:
    load_mot(t, mot_detuning=shot_globals.mot_ta_detuning, mot_coil_ctrl_voltage=0)




if shot_globals.do_dipole_trap:
    turn_on_dipole_trap(t)
else:
    turn_off_dipole_trap(t)


t += 0.5 # how long MOT last

### Bright molasses stage
if shot_globals.do_bm:
    load_molasses(t)
    t += 4e-3 # how long bright molasses last

if shot_globals.do_optical_pump_MOT: ######## Doing optical pumping to pump all atom into F=4 ###########
    devices.ta_aom_digital.go_low(t)
    devices.ta_shutter.close(t)
    devices.repump_aom_analog.constant(t, 1)
    devices.mot_coil_current_ctrl.constant(t, 0)

    t += shot_globals.pump_time
    devices.repump_aom_digital.go_low(t)
    devices.repump_shutter.close(t)

    devices.x_coil_current.ramp(
        t,
        duration=100e-6,
        initial=biasx_calib(0),
        final= biasx_calib(shot_globals.biasx_field),# 0 mG
        samplerate=1e5,
    )

    devices.y_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasx_calib(0),
            final=  biasy_calib(shot_globals.biasy_field),# 0 mG
            samplerate=1e5,
        )

    devices.z_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasz_calib(0),
            final= biasz_calib(shot_globals.biasz_field),# 0 mG
            samplerate=1e5,
        )

if shot_globals.do_optical_depump_MOT: ####### depump all atom into F = 3 level by using F = 4 -> F' = 4 resonance
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
    #devices.ta_aom_analog.constant(t, 0.5)
    #devices.digital_out_ch12.go_low(t)

    devices.mot_coil_current_ctrl.constant(t, 0)

    t += shot_globals.depump_time
    devices.ta_aom_digital.go_low(t)
    devices.ta_shutter.close(t)

    devices.x_coil_current.ramp(
        t,
        duration=100e-6,
        initial=biasx_calib(0),
        final= biasx_calib(shot_globals.biasx_field),# 0 mG
        samplerate=1e5,
    )

    devices.y_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasx_calib(0),
            final=  biasy_calib(shot_globals.biasy_field),# 0 mG
            samplerate=1e5,
        )

    devices.z_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasz_calib(0),
            final= biasz_calib(shot_globals.biasz_field),# 0 mG
            samplerate=1e5,
        )

if shot_globals.do_optical_depump_sigma_plus: # use sigma + polarized light for optical pumping


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
            initial=ta_freq_calib(ta_bm_detuning),
            final=ta_freq_calib(resonance_detuning + ta_pumping_detuning),
            samplerate=4e5,
        )

    devices.repump_vco.ramp(
        t,
        duration=ta_vco_ramp_t,
        initial=repump_freq_calib(0),
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
        final= biasx_calib(shot_globals.biasx_field),# 0 mG
        samplerate=1e5,
    )

    # devices.y_coil_current.ramp(
    #         t,
    #         duration=100e-6,
    #         initial=biasx_calib(shot_globals.op_biasy_field),
    #         final=  biasy_calib(shot_globals.biasy_field),# 0 mG
    #         samplerate=1e5,
    #     )
    devices.y_coil_current.constant(t, biasy_calib(shot_globals.biasy_field)) # define quantization axis

    devices.z_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasz_calib(op_biasz_field),
            final= biasz_calib(shot_globals.biasz_field),# 0 mG
            samplerate=1e5,
        )

    print(f'OP bias x, y, z voltage = {biasx_calib(op_biasx_field)}, {biasy_calib(op_biasy_field)}, {biasz_calib(op_biasz_field)}')

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
            initial=ta_freq_calib(ta_bm_detuning),
            final=ta_freq_calib(resonance_detuning + ta_pumping_detuning),
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
        final= biasx_calib(shot_globals.biasx_field),# 0 mG
        samplerate=1e5,
    )

    # devices.y_coil_current.ramp(
    #         t,
    #         duration=100e-6,
    #         initial=biasx_calib(shot_globals.op_biasy_field),
    #         final=  biasy_calib(shot_globals.biasy_field),# 0 mG
    #         samplerate=1e5,
    #     )
    devices.y_coil_current.constant(t, biasy_calib(shot_globals.biasy_field)) # define quantization axis

    devices.z_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasz_calib(op_biasz_field),
            final= biasz_calib(shot_globals.biasz_field),# 0 mG
            samplerate=1e5,
        )

    print(f'OP bias x, y, z voltage = {biasx_calib(op_biasx_field)}, {biasy_calib(op_biasy_field)}, {biasz_calib(op_biasz_field)}')




print(f'MW bias x, y, z voltage = {biasx_calib(shot_globals.biasx_field)}, {biasy_calib(shot_globals.biasy_field)}, {biasz_calib(shot_globals.biasz_field)}')

# Turn on microwave
# wait until the bias coils are on and the shutter is fullly closed
t += max(bias_coil_on_time, shutter_ramp_time, min_shutter_off_t)

#================================================================================
# DDS related for microwaves
#================================================================================
# if shot_globals.do_mw:
#     devices.uwave_absorp_switch.go_high(t)
#     devices.uwave_absorp_switch.go_low(t + shot_globals.uwave_time)
#     t += shot_globals.uwave_time
# elif shot_globals.do_mw_sweep:
#     devices.uwave_absorp_switch.go_high(t)
#     devices.dds0.sweepUp(t)
#     devices.uwave_absorp_switch.go_low(t + mw_sweepduration)
#     t += mw_sweepduration

#================================================================================
# Spectrum card related for microwaves
#================================================================================

if shot_globals.do_mw_sweep:
    devices.uwave_absorp_switch.go_high(t)
    mw_sweep_duration = spectrum_microwave_sweep(t)
    devices.uwave_absorp_switch.go_low(t + mw_sweep_duration)
    t += mw_sweep_duration

if shot_globals.do_mw:
    t += spectrum_card_offset
    devices.uwave_absorp_switch.go_high(t)
    devices.spectrum_uwave.single_freq(t - spectrum_card_offset, duration=shot_globals.uwave_time, freq=(local_oscillator_freq_mhz - uwave_clock - shot_globals.uwave_detuning)*1e6, amplitude=0.99, phase=0, ch=0, loops=1)
    print(f'Spectrum card freq = {local_oscillator_freq_mhz - uwave_clock - shot_globals.uwave_detuning}')
    devices.uwave_absorp_switch.go_low(t + shot_globals.uwave_time)
    t += shot_globals.uwave_time



if shot_globals.do_optical_pump_MOT: ### ramp back to be on resonance for imaging
    devices.ta_vco.ramp(
        t,
        duration = ta_vco_ramp_t,
        initial = ta_freq_calib(mot_detuning),
        final = ta_freq_calib(shot_globals.img_ta_detuning),
        samplerate = 4e5
    )

if shot_globals.do_optical_depump_MOT or shot_globals.do_optical_depump_sigma_plus or shot_globals.do_optical_pump_sigma_plus: ### ramp back to be on resonance for imaging
    devices.ta_vco.ramp(
        t,
        duration = ta_vco_ramp_t,
        # initial = ta_freq_calib(resonance_detuning),
        # initial = ta_freq_calib(mot_detuning),
        initial = ta_freq_calib(resonance_detuning + ta_pumping_detuning),
        final = ta_freq_calib(shot_globals.img_ta_detuning),
        samplerate = 4e5
    )

if shot_globals.do_optical_depump_sigma_plus:
    devices.repump_vco.ramp(
        t,
        duration = ta_vco_ramp_t,
        initial = repump_freq_calib(repump_pumping_detuning),
        final = repump_freq_calib(0),
        samplerate = 4e5
    )





devices.x_coil_current.constant(t, biasx_calib(0)) # define quantization axis
devices.y_coil_current.constant(t, biasy_calib(0)) # define quantization axis
devices.z_coil_current.constant(t, biasz_calib(0)) # define quantization axis

print(f'Zero field bias x, y, z voltage = {biasx_calib(0)}, {biasy_calib(0)}, {biasz_calib(0)}')

t += max(ta_vco_ramp_t + ta_vco_stable_t, shot_globals.img_tof_imaging_delay)





#======================== State sensitive imaging ==========================#

#========================  First Shot no repump ======================================#
t = imaging_sequence(t, do_repump=shot_globals.do_repump_1st_image)
print(f'the start time for the 1st image {t}')

#==================== Use a strong killing pulse to kick all atoms in F=4 out =======================#
if shot_globals.do_killing_pulse:
    devices.repump_aom_digital.go_low(t)
    devices.repump_shutter.close(t)

    t += min_shutter_off_t
    devices.optical_pump_shutter.open(t)
    devices.ta_aom_digital.go_high(t)
    devices.ta_aom_analog.constant(t, 1)
    t += shot_globals.img_killing_pulse_time
    devices.ta_aom_digital.go_low(t)
    devices.optical_pump_shutter.close(t)
    devices.ta_shutter.close(t)


#=====================   Use repump pulse ===========================#
if shot_globals.do_repump_pulse:
    t += min_shutter_off_t
    devices.repump_shutter.open(t)
    devices.mot_xy_shutter.open(t)
    devices.mot_z_shutter.open(t)
    devices.repump_aom_digital.go_high(t)
    devices.repump_aom_analog.constant(t, 0.1)
    t += shot_globals.img_repump_pulse_time
    devices.repump_aom_digital.go_low(t)
    devices.repump_shutter.close(t)
    devices.mot_xy_shutter.close(t)
    devices.mot_z_shutter.close(t)

#=================== Second Shot no repump ==============================#

t += 2*min_shutter_off_t #shot_globals.img_killing_pulse_time + shot_globals.img_repump_pulse_time

print(f'the start time for the 2nd image {t}')

t = imaging_sequence(t, do_repump=shot_globals.do_repump_2nd_image)

if shot_globals.do_dipole_trap:
    turn_off_dipole_trap(t)
# Wait until the MOT disappear and then take a background
t += 1e-1

#========================  First Shot no repump ======================================#
print(f'the start time for the 3rd image {t}')
#======================== State sensitive imaging ==========================#

#========================  First Shot no repump ======================================#

t = imaging_sequence(t, do_repump=shot_globals.do_repump_1st_image)
print(f'the start time for the 3rd image {t}')

#==================== Use a strong killing pulse to kick all atoms in F=4 out =======================#
if shot_globals.do_killing_pulse:
    # devices.repump_aom_digital.go_low(t)
    # devices.repump_shutter.close(t)
    # devices.ta_vco.ramp(
    #     t,
    #     duration = ta_vco_ramp_t,
    #     # initial = ta_freq_calib(resonance_detuning),
    #     # initial = ta_freq_calib(mot_detuning),
    #     initial = ta_freq_calib(shot_globals.img_ta_detuning),
    #     final = ta_freq_calib(-50),
    #     samplerate = 4e5
    # )
    #t += ta_vco_ramp_t

    # devices.optical_pump_shutter.open(t)
    t += min_shutter_off_t
    devices.mot_xy_shutter.open(t)
    devices.mot_z_shutter.open(t)
    devices.ta_aom_digital.go_high(t)
    devices.ta_aom_analog.constant(t, 0.1)
    t += shot_globals.img_killing_pulse_time
    devices.ta_aom_digital.go_low(t)
    #devices.optical_pump_shutter.close(t)
    devices.mot_xy_shutter.close(t)
    devices.mot_z_shutter.close(t)
    devices.ta_shutter.close(t)

    # devices.ta_vco.ramp(
    #     t,
    #     duration = ta_vco_ramp_t,
    #     # initial = ta_freq_calib(resonance_detuning),
    #     # initial = ta_freq_calib(mot_detuning),
    #     initial = ta_freq_calib(-50),
    #     final = ta_freq_calib(shot_globals.img_ta_detuning),
    #     samplerate = 4e5
    # )

#=====================   Use repump pulse ===========================#
if shot_globals.do_repump_pulse:
    t += min_shutter_off_t
    devices.repump_shutter.open(t)
    devices.mot_xy_shutter.open(t)
    devices.mot_z_shutter.open(t)
    devices.repump_aom_digital.go_high(t)
    devices.repump_aom_analog.constant(t, 1)
    t += shot_globals.img_repump_pulse_time
    devices.repump_aom_digital.go_low(t)
    devices.repump_shutter.close(t)
    devices.mot_xy_shutter.open(t)
    devices.mot_z_shutter.open(t)

#=================== Second Shot no repump ==============================#

t += 2*min_shutter_off_t #shot_globals.img_killing_pulse_time + shot_globals.img_repump_pulse_time

print(f'the start time for the 4th image {t}')

t = imaging_sequence(t, do_repump=shot_globals.do_repump_2nd_image)


devices.spectrum_uwave.single_freq(t, duration=100e-6, freq=10**6, amplitude=0.99, phase=0, ch=0, loops=1)
devices.spectrum_uwave.stop()
# set ta detuning back to initial value
t += 1e-1
devices.ta_vco.ramp(
    t,
    duration=ta_vco_ramp_t,
    # initial=ta_freq_calib(ta_pumping_detuning),
    initial=ta_freq_calib(shot_globals.img_ta_detuning),
    final=ta_freq_calib(mot_detuning),
    samplerate=1e5,
)
load_mot(t) # set the default value into MOT loading value

labscript.stop(t + 1e-2)
