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
from imaging import ta_on_shutter, ta_off_shutter
from calibration import ta_freq_calib

repump_shutter_off_t = 1.984e-3 # delay time between the pulse and shutter
repump_shutter_on_t = 3.442e-3


devices.initialize()


t = 0
labscript.start()


t += 1e-2

devices.ta_aom_digital.go_high(t)
devices.repump_aom_digital.go_high(t)
devices.mot_camera_trigger.go_low(t)
devices.uwave_dds_switch.go_high(t)
devices.uwave_absorp_switch.go_low(t)
devices.ta_shutter.go_high(t)
devices.repump_shutter.go_low(t)

#ta_shutter.go_low(t)
#repump_shutter.go_high(t)
devices.mot_xy_shutter.go_high(t)
devices.mot_z_shutter.go_high(t)
devices.img_xy_shutter.go_high(t)
devices.img_z_shutter.go_low(t)
devices.uv_switch.go_low(t)

devices.ta_aom_analog.constant(t, 0.63) # 0 to 1V
devices.repump_aom_analog.constant(t, 1) # 0 to 1V
devices.ta_vco.constant(t, ta_freq_calib(-18)) # 18 MHz red detuned
devices.repump_vco.constant(t, 2.3)
devices.mot_coil_current_ctrl.constant(t, 0) # 1/6 V/A, do not change to too high which may burn the coil
devices.digital_out_ch12.go_high(t)

t += 0.1
# #repump_aom_digital.go_low(t - aom_delay)
# repump_shutter.go_low(t - repump_shutter_off_t)
# repump_off(t)
# ta_off(t)
ta_off_shutter(t)
devices.digital_out_ch12.go_low(t)


t += 7e-3
# repump_aom_digital.go_high(t - aom_delay)
# repump_shutter.go_high(t - repump_shutter_on_t)
# repump_on(t)
# ta_on(t)
ta_on_shutter(t)
devices.digital_out_ch12.go_high(t)

t += 2e-3
# repump_aom_digital.go_high(t - aom_delay)
# repump_shutter.go_low(t - repump_shutter_off_t)
# repump_off(t)
# ta_off(t)
ta_off_shutter(t)
devices.digital_out_ch12.go_low(t)


labscript.stop(t + 1e-2)
