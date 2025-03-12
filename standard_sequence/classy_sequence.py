from __future__ import annotations

import labscript
import numpy as np
from labscriptlib.shot_globals import shot_globals
from labscriptlib.standard_sequence.experiment_components import (
    PointingConfig,
    RydLasers,
    ShutterConfig,
)

from labscriptlib.connection_table import devices
from labscriptlib.standard_sequence.mot import MOTSequence
from labscriptlib.standard_sequence.optical_pumping import OpticalPumpingSequence
from labscriptlib.standard_sequence.tweezers import TweezerSequence


# TODO is this necessary?
if __name__ == "__main__":
    devices.initialize()



# Sequence Classes
# -------------------------------------------------------------------------------

class RydSequence(TweezerSequence):
    def __init__(self, t):
        super(RydSequence, self).__init__(t)
        blue_pointing = PointingConfig(
            shot_globals.ryd_456_mirror_1_h,
            shot_globals.ryd_456_mirror_1_v,
            shot_globals.ryd_456_mirror_2_h,
            shot_globals.ryd_456_mirror_2_v,
        )
        ir_pointing = PointingConfig(
            shot_globals.ryd_1064_mirror_1_h,
            shot_globals.ryd_1064_mirror_1_v,
            shot_globals.ryd_1064_mirror_2_h,
            shot_globals.ryd_1064_mirror_2_v,
        )
        self.RydLasers_obj = RydLasers(
            t, blue_pointing, ir_pointing, init_blue_detuning=shot_globals.ryd_456_detuning
        )

    def pulsed_rydberg_excitation(self, t, n_pulses, pulse_dur, pulse_wait_dur, power_456, power_1064, just_456=False, close_shutter=False):
        print('multipulse start time t = ', t)

        t, pulse_times = self.RydLasers_obj.do_rydberg_multipulses(
            t, n_pulses, pulse_dur, pulse_wait_dur,
            power_456, power_1064,
            just_456=just_456, close_shutter=close_shutter
            )

        print('multipulse end time t = ',t)

        #offset tweezer pulse times to match Rydberg pulse times; empirically determined workaround
        pulse_times_anticipated = np.asarray(pulse_times) - 0.3e-6
        for pulse_time in pulse_times_anticipated:
            self.TweezerLaser_obj.aom_off(pulse_time, digital_only=True)
            self.TweezerLaser_obj.aom_on(pulse_time + pulse_dur, 0.99, digital_only=True)

        return t

    def _do_dipole_trap_sequence(self, t):

        t = self.do_mot(t, dur=0.5)
        if shot_globals.do_dipole_trap:
            self.RydLasers_obj.pulse_1064_aom_on(0.1, 1)
        else:
            self.RydLasers_obj.pulse_1064_aom_off(0.1)
        if not shot_globals.do_tweezers:
            self.TweezerLaser_obj.aom_off(0.1)
        t = self.do_molasses(t, dur=shot_globals.bm_time, close_all_shutters=True)

        t += 1e-3
        if shot_globals.do_blue_kill:
            #Apply repump pulse
            t, t_aom_start = self.D2Lasers_obj.do_pulse(
                t,
                shot_globals.ryd_456_duration,
                ShutterConfig.OPTICAL_PUMPING_REPUMP,
                0,
                shot_globals.ryd_456_repump_power,
                close_all_shutters=True,
            )
            t = self.RydLasers_obj.do_456_pulse(
                t_aom_start, # synchronize with repump pulse
                dur=shot_globals.ryd_456_duration,
                power_456=shot_globals.ryd_456_power,
                close_shutter=True  # Close shutter after pulse to prevent any residual light
            )
        elif shot_globals.do_ryd_2_photon:
            t = self.RydLasers_obj.do_456_pulse(
                t,
                dur=shot_globals.ryd_456_duration,
                power_456=shot_globals.ryd_456_power,
                close_shutter=False  # Close shutter after pulse to prevent any residual light
            )
        else:
            t += shot_globals.ryd_456_duration

        t += shot_globals.dp_img_tof_imaging_delay
        t = self.do_molasses_dipole_trap_imaging(
            t,
            ta_power = shot_globals.dp_img_ta_power,
            ta_detuning = shot_globals.dp_img_ta_detuning,
            repump_power = shot_globals.dp_img_repump_power,
            do_repump=True,
            exposure_time=shot_globals.dp_img_exposure_time,
            close_all_shutters=True,
        )

        self.RydLasers_obj.pulse_1064_aom_off(t)

        t += 100e-3

        # Background image
        t = self.do_molasses_dipole_trap_imaging(
            t,
            ta_power=shot_globals.dp_img_ta_power,
            ta_detuning = shot_globals.dp_img_ta_detuning,
            repump_power=shot_globals.dp_img_repump_power,
            do_repump=True,
            exposure_time=shot_globals.dp_img_exposure_time,
            close_all_shutters=True,
        )
        t = self.reset_mot(t)

        return t

    def _do_dipole_trap_F4_spec(self, t):

        t = self.do_mot(t, dur=0.5)
        if shot_globals.do_dipole_trap:
            self.RydLasers_obj.pulse_1064_aom_on(0.1, 1)
        else:
            self.RydLasers_obj.pulse_1064_aom_off(0.1)
        if not shot_globals.do_tweezers:
            self.TweezerLaser_obj.aom_off(0.1)
        t = self.do_molasses(t, dur=shot_globals.bm_time, close_all_shutters=True)

        t += 1e-3

        t, t_aom_off = self.pump_to_F4(
            t, shot_globals.op_label, close_all_shutters=False,
        )

        if shot_globals.do_dipole_trap_B_calib:
            t = self.BField_obj.ramp_bias_field(
                    t_aom_off + 200e-6, #TODO: wait for 200e-6s extra time in optical pumping field, can be changed
                    voltage_vector=(shot_globals.mw_y_coil_voltage,
                                    shot_globals.mw_y_coil_voltage,
                                    shot_globals.mw_z_coil_voltage),
                    polar = False
                )
        else:
            t = self.BField_obj.ramp_bias_field(
                t_aom_off + 200e-6, #TODO: wait for 200e-6s extra time in optical pumping field, can be changed
                bias_field_vector=(shot_globals.mw_bias_amp,
                                   shot_globals.mw_bias_phi,
                                   shot_globals.mw_bias_theta),
                polar = True
            )


        t += shot_globals.mw_field_wait_dur
        if shot_globals.drop_dp_during_mw:
            self.RydLasers_obj.pulse_1064_aom_off(t)


        if shot_globals.do_mw_pulse:
            t = self.Microwave_obj.do_pulse(t, shot_globals.mw_time)
        elif shot_globals.do_mw_sweep:
            mw_sweep_start = shot_globals.mw_detuning + shot_globals.mw_sweep_range / 2
            mw_sweep_end = shot_globals.mw_detuning - shot_globals.mw_sweep_range / 2
            t = self.Microwave_obj.do_sweep(
                t, mw_sweep_start, mw_sweep_end, shot_globals.mw_sweep_duration
            )

        t+=10e-6

        if shot_globals.drop_dp_during_mw:
            self.RydLasers_obj.pulse_1064_aom_on(t, 1)


        t += 3e-6 #TODO: wait for extra time before killing, can be changed
        if shot_globals.do_killing_pulse:
            t, _ = self.kill_F4(t, close_all_shutters=True)
        # This is the only place required for the special value of imaging
        # t += 1e-3 # TODO: from the photodetector, the optical pumping beam shutter seems to be closing slower than others
        # that's why we add extra time here before imaging to prevent light leakage from optical pump beam

        t += shot_globals.dp_img_tof_imaging_delay
        t = self.do_molasses_dipole_trap_imaging(
            t,
            ta_power = shot_globals.dp_img_ta_power,
            ta_detuning = shot_globals.dp_img_ta_detuning,
            repump_power = shot_globals.dp_img_repump_power,
            do_repump=True,
            exposure_time=shot_globals.dp_img_exposure_time,
            close_all_shutters=True,
        )

        self.RydLasers_obj.pulse_1064_aom_off(t)

        t += 100e-3

        # Background image
        t = self.do_molasses_dipole_trap_imaging(
            t,
            ta_power=shot_globals.dp_img_ta_power,
            ta_detuning = shot_globals.dp_img_ta_detuning,
            repump_power=shot_globals.dp_img_repump_power,
            do_repump=True,
            exposure_time=shot_globals.dp_img_exposure_time,
            close_all_shutters=True,
        )
        t = self.reset_mot(t)

        return t

    def _do_ryd_check_sequence(self, t):
        """Perform a Rydberg excitation check sequence.

        Executes a sequence to verify Rydberg excitation:
        1. Load atoms into tweezers
        2. Take first image
        3. Apply Rydberg excitation pulse
        4. Take second image to check for atom loss
        5. Reset MOT parameters

        Args:
            t (float): Start time for the sequence

        Returns:
            float: End time of the sequence
        """
        t = self.load_tweezers(t)
        t = self.image_tweezers(t, shot_number=1)

        t += 1e-3

        t = self.pump_then_rotate(
            t,
            (shot_globals.ryd_bias_amp,
             shot_globals.ryd_bias_phi,
             shot_globals.ryd_bias_theta),
             polar=True) # trap is lowered when optical pump happens

        t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99) # ramp trap power back
        # Apply Rydberg pulse with both 456 and 1064 active

        t, _ = self.RydLasers_obj.do_rydberg_pulse(
            t,
            dur=shot_globals.ryd_456_duration,
            power_456=shot_globals.ryd_456_power,
            power_1064=shot_globals.ryd_1064_power,
            close_shutter=True  # Close shutter after pulse to prevent any residual light
        )

        # t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99)
        t += 2e-3  # TODO: from the photodetector, the optical pumping beam shutter seems to be closing slower than others
        # that's why we add extra time here before imaging to prevent light leakage from optical pump beam
        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
        t = self.reset_mot(t)

        return t

    def _do_ryd_check_trap_off_sequence(self,t):
        """Perform a Rydberg excitation check sequence.

        Executes a sequence to verify Rydberg excitation:
        1. Load atoms into tweezers
        2. Take first image
        3. Apply Rydberg excitation pulse
        4. Take second image to check for atom loss
        5. Reset MOT parameters

        Args:
            t (float): Start time for the sequence

        Returns:
            float: End time of the sequence
        """
        t = self.load_tweezers(t)
        t = self.image_tweezers(t, shot_number=1)

        t += 1e-3


        t = self.pump_then_rotate(
            t,
            (shot_globals.ryd_bias_amp,
             shot_globals.ryd_bias_phi,
             shot_globals.ryd_bias_theta),
             polar=True) # trap is lowered when optical pump happens

        E_field_voltage = [shot_globals.ryd_Efield_Vx,
                           shot_globals.ryd_Efield_Vy,
                           shot_globals.ryd_Efield_Vz,]

        self.EField_obj.set_electric_field(t, E_field_voltage)

        # t += 100e-6
        t += shot_globals.ryd_Bfield_stabilize_wait_time
        # Apply Rydberg pulse with both 456 and 1064 active

        t, pulse_time = self.RydLasers_obj.do_rydberg_pulse_short(
            t,
            shot_globals.ryd_pulse_dur,
            power_456 = shot_globals.ryd_456_power,
            power_1064 = shot_globals.ryd_1064_power,
            close_shutter=True)

        # turn off tweezer laser during the Rydberg pulse
        tweezer_switch_buffer = 2e-6
        pulse_time = np.array([pulse_time[0] - tweezer_switch_buffer, pulse_time[1] + tweezer_switch_buffer]) - 0.3e-6
        self.TweezerLaser_obj.aom_off(pulse_time[0], digital_only=True)
        self.TweezerLaser_obj.aom_on(pulse_time[1], 0.99, digital_only=False)
        print(pulse_time)
        # self.TweezerLaser_obj.aom_on(pulse_time[1], shot_globals.tw_ramp_power, digital_only=True)
        # self.TweezerLaser_obj.ramp_power(pulse_time[1], shot_globals.tw_ramp_dur, 0.99)

        zero_E_field_voltage = [shot_globals.zero_Efield_Vx,
                                shot_globals.zero_Efield_Vy,
                                shot_globals.zero_Efield_Vz,]
        self.EField_obj.set_electric_field(t, zero_E_field_voltage) # turn E field back to zero field

        # t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99)
        t += 2e-3  # TODO: from the photodetector, the optical pumping beam shutter seems to be closing slower than others
        # that's why we add extra time here before imaging to prevent light leakage from optical pump beam
        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
        t = self.reset_mot(t)

        return t

    def _do_ryd_multipulse_check_sequence(self, t):
        """Perform a Rydberg pulse excitation check sequence.

        Executes a sequence to verify Rydberg excitation:
        1. Load atoms into tweezers
        2. Take first image
        3. Apply Rydberg excitation multipulses
        4. Take second image to check for atom loss
        5. Reset MOT parameters

        Args:
            t (float): Start time for the sequence

        Returns:
            float: End time of the sequence
        """
        t = self.load_tweezers(t)
        t = self.image_tweezers(t, shot_number=1)

        t += 1e-3

        t = self.pump_then_rotate(
            t,
            (shot_globals.ryd_bias_amp,
             shot_globals.ryd_bias_phi,
             shot_globals.ryd_bias_theta),
             polar=True) # trap is lowered when optical pump happens

        t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99) # ramp trap power back
        t += 100e-6
        # Apply Rydberg pulse with both 456 and 1064 active
        t = self.pulsed_rydberg_excitation(
            t, n_pulses = shot_globals.ryd_n_pulses,
            pulse_dur = shot_globals.ryd_pulse_dur, pulse_wait_dur = shot_globals.ryd_pulse_wait_dur,
            power_456 = shot_globals.ryd_456_power, power_1064 = shot_globals.ryd_1064_power,
            just_456=True, close_shutter=True)

        # t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99)
        t += 2e-3  # TODO: from the photodetector, the optical pumping beam shutter seems to be closing slower than others
        # that's why we add extra time here before imaging to prevent light leakage from optical pump beam
        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
        t = self.reset_mot(t)

        return t

    def _do_456_check_sequence(self, t):
        """Perform a Rydberg excitation check sequence.

        Executes a sequence to verify Rydberg excitation:
        1. Load atoms into tweezers
        2. Take first image
        3. Apply Rydberg excitation pulse
        4. Take second image to check for atom loss
        5. Reset MOT parameters

        Args:
            t (float): Start time for the sequence

        Returns:
            float: End time of the sequence
        """
        t = self.load_tweezers(t)
        t = self.image_tweezers(t, shot_number=1)

        # Apply repump pulse
        t, t_aom_start = self.D2Lasers_obj.do_pulse(
            t,
            shot_globals.ryd_456_duration,
            ShutterConfig.OPTICAL_PUMPING_REPUMP,
            0,
            shot_globals.ryd_456_repump_power,
            close_all_shutters=True,
        )
        # Apply Rydberg pulse with only 456 active
        t, _ = self.RydLasers_obj.do_rydberg_pulse(
            t_aom_start, # synchronize with repump pulse
            dur=shot_globals.ryd_456_duration,
            power_456=shot_globals.ryd_456_power,
            power_1064=0,
            close_shutter=True  # Close shutter after pulse to prevent any residual light
        )

        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
        t = self.reset_mot(t)

        return t

    def _do_456_check_with_dark_state_sequence(self, t):
        """Perform a Rydberg excitation check sequence.

        Executes a sequence to verify Rydberg excitation:
        1. Load atoms into tweezers
        2. Take first image
        3. Optical pumping to strechted state
        4. rotate the field to align with the ryberg beam axis
        5. Apply Rydberg excitation pulse
        6. Take second image to check for atom loss
        7. Reset MOT parameters

        Args:
            t (float): Start time for the sequence

        Returns:
            float: End time of the sequence
        """
        t = self.load_tweezers(t)
        t = self.image_tweezers(t, shot_number=1)

        t += 3e-3


        _ = self.pump_then_rotate(
            t,
            (shot_globals.ryd_bias_amp,
             shot_globals.ryd_bias_phi,
             shot_globals.ryd_bias_theta),
             polar=True) # trap is lowered when optical pump happens

        t += 10e-3



        t, _ = self.RydLasers_obj.do_rydberg_pulse(
            t, #t_aom_start synchronize with repump pulse
            dur=shot_globals.ryd_456_duration,
            power_456=shot_globals.ryd_456_power,
            power_1064=0,
            close_shutter=True  # Close shutter after pulse to prevent any residual light
        )

        t += 10e-3

        if shot_globals.do_killing_pulse:
            t, _ = self.kill_F4(
                t, close_all_shutters=True
            )
            # t, _ = self.kill_F4(
            #     t - D2Lasers.CONST_SHUTTER_TURN_ON_TIME, close_all_shutters=False
            # )
        else:
            t += shot_globals.op_killing_pulse_time

        t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99)

        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
        t = self.reset_mot(t)

        return t


    def _do_456_light_shift_on_hyperfine_ground_states_check(self, t):
        """Check optical pumping using sigma+ beam for atoms in tweezers.

        Performs a comprehensive sequence to verify optical pumping in tweezers:
        1. Load atoms and take initial image
        2. Optional depumping before main pumping
        3. Perform main optical pumping (to F=4) or depumping (to F=3)
        4. Optional post-pump operations (depumping or microwave)
        5. Configure magnetic fields for state manipulation

        The sequence can be configured through shot_globals parameters for
        various pumping and manipulation options.

        Args:
            t (float): Start time for the sequence

        Returns:
            float: End time of the sequence
        """
        t = self.load_tweezers(t)
        t = self.image_tweezers(t, shot_number=1)

        t += 3e-3


        if shot_globals.do_op:
            t, t_aom_off = self.pump_to_F4(
                t, shot_globals.op_label, close_all_shutters=True
            )
            t += 5e-3

        # Making sure the ramp ends right as the pumping is starting
        t_start_ramp = (
            t_aom_off - shot_globals.tw_ramp_dur - shot_globals.op_repump_time
        )

        # ramp down the tweezer power before optical pumping
        _ = self.TweezerLaser_obj.ramp_power(
            t_start_ramp, shot_globals.tw_ramp_dur, shot_globals.tw_ramp_power
        )


        t = self.BField_obj.ramp_bias_field(
            t, # extra time to wait for 5e-3s extra time in optical pumping field
            bias_field_vector=(shot_globals.mw_bias_amp,
                                   shot_globals.mw_bias_phi,
                                   shot_globals.mw_bias_theta),
            # dur=shot_globals.mw_bias_ramp_dur,
            polar = True,
        )

        t += shot_globals.mw_field_wait_dur  # 400e-6

        t, t_aom_start = self.RydLasers_obj.do_rydberg_pulse(
            t,
            dur=shot_globals.mw_time,
            power_456=shot_globals.ryd_456_power,
            power_1064=0,
            close_shutter=True  # Close shutter after pulse to prevent any residual light
        )

        if shot_globals.do_mw_pulse:
            t = self.Microwave_obj.do_pulse(t_aom_start-self.Microwave_obj.CONST_SPECTRUM_CARD_OFFSET, shot_globals.mw_time)
        elif shot_globals.do_mw_sweep:
            mw_sweep_start = (
                shot_globals.mw_detuning + shot_globals.mw_sweep_range / 2
            )
            mw_sweep_end = (
                shot_globals.mw_detuning - shot_globals.mw_sweep_range / 2
            )
            t = self.Microwave_obj.do_sweep(
                t, mw_sweep_start, mw_sweep_end, shot_globals.mw_sweep_duration
            )

        if shot_globals.do_killing_pulse:
            t, _ = self.kill_F4(
                t, close_all_shutters=False
            )

        else:
            t += shot_globals.op_killing_pulse_time

        t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99)
        t += 2e-3  # TODO: from the photodetector, the optical pumping beam shutter seems to be closing slower than others
        # that's why we add extra time here before imaging to prevent light leakage from optical pump beam
        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
        t = self.reset_mot(t)

        return t

