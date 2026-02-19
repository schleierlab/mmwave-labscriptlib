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
from calibration import ta_freq_calib, repump_freq_calib
from labscriptlib.shot_globals import shot_globals
import numpy as np

devices.initialize()

# fixed parameters in the script
coil_off_time = 1.4e-3 # minimum time for the MOT coil to be off
bipolar_coil_flip_time = 6e-3 # the time takes to flip the polarity of the coil
coil_ramp_time = 5e-3
do_x_coil_ramp = True
do_y_coil_ramp = False
do_z_coil_ramp = False

labscript.start()

if do_x_coil_ramp is True:
    t = 0
    x_ini = 0.2
    x_mid = -0.03
    x_fin = -0.2
    devices.x_coil_current.constant(t, x_ini)
    t += 50e-3

    t += devices.x_coil_current.ramp(
            t,
            duration=coil_ramp_time,
            initial=x_ini,
            final=x_mid,  # 0 mG
            samplerate=1e5,
        )

    devices.x_coil_feedback_off.go_high(t)
    devices.x_coil_feedback_off.go_low(t+4.5e-3)
    devices.x_coil_current.constant(t, x_mid)
    t += 10e-3

    t += devices.x_coil_current.ramp(
            t,
            duration=coil_ramp_time,
            initial=x_mid,
            final=x_fin,  # 0 mG
            samplerate=1e5,
        )

    t += 1e-3
    devices.x_coil_current.constant(t, x_fin)
    t += 1e-3


if do_y_coil_ramp is True:
    t = 0
    y_ini = 0.2
    y_mid = -0.03
    y_fin = -0.2
    devices.y_coil_current.constant(t, y_ini)
    t += 50e-3



    t += devices.y_coil_current.ramp(
            t,
            duration=coil_ramp_time,
            initial=y_ini,
            final=y_mid,  # 0 mG
            samplerate=1e5,
        )

    devices.y_coil_feedback_off.go_high(t)
    devices.y_coil_feedback_off.go_low(t+4.5e-3)
    devices.y_coil_current.constant(t, y_mid)
    t += 10e-3


    t += devices.y_coil_current.ramp(
            t,
            duration=coil_ramp_time,
            initial=y_mid,
            final=y_fin,  # 0 mG
            samplerate=1e5,
        )

    t += 1e-3
    devices.y_coil_current.constant(t, y_fin)
    t += 1e-3

if do_z_coil_ramp is True:
    t = 0
    z_ini = 0.2
    z_mid = -0.03
    z_fin = -0.2
    devices.z_coil_current.constant(t, z_ini)
    t += 50e-3

    t += devices.z_coil_current.ramp(
            t,
            duration=coil_ramp_time,
            initial=z_ini,
            final=z_mid,  # 0 mG
            samplerate=1e5,
        )

    devices.z_coil_feedback_off.go_high(t)
    devices.z_coil_feedback_off.go_low(t+4.5e-3)
    devices.z_coil_current.constant(t, z_mid)
    t += 10e-3

    t += devices.z_coil_current.ramp(
            t,
            duration=coil_ramp_time,
            initial=z_mid,
            final=z_fin,  # 0 mG
            samplerate=1e5,
        )

    t += 1e-3
    devices.z_coil_current.constant(t, z_fin)
    t += 1e-3



labscript.stop(t + 1e-2)
