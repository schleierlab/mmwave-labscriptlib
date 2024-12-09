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

devices.initialize()

op_shutter_off_t = 1.74e-3
op_shutter_on_t = 3.66e-3
op_shutter_delays = (op_shutter_on_t, op_shutter_off_t)

labscript.start()

t = 0
t += 10e-3
devices.ta_aom_analog.constant(t,0.1)
devices.ta_aom_digital.go_high(t)
devices.ta_shutter.open(t)
devices.optical_pump_shutter.open(t)
devices.digital_out_ch22.go_high(t)

t += 100e-6
devices.ta_aom_analog.constant(t,0)
devices.ta_aom_digital.go_low(t)
devices.ta_shutter.close(t)
devices.optical_pump_shutter.close(t)
devices.digital_out_ch22.go_low(t)



labscript.stop(t + 1e-2)
