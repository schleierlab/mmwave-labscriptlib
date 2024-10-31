import sys

root_path = r"C:\Users\sslab\labscript-suite\userlib\labscriptlib"

if root_path not in sys.path:
    sys.path.append(root_path)

from calibration import ta_freq_calib, repump_freq_calib, biasx_calib, biasy_calib, biasz_calib
from connection_table import devices
from labscriptlib.shot_globals import shot_globals


def load_mot(t, mot_coil_ctrl_voltage=10/6, mot_detuning = shot_globals.mot_detuning):
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
    devices.optical_pump_shutter.go_low(t)
    if shot_globals.do_uv:
        devices.uv_switch.go_high(t)
    devices.uv_switch.go_low(t+1e-2) # longer time will lead to the overall MOT atom number decay during the cycle

    devices.ta_aom_analog.constant(t, shot_globals.ta_power)
    devices.repump_aom_analog.constant(t, shot_globals.repump_power)

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
