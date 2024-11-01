# -*- coding: utf-8 -*-
"""
Created on Thu Feb 16 11:33:13 2023

@author: sslab
"""

import numpy as np
from labscriptlib.shot_globals import shot_globals
from spectrum_manager_fifo import spectrum_manager_fifo
from spectrum_manager import spectrum_manager
from calibration import ta_freq_calib, repump_freq_calib, biasx_calib, biasy_calib, biasz_calib
from connection_table import devices
import labscript
import sys
root_path = r"X:\userlib\labscriptlib"

if root_path not in sys.path:
    sys.path.append(root_path)


spcm_sequence_mode = shot_globals.do_sequence_mode

if __name__ == "__main__":
    devices.initialize()

# fixed parameters in the script
# TODO: if keeping these global variables, rename them all caps
coil_off_time = 1.4e-3  # minimum time for the MOT coil to be off
ta_vco_ramp_t = 1.2e-4
min_shutter_off_t = 6.28e-3  # minimum time for shutter to be off and on again
# -13 # MHz, optimized based on atom number
mot_detuning = shot_globals.mot_ta_detuning
# -100 # MHz, bright molasses detuning
ta_bm_detuning = shot_globals.bm_ta_detuning
# 0 # MHz, bright molasses detuning
repump_bm_detuning = shot_globals.bm_repump_detuning


def open_mot_shutters(t, label):
    """Open the specified MOT shutters, else open all the MOT shutters"""
    if label == "z":
        devices.mot_z_shutter.go_high(t)
    elif label == "xy":
        devices.mot_xy_shutter.go_high(t)
    else:
        devices.mot_z_shutter.go_high(t)
        devices.mot_xy_shutter.go_high(t)
        
    return t


def open_img_shutters(t, label):
    """Open the specified IMG shutters, else open all the IMG shutters"""
    if label == "z":
        devices.img_z_shutter.go_high(t)
    elif label == "xy":
        devices.img_xy_shutter.go_high(t)
    else:
        devices.img_z_shutter.go_high(t)
        devices.img_xy_shutter.go_high(t)
        
    return t


def load_mot(t, mot_detuning, mot_coil_ctrl_voltage=10 / 6):
    # TODO: abstract MOT laser turn on/off into a function
    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)
    # devices.mot_camera_trigger.go_low(t)
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
    # longer time will lead to the overall MOT atom number decay during the
    # cycle
    devices.uv_switch.go_low(t + 1e-2)

    devices.ta_aom_analog.constant(t, shot_globals.mot_ta_power)
    devices.repump_aom_analog.constant(t, shot_globals.mot_repump_power)

    devices.ta_vco.constant(t, ta_freq_calib(
        mot_detuning))  # 16 MHz red detuned
    devices.repump_vco.constant(t, repump_freq_calib(0))  # on resonance

    # 1/6 V/A, do not change to too high which may burn the coil
    devices.mot_coil_current_ctrl.constant(t, mot_coil_ctrl_voltage)

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


def load_molasses(t, ta_bm_detuning, repump_bm_detuning,
                  ta_last_detuning=shot_globals.mot_ta_detuning):  # -100

    devices.ta_vco.ramp(
        t,
        duration=1e-3,
        initial=ta_freq_calib(ta_last_detuning),
        # -190 MHz from Rydberg lab, -100 MHz from Aidelsburger's group, optimized around -200 MHz
        final=ta_freq_calib(ta_bm_detuning),
        samplerate=1e5,
    )

    devices.repump_vco.ramp(
        t,
        duration=1e-3,
        initial=repump_freq_calib(0),
        # doesn't play any significant effect
        final=repump_freq_calib(repump_bm_detuning),
        samplerate=1e5,
    )

    devices.ta_aom_analog.ramp(
        t,
        duration=100e-6,
        initial=shot_globals.mot_ta_power,
        final=shot_globals.bm_ta_power,
        # 0.16, #0.15, # optimized on both temperature and atom number, too low
        # power will lead to small atom number
        samplerate=1e5,
    )

    devices.repump_aom_analog.ramp(
        t,
        duration=100e-6,
        initial=shot_globals.mot_repump_power,
        final=shot_globals.bm_repump_power,  # doesn't play any significant effect
        samplerate=1e5,
    )

    devices.mot_coil_current_ctrl.ramp(
        t,
        duration=100e-6,
        initial=10 / 6,
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

    print('bias x:', biasx_calib(0),
          '\n bias y:', biasy_calib(0),
          '\n bias z:', biasz_calib(0)
          )

    if shot_globals.mot_x_coil_voltage < 0:
        t_x_coil = t - 4e-3
    else:
        t_x_coil = t
        
    devices.x_coil_current.ramp(
        t_x_coil,
        duration=100e-6,
        initial=shot_globals.mot_x_coil_voltage,
        final=biasx_calib(0),  # 0 mG
        samplerate=1e5,
    )

    if shot_globals.mot_y_coil_voltage < 0:
        devices.y_coil_current.ramp(
            t - 4e-3,
            duration=100e-6,
            initial=shot_globals.mot_y_coil_voltage,
            # TODO: is this correct? not biasy_calib?
            final=biasx_calib(0),  # 0 mG
            samplerate=1e5,
        )
    else:
        devices.y_coil_current.ramp(
            t,
            duration=100e-6,
            initial=shot_globals.mot_y_coil_voltage,
            final=biasy_calib(0),  # 0 mG
            samplerate=1e5,
        )

    if shot_globals.mot_z_coil_voltage < 0:
        t_z_coil = t - 4e-3
    else:
        t_z_coil = t
        
    devices.z_coil_current.ramp(
        t_z_coil,
        duration=100e-6,
        initial=shot_globals.mot_z_coil_voltage,
        final=biasz_calib(0),  # 0 mG
        samplerate=1e5,
    )

    # devices.x_coil_current.constant(t, biasx_calib(0))
    # devices.y_coil_current.constant(t, biasy_calib(0))
    # devices.z_coil_current.constant(t, biasz_calib(0))

    ta_last_detuning = shot_globals.bm_ta_detuning
    repump_last_detuning = shot_globals.bm_repump_detuning

    print('Molasses stage')
    print(f'ta_last_detuning = {ta_last_detuning}')
    print(f'repump_last_detuning = {repump_last_detuning}')
    return t, ta_last_detuning, repump_last_detuning


def load_molasses_img_beam(t, ta_bm_detuning, repump_bm_detuning):  # -100
    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)
    devices.ta_vco.ramp(
        t,
        duration=1e-3,
        initial=ta_freq_calib(shot_globals.mot_ta_detuning),
        # -190 MHz from Rydberg lab, -100 MHz from Aidelsburger's group, optimized around -200 MHz
        final=ta_freq_calib(ta_bm_detuning),
        samplerate=1e5,
    )

    devices.repump_vco.ramp(
        t,
        duration=1e-3,
        initial=repump_freq_calib(0),
        # doesn't play any significant effect
        final=repump_freq_calib(repump_bm_detuning),
        samplerate=1e5,
    )

    devices.ta_aom_analog.ramp(
        t,
        duration=100e-6,
        initial=shot_globals.mot_ta_power,
        final=shot_globals.bm_img_ta_power,
        # 0.16, #0.15, # optimized on both temperature and atom number, too low
        # power will lead to small atom number
        samplerate=1e5,
    )

    devices.repump_aom_analog.ramp(
        t,
        duration=100e-6,
        initial=shot_globals.mot_repump_power,
        final=shot_globals.bm_img_repump_power,  # doesn't play any significant effect
        samplerate=1e5,
    )

    devices.mot_coil_current_ctrl.ramp(
        t,
        duration=100e-6,
        initial=10 / 6,
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

    # devices.x_coil_current.constant(t, biasx_calib(0))
    # devices.y_coil_current.constant(t, biasy_calib(0))
    # devices.z_coil_current.constant(t, biasz_calib(0))
    if shot_globals.mot_x_coil_voltage < 0:
        t_x_coil = t - 4e-3
    else:
        t_x_coil = t
        
    devices.x_coil_current.ramp(
        t_x_coil,
        duration=100e-6,
        initial=shot_globals.mot_x_coil_voltage,
        final=biasx_calib(0),  # 0 mG
        samplerate=1e5,
    )

    if shot_globals.mot_y_coil_voltage < 0:
        devices.y_coil_current.ramp(
            t - 4e-3,
            duration=100e-6,
            initial=shot_globals.mot_y_coil_voltage,
            # TODO: compare to statement below, is this correct?
            final=biasx_calib(0),  # 0 mG
            samplerate=1e5,
        )
    else:
        devices.y_coil_current.ramp(
            t,
            duration=100e-6,
            initial=shot_globals.mot_y_coil_voltage,
            final=biasy_calib(0),  # 0 mG
            samplerate=1e5,
        )

    if shot_globals.mot_z_coil_voltage < 0:
        t_z_coil = t - 4e-3
    else:
        t_z_coil = t
        
    devices.z_coil_current.ramp(
        t_z_coil,
        duration=100e-6,
        initial=shot_globals.mot_z_coil_voltage,
        final=biasz_calib(0),  # 0 mG
        samplerate=1e5,
    )

    ta_last_detuning = shot_globals.bm_img_ta_detuning
    repump_last_detuning = shot_globals.bm_img_repump_detuning

    print('Molasses stage')
    print(f'ta_last_detuning = {ta_last_detuning}')
    print(f'repump_last_detuning = {repump_last_detuning}')
    return t, ta_last_detuning, repump_last_detuning


def do_mot(t, dur, *, use_coil, close_aom=True, close_shutter=True):
    # TODO: compare this method to do_MOT() below
    if use_coil:
        load_mot(t, mot_detuning=shot_globals.mot_ta_detuning)
        devices.mot_coil_current_ctrl.constant(t + dur, 0)  # Turn off coils
    else:
        load_mot(
            t,
            mot_detuning=shot_globals.mot_ta_detuning,
            mot_coil_ctrl_voltage=0
        )

    if close_aom:
        devices.ta_aom_digital.go_low(t + dur)
        devices.repump_aom_digital.go_low(t + dur)

    if close_shutter:
        devices.mot_xy_shutter.close(t + dur)
        devices.mot_z_shutter.close(t + dur)

    return t


def do_MOT(t, dur, coils_bool):
    # TODO: compare this method to do_mot() above
    if coils_bool:
        load_mot(t, mot_detuning=mot_detuning)
    else:
        load_mot(t, mot_detuning=mot_detuning, mot_coil_ctrl_voltage=0)

    if shot_globals.do_molasses_img_beam:
        devices.mot_xy_shutter.close(t + dur)
        devices.mot_z_shutter.close(t + dur)

    # MOT coils ramped down in load_molasses

    ta_last_detuning = mot_detuning
    repump_last_detuning = 0

    return t


def do_mot_imaging(t, *, use_shutter=True):
    devices.ta_vco.ramp(
        t - ta_vco_ramp_t,
        duration=ta_vco_ramp_t,
        initial=ta_freq_calib(shot_globals.mot_ta_detuning),
        final=ta_freq_calib(0),
        samplerate=4e5,
    )  # ramp to imaging

    # set ta and repump to full power
    devices.ta_aom_analog.constant(t, 1)
    devices.repump_aom_analog.constant(t, 1)

    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)

    if use_shutter:
        devices.mot_xy_shutter.open(t)
        devices.mot_z_shutter.open(t)

    devices.manta419b_mot.expose(
        'manta419b',
        t,
        'atoms',
        exposure_time=shot_globals.mot_exposure_time)

    t += shot_globals.mot_exposure_time

    devices.ta_aom_digital.go_low(t)
    devices.repump_aom_digital.go_low(t)

    if use_shutter:
        devices.mot_xy_shutter.close(t)
        devices.mot_z_shutter.close(t)

    return t


def reset_mot(t, ta_last_detuning):
    print(f"time in diagnostics python {t}")
    t += devices.ta_vco.ramp(
        t,
        duration=ta_vco_ramp_t,
        initial=ta_freq_calib(ta_last_detuning),
        final=ta_freq_calib(shot_globals.mot_ta_detuning),
        samplerate=4e5,
    )  # ramp to MOT loading

    # set the default value into MOT loading value
    if shot_globals.do_mot_coil:
        load_mot(t, mot_detuning=shot_globals.mot_ta_detuning)
    else:
        load_mot(t, mot_detuning=shot_globals.mot_ta_detuning,
                 mot_coil_ctrl_voltage=0)
    # devices.uv_switch.go_low(t)
    return t


def do_molasses(t, dur, ta_last_detuning=shot_globals.mot_ta_detuning,
                repump_last_detuning=0, *, close_shutter=True):
    assert (shot_globals.do_molasses_img_beam or shot_globals.do_molasses_mot_beam), "either do_molasses_img_beam or do_molasses_mot_beam has to be on"

    if shot_globals.do_molasses_mot_beam:
        # TODO: what does this assert statement mean?
        assert shot_globals.bm_ta_detuning != 0, "bright molasses detuning = 0, did you forget to correct for the new case?"
        devices.ta_shutter.open(t)
        devices.repump_shutter.open(t)
        devices.mot_xy_shutter.open(t)
        devices.mot_z_shutter.open(t)
        _, ta_last_detuning, repump_last_detuning = load_molasses(t, shot_globals.bm_ta_detuning, shot_globals.bm_repump_detuning, ta_last_detuning=ta_last_detuning)

        print(f"molasses detuning is {shot_globals.bm_ta_detuning}")
        # turn off coil and light for TOF measurement, coil is already off in
        # load_molasses
        if close_shutter:
            devices.mot_xy_shutter.close(t + dur)
            devices.mot_z_shutter.close(t + dur)

    if shot_globals.do_molasses_img_beam:
        devices.ta_aom_digital.go_low(t)
        devices.repump_aom_digital.go_low(t)
        devices.mot_xy_shutter.close(t)
        devices.mot_z_shutter.close(t)
        devices.img_xy_shutter.open(t)
        devices.img_z_shutter.open(t)
        # TODO: what does this assert statement mean?
        assert shot_globals.bm_ta_detuning != 0, "bright molasses detuning = 0, did you forget to correct for the new case ?"
        _, ta_last_detuning, repump_last_detuning = load_molasses_img_beam(t, shot_globals.bm_img_ta_detuning, shot_globals.bm_img_repump_detuning)
        if close_shutter:
            devices.img_xy_shutter.close(t + dur)
            devices.img_z_shutter.close(t + dur)

    # turn off coil and light for TOF measurement, coil is already off in
    # load_molasses
    devices.ta_aom_digital.go_low(t + dur)
    devices.repump_aom_digital.go_low(t + dur)

    return ta_last_detuning, repump_last_detuning


