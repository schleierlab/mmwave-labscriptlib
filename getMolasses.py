import sys

root_path = r"C:\Users\sslab\labscript-suite\userlib\labscriptlib"

if root_path not in sys.path:
    sys.path.append(root_path)

from calibration import ta_freq_calib, repump_freq_calib, biasx_calib, biasy_calib, biasz_calib
from connection_table import devices
from labscriptlib.shot_globals import shot_globals

mot_detuning = shot_globals.mot_detuning # MHz, optimized based on atom number
# ta_bm_detuning = shot_globals.ta_bm_detuning
# repump_bm_detuning = shot_globals.repump_bm_detuning


def load_molasses(t, ta_bm_detuning = shot_globals.ta_bm_detuning, repump_bm_detuning = shot_globals.repump_bm_detuning): #-100
    devices.ta_vco.ramp(
            t,
            duration=1e-3,
            initial=ta_freq_calib(mot_detuning),
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
            initial=shot_globals.ta_power,
            final=shot_globals.ta_bm_power, #0.16, #0.15, # optimized on both temperature and atom number, too low power will lead to small atom number
            samplerate=1e5,
        )

    devices.repump_aom_analog.ramp(
            t,
            duration=100e-6,
            initial=shot_globals.repump_power,
            final=shot_globals.repump_bm_power, # doesn't play any significant effect
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


def load_molasses_img_beam(t, ta_bm_detuning = shot_globals.img_ta_bm_detuning, repump_bm_detuning = shot_globals.img_repump_bm_detuning): #-100
    devices.ta_vco.ramp(
            t,
            duration=1e-3,
            initial=ta_freq_calib(mot_detuning),
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
            initial=shot_globals.ta_power,
            final=shot_globals.img_ta_bm_power, #0.16, #0.15, # optimized on both temperature and atom number, too low power will lead to small atom number
            samplerate=1e5,
        )

    devices.repump_aom_analog.ramp(
            t,
            duration=100e-6,
            initial=shot_globals.repump_power,
            final=shot_globals.img_repump_bm_power, # doesn't play any significant effect
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


    # devices.x_coil_current.ramp(
    #         t,
    #         duration=100e-6,
    #         initial=shot_globals.mot_x_coil_voltage,
    #         final= biasx_calib(0),# 0 mG
    #         samplerate=1e5,
    #     )

    # devices.y_coil_current.ramp(
    #         t,
    #         duration=100e-6,
    #         initial=shot_globals.mot_y_coil_voltage,
    #         final= biasy_calib(0),# 0 mG
    #         samplerate=1e5,
    #     )

    # devices.z_coil_current.ramp(
    #         t,
    #         duration=100e-6,
    #         initial=shot_globals.mot_z_coil_voltage,
    #         final= biasz_calib(0),# 0 mG
    #         samplerate=1e5,
    #     )

    devices.x_coil_current.constant(t, biasx_calib(0))
    devices.y_coil_current.constant(t, biasy_calib(0))
    devices.z_coil_current.constant(t, biasz_calib(0))

    return t