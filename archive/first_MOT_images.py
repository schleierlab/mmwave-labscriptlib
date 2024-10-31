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
from getMOT import load_mot
from imaging import beam_off_aom, mot_imaging_aom, repump_off
from calibration import ta_freq_calib
from labscriptlib.shot_globals import shot_globals



coil_off_time = 1.4e-3 # minimum time for the MOT coil to be off
# mot_detuning = -13 # MHz, optimized based on atom number
mot_detuning = shot_globals.mot_detuning # MHz, optimized based on atom number

devices.initialize()


t = 0
labscript.start()

load_mot(t,mot_detuning =mot_detuning)

t += 0.5 #0.1 # MOT loading time 100 ms

devices.mot_coil_current_ctrl.constant(t, 0) # Turn off coils
beam_off_aom(t) # Only using the AOM for imaging MOT now
devices.uv_switch.go_low(t) # turn off UV diode

t += coil_off_time # turn off the coil fully after this time

devices.ta_vco.ramp(
        t,
        duration=1e-4,
        initial=ta_freq_calib(mot_detuning),
        final=ta_freq_calib(0),
        samplerate=4e5,
    )# ramp to imaging

t += 1e-4
mot_imaging_aom(
    t,
    repump=True
)


# Turn off MOT for taking background images
t += 0.1 # Wait until the MOT disappear
mot_imaging_aom(
    t,
    repump=True,
)


# set back to initial value
t += 1e-2
devices.ta_vco.ramp(
        t,
        duration=1e-4,
        initial=ta_freq_calib(0),
        final=ta_freq_calib(mot_detuning),
        samplerate=4e5,
    )# ramp to MOT loading

load_mot(t, mot_detuning =mot_detuning)

labscript.stop(t + 1e-2)