def do_molasses_dipole_trap_imaging(
        t,
        ta_last_detuning,
        repump_last_detuning,
        *,
        img_ta_detuning=0,
        img_repump_detuning=0,
        img_ta_power=1,
        img_repump_power=1,
        exposure=shot_globals.bm_exposure_time,
        do_repump=True,
        close_shutter=True):
    
    # define quantization axis
    devices.x_coil_current.constant(t, biasx_calib(0))
    devices.y_coil_current.constant(t, biasy_calib(0))
    devices.z_coil_current.constant(t, biasz_calib(0))

    devices.ta_shutter.open(t)
    if do_repump:
        devices.repump_shutter.open(t)
    else:
        devices.repump_shutter.close(t)

    if shot_globals.do_molasses_mot_beam:
        devices.ta_vco.ramp(
            t - ta_vco_ramp_t,
            duration=ta_vco_ramp_t,
            initial=ta_freq_calib(ta_last_detuning),
            # ta_freq_calib(shot_globals.bm_ta_detuning),
            final=ta_freq_calib(img_ta_detuning),
            samplerate=4e5,
        )  # ramp back to imaging

        devices.repump_vco.ramp(
            t - ta_vco_ramp_t,
            duration=ta_vco_ramp_t,
            # repump_freq_calib(shot_globals.bm_repump_detuning),
            initial=repump_freq_calib(repump_last_detuning),
            final=repump_freq_calib(img_repump_detuning),
            samplerate=4e5,
        )  # ramp back to imaging

    if shot_globals.do_molasses_img_beam:
        devices.ta_vco.ramp(
            t - ta_vco_ramp_t,
            duration=ta_vco_ramp_t,
            # ta_freq_calib(shot_globals.bm_img_ta_detuning),
            initial=ta_freq_calib(ta_last_detuning),
            final=ta_freq_calib(img_ta_detuning),
            samplerate=4e5,
        )  # ramp back to imaging

        devices.repump_vco.ramp(
            t - ta_vco_ramp_t,
            duration=ta_vco_ramp_t,
            # repump_freq_calib(shot_globals.bm_img_repump_detuning),
            initial=repump_freq_calib(repump_last_detuning),
            final=repump_freq_calib(img_repump_detuning),
            samplerate=4e5,
        )  # ramp back to imaging

    ta_last_detuning = img_ta_detuning
    repump_last_detuning = img_repump_detuning

    if shot_globals.do_molasses_in_situ_check:
        if shot_globals.do_mot_beams_during_imaging:
            if shot_globals.do_mot_xy_beams_during_imaging:
                devices.mot_xy_shutter.open(t)
            if shot_globals.do_mot_z_beam_during_imaging:
                devices.mot_z_shutter.open(t)
    else:
        if shot_globals.do_mot_beams_during_imaging:
            devices.img_xy_shutter.close(t)
            devices.img_z_shutter.close(t)
            if shot_globals.do_mot_xy_beams_during_imaging:
                devices.mot_xy_shutter.open(t)
            if shot_globals.do_mot_z_beam_during_imaging:
                devices.mot_z_shutter.open(t)
        if shot_globals.do_img_beams_during_imaging:
            devices.mot_xy_shutter.close(t)
            devices.mot_z_shutter.close(t)
            if shot_globals.do_img_xy_beams_during_imaging:
                devices.img_xy_shutter.open(t)
            if shot_globals.do_img_z_beam_during_imaging:
                devices.img_z_shutter.open(t)

    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)
    # set ta and repump to full power
    devices.ta_aom_analog.constant(t, img_ta_power)
    devices.repump_aom_analog.constant(t, img_repump_power)

    if shot_globals.do_mot_camera:
        devices.manta419b_mot.expose(
            'manta419b',
            t,
            'atoms',
            exposure_time=max(exposure, 50e-6),
        )
        devices.tweezer_camera_trigger.go_high(t)
        devices.tweezer_camera_trigger.go_low(
            t + shot_globals.bm_exposure_time)

    if shot_globals.do_tweezer_camera:
        devices.manta419b_tweezer.expose(
            'manta419b',
            t,
            'atoms',
            exposure_time=max(exposure, 50e-6),
        )

        # send a trigger to a local manta camera: (mot camera or blue laser
        # camera)
        devices.mot_camera_trigger.go_high(t)
        devices.mot_camera_trigger.go_low(t + shot_globals.bm_exposure_time)

    if shot_globals.do_kinetix_camera:
        devices.kinetix.expose(
            'Kinetix',
            t,
            'atoms',
            exposure_time=max(exposure, 1e-3),
        )
        print('t after exposure', t)
        print('exposure time', max(exposure, 1e-3))

    t += exposure
    devices.repump_aom_digital.go_low(t)
    devices.ta_aom_digital.go_low(t)

    if close_shutter:
        if shot_globals.do_mot_beams_during_imaging:
            if shot_globals.do_mot_xy_beams_during_imaging:
                devices.mot_xy_shutter.close(t)
            if shot_globals.do_mot_z_beam_during_imaging:
                devices.mot_z_shutter.close(t)
        if shot_globals.do_img_beams_during_imaging:
            if shot_globals.do_img_xy_beams_during_imaging:
                devices.img_xy_shutter.close(t)
            if shot_globals.do_img_z_beam_during_imaging:
                devices.img_z_shutter.close(t)
    return t, ta_last_detuning, repump_last_detuning


def do_imaging_beam_pulse(t, ta_last_detuning, repump_last_detuning):

    blue_detuning = 10

    devices.ta_vco.ramp(
        t - ta_vco_ramp_t,
        duration=ta_vco_ramp_t,
        initial=ta_freq_calib(ta_last_detuning),
        # ta_freq_calib(shot_globals.bm_img_ta_detuning),
        final=ta_freq_calib(blue_detuning),
        samplerate=4e5,
    )  # ramp back to imaging

    devices.repump_vco.ramp(
        t - ta_vco_ramp_t,
        duration=ta_vco_ramp_t,
        # repump_freq_calib(shot_globals.bm_img_repump_detuning),
        initial=repump_freq_calib(repump_last_detuning),
        final=repump_freq_calib(blue_detuning),
        samplerate=4e5,
    )  # ramp back to imaging

    devices.mot_xy_shutter.close(t)
    devices.mot_z_shutter.close(t)

    devices.img_xy_shutter.open(t)
    # devices.img_z_shutter.open(t)
    # if shot_globals.do_img_xy_beams_during_imaging:
    #     devices.img_xy_shutter.open(t)
    # if shot_globals.do_img_z_beam_during_imaging:
    #     devices.img_z_shutter.open(t)

    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)
    # set ta and repump to full power
    devices.ta_aom_analog.constant(t, 0.15)
    devices.repump_aom_analog.constant(t, 0.15)

    t += shot_globals.img_pulse_time
    devices.repump_aom_digital.go_low(t)
    devices.ta_aom_digital.go_low(t)

    if shot_globals.do_mot_beams_during_imaging:
        if shot_globals.do_mot_xy_beams_during_imaging:
            devices.mot_xy_shutter.close(t)
        if shot_globals.do_mot_z_beam_during_imaging:
            devices.mot_z_shutter.close(t)
    if shot_globals.do_img_beams_during_imaging:
        if shot_globals.do_img_xy_beams_during_imaging:
            devices.img_xy_shutter.close(t)
        if shot_globals.do_img_z_beam_during_imaging:
            devices.img_z_shutter.close(t)

    t += 3e-3
    devices.ta_vco.ramp(
        t - ta_vco_ramp_t,
        duration=ta_vco_ramp_t,
        initial=ta_freq_calib(blue_detuning),
        final=ta_freq_calib(shot_globals.bm_img_ta_detuning),
        samplerate=4e5,
    )  # ramp back to imaging

    devices.repump_vco.ramp(
        t - ta_vco_ramp_t,
        duration=ta_vco_ramp_t,
        initial=repump_freq_calib(blue_detuning),
        final=repump_freq_calib(shot_globals.bm_img_repump_detuning),
        samplerate=4e5,
    )  # ramp back to imaging

    ta_last_detuning = shot_globals.bm_img_ta_detuning
    repump_last_detuning = shot_globals.bm_img_repump_detuning
    return t, ta_last_detuning, repump_last_detuning


def turn_on_dipole_trap(t):
    devices.pulse_1064_digital.go_high(t)
    devices.pulse_1064_analog.constant(t, 1)


def turn_off_dipole_trap(t):
    devices.pulse_1064_digital.go_low(t)
    devices.pulse_1064_analog.constant(t, 0)


def pre_imaging(t, ta_last_detuning, repump_last_detuning):
    devices.x_coil_current.constant(
        t, biasx_calib(0))  # define quantization axis
    devices.y_coil_current.constant(
        t, biasy_calib(0))  # define quantization axis
    devices.z_coil_current.constant(
        t, biasz_calib(0))  # define quantization axis

    devices.ta_vco.ramp(
        t,
        duration=ta_vco_ramp_t,
        initial=ta_freq_calib(ta_last_detuning),
        final=ta_freq_calib(shot_globals.img_ta_detuning),
        samplerate=4e5,
    )  # ramp back to imaging

    devices.repump_vco.ramp(
        t,
        duration=ta_vco_ramp_t,
        initial=repump_freq_calib(repump_last_detuning),
        final=repump_freq_calib(0),
        samplerate=4e5,
    )  # ramp back to imaging

    ta_last_detuning = shot_globals.img_ta_detuning
    repump_last_detuning = 0

    assert shot_globals.img_ta_power != 0, "Imaging ta power = 0, did you forget to adjust for the case?"
    assert shot_globals.img_repump_power != 0, "Imaging repump power = 0, did you forget to adjust for the case?"
    # back to full power for imaging
    devices.ta_aom_analog.constant(t, shot_globals.img_ta_power)
    devices.repump_aom_analog.constant(t, shot_globals.img_repump_power)

    t += ta_vco_ramp_t

    print('preimaging stage')
    print(f'ta_last_detuning = {ta_last_detuning}')
    print(f'repump_last_detuning = {repump_last_detuning}')
    return t, ta_last_detuning, repump_last_detuning


def robust_loading_pulse(t, dur):
    # TODO: rename this function, what is robust about this?
    devices.ta_shutter.open(t)
    devices.repump_shutter.open(t)
    devices.img_xy_shutter.open(t)
    devices.img_z_shutter.open(t)
    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)
    t += dur
    devices.repump_aom_digital.go_low(t)
    devices.ta_aom_digital.go_low(t)
    devices.img_xy_shutter.close(t)
    devices.img_z_shutter.close(t)
    devices.ta_shutter.close(t)
    devices.repump_shutter.close(t)
    return t


def parity_projection_pulse(t, dur, ta_last_detuning, repump_last_detuning):
    devices.ta_vco.ramp(
        t,
        duration=ta_vco_ramp_t,
        initial=ta_freq_calib(ta_last_detuning),
        final=ta_freq_calib(shot_globals.bm_parity_projection_ta_detuning),
        samplerate=4e5,
    )  # ramp back to imaging

    ta_last_detuning = shot_globals.bm_parity_projection_ta_detuning
    repump_last_detuning = 0

    devices.ta_aom_analog.constant(
        t, shot_globals.bm_parity_projection_ta_power)

    t += ta_vco_ramp_t

    print('parity projection stage')
    print(f'ta_last_detuning = {ta_last_detuning}')
    print(f'repump_last_detuning = {repump_last_detuning}')

    devices.ta_shutter.open(t)
    devices.mot_xy_shutter.open(t)
    devices.mot_z_shutter.open(t)
    devices.ta_aom_digital.go_high(t)
    t += dur
    devices.ta_aom_digital.go_low(t)
    devices.mot_xy_shutter.close(t)
    devices.mot_z_shutter.close(t)
    return t, ta_last_detuning, repump_last_detuning


def do_blue(t, dur, blue_power):
    devices.blue_456_shutter.open(t)
    devices.octagon_456_aom_analog.constant(t, blue_power)
    devices.octagon_456_aom_digital.go_high(t)
    # devices.optical_pump_shutter.open(t)
    devices.img_xy_shutter.open(t)
    devices.img_z_shutter.open(t)
    devices.repump_shutter.open(t)
    devices.repump_aom_digital.go_high(t)
    devices.repump_aom_analog.constant(t - 10e-6,
                                       shot_globals.ryd_456_repump_power)
    devices.octagon_456_aom_digital.go_low(t + dur)
    devices.octagon_456_aom_analog.constant(t, 0)
    devices.repump_aom_digital.go_low(t + dur)
    # devices.optical_pump_shutter.close(t+dur)
    devices.img_xy_shutter.close(t + dur)
    devices.img_z_shutter.close(t + dur)
    devices.repump_shutter.close(t + dur)
    devices.blue_456_shutter.close(t + dur)
    return t


def do_imaging(t, shot_number, ta_last_detuning, repump_last_detuning):
    devices.ta_shutter.open(t)
    devices.repump_shutter.open(t)
    if shot_number == 1:
        if shot_globals.do_mot_beams_during_imaging:
            if shot_globals.do_mot_xy_beams_during_imaging:
                devices.mot_xy_shutter.open(t)
            if shot_globals.do_mot_z_beam_during_imaging:
                devices.mot_z_shutter.open(t)
        if shot_globals.do_img_beams_during_imaging:
            if shot_globals.do_img_xy_beams_during_imaging:
                devices.img_xy_shutter.open(t)
            if shot_globals.do_img_z_beam_during_imaging:
                devices.img_z_shutter.open(t)
    elif shot_number == 2:
        # pulse for the second shots and wait for the first shot to finish the
        # first reading
        kinetix_readout_time = shot_globals.kinetix_roi_row[1] * 4.7065e-6
        print('kinetix readout time:', kinetix_readout_time)
        # need extra 7 ms for shutter to close on the second shot
        t += kinetix_readout_time + shot_globals.kinetix_extra_readout_time

        if shot_globals.do_shutter_close_on_second_shot:
            if shot_globals.do_mot_beams_during_imaging:
                if shot_globals.do_mot_xy_beams_during_imaging:
                    devices.mot_xy_shutter.open(t)
                if shot_globals.do_mot_z_beam_during_imaging:
                    devices.mot_z_shutter.open(t)
            if shot_globals.do_img_beams_during_imaging:
                if shot_globals.do_img_xy_beams_during_imaging:
                    devices.img_xy_shutter.open(t)
                if shot_globals.do_img_z_beam_during_imaging:
                    devices.img_z_shutter.open(t)

    devices.ta_aom_digital.go_high(t)
    devices.repump_aom_digital.go_high(t)

    # if shot_globals.do_tweezer_camera:
    #     devices.manta419b_tweezer.expose(
    #         'manta419b',
    #         t,
    #         'atoms',
    #         exposure_time=max(shot_globals.manta_exposure, 50e-6),
    #     )

    #     t +=  shot_globals.manta_exposure
    #     devices.repump_aom_digital.go_low(t)
    #     devices.ta_aom_digital.go_low(t)
    # TODO: what does this assert mean?
    assert shot_globals.img_exposure_time != 0, ("Imaging exposure time = 0, "
                                                 "did you forget to adjust "
                                                 "for the case?")

    if shot_globals.do_kinetix_camera:

        devices.kinetix.expose(
            'Kinetix',
            t,
            'atoms',
            exposure_time=max(shot_globals.img_exposure_time, 1e-3),
        )
        # do this when not using kinetix server (take picture locally)
        # devices.kinetix_camera_trigger.go_high(t)
        # devices.kinetix_camera_trigger.go_low(t+shot_globals.img_exposure_time)

        t += shot_globals.img_exposure_time

    # if shot_globals.do_tweezer_camera:
    #     devices.manta419b_tweezer.expose(
    #         'manta419b',
    #         t,
    #         'atoms',
    #         exposure_time=max(exposure, 50e-6),
    #     )

    #     # send a trigger to a local manta camera: (mot camera or blue laser camera)
    #     devices.mot_camera_trigger.go_high(t)
    #     devices.mot_camera_trigger.go_low(t+shot_globals.bm_exposure_time)

    #     t += exposure

    devices.repump_aom_digital.go_low(t)
    devices.ta_aom_digital.go_low(t)

    if shot_number == 1:
        # TODO: replace sections like this with a function literal
        if shot_globals.do_shutter_close_on_second_shot:
            if shot_globals.do_mot_beams_during_imaging:
                if shot_globals.do_mot_xy_beams_during_imaging:
                    devices.mot_xy_shutter.close(t)
                if shot_globals.do_mot_z_beam_during_imaging:
                    devices.mot_z_shutter.close(t)
            if shot_globals.do_img_beams_during_imaging:
                if shot_globals.do_img_xy_beams_during_imaging:
                    devices.img_xy_shutter.close(t)
                if shot_globals.do_img_z_beam_during_imaging:
                    devices.img_z_shutter.close(t)
    elif shot_number == 2:
        if shot_globals.do_mot_beams_during_imaging:
            if shot_globals.do_mot_xy_beams_during_imaging:
                devices.mot_xy_shutter.close(t)
            if shot_globals.do_mot_z_beam_during_imaging:
                devices.mot_z_shutter.close(t)
        if shot_globals.do_img_beams_during_imaging:
            if shot_globals.do_img_xy_beams_during_imaging:
                devices.img_xy_shutter.close(t)
            if shot_globals.do_img_z_beam_during_imaging:
                devices.img_z_shutter.close(t)
    return t, ta_last_detuning, repump_last_detuning


