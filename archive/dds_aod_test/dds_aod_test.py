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
kinetix_readout_time = 1800*4.7065e-6 #2400*4.7065e-6
spectrum_card_offset = 52.8e-6 # the offset for the beging of output comparing to the trigger
spectrum_uwave_cable_atten = 4.4 #dB at 300 MHz
spectrum_uwave_power = -3 # dBm

devices.initialize()

t = 0
labscript.start()

devices.dds0.synthesize(t+1e-2, 69.5 , 0.95, 0)

t +=1e-2
devices.tweezer_aom_digital.go_high(t)
devices.tweezer_aom_analog.constant(t, 1)

labscript.stop(t + 1e-2)
