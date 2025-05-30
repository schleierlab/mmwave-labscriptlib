from __future__ import annotations

import labscript

from labscriptlib.connection_table import devices
from labscriptlib.shot_globals import shot_globals
from labscriptlib.standard_operations import (
    MOTOperations, OpticalPumpingOperations, RydbergOperations, TweezerOperations
)


if __name__ == "__main__":
    devices.initialize()
    labscript.start()
    t = 0
    sequence_objects = []
    # Insert "stay on" statements for alignment here...

    if shot_globals.do_test_analog_in:
        duration = devices.test_analog_in.acquire('test_analog_in', t+1e-3, t+2e-3)
        print("Duration was:", duration)
        t += 2e-3

    if shot_globals.do_mot_in_situ_check:
        MOTSeq_obj = MOTOperations(t)
        sequence_objects.append(MOTSeq_obj)
        t = MOTSeq_obj._do_mot_in_situ_sequence(t, reset_mot=True)

    elif shot_globals.do_molasses_in_situ_check:
        if shot_globals.do_molasses_in_situ_check and shot_globals.imaging_beam_choice() != 'mot':
            raise ValueError

        MOTSeq_obj = MOTOperations(t)
        sequence_objects.append(MOTSeq_obj)
        t = MOTSeq_obj._do_molasses_in_situ_sequence(t, reset_mot=True)

    elif shot_globals.do_molasses_tof_check:
        MOTSeq_obj = MOTOperations(t)
        sequence_objects.append(MOTSeq_obj)
        t = MOTSeq_obj._do_molasses_tof_sequence(t, reset_mot=True)

    elif shot_globals.do_optical_pump_in_molasses_check:
        OPSeq_obj = OpticalPumpingOperations(t)
        sequence_objects.append(OPSeq_obj)
        t = OPSeq_obj._do_optical_pump_in_molasses_sequence(t, reset_mot=True)

    elif shot_globals.do_pump_debug_in_molasses:
        OPSeq_obj = OpticalPumpingOperations(t)
        sequence_objects.append(OPSeq_obj)
        t = OPSeq_obj._do_pump_debug_in_molasses(t, reset_mot=True)

    elif shot_globals.do_F4_microwave_spec_molasses:
        OPSeq_obj = OpticalPumpingOperations(t)
        sequence_objects.append(OPSeq_obj)
        t = OPSeq_obj._do_F4_microwave_spec_molasses(t, reset_mot=True)

    elif shot_globals.do_tweezer_check:
        TweezerSequence_obj = TweezerOperations(t)
        sequence_objects.append(TweezerSequence_obj)
        t = TweezerSequence_obj._do_tweezer_check(t)

    elif shot_globals.do_tweezer_position_check:
        TweezerSequence_obj = TweezerOperations(t)
        sequence_objects.append(TweezerSequence_obj)
        t = TweezerSequence_obj._do_tweezer_position_check_sequence(t, check_with_vimba=False)

    elif shot_globals.do_F4_microwave_spec_dipole_trap or shot_globals.do_dipole_trap_B_calib:
        RydSequence_obj = RydbergOperations(t)
        sequence_objects.append(RydSequence_obj)
        t = RydSequence_obj._do_dipole_trap_F4_spec(t)

    elif shot_globals.do_dipole_trap_dark_state_measurement:
        RydSequence_obj = RydbergOperations(t)
        sequence_objects.append(RydSequence_obj)
        t = RydSequence_obj._do_dipole_trap_dark_state_measurement(t)

    elif shot_globals.do_ryd_tweezer_check:
        RydSequence_obj = RydbergOperations(t)
        sequence_objects.append(RydSequence_obj)
        t = RydSequence_obj._do_ryd_tweezer_check_sequence(t)

    elif shot_globals.do_ryd_multipulse_check:
        RydSequence_obj = RydbergOperations(t)
        sequence_objects.append(RydSequence_obj)
        t = RydSequence_obj._do_ryd_multipulse_check_sequence(t)

    elif shot_globals.do_456_check:
        RydSequence_obj = RydbergOperations(t)
        sequence_objects.append(RydSequence_obj)
        t = RydSequence_obj._do_456_check_sequence(t)

    elif shot_globals.do_dipole_trap_check:
        RydSequence_obj = RydbergOperations(t)
        sequence_objects.append(RydSequence_obj)
        t = RydSequence_obj._do_dipole_trap_sequence(t)

    elif shot_globals.do_dipole_trap_state_sensitive_img_check:
        RydSequence_obj = RydbergOperations(t)
        sequence_objects.append(RydSequence_obj)
        t = RydSequence_obj._do_dipole_trap_state_sensitive_img_check(t)

    elif shot_globals.do_optical_pump_in_tweezer_check:
        TweezerSequence_obj = TweezerOperations(t)
        sequence_objects.append(TweezerSequence_obj)
        if shot_globals.op_label == "mot":
            t = TweezerSequence_obj._do_optical_pump_mot_in_tweezer_check(t)
        elif shot_globals.op_label == "sigma":
            t = TweezerSequence_obj._do_optical_pump_sigma_in_tweezer_check(t)

    elif shot_globals.do_dark_state_lifetime_in_tweezer_check:
        TweezerSequence_obj = TweezerOperations(t)
        sequence_objects.append(TweezerSequence_obj)
        if shot_globals.op_label == "sigma":
            t = TweezerSequence_obj._do_dark_state_lifetime_in_tweezer_check(t)
        else:
            raise NotImplementedError

    elif shot_globals.do_456_with_dark_state_check:
        RydSequence_obj = RydbergOperations(t)
        sequence_objects.append(RydSequence_obj)
        if shot_globals.op_label == "sigma":
            t = RydSequence_obj._do_456_with_dark_state_sequence(t)
        else:
            raise NotImplementedError

    elif shot_globals.do_456_light_shift_check:
        RydSequence_obj = RydbergOperations(t)
        sequence_objects.append(RydSequence_obj)
        if shot_globals.op_label == "sigma":
            t = RydSequence_obj._do_456_light_shift_check_sequence(t)
        else:
            raise NotImplementedError

    elif shot_globals.do_1064_light_shift_check:
        RydSequence_obj = RydbergOperations(t)
        sequence_objects.append(RydSequence_obj)
        t = RydSequence_obj._do_1064_light_shift_check_sequence(t)

    """ Here doing all the finish up quirk for spectrum cards """
    # Find the first non-None sequence object
    current_obj = next((obj for obj in sequence_objects if obj is not None), None)

    if current_obj is None:
        print("Warning: No valid sequence object found")

    # Stop tweezers if the object has a TweezerLaser_obj
    if hasattr(current_obj, 'TweezerLaser_obj'):
        print("current_obj has TweezerLaser_obj")
        t = current_obj.TweezerLaser_obj.stop_tweezers(t)

    # Reset spectrum if the object has Microwave_obj and if we use microwave in the sequence
    do_mw = shot_globals.do_mw_pulse or shot_globals.do_mw_sweep
    for obj in sequence_objects:
        if obj is not None and hasattr(obj, 'Microwave_obj') and do_mw:
            t = obj.Microwave_obj.reset_spectrum(t)

    labscript.stop(t + 1e-2)
