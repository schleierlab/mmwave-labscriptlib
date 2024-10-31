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
from imaging import beam_off_aom, mot_imaging_aom, repump_off
from calibration import ta_freq_calib
from labscriptlib.shot_globals import shot_globals

resonance_detuning = -4 # MHz, measured under lower ta power to find the resonance
coil_off_time = 1.4e-3 # minimum time for the MOT coil to be off
min_shutter_off_t = 6.28e-3 # minimum time for shutter to be off and on again

devices.initialize()
ta_vco_ramp_t = 1.2e-4 # minimum TA ramp time to stay locked
ta_vco_stable_t = 1e-4 # stable time waited for lock
mot_detuning = -18 # MHz, optimized based on atom number

t = 0
labscript.start()

load_mot(t)

t += 0.1


#turn off coil and light for TOF measurement
devices.mot_coil_current_ctrl.constant(t,0)
devices.ta_aom_digital.go_low(t)
devices.repump_aom_digital.go_low(t)

devices.ta_vco.ramp(
        t,
        duration=ta_vco_ramp_t,
        initial=ta_freq_calib(mot_detuning),
        final=ta_freq_calib(-70),
        samplerate=4e5,
    )# ramp to far detune so atom won't see the light
t += ta_vco_ramp_t
# devices.ta_shutter.close(t)
# devices.repump_shutter.close(t)

# assert shot_globals.tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter'"

t += shot_globals.tof_imaging_delay-2*ta_vco_ramp_t-ta_vco_stable_t

# devices.ta_shutter.open(t)
# devices.repump_shutter.open(t)
devices.ta_vco.ramp(
        t,
        duration=ta_vco_ramp_t,
        initial=ta_freq_calib(-70),
        final=ta_freq_calib(0),
        samplerate=4e5,
    )# ramp back to imaging
t += ta_vco_ramp_t + ta_vco_stable_t

devices.ta_aom_digital.go_high(t)
devices.repump_aom_digital.go_high(t)
devices.manta419b_mot.expose('manta419b', t, 'atoms', exposure_time=max(shot_globals.manta_exposure,50e-6))
t += shot_globals.manta_exposure
devices.repump_aom_digital.go_low(t)
devices.ta_aom_digital.go_low(t)
# devices.ta_shutter.close(t)
# devices.repump_shutter.close(t)


# Turn off MOT for taking background images
t += 1e-1

devices.ta_aom_digital.go_low(t)
devices.repump_aom_digital.go_low(t)
# devices.ta_shutter.close(t)
# devices.repump_shutter.close(t)

t += shot_globals.tof_imaging_delay
# devices.ta_shutter.open(t)
# devices.repump_shutter.open(t)
devices.ta_aom_digital.go_high(t)
devices.repump_aom_digital.go_high(t)
devices.manta419b_mot.expose('manta419b', t, 'atoms', exposure_time=max(shot_globals.manta_exposure,50e-6))
t += shot_globals.manta_exposure
devices.repump_aom_digital.go_low(t)
devices.ta_aom_digital.go_low(t)
# devices.ta_shutter.close(t)
# devices.repump_shutter.close(t)

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

labscript.stop(t + 1e-2)