def optical_pumping(
        t,
        ta_last_detuning,
        repump_last_detuning,
        next_step='microwave'):
    ta_pumping_detuning = -251  # MHz 4->4 tansition
    repump_depumping_detuning = -201.24  # MHz 3->3 transition
    repump_pumping_detuning = shot_globals.op_repump_pumping_detuning
    ta_vco_stable_t = 1e-4  # stable time waited for lock

    if next_step == 'microwave':
        final_biasx_field = shot_globals.mw_biasx_field
        final_biasy_field = shot_globals.mw_biasy_field
        final_biasz_field = shot_globals.mw_biasz_field
    elif next_step == 'rydberg':
        final_biasx_field = shot_globals.ryd_biasx_field
        final_biasy_field = shot_globals.ryd_biasy_field
        final_biasz_field = shot_globals.ryd_biasz_field
    else:
        print("This next step is not defined in the function.")

    ######## pump all atom into F=4 using MOT beams ###########
    if shot_globals.do_optical_pump_MOT:
        do_optical_pump_beam = False
        print("I'm doing optical pumping now using MOT beams")
        if do_optical_pump_beam:
            devices.mot_xy_shutter.close(t)
            devices.mot_z_shutter.close(t)
            devices.optical_pump_shutter.open(t)
        else:
            devices.mot_xy_shutter.open(t)
            devices.mot_z_shutter.open(t)

        devices.img_xy_shutter.close(t)
        devices.img_z_shutter.close(t)
        devices.ta_aom_digital.go_low(t)
        devices.ta_shutter.close(t)
        devices.repump_shutter.open(t)
        devices.repump_aom_digital.go_high(t)
        devices.repump_aom_analog.constant(t, 1)
        devices.mot_coil_current_ctrl.constant(t, 0)

        t += shot_globals.op_MOT_op_time
        devices.repump_aom_digital.go_low(t)
        devices.repump_shutter.close(t)
        if do_optical_pump_beam:
            devices.optical_pump_shutter.close(t)

        devices.x_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasx_calib(0),
            final=biasx_calib(final_biasx_field),  # 0 mG
            samplerate=1e5,
        )

        devices.y_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasx_calib(0),
            final=biasy_calib(final_biasy_field),  # 0 mG
            samplerate=1e5,
        )

        devices.z_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasz_calib(0),
            final=biasz_calib(final_biasz_field),  # 0 mG
            samplerate=1e5,
        )

        ta_last_detuning = ta_last_detuning
        repump_last_detuning = repump_last_detuning

    # depump all atom into F = 3 level by using MOT beams F = 4 -> F' =
    if shot_globals.do_optical_depump_MOT:
        print("I'm doing optical de pumping now using MOT beams")
        devices.repump_aom_digital.go_low(t)
        devices.repump_shutter.close(t)
        devices.ta_aom_digital.go_low(t)

        devices.ta_vco.ramp(
            t,
            duration=ta_vco_ramp_t,
            initial=ta_freq_calib(ta_last_detuning),
            final=ta_freq_calib(ta_pumping_detuning),
            samplerate=4e5,
        )

        ta_last_detuning = ta_pumping_detuning
        repump_last_detuning = repump_last_detuning

        t += ta_vco_ramp_t + ta_vco_stable_t

        devices.mot_xy_shutter.open(t)
        devices.mot_z_shutter.open(t)
        devices.ta_shutter.open(t)  # at time t shutter already fully open
        devices.ta_aom_digital.go_high(t)
        devices.ta_aom_analog.constant(t, 1)
        devices.mot_coil_current_ctrl.constant(t, 0)

        t += shot_globals.op_MOT_odp_time
        devices.ta_aom_digital.go_low(t)
        # there will be lekage light because at time t shutter only start to
        # close
        devices.ta_shutter.close(t)

        devices.x_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasx_calib(0),
            final=biasx_calib(final_biasx_field),  # 0 mG
            samplerate=1e5,
        )

        devices.y_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasx_calib(0),
            final=biasy_calib(final_biasy_field),  # 0 mG
            samplerate=1e5,
        )

        devices.z_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasz_calib(0),
            final=biasz_calib(final_biasz_field),  # 0 mG
            samplerate=1e5,
        )

    ####### depump all atom into F = 3, mF =3 level by using sigma+ beam #####
    if shot_globals.do_optical_depump_sigma_plus:
        print("I'm doing optical de pumping now using sigma+ beams")

        op_biasx_field = shot_globals.op_bias_amp * \
            np.cos(shot_globals.op_bias_phi / 180 * np.pi) * np.sin(shot_globals.op_bias_theta / 180 * np.pi)
        op_biasy_field = shot_globals.op_bias_amp * \
            np.sin(shot_globals.op_bias_phi / 180 * np.pi) * np.sin(shot_globals.op_bias_theta / 180 * np.pi)
        op_biasz_field = shot_globals.op_bias_amp * \
            np.cos(shot_globals.op_bias_theta / 180 * np.pi)

        devices.x_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasx_calib(0),
            final=biasx_calib(op_biasx_field),  # 0 mG
            samplerate=1e5,
        )

        # devices.y_coil_current.ramp(
        #         t,
        #         duration=100e-6,
        #         initial=biasx_calib(0),
        #         final=  biasy_calib(shot_globals.op_biasy_field),# 0 mG
        #         samplerate=1e5,
        #     )

        devices.y_coil_current.constant(t, biasy_calib(
            op_biasy_field))  # define quantization axis

        devices.z_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasz_calib(0),
            final=biasz_calib(op_biasz_field),  # 0 mG
            samplerate=1e5,
        )

        devices.ta_vco.ramp(
            t,
            duration=ta_vco_ramp_t,
            initial=ta_freq_calib(ta_last_detuning),
            final=ta_freq_calib(ta_pumping_detuning),
            samplerate=4e5,
        )

        devices.repump_vco.ramp(
            t,
            duration=ta_vco_ramp_t,
            initial=repump_freq_calib(repump_last_detuning),
            final=repump_freq_calib(repump_depumping_detuning),
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
            final=biasx_calib(final_biasx_field),  # 0 mG
            samplerate=1e5,
        )

        # devices.y_coil_current.ramp(
        #         t,
        #         duration=100e-6,
        #         initial=biasx_calib(shot_globals.op_biasy_field),
        #         final=  biasy_calib(shot_globals.biasy_field),# 0 mG
        #         samplerate=1e5,
        #     )
        devices.y_coil_current.constant(t, biasy_calib(
            final_biasy_field))  # define quantization axis

        devices.z_coil_current.ramp(
            t,
            duration=100e-6,
            initial=biasz_calib(op_biasz_field),
            final=biasz_calib(final_biasz_field),  # 0 mG
            samplerate=1e5,
        )

        print(
            f'OP bias x, y, z voltage = {
                biasx_calib(op_biasx_field)}, {
                biasy_calib(op_biasy_field)}, {
                biasz_calib(op_biasz_field)}')

        ta_last_detuning = ta_pumping_detuning
        repump_last_detuning = repump_depumping_detuning

    ##### pump all atom into F = 4, mF = 4 level by using sigma+ beam #########
    if shot_globals.do_optical_pump_sigma_plus:  # use sigma + polarized light for optical pumping
        print("I'm doing optical pumping now using sigma+ beams")
        do_comparison_with_optical_pump_MOT = False
        ta_shutter_off_t = 1.74e-3
        devices.mot_xy_shutter.close(t)
        devices.mot_z_shutter.close(t)
        devices.img_xy_shutter.close(t)
        devices.img_z_shutter.close(t)
        devices.ta_aom_digital.go_low(t - ta_shutter_off_t)
        devices.ta_aom_analog.constant(t - ta_shutter_off_t, 0)
        devices.mot_coil_current_ctrl.constant(t, 0)

        if do_comparison_with_optical_pump_MOT:
            devices.ta_shutter.close(t)
        else:
            devices.ta_shutter.close(t)
            devices.repump_shutter.close(t)
            devices.repump_aom_digital.go_low(t - ta_shutter_off_t)
            devices.repump_aom_analog.constant(t - ta_shutter_off_t, 0)

            op_biasx_field = shot_globals.op_bias_amp * \
                np.cos(shot_globals.op_bias_phi / 180 * np.pi) * np.sin(shot_globals.op_bias_theta / 180 * np.pi)
            op_biasy_field = shot_globals.op_bias_amp * \
                np.sin(shot_globals.op_bias_phi / 180 * np.pi) * np.sin(shot_globals.op_bias_theta / 180 * np.pi)
            op_biasz_field = shot_globals.op_bias_amp * \
                np.cos(shot_globals.op_bias_theta / 180 * np.pi)
            devices.x_coil_current.ramp(
                t,
                duration=100e-6,
                initial=biasx_calib(0),
                final=biasx_calib(op_biasx_field),  # 0 mG
                samplerate=1e5,
            )

            devices.y_coil_current.constant(
                t, biasy_calib(op_biasy_field))  # define quantization axis

            devices.z_coil_current.ramp(
                t,
                duration=100e-6,
                initial=biasz_calib(0),
                final=biasz_calib(op_biasz_field),  # 0 mG
                samplerate=1e5,
            )

            devices.ta_vco.ramp(
                t,
                duration=ta_vco_ramp_t,
                initial=ta_freq_calib(ta_last_detuning),
                final=ta_freq_calib(ta_pumping_detuning),
                samplerate=4e5,
            )

            devices.repump_vco.ramp(
                t,
                duration=ta_vco_ramp_t,
                initial=repump_freq_calib(repump_last_detuning),
                final=repump_freq_calib(repump_pumping_detuning),
                samplerate=4e5,
            )

            ta_last_detuning = ta_pumping_detuning
            repump_last_detuning = repump_pumping_detuning

            t += max(ta_vco_ramp_t, 100e-6, shot_globals.op_ramp_delay)
            devices.ta_shutter.open(t)
            devices.ta_aom_digital.go_high(t)

        devices.optical_pump_shutter.open(t)
        devices.ta_aom_analog.constant(t, shot_globals.op_ta_power)
        devices.repump_shutter.open(t)
        devices.repump_aom_digital.go_high(t)
        devices.repump_aom_analog.constant(t, shot_globals.op_repump_power)

        devices.ta_aom_digital.go_low(t + shot_globals.op_ta_time)
        devices.repump_aom_digital.go_low(t + shot_globals.op_repump_time)
        devices.repump_shutter.close(t + shot_globals.op_repump_time)
        if shot_globals.do_depump_pulse_after_pumping:
            # do not close the TA shutter, pulsing the TA AOM for measuring
            # dark states
            assert shot_globals.op_ta_time < shot_globals.op_repump_time, "TA time should be shorter than repump for atom in F = 4"
            t += max(shot_globals.op_ta_time, shot_globals.op_repump_time)
            # devices.ta_shutter.open(t)
            devices.ta_aom_digital.go_high(t)
            devices.ta_aom_analog.constant(t, 0.1)  # 0.3)
            t += shot_globals.op_depump_pulse_time
            devices.ta_aom_digital.go_low(t)
            devices.ta_shutter.close(t)
        else:
            devices.ta_shutter.close(t + shot_globals.op_ta_time)

            assert shot_globals.op_ta_time < shot_globals.op_repump_time, "TA time should be shorter than repump for atom in F = 4"
            t += max(shot_globals.op_ta_time, shot_globals.op_repump_time)

        devices.optical_pump_shutter.close(t)

        if not do_comparison_with_optical_pump_MOT:
            devices.x_coil_current.ramp(
                t,
                duration=100e-6,
                initial=biasx_calib(op_biasx_field),
                final=biasx_calib(final_biasx_field),  # 0 mG
                samplerate=1e5,
            )

            # devices.y_coil_current.ramp(
            #         t,
            #         duration=100e-6,
            #         initial=biasx_calib(shot_globals.op_biasy_field),
            #         final=  biasy_calib(shot_globals.biasy_field),# 0 mG
            #         samplerate=1e5,
            #     )
            devices.y_coil_current.constant(
                t, biasy_calib(final_biasy_field))  # define quantization axis

            devices.z_coil_current.ramp(
                t,
                duration=100e-6,
                initial=biasz_calib(op_biasz_field),
                final=biasz_calib(final_biasz_field),  # 0 mG
                samplerate=1e5,
            )
            print(
                f'OP bias x, y, z voltage = {
                    biasx_calib(op_biasx_field)}, {
                    biasy_calib(op_biasy_field)}, {
                    biasz_calib(op_biasz_field)}')

    # ###### pump all atom into F = 4, mF = 4 level by using sigma+ beam #####
    # if shot_globals.do_optical_pump_sigma_plus: # use sigma + polarized light for optical pumping
    #     print("I'm doing optical pumping now using sigma+ beams")
    #     devices.mot_xy_shutter.close(t)
    #     devices.mot_z_shutter.close(t)
    #     devices.img_xy_shutter.close(t)
    #     devices.img_z_shutter.close(t)
    #     devices.ta_aom_digital.go_low(t)
    #     devices.mot_coil_current_ctrl.constant(t, 0)
    #     devices.ta_shutter.close(t-3e-3)
    #     devices.optical_pump_shutter.open(t)
    #     devices.ta_aom_analog.constant(t, shot_globals.op_ta_power)
    #     devices.repump_shutter.open(t)
    #     devices.repump_aom_digital.go_high(t)
    #     devices.repump_aom_analog.constant(t, shot_globals.op_repump_power)

    #     devices.ta_aom_digital.go_low(t + shot_globals.op_ta_time)
    #     devices.repump_aom_digital.go_low(t + shot_globals.op_repump_time)
    #     devices.repump_shutter.close(t + shot_globals.op_repump_time)
    #     devices.ta_shutter.close(t + shot_globals.op_ta_time)
    #     assert shot_globals.op_ta_time < shot_globals.op_repump_time, "TA time should be shorter than repump for atom in F = 4"
    #     t += max(shot_globals.op_ta_time, shot_globals.op_repump_time)
    #     devices.optical_pump_shutter.close(t)
    #     devices.x_coil_current.ramp(
    #         t,
    #         duration=100e-6,
    #         initial=biasx_calib(0),
    #         final= biasx_calib(final_biasx_field),# 0 mG
    #         samplerate=1e5,
    #     )

    #     devices.y_coil_current.ramp(
    #             t,
    #             duration=100e-6,
    #             initial=biasx_calib(0),
    #             final=  biasy_calib(final_biasy_field),# 0 mG
    #             samplerate=1e5,
    #         )

    #     devices.z_coil_current.ramp(
    #             t,
    #             duration=100e-6,
    #             initial=biasz_calib(0),
    #             final= biasz_calib(final_biasz_field),# 0 mG
    #             samplerate=1e5,
    #         )

    #     ta_last_detuning = ta_last_detuning
    #     repump_last_detuning = repump_last_detuning

    devices.mot_xy_shutter.close(t)
    devices.mot_z_shutter.close(t)
    return t, ta_last_detuning, repump_last_detuning