#TODO: It's not yet tested!
    def _do_1064_light_shift_check_sequence(self, t):
        """Perform a Rydberg excitation check sequence.

        Executes a sequence to verify Rydberg excitation:
        1. Load atoms into tweezers
        2. Take first image
        3. Apply Rydberg excitation pulse
        4. Take second image to check for atom loss
        5. Reset MOT parameters

        Args:
            t (float): Start time for the sequence

        Returns:
            float: End time of the sequence
        """

        t = self.load_tweezers(t)
        t = self.image_tweezers(t, shot_number=1)

        t += 3e-3

        t, t_aom_off = self.pump_to_F4(
            t, shot_globals.op_label, close_all_shutters=True
        )
        t += 5e-3

        # Making sure the ramp ends right as the pumping is starting
        t_start_ramp = (
            t_aom_off - shot_globals.tw_ramp_dur - shot_globals.op_repump_time
        )

        # ramp down the tweezer power before optical pumping
        t = self.TweezerLaser_obj.ramp_power(
            t_start_ramp, shot_globals.tw_ramp_dur, shot_globals.tw_ramp_power
        )


        t = self.BField_obj.ramp_bias_field(
            t, # extra time to wait for 5e-3s extra time in optical pumping field
            bias_field_vector=(shot_globals.mw_bias_amp,
                               shot_globals.mw_bias_phi,
                               shot_globals.mw_bias_theta),
            # dur=shot_globals.mw_bias_ramp_dur,
            polar = True
        )

        t += 10e-3

        if shot_globals.do_mw_pulse:
            # self.TweezerLaser_obj.aom_off(t)
            t, t_1st_end = self.Microwave_obj.do_ramsey_pulse(t, shot_globals.mw_time, shot_globals.ryd_456_duration)

        # insert a 1064 pulse between two microwave pulse that has the same phase, make sure the pulse start the end of the 1st pulse
        self.RydLasers_obj.pulse_1064_aom_on(t_1st_end, shot_globals.ryd_1064_power)
        t = t_1st_end + shot_globals.ryd_456_duration
        self.RydLasers_obj.pulse_1064_aom_off(t)

        t += 10e-3

        if shot_globals.do_killing_pulse:
            t, _ = self.kill_F4(
                t, close_all_shutters=True
            )
            # t, _ = self.kill_F4(
            #     t - D2Lasers.CONST_SHUTTER_TURN_ON_TIME, close_all_shutters=False
            # )
        else:
            t += shot_globals.op_killing_pulse_time

        t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99)

        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
        t = self.reset_mot(t)

        return t


