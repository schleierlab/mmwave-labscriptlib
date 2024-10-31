# -*- coding: utf-8 -*-
"""
Created on Sep 20th 2024

@author: sslab
"""

import sys
root_path = r"X:\userlib\labscriptlib"
function_path = r"X:\userlib\labscriptlib\new_tweezer_loading_seq_test"

if root_path not in sys.path:
    sys.path.append(root_path)
if function_path not in sys.path:
    sys.path.append(function_path)

import labscript

from connection_table import devices
from calibration import ta_freq_calib, repump_freq_calib, biasx_calib, biasy_calib, biasz_calib
from spectrum_manager import spectrum_manager
from spectrum_manager_fifo import spectrum_manager_fifo
from labscriptlib.shot_globals import shot_globals
import new_tweezer_loading_seq_test as functions
import numpy as np

spcm_sequence_mode = shot_globals.do_sequence_mode

if __name__ == "__main__":
    devices.initialize()

## fixed parameters in the script
coil_off_time = 1.4e-3 # minimum time for the MOT coil to be off
ta_vco_ramp_t = 1.2e-4
min_shutter_off_t = 6.28e-3  # minimum time for shutter to be off and on again
mot_detuning = shot_globals.mot_ta_detuning  # -13 # MHz, optimized based on atom number
ta_bm_detuning = shot_globals.bm_ta_detuning  # -100 # MHz, bright molasses detuning
repump_bm_detuning = shot_globals.bm_repump_detuning  # 0 # MHz, bright molasses detuning

def rydberg_pulse_with_repump(t): #turn analog on at all time and only pulse the digital
    if shot_globals.do_tw_trap_off:# turn traps off during rydberg excitation
        devices.tweezer_aom_digital.go_low(t)

    if shot_globals.do_456nm_laser:
        devices.moglabs_456_aom_digital.go_high(t)
        devices.octagon_456_aom_digital.go_high(t)
        # devices.ipg_1064_aom_digital.go_high(t)

        devices.repump_aom_digital.go_high(t)
        devices.repump_aom_analog.constant(t-10e-6, shot_globals.ryd_456_repump_power)


        t += shot_globals.blue_456nm_duration # 456 nm AOM raise time is 500 ns

        devices.repump_aom_digital.go_low(t)

        devices.moglabs_456_aom_digital.go_low(t)
        # devices.ipg_1064_aom_digital.go_low(t)
    else:
        t += shot_globals.blue_456nm_duration # no rydberg beams but still wait for the same time as the ryd pulse time

    if shot_globals.do_tw_trap_off:# turn traps back on
        devices.tweezer_aom_digital.go_high(t)
    return t