def killing_pulse(t, ta_last_detuning, repump_last_detuning):
    # ==================== Use a strong killing pulse to kick all atoms in F=4 out =======================#
    ta_vco_ramp_t = 1.2e-4
    min_shutter_off_t = 6.28e-3  # minimum time for shutter to be off and on again
    time_offset = ta_vco_ramp_t + min_shutter_off_t

    devices.repump_aom_digital.go_low(t - time_offset)
    devices.repump_shutter.close(t - time_offset)
    devices.ta_aom_digital.go_low(t - time_offset)
    devices.ta_aom_analog.constant(t - time_offset, 0)
    devices.ta_shutter.close(t - time_offset)
    devices.mot_xy_shutter.close(t - time_offset)
    devices.mot_z_shutter.close(t - time_offset)

    devices.ta_vco.ramp(
        t - time_offset,
        duration=ta_vco_ramp_t,
        initial=ta_freq_calib(ta_last_detuning),
        final=ta_freq_calib(0),  # -45), #ta_bm_detuning),
        samplerate=4e5,
    )

    devices.ta_shutter.open(t)
    # shutter fully open. killing pulse starts at time t
    devices.optical_pump_shutter.open(t)
    devices.ta_aom_digital.go_high(t)
    devices.ta_aom_analog.constant(t, shot_globals.op_killing_ta_power)
    t += shot_globals.op_killing_pulse_time
    devices.ta_aom_digital.go_low(t)
    devices.ta_aom_analog.constant(t, 0)
    devices.optical_pump_shutter.close(t)
    devices.ta_shutter.close(t)

    ta_last_detuning = 0  # -45
    repump_last_detuning = repump_last_detuning

    return t, ta_last_detuning, repump_last_detuning


def spectrum_microwave_sweep(t):
    uwave_clock = 9.192631770e3  # in unit of MHz
    local_oscillator_freq_mhz = 9486  # in unit of MHz MKU LO 8-13 PLL setting
    if shot_globals.do_mw_sweep_starttoend:
        mw_freq_start = local_oscillator_freq_mhz - \
            uwave_clock - shot_globals.mw_detuning_start
        mw_freq_end = local_oscillator_freq_mhz - \
            uwave_clock - shot_globals.mw_detuning_end
        mw_sweep_range = abs(mw_freq_end - mw_freq_start)
        if shot_globals.do_mw_sweep_duration:
            mw_sweep_duration = shot_globals.mw_sweep_duration
        else:
            mw_sweep_duration = mw_sweep_range / shot_globals.mw_sweep_rate
        devices.spectrum_uwave.sweep(
            t - spectrum_card_offset,
            duration=mw_sweep_duration,
            start_freq=mw_freq_start * 1e6,
            end_freq=mw_freq_end * 1e6,
            amplitude=0.99,
            phase=0,
            ch=0,
            freq_ramp_type='linear')
        print(f'Start the sweep from {shot_globals.mw_detuning_start} MHz to {
              shot_globals.mw_detuning_end} MHz within {mw_sweep_duration}s ')
    else:
        mw_sweep_range = shot_globals.mw_sweep_range
        mw_detuning_center = shot_globals.mw_detuning_center
        mw_freq_center = local_oscillator_freq_mhz - uwave_clock - mw_detuning_center
        mw_freq_start = mw_freq_center - mw_sweep_range / 2
        mw_freq_end = mw_freq_center + mw_sweep_range / 2
        if shot_globals.do_mw_sweep_duration:
            mw_sweep_duration = shot_globals.mw_sweep_duration
        else:
            mw_sweep_duration = mw_sweep_range / shot_globals.mw_sweep_rate
        devices.spectrum_uwave.sweep(
            t - spectrum_card_offset,
            duration=mw_sweep_duration,
            start_freq=mw_freq_start * 1e6,
            end_freq=mw_freq_end * 1e6,
            amplitude=0.99,
            phase=0,
            ch=0,
            freq_ramp_type='linear')
        print(f'Sweep around center {shot_globals.mw_sweep_range} MHz for a range of {
              shot_globals.mw_detuning_end} MHz within {mw_sweep_duration}s ')

    return mw_sweep_duration


def intensity_servo_keep_on(t):
    # keep the AOM digital high for intensity servo
    devices.ipg_1064_aom_digital.go_high(t)
    devices.moglabs_456_aom_digital.go_high(t)


def do_mot_in_situ_check():
    labscript.start()
    t = 0
    mot_load_dur = 0.5

    do_mot(t, mot_load_dur, use_coil=True, close_aom=True, close_shutter=False)
    t += mot_load_dur  # MOT loading time 500 ms

    t += coil_off_time  # wait for the coil fully off

    t = do_mot_imaging(t, use_shutter=False)

    # Turn off MOT for taking background images
    t += 0.1  # Wait until the MOT disappear
    t = do_mot_imaging(t, use_shutter=False)
    print("Running do_mot_in_situ_check")
    # set back to initial value
    t += 1e-2
    t = reset_mot(t, ta_last_detuning=0)

    labscript.stop(t + 1e-2)

    return t


def do_mot_tof_check():
    labscript.start()
    t = 0
    mot_load_dur = 0.5

    do_mot(t, mot_load_dur, use_coil=True, close_aom=True, close_shutter=False)
    t += mot_load_dur  # MOT loading time 500 ms

    assert shot_globals.mot_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter"
    t += shot_globals.mot_tof_imaging_delay

    t = do_mot_imaging(t, use_shutter=True)

    # Turn off MOT for taking background images
    t += 0.1  # Wait until the MOT disappear
    t = do_mot_imaging(t, use_shutter=True)

    # set back to initial value
    t += 1e-2
    t = reset_mot(t, ta_last_detuning=0)

    labscript.stop(t + 1e-2)

    return t


def do_molasses_in_situ_check():
    labscript.start()

    t = 0
    mot_load_dur = 0.75

    # if shot_globals.do_tweezers:
    #     print("Initializing tweezers")
    #     devices.dds0.synthesize(t+1e-2, shot_globals.TW_y_freqs, 0.95, 0)
    #     spectrum_manager.start_card()
    #     t1 = spectrum_manager.start_tweezers(t) #has to be the first thing in the timing sequence (?)
    #     print('tweezer start time:',t1)
    #     # Turn on the tweezer
    #     devices.tweezer_aom_digital.go_high(t)
    #     devices.tweezer_aom_analog.constant(t, 1) #0.3) #for single tweezer
    if shot_globals.do_dipole_trap:
        turn_on_dipole_trap(t)
    else:
        turn_off_dipole_trap(t)

    do_mot(
        t,
        mot_load_dur,
        use_coil=True,
        close_aom=False,
        close_shutter=False)
    t += mot_load_dur  # how long MOT last

    molasses_dur = shot_globals.bm_time
    ta_last_detuning, repump_last_detuning = do_molasses(
        t, molasses_dur, close_shutter=False)
    t += molasses_dur

    t += ta_vco_ramp_t  # account for the ramp before imaging

    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(
        t, ta_last_detuning, repump_last_detuning,
        img_ta_detuning=0,
        img_repump_detuning=0,
        img_ta_power=1,
        img_repump_power=1,
        exposure=shot_globals.bm_exposure_time,
        close_shutter=False
    )

    turn_off_dipole_trap(t)

    # Turn off MOT for taking background images
    t += 1e-1
    # devices.ta_aom_digital.go_low(t)
    # devices.repump_aom_digital.go_low(t)
    # devices.mot_xy_shutter.close(t)
    # devices.mot_z_shutter.close(t)

    t += ta_vco_ramp_t
    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(
        t, ta_last_detuning, repump_last_detuning, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=1, img_repump_power=1, exposure=shot_globals.bm_exposure_time, close_shutter=False)

    t += 1e-2
    t = reset_mot(t, ta_last_detuning)

    # if shot_globals.do_tweezers:
    #     # stop tweezers
    #     t2 = spectrum_manager.stop_tweezers(t)
    #     print('tweezer stop time:', t2)
    #     #t += 1e-3

    #     ##### dummy segment ######
    #     t1 = spectrum_manager.start_tweezers(t)
    #     print('tweezer start time:', t1)
    #     t += 2e-3
    #     t2 = spectrum_manager.stop_tweezers(t)
    #     print('tweezer stop time:',t2)
    #     #t += 1e-3################
    #     spectrum_manager.stop_card(t)

    labscript.stop(t + 1e-2)

    return t


def do_molasses_tof_check():
    labscript.start()

    t = 0
    mot_load_dur = 0.75

    # temporal for Nolan's alignment
    # devices.local_addr_1064_aom_digital.go_high(t)
    # devices.ipg_1064_aom_digital.go_high(t)
    # devices.ipg_1064_aom_analog.constant(t, 1)
    # devices.local_addr_1064_aom_analog.constant(t, 1)

    # if shot_globals.do_tweezers:
    #     print("Initializing tweezers")
    #     devices.dds0.synthesize(t+1e-2, shot_globals.TW_y_freqs, 0.95, 0)
    #     spectrum_manager.start_card()
    #     t1 = spectrum_manager.start_tweezers(t) #has to be the first thing in the timing sequence (?)
    #     print('tweezer start time:',t1)
    #     # Turn on the tweezer
    #     devices.tweezer_aom_digital.go_high(t)
    #     devices.tweezer_aom_analog.constant(t, 1) #0.3) #for single tweezer

    do_mot(
        t,
        mot_load_dur,
        use_coil=True,
        close_aom=False,
        close_shutter=False)
    t += mot_load_dur  # how long MOT last

    molasses_dur = shot_globals.bm_time
    ta_last_detuning, repump_last_detuning = do_molasses(
        t, molasses_dur, close_shutter=True)
    t += molasses_dur

    assert shot_globals.bm_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter"
    t += shot_globals.bm_tof_imaging_delay
    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(
        t, ta_last_detuning, repump_last_detuning, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=1, img_repump_power=1, exposure=shot_globals.bm_exposure_time, close_shutter=True)

    # Turn off MOT for taking background images
    t += 1e-1
    # devices.ta_aom_digital.go_low(t)
    # devices.repump_aom_digital.go_low(t)
    # devices.mot_xy_shutter.close(t)
    # devices.mot_z_shutter.close(t)

    t += shot_globals.bm_tof_imaging_delay
    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(
        t, ta_last_detuning, repump_last_detuning, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=1, img_repump_power=1, exposure=shot_globals.bm_exposure_time, close_shutter=True)

    t += 1e-2
    t = reset_mot(t, ta_last_detuning)

    # if shot_globals.do_tweezers:
    #     # stop tweezers
    #     t2 = spectrum_manager.stop_tweezers(t)
    #     print('tweezer stop time:', t2)
    #     #t += 1e-3

    #     ##### dummy segment ######
    #     t1 = spectrum_manager.start_tweezers(t)
    #     print('tweezer start time:', t1)
    #     t += 2e-3
    #     t2 = spectrum_manager.stop_tweezers(t)
    #     print('tweezer stop time:',t2)
    #     #t += 1e-3################
    #     spectrum_manager.stop_card(t)

    labscript.stop(t + 1e-2)

    return t