# Full Sequences, we'll see if we really want all these in a class or just separate sequence files?
class ScienceSequence(RydSequence):
    def __init__(self):
        super(ScienceSequence, self).__init__()


if __name__ == "__main__":
    labscript.start()
    t = 0
    sequence_objects = []
    # Insert "stay on" statements for alignment here...

    if shot_globals.do_mot_in_situ_check:
        MOTSeq_obj = MOTSequence(t)
        sequence_objects.append(MOTSeq_obj)
        t = MOTSeq_obj._do_mot_in_situ_sequence(t, reset_mot=True)

    elif shot_globals.do_mot_tof_check:
        MOTSeq_obj = MOTSequence(t)
        sequence_objects.append(MOTSeq_obj)
        t = MOTSeq_obj._do_mot_tof_sequence(t, reset_mot=True)

    elif shot_globals.do_molasses_in_situ_check:
        # TODO this logic can be moved once we figure out a good code structure for separate sequences
        # If you're trying to do in-situ imaging, you want to image faster than switch shutters allows for,
        # so you can't do imaging beam imaging
        if shot_globals.do_molasses_in_situ_check and shot_globals.imaging_beam_choice() != 'mot':
            raise ValueError

        MOTSeq_obj = MOTSequence(t)
        sequence_objects.append(MOTSeq_obj)
        t = MOTSeq_obj._do_molasses_in_situ_sequence(t, reset_mot=True)

    elif shot_globals.do_molasses_tof_check:
        MOTSeq_obj = MOTSequence(t)
        sequence_objects.append(MOTSeq_obj)
        t = MOTSeq_obj._do_molasses_tof_sequence(t, reset_mot=True)

    elif shot_globals.do_optical_pump_in_molasses_check:
        OPSeq_obj = OpticalPumpingSequence(t)
        sequence_objects.append(OPSeq_obj)
        t = OPSeq_obj._do_optical_pump_in_molasses_sequence(t, reset_mot=True)

    elif shot_globals.do_pump_debug_in_molasses:
        OPSeq_obj = OpticalPumpingSequence(t)
        sequence_objects.append(OPSeq_obj)
        t = OPSeq_obj._do_pump_debug_in_molasses(t, reset_mot=True)

    elif shot_globals.do_F4_microwave_spec_molasses:
        OPSeq_obj = OpticalPumpingSequence(t)
        sequence_objects.append(OPSeq_obj)
        t = OPSeq_obj._do_F4_microwave_spec_molasses(t, reset_mot=True)

    elif shot_globals.do_tweezer_check:
        TweezerSequence_obj = TweezerSequence(t)
        sequence_objects.append(TweezerSequence_obj)
        t = TweezerSequence_obj._do_tweezer_check_sequence(t)

    elif shot_globals.do_tweezer_position_check:
        TweezerSequence_obj = TweezerSequence(t)
        sequence_objects.append(TweezerSequence_obj)
        t = TweezerSequence_obj._do_tweezer_position_check_sequence(t)

    elif shot_globals.do_F4_microwave_spec_dipole_trap or shot_globals.do_dipole_trap_B_calib:
        RydSequence_obj = RydSequence(t)
        sequence_objects.append(RydSequence_obj)
        t = RydSequence_obj._do_dipole_trap_F4_spec(t)

    elif shot_globals.do_ryd_tweezer_check:
        RydSequence_obj = RydSequence(t)
        sequence_objects.append(RydSequence_obj)
        t = RydSequence_obj._do_ryd_check_sequence(t)

    elif shot_globals.do_ryd_tweezer_trap_off_check:
        RydSequence_obj = RydSequence(t)
        sequence_objects.append(RydSequence_obj)
        t = RydSequence_obj._do_ryd_check_trap_off_sequence(t)

    elif shot_globals.do_ryd_multipulse_check:
        RydSequence_obj = RydSequence(t)
        sequence_objects.append(RydSequence_obj)
        t = RydSequence_obj._do_ryd_multipulse_check_sequence(t)

    elif shot_globals.do_456_check:
        RydSequence_obj = RydSequence(t)
        sequence_objects.append(RydSequence_obj)
        t = RydSequence_obj._do_456_check_sequence(t)

    elif shot_globals.do_dipole_trap_check:
        RydSequence_obj = RydSequence(t)
        sequence_objects.append(RydSequence_obj)
        t = RydSequence_obj._do_dipole_trap_sequence(t)

    # if shot_globals.do_tweezer_check_fifo:
    #     t = do_tweezer_check_fifo(t)

    elif shot_globals.do_optical_pump_in_tweezer_check:
        TweezerSequence_obj = TweezerSequence(t)
        sequence_objects.append(TweezerSequence_obj)
        if shot_globals.op_label == "mot":
            t = TweezerSequence_obj._do_optical_pump_mot_in_tweezer_check(t)
        elif shot_globals.op_label == "sigma":
            t = TweezerSequence_obj._do_optical_pump_sigma_in_tweezer_check(t)

    elif shot_globals.do_dark_state_lifetime_in_tweezer_check:
        TweezerSequence_obj = TweezerSequence(t)
        sequence_objects.append(TweezerSequence_obj)
        if shot_globals.op_label == "sigma":
            t = TweezerSequence_obj._do_dark_state_lifetime_in_tweezer_check(t)
        else:
            raise NotImplementedError

    elif shot_globals.do_456_with_dark_state_check:
        RydSequence_obj = RydSequence(t)
        sequence_objects.append(RydSequence_obj)
        if shot_globals.op_label == "sigma":
            t = RydSequence_obj._do_456_check_with_dark_state_sequence(t)
        else:
            raise NotImplementedError

    elif shot_globals.do_456_light_shift_check:
        RydSequence_obj = RydSequence(t)
        sequence_objects.append(RydSequence_obj)
        if shot_globals.op_label == "sigma":
            t = RydSequence_obj._do_456_light_shift_on_hyperfine_ground_states_check(t)
        else:
            raise NotImplementedError


    elif shot_globals.do_1064_check:
        RydSequence_obj = RydSequence(t)
        sequence_objects.append(RydSequence_obj)
        t = RydSequence_obj._do_1064_check_sequence(t)

    elif shot_globals.do_1064_light_shift_check:
        RydSequence_obj = RydSequence(t)
        sequence_objects.append(RydSequence_obj)
        t = RydSequence_obj._do_1064_light_shift_check_sequence(t)

    # if shot_globals.do_optical_pump_in_microtrap_check:
    #     t = do_optical_pump_in_microtrap_check(t)

    """ Here doing all the finish up quirk for spectrum cards """
    # Find the first non-None sequence object
    current_obj = next((obj for obj in sequence_objects if obj is not None), None)

    if current_obj is None:
        raise NotImplementedError("No valid sequence object found")

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