if __name__ == "__main__":
    MOT_load_dur = 0.5
    molasses_dur = shot_globals.bm_time
    labscript.start()

    t = 0

    assert shot_globals.do_sequence_mode, "shot_globals.do_sequence_mode is False, running Fifo mode now. Set to True for sequence mode"

    if shot_globals.do_tweezers:
        print("Initializing tweezers")
        devices.dds0.synthesize(t+1e-2, shot_globals.TW_y_freqs, 0.95, 0)
        spectrum_manager.start_card()
        t1 = spectrum_manager.start_tweezers(t) # has to be the first thing in the timing sequence (?)
        print('tweezer start time:',t1)
        # Turn on the tweezer
        devices.tweezer_aom_digital.go_high(t)
        # devices.tweezer_aom_analog.constant(t, 1) #0.3) #for single tweezer
        devices.tweezer_aom_analog.constant(t, shot_globals.tw_power) #0.3) #for single tweezer

    if shot_globals.do_dipole_trap:
        functions.turn_on_dipole_trap(t)
    else:
        functions.turn_off_dipole_trap(t)

    devices.dds1.synthesize(t+1e-3, freq = shot_globals.blue_456_detuning, amp = 0.5, ph = 0) # set the correct frequency for 456 nm laser
    devices.mirror_1_horizontal.constant(t, 0)
    devices.mirror_1_vertical.constant(t, 5)
    devices.mirror_2_horizontal.constant(t, 5)
    devices.mirror_2_vertical.constant(t, 5)


    #--------------------------------------------------------------------------------------------------------------
    #Loading Tweezers

    # devices.dispenser_off_trigger.go_high(t)
    functions.do_MOT(t, MOT_load_dur, shot_globals.do_mot_coil)
    t += MOT_load_dur # how long MOT last


    ta_last_detuning, repump_last_detuning = functions.do_molasses(
        t,
        molasses_dur,
        close_shutter = True)

    t += molasses_dur

    t += 7e-3

    devices.tweezer_aom_analog.ramp(
        t,
        duration=10e-3,
        initial=shot_globals.tw_power,
        final=1,
        samplerate=4e5,
        )  # ramp back to full tweezer power

    if shot_globals.do_parity_projection_pulse:
        t, ta_last_detuning, repump_bm_detuning = functions.parity_projection_pulse(
            t,
            shot_globals.bm_parity_projection_pulse_dur,
            ta_last_detuning,
            repump_last_detuning)


    ta_last_detuning, repump_last_detuning = functions.do_molasses(
        t,
        molasses_dur,
        close_shutter = True,
        ta_last_detuning=ta_last_detuning,
        repump_last_detuning= repump_last_detuning)
    t += molasses_dur


    t, ta_last_detuning, repump_last_detuning = functions.pre_imaging(
        t,
        ta_last_detuning,
        repump_last_detuning)


    if shot_globals.do_robust_loading_pulse:
        functions.robust_loading_pulse(
            t,
            dur = shot_globals.bm_robust_loading_pulse_dur)
        t += shot_globals.bm_robust_loading_pulse_dur

    assert shot_globals.img_tof_imaging_delay > min_shutter_off_t, "time of flight too short for shutter'"
    t += shot_globals.img_tof_imaging_delay

    # first shot
    devices.digital_out_ch22.go_high(t)
    t, ta_last_detuning, repump_last_detuning= functions.do_imaging(
        t,
        1,
        ta_last_detuning,
        repump_last_detuning)
    devices.digital_out_ch22.go_low(t)
    t += 7e-3 # make sure shutter fully closed after 1st imaging


    #--------------------------------------------------------------------------------------------------------------
    # Rydberg Pulses

    t, ta_last_detuning, repump_last_detuning = functions.optical_pumping(
        t,
        ta_last_detuning,
        repump_last_detuning,
        next_step ='rydberg')

    devices.moglabs_456_aom_analog.constant(t, blue_456nm_power)
    devices.octagon_456_aom_analog.constant(t, 1)

    t += 10e-3 # wait for shutter to close and then open
    if shot_globals.do_456nm_laser:
        devices.blue_456_shutter.open(t)
        devices.octagon_456_aom_digital.go_high(t-3e-3)
        if shot_globals.do_rydberg_pulse_with_repump:
            devices.optical_pump_shutter.open(t)
            devices.repump_shutter.open(t)
        devices.moglabs_456_aom_digital.go_low(t-3e-3) # turn off before shutter entirely open
        if not(shot_globals.do_rydberg_pulse_with_repump):
            devices.ipg_1064_aom_digital.go_high(t-100e-6)

    t+=1e-6
    for i in range(shot_globals.num_pulses):
        print('tp = ', t)
        if shot_globals.do_rydberg_pulse_with_repump:
            t = rydberg_pulse_with_repump(t)
        # else:
        #     t = rydberg_pulse(t)
        t += shot_globals.time_between_pulses

    t += 2e-3

    if shot_globals.do_456nm_laser:
        devices.blue_456_shutter.close(t)
        devices.optical_pump_shutter.close(t)
        devices.repump_shutter.close(t)
        devices.moglabs_456_aom_digital.go_high(t+3e-3)
        devices.ipg_1064_aom_digital.go_low(t)

    t += 3e-3

    devices.moglabs_456_aom_analog.constant(t, 0)
    devices.octagon_456_aom_analog.constant(t, 0)

    #--------------------------------------------------------------------------------------------------------------
    # Second Image

    t += shot_globals.img_wait_time_between_shots


    # second shot
    t, ta_last_detuning, repump_last_detuning = functions.pre_imaging(
        t,
        ta_last_detuning,
        repump_last_detuning)
    t += 10e-3 #100e-3
    devices.digital_out_ch22.go_high(t)
    t, ta_last_detuning, repump_last_detuning = functions.do_imaging(
        t,
        2,
        ta_last_detuning,
        repump_last_detuning)
    devices.digital_out_ch22.go_low(t)

    t += 1e-2
    t = functions.reset_mot(t, ta_last_detuning)
    # make sure tweezer AOM has full rf power
    if shot_globals.do_tweezers:
        # stop tweezers
        t2 = spectrum_manager.stop_tweezers(t)
        print('tweezer stop time:', t2)
        #t += 1e-3

        ##### dummy segment ######
        t1 = spectrum_manager.start_tweezers(t)
        print('tweezer start time:', t1)
        t += 2e-3
        t2 = spectrum_manager.stop_tweezers(t)
        print('tweezer stop time:',t2)
        #t += 1e-3################
        spectrum_manager.stop_card(t)

    test = (1,2)
    a,b = test
    a = 10
    print(test)

    labscript.stop(t + 1e-2)