def do_field_calib_in_molasses_check():
    labscript.start()

    t = 0
    mot_load_dur = 0.5
    spectrum_uwave_cable_atten = 4.4  # dB at 300 MHz
    spectrum_uwave_power = -1  # -3 # dBm

    # temproral for Nolan's alignment
    # devices.ipg_1064_aom_digital.go_high(t)
    # devices.ipg_1064_aom_analog.constant(t, 1)
    # devices.pulse_1064_analog.constant(t,1)
    # devices.pulse_1064_digital.go_high(t)
    # devices.moglabs_456_aom_analog.constant(t,0.3)
    # devices.moglabs_456_aom_digital.go_high(t)
    # devices.blue_456_shutter.open(t)
    # devices.octagon_456_aom_analog.constant(t,0.05)
    # devices.octagon_456_aom_digital.go_high(t)

    # ================================================================================
    # Spectrum card related for microwaves
    # ================================================================================
    devices.spectrum_uwave.set_mode(replay_mode=b'sequence',
                                    channels=[{'name': 'microwaves',
                                               'power': spectrum_uwave_power + spectrum_uwave_cable_atten,
                                               'port': 0,
                                               'is_amplified': False,
                                               'amplifier': None,
                                               'calibration_power': 12,
                                               'power_mode': 'constant_total',
                                               'max_pulses': 1},
                                              {'name': 'mmwaves',
                                               'power': -11,
                                               'port': 1,
                                               'is_amplified': False,
                                               'amplifier': None,
                                               'calibration_power': 12,
                                               'power_mode': 'constant_total',
                                               'max_pulses': 1}],
                                    clock_freq=625,
                                    use_ext_clock=True,
                                    ext_clock_freq=10)

    do_mot(
        t,
        mot_load_dur,
        use_coil=True,
        close_aom=False,
        close_shutter=False)
    t += mot_load_dur  # how long MOT last

    molasses_dur = shot_globals.bm_time
    do_molasses(t, molasses_dur, close_shutter=True)
    t += molasses_dur

    ta_last_detuning = shot_globals.bm_ta_detuning
    repump_last_detuning = shot_globals.bm_repump_detuning
    t, ta_last_detuning, repump_last_detuning = optical_pumping(
        t, ta_last_detuning, repump_last_detuning)

    devices.x_coil_current.constant(t, biasx_calib(
        shot_globals.mw_biasx_field))   # define quantization axis
    devices.y_coil_current.constant(t, biasy_calib(
        shot_globals.mw_biasy_field))   # define quantization axis
    devices.z_coil_current.constant(t, biasz_calib(
        shot_globals.mw_biasz_field))   # define quantization axis

    # Turn on microwave
    # wait until the bias coils are on and the shutter is fullly closed
    bias_coil_on_time = 0.5e-3  # minimum time for the bias coil to be on
    shutter_ramp_time = 1.5e-3  # time for shutter to start open/close to fully open/close
    t += max(bias_coil_on_time, shutter_ramp_time, min_shutter_off_t)
    if shot_globals.do_mw_pulse:
        # the offset for the beging of output comparing to the trigger
        spectrum_card_offset = 52.8e-6
        uwave_clock = 9.192631770e3  # in unit of MHz
        local_oscillator_freq_mhz = 9486  # in unit of MHz MKU LO 8-13 PLL setting
        t += spectrum_card_offset
        devices.uwave_absorp_switch.go_high(t)
        devices.spectrum_uwave.single_freq(
            t -
            spectrum_card_offset,
            duration=shot_globals.mw_time,
            freq=(
                local_oscillator_freq_mhz -
                uwave_clock -
                shot_globals.mw_detuning) *
            1e6,
            amplitude=0.99,
            phase=0,
            ch=0,
            loops=1)
        print(
            f'Spectrum card freq = {
                local_oscillator_freq_mhz -
                uwave_clock -
                shot_globals.mw_detuning}')
        devices.uwave_absorp_switch.go_low(t + shot_globals.mw_time)
        t += shot_globals.mw_time

    if shot_globals.do_mw_multi_pulse:
        # the offset for the beging of output comparing to the trigger
        spectrum_card_offset = 52.8e-6
        uwave_clock = 9.192631770e3  # in unit of MHz
        local_oscillator_freq_mhz = 9486  # in unit of MHz MKU LO 8-13 PLL setting
        t += spectrum_card_offset
        devices.spectrum_uwave.single_freq(
            t -
            spectrum_card_offset,
            duration=2 *
            shot_globals.mw_time,
            freq=(
                local_oscillator_freq_mhz -
                uwave_clock -
                shot_globals.mw_detuning) *
            1e6,
            amplitude=0.99,
            phase=0,
            ch=0,
            loops=1)
        print(
            f'Spectrum card freq = {
                local_oscillator_freq_mhz -
                uwave_clock -
                shot_globals.mw_detuning}')
        t_pulse = shot_globals.mw_time / shot_globals.mw_num_pulses
        print(f't_pulse = {t_pulse * 1e6}us')
        print(f't before microwave pulse = {t}')
        for i in range(shot_globals.mw_num_pulses):
            devices.uwave_absorp_switch.go_high(t)
            t += t_pulse
            devices.uwave_absorp_switch.go_low(t)
            t += t_pulse
        print(f't after microwave pulse = {t}')

    if shot_globals.do_killing_pulse:
        t, ta_last_detuning, repump_last_detuning = killing_pulse(
            t, ta_last_detuning, repump_last_detuning)
        t += 4e-3

    # assert shot_globals.bm_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter"
    # t += shot_globals.bm_tof_imaging_delay
    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(
        t, ta_last_detuning, repump_last_detuning, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=0.1, img_repump_power=1, exposure=10e-3, do_repump=shot_globals.mw_imaging_do_repump, close_shutter=True)

    # Turn off MOT for taking background images
    t += 1e-1
    # devices.ta_aom_digital.go_low(t)
    # devices.repump_aom_digital.go_low(t)
    # devices.mot_xy_shutter.close(t)
    # devices.mot_z_shutter.close(t)

    # t += shot_globals.bm_tof_imaging_delay
    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(
        t, ta_last_detuning, repump_last_detuning, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=0.1, img_repump_power=1, exposure=10e-3, do_repump=shot_globals.mw_imaging_do_repump, close_shutter=True)
    ##### dummy segment ####
    devices.spectrum_uwave.single_freq(
        t,
        duration=100e-6,
        freq=10**6,
        amplitude=0.99,
        phase=0,
        ch=0,
        loops=1)  # dummy segment
    devices.spectrum_uwave.stop()

    t += 1e-2
    t = reset_mot(t, ta_last_detuning)

    labscript.stop(t + 1e-2)

    return t


def do_dipole_trap_tof_check():
    labscript.start()

    t = 0

    intensity_servo_keep_on(t)
    devices.mirror_1_horizontal.constant(t, 0)
    devices.mirror_1_vertical.constant(t, 0)
    devices.mirror_2_horizontal.constant(t, 0)
    devices.mirror_2_vertical.constant(t, 0)

    if shot_globals.do_dipole_trap:
        turn_on_dipole_trap(t)
    else:
        turn_off_dipole_trap(t)

    if spcm_sequence_mode:
        spectrum_manager.start_card()
        t1 = spectrum_manager.start_tweezers(t)
    else:
        spectrum_manager_fifo.start_tweezer_card()
        # has to be the first thing in the timing sequence (?)
        t1 = spectrum_manager_fifo.start_tweezers(t)
    devices.dds0.synthesize(
        t + 1e-3,
        freq=TW_y_freqs,
        amp=0.95,
        ph=0)  # unit: MHz
    # devices.dds1.synthesize(t+1e-3, freq = shot_globals.blue_456_detuning, amp = 0.95, ph = 0)
    print('tweezer x start time:', t1)
    # Turn on the tweezer
    if shot_globals.do_tweezers:
        devices.tweezer_aom_digital.go_high(t)
        devices.tweezer_aom_analog.constant(t, 1)  # 0.3) #for single tweezer
    else:
        devices.tweezer_aom_digital.go_low(t)
        devices.tweezer_aom_analog.constant(t, 0)  # 0.3) #for single tweezer

    if shot_globals.do_local_addr:
        devices.local_addr_1064_aom_analog.constant(
            t, 1)  # for aligning local addressing beams
        devices.local_addr_1064_aom_digital.go_high(t)
    else:
        devices.local_addr_1064_aom_analog.constant(
            t, 0)  # for aligning local addressing beams
        devices.local_addr_1064_aom_digital.go_low(t)

    # the offset for the beging of output comparing to the trigger
    spectrum_card_offset = 52.8e-6
    spectrum_uwave_cable_atten = 4.4  # dB at 300 MHz
    spectrum_uwave_power = -1  # -3 # dBm
    uwave_clock = 9.192631770e3  # in unit of MHz
    local_oscillator_freq_mhz = 9486  # in unit of MHz MKU LO 8-13 PLL setting
    if shot_globals.do_mw_pulse or shot_globals.do_mw_sweep:
        devices.spectrum_uwave.set_mode(replay_mode=b'sequence',
                                        channels=[{'name': 'microwaves',
                                                   'power': spectrum_uwave_power + spectrum_uwave_cable_atten,
                                                   'port': 0,
                                                   'is_amplified': False,
                                                   'amplifier': None,
                                                   'calibration_power': 12,
                                                   'power_mode': 'constant_total',
                                                   'max_pulses': 1},
                                                  {'name': 'mmwaves',
                                                   'power': -11,
                                                   'port': 1,
                                                   'is_amplified': False,
                                                   'amplifier': None,
                                                   'calibration_power': 12,
                                                   'power_mode': 'constant_total',
                                                   'max_pulses': 1}],
                                        clock_freq=625,
                                        use_ext_clock=True,
                                        ext_clock_freq=10)

    mot_load_dur = 1  # 0.75
    do_mot(
        t,
        mot_load_dur,
        use_coil=True,
        close_aom=False,
        close_shutter=False)
    t += mot_load_dur  # how long MOT last

    molasses_dur = shot_globals.bm_time
    ta_last_detuning, repump_last_detuning = do_molasses(
        t, molasses_dur, close_shutter=True)
    t += molasses_dur

    t, ta_last_detuning, repump_last_detuning = optical_pumping(
        t, ta_last_detuning, repump_last_detuning)
    if shot_globals.do_mw_pulse:
        devices.x_coil_current.constant(t, biasx_calib(
            shot_globals.mw_biasx_field))   # define quantization axis
        devices.y_coil_current.constant(t, biasy_calib(
            shot_globals.mw_biasy_field))   # define quantization axis
        devices.z_coil_current.constant(t, biasz_calib(
            shot_globals.mw_biasz_field))   # define quantization axis

    if shot_globals.do_mw_sweep:
        devices.uwave_absorp_switch.go_high(t)
        mw_sweep_duration = spectrum_microwave_sweep(t)
        devices.uwave_absorp_switch.go_low(t + mw_sweep_duration)
        t += mw_sweep_duration

    if shot_globals.do_mw_pulse:
        t += spectrum_card_offset
        devices.uwave_absorp_switch.go_high(t)
        devices.spectrum_uwave.single_freq(
            t -
            spectrum_card_offset,
            duration=shot_globals.mw_time,
            freq=(
                local_oscillator_freq_mhz -
                uwave_clock -
                shot_globals.mw_detuning) *
            1e6,
            amplitude=0.99,
            phase=0,
            ch=0,
            loops=1)
        print(
            f'Spectrum card freq = {
                local_oscillator_freq_mhz -
                uwave_clock -
                shot_globals.mw_detuning}')
        devices.uwave_absorp_switch.go_low(t + shot_globals.mw_time)
        t += shot_globals.mw_time

    if shot_globals.do_killing_pulse:
        # for shutter and vco to be ready for killing pulse
        t += ta_vco_ramp_t + min_shutter_off_t
        t, ta_last_detuning, repump_last_detuning = killing_pulse(
            t, ta_last_detuning, repump_last_detuning)
        t += 10e-3

    else:
        t += 10e-3

    assert shot_globals.img_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter"
    t += shot_globals.img_tof_imaging_delay
    assert shot_globals.img_exposure_time != 0, "Imaging expsorue time = 0, did you forget to adjust for the case?"
    assert shot_globals.img_ta_power != 0, "Imaging ta power = 0, did you forget to adjust for the case?"
    assert shot_globals.img_repump_power != 0, "Imaging repump power = 0, did you forget to adjust for the case?"
    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(
        t, ta_last_detuning, repump_last_detuning,
        img_ta_detuning=shot_globals.img_ta_detuning,
        img_repump_detuning=0,
        img_ta_power=shot_globals.img_ta_power,
        img_repump_power=shot_globals.img_repump_power,
        exposure=shot_globals.img_exposure_time,
        close_shutter=True
    )

    turn_off_dipole_trap(t)

    # Turn off MOT for taking background images
    t += 1e-1
    # devices.ta_aom_digital.go_low(t)
    # devices.repump_aom_digital.go_low(t)
    # devices.mot_xy_shutter.close(t)
    # devices.mot_z_shutter.close(t)

    t += shot_globals.img_tof_imaging_delay
    assert shot_globals.img_exposure_time != 0, "Imaging expsorue time = 0, did you forget to adjust for the case?"
    assert shot_globals.img_ta_power != 0, "Imaging ta power = 0, did you forget to adjust for the case?"
    assert shot_globals.img_repump_power != 0, "Imaging repump power = 0, did you forget to adjust for the case?"
    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(
        t, ta_last_detuning, repump_last_detuning,
        img_ta_detuning=shot_globals.img_ta_detuning,
        img_repump_detuning=0,
        img_ta_power=shot_globals.img_ta_power,
        img_repump_power=shot_globals.img_repump_power,
        exposure=shot_globals.img_exposure_time,
        close_shutter=True
    )

    t += 1e-2
    t = reset_mot(t, ta_last_detuning)

    if spcm_sequence_mode:
        t2 = spectrum_manager.stop_tweezers(t)
        ##### dummy segment ######
        t1 = spectrum_manager.start_tweezers(t)
        print('tweezer start time:', t1)
        t += 2e-3
        t2 = spectrum_manager.stop_tweezers(t)
        print('tweezer stop time:', t2)
        #################
        spectrum_manager.stop_card(t)
    else:
        t2 = spectrum_manager_fifo.stop_tweezers(t)
        spectrum_manager_fifo.stop_tweezer_card()
    print('tweezer stop time:', t2)

    if shot_globals.do_tweezers:
        # stop tweezers
        devices.tweezer_aom_digital.go_low(t)
    if shot_globals.do_local_addr:
        # stop tweezers
        devices.local_addr_1064_aom_digital.go_low(t)

    labscript.stop(t + 1e-2)

    return t


def do_img_beam_alignment_check():
    labscript.start()

    t = 0
    if shot_globals.do_dipole_trap:
        turn_on_dipole_trap(t)
    else:
        turn_off_dipole_trap(t)

    if shot_globals.do_tweezers:
        devices.dds0.synthesize(t + 1e-2, shot_globals.TW_y_freqs, 0.95, 0)
        spectrum_manager.start_card()
        # has to be the first thing in the timing sequence (?)
        t1 = spectrum_manager.start_tweezers(t)
        print('tweezer start time:', t1)
        # Turn on the tweezer
        devices.tweezer_aom_digital.go_high(t)
        devices.tweezer_aom_analog.constant(t, 0.25)  # 1) #for single tweezer

    mot_load_dur = 0.75
    do_mot(
        t,
        mot_load_dur,
        use_coil=True,
        close_aom=False,
        close_shutter=False)
    t += mot_load_dur  # how long MOT last

    molasses_dur = shot_globals.bm_time
    ta_last_detuning, repump_last_detuning = do_molasses(
        t, molasses_dur, close_shutter=True)
    t += molasses_dur

    assert shot_globals.img_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter"
    t += shot_globals.img_tof_imaging_delay

    if shot_globals.do_img_pulse:
        t, ta_last_detuning, repump_last_detuning = do_imaging_beam_pulse(
            t, ta_last_detuning, repump_last_detuning)
        # t,
        # img_ta_detuning = shot_globals.img_ta_detuning,
        # img_repump_detuning = 0,
        # img_ta_power = shot_globals.img_ta_power,
        # img_repump_power = shot_globals.img_repump_power,
        # exposure = shot_globals.img_exposure_time,
        # close_shutter = True
        # )
    else:
        t += shot_globals.img_pulse_time + 3e-3 + ta_vco_ramp_t * 2

    t += 7e-3

    assert shot_globals.img_exposure_time != 0, "Imaging expsorue time = 0, did you forget to adjust for the case?"
    assert shot_globals.img_ta_power != 0, "Imaging ta power = 0, did you forget to adjust for the case?"
    assert shot_globals.img_repump_power != 0, "Imaging repump power = 0, did you forget to adjust for the case?"
    t, ta_last_detuning, repump_last_detuning, = do_molasses_dipole_trap_imaging(
        t, ta_last_detuning, repump_last_detuning,
        img_ta_detuning=shot_globals.img_ta_detuning,
        img_repump_detuning=0,
        img_ta_power=shot_globals.img_ta_power,
        img_repump_power=shot_globals.img_repump_power,
        exposure=shot_globals.img_exposure_time,
        close_shutter=True
    )

    turn_off_dipole_trap(t)

    # Turn off MOT for taking background images
    t += 1e-1
    # devices.ta_aom_digital.go_low(t)
    # devices.repump_aom_digital.go_low(t)
    # devices.mot_xy_shutter.close(t)
    # devices.mot_z_shutter.close(t)

    t += shot_globals.img_tof_imaging_delay
    assert shot_globals.img_exposure_time != 0, "Imaging expsorue time = 0, did you forget to adjust for the case?"
    assert shot_globals.img_ta_power != 0, "Imaging ta power = 0, did you forget to adjust for the case?"
    assert shot_globals.img_repump_power != 0, "Imaging repump power = 0, did you forget to adjust for the case?"
    t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(
        t, ta_last_detuning, repump_last_detuning,
        img_ta_detuning=shot_globals.img_ta_detuning,
        img_repump_detuning=0,
        img_ta_power=shot_globals.img_ta_power,
        img_repump_power=shot_globals.img_repump_power,
        exposure=shot_globals.img_exposure_time,
        close_shutter=True
    )

    t += 1e-2
    t = reset_mot(t, ta_last_detuning)

    if shot_globals.do_tweezers:
        # stop tweezers
        t2 = spectrum_manager.stop_tweezers(t)
        print('tweezer stop time:', t2)
        # t += 1e-3

        ##### dummy segment ######
        t1 = spectrum_manager.start_tweezers(t)
        print('tweezer start time:', t1)
        t += 2e-3
        t2 = spectrum_manager.stop_tweezers(t)
        print('tweezer stop time:', t2)
        # t += 1e-3################
        spectrum_manager.stop_card(t)

    labscript.stop(t + 1e-2)

    return t


def do_tweezer_position_check():
    check_on_vimba_viewer = True  # False
    # look at the trap intensity distribution on the tweezer camera
    # look at it's relative position to the molasses
    labscript.start()
    t = 0

    intensity_servo_keep_on(t)

    t += 1e-3

    if spcm_sequence_mode:
        spectrum_manager.start_card()
        t1 = spectrum_manager.start_tweezers(t)
    else:
        spectrum_manager_fifo.start_tweezer_card()
        # has to be the first thing in the timing sequence (?)
        t1 = spectrum_manager_fifo.start_tweezers(t)
    # devices.dds0.synthesize(t+1e-3, freq = TW_y_freqs, amp = 0.95, ph = 0) # unit: MHz
    # devices.dds1.synthesize(t+1e-3, freq = shot_globals.blue_456_detuning, amp = 0.95, ph = 0)
    print('tweezer x start time:', t1)
    # Turn on the tweezer
    if shot_globals.do_tweezers:
        devices.tweezer_aom_digital.go_high(t)
        devices.tweezer_aom_analog.constant(
            t, 0.175)  # 0.3) #for single tweezer
    else:
        devices.tweezer_aom_digital.go_low(t)
        devices.tweezer_aom_analog.constant(t, 0)  # 0.3) #for single tweezer

    if shot_globals.do_local_addr:
        devices.local_addr_1064_aom_analog.constant(
            t, 0.1)  # for aligning local addressing beams
        devices.local_addr_1064_aom_digital.go_high(t)
    else:
        devices.local_addr_1064_aom_analog.constant(
            t, 0)  # for aligning local addressing beams
        devices.local_addr_1064_aom_digital.go_low(t)

    t += 1e-3

    ta_last_detuning = shot_globals.mot_ta_detuning
    repump_last_detuning = 0

    if shot_globals.do_rearrangement:
        # take image in kinetix camera for rearrangement to work (need to check
        # do_kinetic_camera for this to work)
        t, ta_last_detuning, repump_last_detuning = do_imaging(
            t, 1, ta_last_detuning, repump_last_detuning)
        t += 300e-3  # time for rearrangemeent
        t, ta_last_detuning, repump_last_detuning = do_imaging(
            t, 2, ta_last_detuning, repump_last_detuning)

    if not check_on_vimba_viewer:
        t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(
            t, ta_last_detuning, repump_last_detuning, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=0, img_repump_power=0, exposure=50e-6, close_shutter=False)

        t += 7e-2
    else:
        t += 5  # 1e-3 #10 #

    # devices.tweezer_aom_digital.go_low(t)

    # t, ta_last_detuning, repump_last_detuning = do_molasses_dipole_trap_imaging(t, ta_last_detuning, repump_last_detuning, img_ta_detuning=0, img_repump_detuning=0, img_ta_power=0, img_repump_power=0, exposure= 50e-6, close_shutter= False)

    if spcm_sequence_mode:
        t2 = spectrum_manager.stop_tweezers(t)
        ##### dummy segment ######
        t1 = spectrum_manager.start_tweezers(t)
        print('tweezer start time:', t1)
        t += 2e-3
        t2 = spectrum_manager.stop_tweezers(t)
        print('tweezer stop time:', t2)
        #################
        spectrum_manager.stop_card(t)
    else:
        t2 = spectrum_manager_fifo.stop_tweezers(t)
        spectrum_manager_fifo.stop_tweezer_card()
    print('tweezer stop time:', t2)

    if shot_globals.do_tweezers:
        # stop tweezers
        devices.tweezer_aom_digital.go_low(t)
    if shot_globals.do_local_addr:
        # stop tweezers
        devices.local_addr_1064_aom_digital.go_low(t)

    labscript.stop(t + 1e-2)

    return t


def do_tweezer_check():
    import numpy as np
    MOT_load_dur = 0.5
    molasses_dur = shot_globals.bm_time
    labscript.start()

    t = 0

    intensity_servo_keep_on(t)
    devices.mirror_1_horizontal.constant(
        t, shot_globals.ryd_456_mirror_1_h_position)
    devices.mirror_1_vertical.constant(
        t, shot_globals.ryd_456_mirror_1_v_position)
    devices.mirror_2_horizontal.constant(
        t, shot_globals.ryd_456_mirror_2_h_position)
    devices.mirror_2_vertical.constant(
        t, shot_globals.ryd_456_mirror_2_v_position)

    assert shot_globals.do_sequence_mode, "shot_globals.do_sequence_mode is False, running Fifo mode now. Set to True for sequence mode"
    if shot_globals.do_tweezers:
        print("Initializing tweezers")
        # devices.dds0.synthesize(t+1e-2, shot_globals.TW_y_freqs, 0.95, 0)
        devices.dds1.synthesize(
            t + 1e-3,
            freq=shot_globals.blue_456_detuning,
            amp=0.5,
            ph=0)  # for Sam's blue laser test
        spectrum_manager.start_card()
        # has to be the first thing in the timing sequence (?)
        t1 = spectrum_manager.start_tweezers(t)
        print('tweezer start time:', t1)
        # Turn on the tweezer
        devices.tweezer_aom_digital.go_high(t)
        # devices.tweezer_aom_analog.constant(t, 1) #0.3) #for single tweezer
        devices.tweezer_aom_analog.constant(
            t, shot_globals.tw_power)  # 0.3) #for single tweezer

    if shot_globals.do_dipole_trap:
        turn_on_dipole_trap(t)
    else:
        turn_off_dipole_trap(t)

    # devices.dispenser_off_trigger.go_high(t)
    do_MOT(t, MOT_load_dur, shot_globals.do_mot_coil)
    t += MOT_load_dur  # how long MOT last

    # _, ta_last_detuning, repump_last_detuning = load_molasses(t, ta_bm_detuning, repump_bm_detuning)
    ta_last_detuning, repump_last_detuning = do_molasses(
        t, molasses_dur, close_shutter=True)
    t += molasses_dur
    # ta_last_detuning =  ta_bm_detuning
    # repump_last_detuning = repump_bm_detuning
    # devices.mot_xy_shutter.close(t)
    # devices.mot_z_shutter.close(t)

    t += 7e-3

    devices.tweezer_aom_analog.ramp(
        t,
        duration=10e-3,
        initial=shot_globals.tw_power,
        final=1,
        samplerate=4e5,
    )  # ramp back to full tweezer power

    if shot_globals.do_parity_projection_pulse:
        t, ta_last_detuning, repump_bm_detuning = parity_projection_pulse(
            t, shot_globals.bm_parity_projection_pulse_dur, ta_last_detuning, repump_last_detuning)

    ta_last_detuning, repump_last_detuning = do_molasses(
        t, molasses_dur, close_shutter=True, ta_last_detuning=ta_last_detuning, repump_last_detuning=repump_last_detuning)
    t += molasses_dur

    t, ta_last_detuning, repump_last_detuning = pre_imaging(
        t, ta_last_detuning, repump_last_detuning)

    if shot_globals.do_robust_loading_pulse:
        robust_loading_pulse(t, dur=shot_globals.bm_robust_loading_pulse_dur)
        t += shot_globals.bm_robust_loading_pulse_dur

    assert shot_globals.img_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter'"
    t += shot_globals.img_tof_imaging_delay

    # first shot
    devices.digital_out_ch22.go_high(t)
    t, ta_last_detuning, repump_last_detuning = do_imaging(
        t, 1, ta_last_detuning, repump_last_detuning)
    devices.digital_out_ch22.go_low(t)
    t += 7e-3  # make sure shutter fully closed after 1st imaging

    # ta_last_detuning, repump_last_detuning = do_molasses(t, molasses_dur, close_shutter = True, use_img_beam = shot_globals.do_molasses_img_beam, use_mot_beam = shot_globals.do_molasses_mot_beam, ta_last_detuning=ta_last_detuning, repump_last_detuning= repump_last_detuning)
    # t += molasses_dur

    if shot_globals.do_tweezer_modulation:
        devices.tweezer_aom_analog.ramp(
            t,
            duration=10e-3,
            initial=1,
            final=shot_globals.tw_power,
            samplerate=4e5,
        )  # ramp back to full tweezer power

        t += 10e-3

        devices.tweezer_aom_analog.sine(
            t,
            duration=20e-3,
            amplitude=0.015,
            angfreq=2 * np.pi * shot_globals.tw_modulation_freq,  # 0.5e6,
            phase=0,
            dc_offset=shot_globals.tw_power,
            samplerate=0.4e6
        )
        t += 20e-3

        devices.tweezer_aom_analog.ramp(
            t,
            duration=10e-3,
            initial=shot_globals.tw_power,
            final=1,
            samplerate=4e5,
        )  # ramp back to full tweezer power

        # devices.tweezer_aom_analog.ramp(
        # t,
        # duration=10e-3,
        # initial=shot_globals.tw_power,
        # final=1,
        # samplerate=4e5,
        # )  # ramp back to full tweezer power

    if shot_globals.do_456nm_laser:
        blue_dur = shot_globals.blue_456nm_duration
        do_blue(t, blue_dur)
        t += blue_dur

    # if shot_globals.

    t += shot_globals.img_wait_time_between_shots

    # turn traps off for temperature measurement (release and recapture)
    if do_tw_trap_off:
        devices.tweezer_aom_analog.ramp(
            t,
            duration=10e-3,
            initial=1,
            final=shot_globals.tw_power,
            samplerate=4e5,
        )  # ramp to loading tweezer power

        t += 10e-3

        devices.tweezer_aom_digital.go_low(t)

        t += shot_globals.tw_turn_off_time

        devices.tweezer_aom_digital.go_high(t)  # turn traps back on

        devices.tweezer_aom_analog.ramp(
            t,
            duration=10e-3,
            initial=shot_globals.tw_power,
            final=1,
            samplerate=4e5,
        )  # ramp to full tweezer power

    # second shot
    t, ta_last_detuning, repump_last_detuning = pre_imaging(
        t, ta_last_detuning, repump_last_detuning)
    t += 10e-3  # 100e-3
    devices.digital_out_ch22.go_high(t)
    t, ta_last_detuning, repump_last_detuning = do_imaging(
        t, 2, ta_last_detuning, repump_last_detuning)
    devices.digital_out_ch22.go_low(t)

    t += 1e-2
    t = reset_mot(t, ta_last_detuning)
    # make sure tweezer AOM has full rf power
    if shot_globals.do_tweezers:
        # stop tweezers
        t2 = spectrum_manager.stop_tweezers(t)
        print('tweezer stop time:', t2)
        # t += 1e-3

        ##### dummy segment ######
        t1 = spectrum_manager.start_tweezers(t)
        print('tweezer start time:', t1)
        t += 2e-3
        t2 = spectrum_manager.stop_tweezers(t)
        print('tweezer stop time:', t2)
        # t += 1e-3################
        spectrum_manager.stop_card(t)

    labscript.stop(t + 1e-2)

    return t


def do_tweezer_check_fifo():

    MOT_load_dur = 0.5  # 0.5
    molasses_dur = shot_globals.bm_time
    labscript.start()

    t = 0

    intensity_servo_keep_on(t)

    # temporal for Sam's alignment
    # devices.moglabs_456_aom_digital.go_high(t)
    # devices.moglabs_456_aom_analog.constant(t, 1)
    # devices.octagon_456_aom_digital.go_high(t)
    # devices.octagon_456_aom_analog.constant(t, 1)
    # devices.blue_456_shutter.open(t)

    if shot_globals.do_tweezers:
        if spcm_sequence_mode:
            spectrum_manager.start_card()
            t1 = spectrum_manager.start_tweezers(t)
        else:
            spectrum_manager_fifo.start_tweezer_card()
            # has to be the first thing in the timing sequence (?)
            t1 = spectrum_manager_fifo.start_tweezers(t)
        devices.dds0.synthesize(
            t + 1e-3,
            freq=TW_y_freqs,
            amp=0.95,
            ph=0)  # unit: MHz
        devices.dds1.synthesize(
            t + 1e-3,
            freq=shot_globals.blue_456_detuning,
            amp=0.5,
            ph=0)  # for Sam's blue laser test
        print('tweezer x start time:', t1)
        # Turn on the tweezer
        devices.tweezer_aom_digital.go_high(t)
        devices.tweezer_aom_analog.constant(
            t, shot_globals.tw_power)  # 0.3) #for single tweezer

    if shot_globals.do_local_addr:
        devices.local_addr_1064_aom_analog.constant(
            t, 0.1)  # for aligning local addressing beams
        devices.local_addr_1064_aom_digital.go_high(t)
    else:
        devices.local_addr_1064_aom_analog.constant(
            t, 0)  # for aligning local addressing beams
        devices.local_addr_1064_aom_digital.go_low(t)

    if shot_globals.do_dipole_trap:
        turn_on_dipole_trap(t)
    else:
        turn_off_dipole_trap(t)

    do_MOT(t, MOT_load_dur, shot_globals.do_mot_coil)
    t += MOT_load_dur  # how long MOT last

    # _, ta_last_detuning, repump_last_detuning = load_molasses(t, ta_bm_detuning, repump_bm_detuning)
    ta_last_detuning, repump_last_detuning = do_molasses(
        t, molasses_dur, close_shutter=True)
    t += molasses_dur
    # ta_last_detuning =  ta_bm_detuning
    # repump_last_detuning = repump_bm_detuning
    # devices.mot_xy_shutter.close(t)
    # devices.mot_z_shutter.close(t)

    t += 7e-3

    devices.tweezer_aom_analog.ramp(
        t,
        duration=10e-3,
        initial=shot_globals.tw_power,
        final=1,
        samplerate=4e5,
    )  # ramp back to full tweezer power for imaging

    if shot_globals.do_parity_projection_pulse:
        t, ta_last_detuning, repump_bm_detuning = parity_projection_pulse(
            t, shot_globals.bm_parity_projection_pulse_dur, ta_last_detuning, repump_last_detuning)

    ta_last_detuning, repump_last_detuning = do_molasses(
        t, molasses_dur, close_shutter=True, ta_last_detuning=ta_last_detuning, repump_last_detuning=repump_last_detuning)
    t += molasses_dur

    t, ta_last_detuning, repump_last_detuning = pre_imaging(
        t, ta_last_detuning, repump_last_detuning)

    if shot_globals.do_robust_loading_pulse:
        robust_loading_pulse(t, dur=shot_globals.bm_robust_loading_pulse_dur)
        t += shot_globals.bm_robust_loading_pulse_dur

    assert shot_globals.img_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter"
    t += shot_globals.img_tof_imaging_delay

    # first shot
    devices.digital_out_ch22.go_high(t)
    t, ta_last_detuning, repump_last_detuning = do_imaging(
        t, 1, ta_last_detuning, repump_last_detuning)
    devices.digital_out_ch22.go_low(t)
    # devices.digital_out_ch26.go_high(t) #for testing spectrum card output

    t += 7e-3  # make sure sutter fully closed after 1st imaging

    # ta_last_detuning, repump_last_detuning = do_molasses(t, molasses_dur, close_shutter = True, use_img_beam = shot_globals.do_molasses_img_beam, use_mot_beam = shot_globals.do_molasses_mot_beam, ta_last_detuning=ta_last_detuning, repump_last_detuning= repump_last_detuning)
    # t += molasses_dur

    if shot_globals.do_tweezer_modulation:
        devices.tweezer_aom_analog.ramp(
            t,
            duration=10e-3,
            initial=1,
            final=shot_globals.tw_power,
            samplerate=4e5,
        )  # ramp back to full tweezer power

        t += 10e-3

        devices.tweezer_aom_analog.sine(
            t,
            duration=20e-3,
            amplitude=0.015,  # 0.025,
            angfreq=2 * np.pi() * shot_globals.tw_modulation_freq,  # 0.5e6,
            phase=0,
            dc_offset=shot_globals.tw_power,
            samplerate=0.4e6
        )
        t += 20e-3

        # lower trap after modulation
        tw_power = 0.3
        # devices.tweezer_aom_analog.constant(t, tw_power)
        # t += 1e-3

        devices.tweezer_aom_analog.ramp(
            t,
            duration=10e-3,
            initial=tw_power,  # shot_globals.tw_power,
            final=1,
            samplerate=4e5,
        )  # ramp back to full tweezer power

        # devices.tweezer_aom_analog.ramp(
        # t,
        # duration=10e-3,
        # initial=shot_globals.tw_power,
        # final=1,
        # samplerate=4e5,
        # )  # ramp back to full tweezer power

    t += shot_globals.img_wait_time_between_shots

    if shot_globals.do_cooling_while_rearrange:
        t += 93e-3
        ta_last_detuning, repump_last_detuning = do_molasses(
            t, 7e-3, close_shutter=True, ta_last_detuning=ta_last_detuning, repump_last_detuning=repump_last_detuning)
        t += 7e-3  # molasses_dur
    else:
        t += 140e-3

    # t += 10e-3

    # turn traps off for temperature measurement (release and recapture)
    if do_tw_trap_off:
        devices.tweezer_aom_digital.go_low(t)
        devices.tweezer_aom_analog.constant(t, 0)

        t += shot_globals.tw_turn_off_time

        devices.tweezer_aom_digital.go_high(t)  # turn traps back on
        devices.tweezer_aom_analog.constant(t, 1)

    # second shot
    t, ta_last_detuning, repump_last_detuning = pre_imaging(
        t, ta_last_detuning, repump_last_detuning)

    # devices.digital_out_ch26.go_low(t) #for testing spectrum card output
    devices.digital_out_ch22.go_high(t)
    t, ta_last_detuning, repump_last_detuning = do_imaging(
        t, 2, ta_last_detuning, repump_last_detuning)
    devices.digital_out_ch22.go_low(t)

    t += 2e-2  # 1e-3, need to  change to longer before turn off the tweezer since need to be > 1 Notifiysize
    t = reset_mot(t, ta_last_detuning)
    # make sure tweezer AOM has full rf power
    if shot_globals.do_rearrange_position_check:
        devices.manta419b_tweezer.expose(
            'manta419b',
            t -
            shot_globals.TW_rearrangement_time_offset +
            shot_globals.TW_rearrangement_fine_time_offset,
            'atoms',
            exposure_time=50e-6,
        )

    if shot_globals.do_tweezers:
        # stop tweezers
        # devices.tweezer_aom_digital.go_low(t)
        if spcm_sequence_mode:
            t2 = spectrum_manager.stop_tweezers(t)
            ##### dummy segment ######
            t1 = spectrum_manager.start_tweezers(t)
            print('tweezer start time:', t1)
            t += 2e-3
            t2 = spectrum_manager.stop_tweezers(t)
            print('tweezer stop time:', t2)
            #################
            spectrum_manager.stop_card(t)
        else:
            devices.digital_out_ch22.go_high(
                t - shot_globals.TW_rearrangement_time_offset)
            devices.digital_out_ch22.go_low(
                t - shot_globals.TW_rearrangement_time_offset + 1e-3)
            t2 = spectrum_manager_fifo.stop_tweezers(t)
            print('tweezer stop time:', t2)
            spectrum_manager_fifo.stop_tweezer_card()

    labscript.stop(t + 1e-2)
    return t


def do_optical_pump_in_tweezer_check():

    MOT_load_dur = 0.5  # 0.5
    molasses_dur = shot_globals.bm_time
    labscript.start()

    t = 0

    intensity_servo_keep_on(t)
    devices.mirror_1_horizontal.constant(
        t, shot_globals.ryd_456_mirror_1_h_position)
    devices.mirror_1_vertical.constant(
        t, shot_globals.ryd_456_mirror_1_v_position)
    devices.mirror_2_horizontal.constant(
        t, shot_globals.ryd_456_mirror_2_h_position)
    devices.mirror_2_vertical.constant(
        t, shot_globals.ryd_456_mirror_2_v_position)

    if shot_globals.do_tweezers:
        if spcm_sequence_mode:
            spectrum_manager.start_card()
            t1 = spectrum_manager.start_tweezers(t)
        else:
            spectrum_manager_fifo.start_tweezer_card()
            # has to be the first thing in the timing sequence (?)
            t1 = spectrum_manager_fifo.start_tweezers(t)
        # devices.dds0.synthesize(t+1e-3, freq = TW_y_freqs, amp = 0.95, ph =
        # 0) # unit: MHz
        devices.dds1.synthesize(
            t + 1e-3,
            freq=shot_globals.blue_456_detuning,
            amp=0.5,
            ph=0)  # for Sam's blue laser test
        print('tweezer x start time:', t1)
        # Turn on the tweezer
        devices.tweezer_aom_digital.go_high(t)
        devices.tweezer_aom_analog.constant(
            t, shot_globals.tw_power)  # 0.3) #for single tweezer

    # the offset for the beging of output comparing to the trigger
    spectrum_card_offset = 52.8e-6
    spectrum_uwave_cable_atten = 4.4  # dB at 300 MHz
    spectrum_uwave_power = -1  # -3 # dBm
    uwave_clock = 9.192631770e3  # in unit of MHz
    local_oscillator_freq_mhz = 9486  # in unit of MHz MKU LO 8-13 PLL setting
    if shot_globals.do_mw_pulse or shot_globals.do_mw_sweep:
        devices.spectrum_uwave.set_mode(replay_mode=b'sequence',
                                        channels=[{'name': 'microwaves',
                                                   'power': spectrum_uwave_power + spectrum_uwave_cable_atten,
                                                   'port': 0,
                                                   'is_amplified': False,
                                                   'amplifier': None,
                                                   'calibration_power': 12,
                                                   'power_mode': 'constant_total',
                                                   'max_pulses': 1},
                                                  {'name': 'mmwaves',
                                                   'power': -11,
                                                   'port': 1,
                                                   'is_amplified': False,
                                                   'amplifier': None,
                                                   'calibration_power': 12,
                                                   'power_mode': 'constant_total',
                                                   'max_pulses': 1}],
                                        clock_freq=625,
                                        use_ext_clock=True,
                                        ext_clock_freq=10)

    if shot_globals.do_local_addr:
        devices.local_addr_1064_aom_analog.constant(
            t, 1)  # for aligning local addressing beams
        devices.local_addr_1064_aom_digital.go_high(t)
    else:
        devices.local_addr_1064_aom_analog.constant(
            t, 0)  # for aligning local addressing beams
        devices.local_addr_1064_aom_digital.go_low(t)

    if shot_globals.do_dipole_trap:
        turn_on_dipole_trap(t)
    else:
        turn_off_dipole_trap(t)

    # temproral for Nolan's alignment
    # devices.ipg_1064_aom_digital.go_high(t)
    # devices.ipg_1064_aom_analog.constant(t, 1)
    # devices.pulse_1064_analog.constant(t,1)
    # devices.pulse_1064_digital.go_high(t)
    # devices.moglabs_456_aom_analog.constant(t,1)
    # devices.moglabs_456_aom_digital.go_high(t)
    # devices.blue_456_shutter.open(t)
    # devices.octagon_456_aom_analog.constant(t,0.5)
    # devices.octagon_456_aom_digital.go_high(t)

    do_MOT(t, MOT_load_dur, shot_globals.do_mot_coil)
    t += MOT_load_dur  # how long MOT last

    # _, ta_last_detuning, repump_last_detuning = load_molasses(t, ta_bm_detuning, repump_bm_detuning)
    ta_last_detuning, repump_last_detuning = do_molasses(
        t, molasses_dur, close_shutter=True)
    t += molasses_dur
    # ta_last_detuning =  ta_bm_detuning
    # repump_last_detuning = repump_bm_detuning
    # devices.mot_xy_shutter.close(t)
    # devices.mot_z_shutter.close(t)

    t += 7e-3

    devices.tweezer_aom_analog.ramp(
        t,
        duration=10e-3,
        initial=shot_globals.tw_power,
        final=1,
        samplerate=4e5,
    )  # ramp back to full tweezer fpower for imaging

    if shot_globals.do_parity_projection_pulse:
        t, ta_last_detuning, repump_bm_detuning = parity_projection_pulse(
            t, shot_globals.bm_parity_projection_pulse_dur, ta_last_detuning, repump_last_detuning)

    ta_last_detuning, repump_last_detuning = do_molasses(
        t, molasses_dur, close_shutter=True, ta_last_detuning=ta_last_detuning, repump_last_detuning=repump_last_detuning)
    t += molasses_dur

    t, ta_last_detuning, repump_last_detuning = pre_imaging(
        t, ta_last_detuning, repump_last_detuning)

    if shot_globals.do_robust_loading_pulse:
        robust_loading_pulse(t, dur=shot_globals.bm_robust_loading_pulse_dur)
        t += shot_globals.bm_robust_loading_pulse_dur

    assert shot_globals.img_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter"
    t += shot_globals.img_tof_imaging_delay

    # first shot
    devices.digital_out_ch22.go_high(t)
    t, ta_last_detuning, repump_last_detuning = do_imaging(
        t, 1, ta_last_detuning, repump_last_detuning)
    devices.digital_out_ch22.go_low(t)
    # devices.digital_out_ch26.go_high(t) #for testing spectrum card output

    t += 7e-3  # make sure sutter fully closed after 1st imaging

    devices.digital_out_ch22.go_high(t)
    t, ta_last_detuning, repump_last_detuning = optical_pumping(
        t, ta_last_detuning, repump_last_detuning)
    devices.digital_out_ch22.go_low(t)
    devices.x_coil_current.constant(t, biasx_calib(
        shot_globals.mw_biasx_field))   # define quantization axis
    devices.y_coil_current.constant(t, biasy_calib(
        shot_globals.mw_biasy_field))   # define quantization axis
    devices.z_coil_current.constant(t, biasz_calib(
        shot_globals.mw_biasz_field))   # define quantization axis

    t += shot_globals.img_wait_time_between_shots

    if shot_globals.do_456nm_laser:
        blue_dur = shot_globals.blue_456nm_duration
        do_blue(t, blue_dur)
        t += blue_dur

    # ================================================================================
    # Spectrum card related for microwaves
    # ================================================================================
    if do_tw_power_ramp:
        t += devices.tweezer_aom_analog.ramp(
            t,
            duration=shot_globals.tw_ramp_dur,
            initial=1,
            final=shot_globals.tw_ramp_power,
            samplerate=4e5,
        )

    if shot_globals.do_mw_sweep:
        devices.uwave_absorp_switch.go_high(t)
        mw_sweep_duration = spectrum_microwave_sweep(t)
        devices.uwave_absorp_switch.go_low(t + mw_sweep_duration)
        t += mw_sweep_duration

    if shot_globals.do_mw_pulse:

        if do_tw_trap_off:  # turn traps off during microwave
            devices.tweezer_aom_digital.go_low(t)
        # elif do_tw_lower_trap_during_mw: #lower trap depth during microwave
        # devices.tweezer_aom_analog.constant(t - tweezer_aom_thermal_time,
        # 0.05)#0.15)

        t += spectrum_card_offset
        devices.uwave_absorp_switch.go_high(t)
        devices.spectrum_uwave.single_freq(
            t -
            spectrum_card_offset,
            duration=shot_globals.mw_time,
            freq=(
                local_oscillator_freq_mhz -
                uwave_clock -
                shot_globals.mw_detuning) *
            1e6,
            amplitude=0.99,
            phase=0,
            ch=0,
            loops=1)
        print(
            f'Spectrum card freq = {
                local_oscillator_freq_mhz -
                uwave_clock -
                shot_globals.mw_detuning}')
        devices.uwave_absorp_switch.go_low(t + shot_globals.mw_time)
        t += shot_globals.mw_time

        if do_tw_trap_off:  # turn traps back on
            devices.tweezer_aom_digital.go_high(t)
        # elif do_tw_lower_trap_during_mw: #turn trap back to full power
        #     devices.tweezer_aom_analog.constant(t,1)

    if do_tw_power_ramp:
        t += devices.tweezer_aom_analog.ramp(
            t,
            duration=shot_globals.tw_ramp_dur,
            initial=shot_globals.tw_ramp_power,
            final=1,
            samplerate=4e5,
        )
        # if shot_globals.tw_ramp_dur < 7e-3:
        #     t += 7e-3 - shot_globals.tw_ramp_dur
    else:
        devices.tweezer_aom_analog.constant(t, 1)
        t += 7e-3  # 10e-3 #for shutter to close and open after optical pump before killing pulse

    if shot_globals.do_killing_pulse:
        # for shutter and vco to be ready for killing pulse
        t += ta_vco_ramp_t + min_shutter_off_t

        # tw power ramp
        t += devices.tweezer_aom_analog.ramp(
            t,
            duration=shot_globals.tw_ramp_dur,
            initial=1,
            final=shot_globals.tw_power,
            samplerate=4e5,
        )

        devices.tweezer_aom_analog.constant(t, 0)
        devices.tweezer_aom_digital.go_low(t)
        # devices,tweezer_aom_analog.constant(t, 0.15)
        t, ta_last_detuning, repump_last_detuning = killing_pulse(
            t, ta_last_detuning, repump_last_detuning)

        devices.tweezer_aom_digital.go_high(t)
        devices.tweezer_aom_analog.constant(t, shot_globals.tw_power)
        t += 1e-3  # 10e-3

        # tw power ramp
        t += devices.tweezer_aom_analog.ramp(
            t,
            duration=shot_globals.tw_ramp_dur,
            initial=shot_globals.tw_power,
            final=1,
            samplerate=4e5,
        )

    else:
        t += 10e-3

    # for testing only
    # devices.tweezer_aom_digital.go_low(t)
    # devices.tweezer_aom_analog.constant(t,0)
    # t += shot_globals.op_killing_pulse_time
    # devices.tweezer_aom_digital.go_high(t)
    # devices.tweezer_aom_analog.constant(t,shot_globals.tw_power)
    # t += 10e-3
    # devices.tweezer_aom_analog.constant(t,1)

    # t += 10e-3

    # second shot
    t, ta_last_detuning, repump_last_detuning = pre_imaging(
        t, ta_last_detuning, repump_last_detuning)
    t += 10e-3

    # devices.digital_out_ch26.go_low(t) #for testing spectrum card output
    devices.digital_out_ch22.go_high(t)
    t, ta_last_detuning, repump_last_detuning = do_imaging(
        t, 2, ta_last_detuning, repump_last_detuning)
    devices.digital_out_ch22.go_low(t)

    t += 2e-2  # 1e-3, need to  change to longer before turn off the tweezer since need to be > 1 Notifiysize
    t = reset_mot(t, ta_last_detuning)
    # make sure tweezer AOM has full rf power
    if shot_globals.do_rearrange_position_check:
        devices.manta419b_tweezer.expose(
            'manta419b',
            t -
            shot_globals.TW_rearrangement_time_offset +
            shot_globals.TW_rearrangement_fine_time_offset,
            'atoms',
            exposure_time=50e-6,
        )

    if shot_globals.do_mw_pulse or shot_globals.do_mw_sweep:
        ##### dummy segment ######
        devices.spectrum_uwave.single_freq(
            t,
            duration=100e-6,
            freq=10**6,
            amplitude=0.99,
            phase=0,
            ch=0,
            loops=1)  # dummy segment
        devices.spectrum_uwave.stop()

    if shot_globals.do_tweezers:
        # stop tweezers
        # devices.tweezer_aom_digital.go_low(t)
        if spcm_sequence_mode:
            t2 = spectrum_manager.stop_tweezers(t)
            ##### dummy segment ######
            t1 = spectrum_manager.start_tweezers(t)
            print('tweezer start time:', t1)
            t += 2e-3
            t2 = spectrum_manager.stop_tweezers(t)
            print('tweezer stop time:', t2)
            #################
            spectrum_manager.stop_card(t)
        else:
            devices.digital_out_ch22.go_high(
                t - shot_globals.TW_rearrangement_time_offset)
            devices.digital_out_ch22.go_low(
                t - shot_globals.TW_rearrangement_time_offset + 1e-3)
            t2 = spectrum_manager_fifo.stop_tweezers(t)
            print('tweezer stop time:', t2)
            spectrum_manager_fifo.stop_tweezer_card()

    labscript.stop(t + 1e-2)
    return t


def do_optical_pump_in_microtrap_check():

    MOT_load_dur = 0.5  # 0.5
    molasses_dur = shot_globals.bm_time
    labscript.start()

    t = 0

    intensity_servo_keep_on(t)

    if spcm_sequence_mode:
        spectrum_manager.start_card()
        t1 = spectrum_manager.start_tweezers(t)
    else:
        spectrum_manager_fifo.start_tweezer_card()
        # has to be the first thing in the timing sequence (?)
        t1 = spectrum_manager_fifo.start_tweezers(t)
    devices.dds0.synthesize(
        t + 1e-3,
        freq=TW_y_freqs,
        amp=0.95,
        ph=0)  # unit: MHz
    # devices.dds1.synthesize(t+1e-3, freq = shot_globals.blue_456_detuning, amp = 0.95, ph = 0)
    print('tweezer x start time:', t1)
    # Turn on the tweezer
    if shot_globals.do_tweezers:
        devices.tweezer_aom_digital.go_high(t)
        devices.tweezer_aom_analog.constant(t, 1)  # 0.3) #for single tweezer
    else:
        devices.tweezer_aom_digital.go_low(t)
        devices.tweezer_aom_analog.constant(t, 0)  # 0.3) #for single tweezer

    if shot_globals.do_local_addr:
        devices.local_addr_1064_aom_analog.constant(
            t, 1)  # for aligning local addressing beams
        devices.local_addr_1064_aom_digital.go_high(t)
    else:
        devices.local_addr_1064_aom_analog.constant(
            t, 0)  # for aligning local addressing beams
        devices.local_addr_1064_aom_digital.go_low(t)

    # the offset for the beging of output comparing to the trigger
    spectrum_card_offset = 52.8e-6
    spectrum_uwave_cable_atten = 4.4  # dB at 300 MHz
    spectrum_uwave_power = -1  # -3 # dBm
    uwave_clock = 9.192631770e3  # in unit of MHz
    local_oscillator_freq_mhz = 9486  # in unit of MHz MKU LO 8-13 PLL setting
    if shot_globals.do_mw_pulse or shot_globals.do_mw_sweep:
        devices.spectrum_uwave.set_mode(replay_mode=b'sequence',
                                        channels=[{'name': 'microwaves',
                                                   'power': spectrum_uwave_power + spectrum_uwave_cable_atten,
                                                   'port': 0,
                                                   'is_amplified': False,
                                                   'amplifier': None,
                                                   'calibration_power': 12,
                                                   'power_mode': 'constant_total',
                                                   'max_pulses': 1},
                                                  {'name': 'mmwaves',
                                                   'power': -11,
                                                   'port': 1,
                                                   'is_amplified': False,
                                                   'amplifier': None,
                                                   'calibration_power': 12,
                                                   'power_mode': 'constant_total',
                                                   'max_pulses': 1}],
                                        clock_freq=625,
                                        use_ext_clock=True,
                                        ext_clock_freq=10)

    do_MOT(t, MOT_load_dur, shot_globals.do_mot_coil)
    t += MOT_load_dur  # how long MOT last

    ta_last_detuning, repump_last_detuning = do_molasses(
        t, molasses_dur, close_shutter=True)
    t += molasses_dur

    t += 7e-3
    t, ta_last_detuning, repump_last_detuning = optical_pumping(
        t, ta_last_detuning, repump_last_detuning)
    devices.x_coil_current.constant(t, biasx_calib(
        shot_globals.mw_biasx_field))   # define quantization axis
    devices.y_coil_current.constant(t, biasy_calib(
        shot_globals.mw_biasy_field))   # define quantization axis
    devices.z_coil_current.constant(t, biasz_calib(
        shot_globals.mw_biasz_field))   # define quantization axis
    # ================================================================================
    # Spectrum card related for microwaves
    # ================================================================================
    if do_local_addr_ramp:
        t += devices.local_addr_1064_aom_analog.ramp(
            t,
            duration=shot_globals.local_addr_ramp_dur,
            initial=1,
            final=shot_globals.local_addr_ramp_power,
            samplerate=4e5,
        )

    if shot_globals.do_mw_sweep:
        devices.uwave_absorp_switch.go_high(t)
        mw_sweep_duration = spectrum_microwave_sweep(t)
        devices.uwave_absorp_switch.go_low(t + mw_sweep_duration)
        t += mw_sweep_duration

    if shot_globals.do_mw_pulse:
        t += spectrum_card_offset
        devices.uwave_absorp_switch.go_high(t)
        devices.spectrum_uwave.single_freq(
            t -
            spectrum_card_offset,
            duration=shot_globals.mw_time,
            freq=(
                local_oscillator_freq_mhz -
                uwave_clock -
                shot_globals.mw_detuning) *
            1e6,
            amplitude=0.99,
            phase=0,
            ch=0,
            loops=1)
        print(
            f'Spectrum card freq = {
                local_oscillator_freq_mhz -
                uwave_clock -
                shot_globals.mw_detuning}')
        devices.uwave_absorp_switch.go_low(t + shot_globals.mw_time)
        t += shot_globals.mw_time
    else:
        # 10e-3 #for shutter to close and open after optical pump before
        # killing pulse
        t += shot_globals.mw_time

    if do_local_addr_ramp:
        t += devices.local_addr_1064_aom_analog.ramp(
            t,
            duration=shot_globals.local_addr_ramp_dur,
            initial=shot_globals.local_addr_ramp_power,
            final=1,
            samplerate=4e5,
        )

    if shot_globals.do_killing_pulse:
        # tw power ramp
        t += devices.local_addr_1064_aom_analog.ramp(
            t,
            duration=shot_globals.local_addr_ramp_dur,
            initial=1,
            final=shot_globals.local_addr_ramp_power,
            samplerate=4e5,
        )

        # for shutter and vco to be ready for killing pulse
        t += ta_vco_ramp_t + min_shutter_off_t
        t, ta_last_detuning, repump_last_detuning = killing_pulse(
            t, ta_last_detuning, repump_last_detuning)
        # t += 1e-3

        t += devices.local_addr_1064_aom_analog.ramp(
            t,
            duration=shot_globals.local_addr_ramp_dur,
            initial=shot_globals.local_addr_ramp_power,
            final=1,
            samplerate=4e5,
        )
    else:
        t += 10e-3

    t, ta_last_detuning, repump_last_detuning = pre_imaging(
        t, ta_last_detuning, repump_last_detuning)

    assert shot_globals.img_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter"
    t += shot_globals.img_tof_imaging_delay

    # first shot
    t, ta_last_detuning, repump_last_detuning = do_imaging(
        t, 1, ta_last_detuning, repump_last_detuning)

    t += 7e-3  # make sure sutter fully closed after 1st imaging

    t += shot_globals.img_wait_time_between_shots

    # second shot
    t, ta_last_detuning, repump_last_detuning = pre_imaging(
        t, ta_last_detuning, repump_last_detuning)
    t += 10e-3

    # devices.digital_out_ch26.go_low(t) #for testing spectrum card output
    t, ta_last_detuning, repump_last_detuning = do_imaging(
        t, 2, ta_last_detuning, repump_last_detuning)
    t += 2e-2  # 1e-3, need to  change to longer before turn off the tweezer since need to be > 1 Notifiysize
    t = reset_mot(t, ta_last_detuning)
    # make sure tweezer AOM has full rf power
    if shot_globals.do_rearrange_position_check:
        devices.manta419b_tweezer.expose(
            'manta419b',
            t -
            shot_globals.TW_rearrangement_time_offset +
            shot_globals.TW_rearrangement_fine_time_offset,
            'atoms',
            exposure_time=50e-6,
        )

    # if shot_globals.do_mw_pulse or shot_globals.do_mw_sweep:
    #     ##### dummy segment ####
    devices.spectrum_uwave.single_freq(
        t,
        duration=100e-6,
        freq=10**6,
        amplitude=0.99,
        phase=0,
        ch=0,
        loops=1)  # dummy segment
    devices.spectrum_uwave.stop()

    if spcm_sequence_mode:
        t2 = spectrum_manager.stop_tweezers(t)
        ##### dummy segment ######
        t1 = spectrum_manager.start_tweezers(t)
        print('tweezer start time:', t1)
        t += 2e-3
        t2 = spectrum_manager.stop_tweezers(t)
        print('tweezer stop time:', t2)
        #################
        spectrum_manager.stop_card(t)
    else:
        t2 = spectrum_manager_fifo.stop_tweezers(t)
        spectrum_manager_fifo.stop_tweezer_card()
    print('tweezer stop time:', t2)

    if shot_globals.do_tweezers:
        # stop tweezers
        devices.tweezer_aom_digital.go_low(t)
    if shot_globals.do_local_addr:
        # stop tweezers
        devices.local_addr_1064_aom_digital.go_low(t)

    labscript.stop(t + 1e-2)
    return t


if __name__ == "__main__":
    # TODO: Can labscript.start() and t = 0 statements be moved here?
    if shot_globals.do_mot_in_situ_check:
        do_mot_in_situ_check()

    if shot_globals.do_mot_tof_check:
        do_mot_tof_check()

    if shot_globals.do_molasses_in_situ_check:
        do_molasses_in_situ_check()

    if shot_globals.do_molasses_tof_check:
        do_molasses_tof_check()

    if shot_globals.do_field_calib_in_molasses_check:
        do_field_calib_in_molasses_check()

    if shot_globals.do_dipole_trap_tof_check:
        do_dipole_trap_tof_check()

    if shot_globals.do_img_beam_alignment_check:
        do_img_beam_alignment_check()

    if shot_globals.do_tweezer_position_check:
        do_tweezer_position_check()

    if shot_globals.do_tweezer_check:
        do_tweezer_check()

    if shot_globals.do_tweezer_check_fifo:
        do_tweezer_check_fifo()

    if shot_globals.do_optical_pump_in_tweezer_check:
        do_optical_pump_in_tweezer_check()

    if shot_globals.do_optical_pump_in_microtrap_check:
        do_optical_pump_in_microtrap_check()
