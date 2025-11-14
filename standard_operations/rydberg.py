import numpy as np

import labscript.labscript as ls  # type:ignore

from labscriptlib.experiment_components import PointingConfig, RydLasers, ShutterConfig
from labscriptlib.shot_globals import shot_globals

from labscriptlib.standard_operations.tweezers import TweezerOperations
from labscriptlib.connection_table import devices # temperal



class RydbergOperations(TweezerOperations):
    def __init__(self, t):
        super(RydbergOperations, self).__init__(t)
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

    def load_dipole_trap(self, t: float):
        """
        Load a dipole trap. Runs at the start of a sequence.

        Parameters
        ----------
        t: float
            Start time of sequence.

        Returns
        -------
        float
            End time of sequence.
        """
        dipole_trap_on_time = t + 0.1
        t = self.do_mot(t, dur=0.5)
        if shot_globals.do_dipole_trap:
            self.RydLasers_obj.pulse_1064_aom_on(dipole_trap_on_time, 1)
        else:
            self.RydLasers_obj.pulse_1064_aom_off(dipole_trap_on_time)
        if not shot_globals.do_tweezers:
            self.TweezerLaser_obj.aom_off(dipole_trap_on_time)
        t = self.do_molasses(t, dur=shot_globals.bm_time, close_all_shutters=True)

        return t

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
        t = self.load_dipole_trap(t)
        t += 1e-3

        if shot_globals.do_op:
            t, _ = self.pump_to_F4(
                t,
                shot_globals.op_label,
                close_all_shutters=True,
            )

        if shot_globals.do_blue:
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

    def _do_dipole_trap_state_sensitive_img_check(
            self,
            t: float,
    ):
        """
        Largely copied from _do_dipole_trap_sequence.
        """
        t = self.load_dipole_trap(t)
        t += 1e-3

        if shot_globals.do_op:
            t, _ = self.pump_to_F4(
                t,
                shot_globals.op_label,
                close_all_shutters=True,
            )

        if shot_globals.do_blue:
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

        # drop dipole trap, image and kill F = 4, raise dipole trap
        # self.RydLasers_obj.pulse_1064_aom_off(t)
        t = self.do_molasses_dipole_trap_imaging(
            t,
            ta_power = shot_globals.dp_state_sel_ta_power,
            ta_detuning = shot_globals.dp_state_sel_ta_det,
            repump_power = shot_globals.dp_img_repump_power,
            do_repump=True,
            exposure_time=shot_globals.dp_img_exposure_time,
            pulse_time=shot_globals.dp_state_sel_exp_time,
            close_all_shutters=True,
        )
        # self.kill_F4(t)
        # self.RydLasers_obj.pulse_1064_aom_on(t, 1)

        # wait
        t += 20e-3

        # repump the F=3 atoms to F=4, then image as before
        # t, _ = self.pump_to_F4(
        #         t,
        #         shot_globals.op_label,
        #         close_all_shutters=True,
        #     )
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
            ta_power = shot_globals.dp_state_sel_ta_power,
            ta_detuning = shot_globals.dp_img_ta_detuning,
            repump_power = 0,
            do_repump=False,
            exposure_time=shot_globals.dp_img_exposure_time,
            pulse_time=shot_globals.dp_state_sel_exp_time,
            close_all_shutters=True,
        )

        # t = self.do_molasses_dipole_trap_imaging(
        #     t,
        #     ta_power = shot_globals.dp_state_sel_ta_power,
        #     ta_detuning = shot_globals.dp_state_sel_ta_det,
        #     repump_power = shot_globals.dp_img_repump_power,
        #     do_repump=False,
        #     exposure_time=shot_globals.dp_state_sel_exp_time,
        #     close_all_shutters=True,
        # )

        t += 50e-3
        t = self.reset_mot(t)

        return t

    def _do_dipole_trap_F4_spec(self, t):
        t = self.load_dipole_trap(t)
        t += 1e-3

        t, t_aom_off = self.pump_to_F4(
            t, shot_globals.op_label, close_all_shutters=True,
        )

        if shot_globals.do_dipole_trap_B_calib:
            t = self.BField_obj.ramp_bias_field(
                    t_aom_off + 200e-6, #TODO: wait for 200e-6s extra time in optical pumping field, can be changed
                    voltage_vector=(shot_globals.mw_x_coil_voltage,
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
            t = self.Microwave_obj.do_pulse(t, shot_globals.mw_pulse_time)
        elif shot_globals.do_mw_sweep:
            mw_sweep_start = shot_globals.mw_detuning + shot_globals.mw_sweep_range / 2
            mw_sweep_end = shot_globals.mw_detuning - shot_globals.mw_sweep_range / 2
            t = self.Microwave_obj.do_sweep(
                t, mw_sweep_start, mw_sweep_end, shot_globals.mw_sweep_duration
            )

        # t+=10e-6

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

    def _do_dipole_trap_dark_state_measurement(self, t):
        t = self.load_dipole_trap(t)
        t += 10e-3

        t, t_aom_off = self.pump_to_F4(
            t, shot_globals.op_label, close_all_shutters=True,
        )

        if shot_globals.do_blue:
            t = self.BField_obj.ramp_bias_field(
                t_aom_off + 200e-6, #TODO: wait for 200e-6s extra time in optical pumping field, can be changed
                bias_field_vector=(shot_globals.ryd_bias_amp,
                                   shot_globals.ryd_bias_phi,
                                   shot_globals.ryd_bias_theta),
                polar = True
            )
            t += shot_globals.mw_field_wait_dur


        t += 1e-3

        if shot_globals.do_dp:
            t, _ = self.depump_ta_pulse(t, close_all_shutters=True)
        if shot_globals.do_blue:
            t, _ = self.RydLasers_obj.do_rydberg_pulse_short(
                t,
                dur=shot_globals.ryd_456_duration,
                power_456=shot_globals.ryd_456_power,
                power_1064=shot_globals.ryd_1064_power, # use this to do A-T measurement when 1064 power is non-zero
                close_shutter=True,  # Close shutter after pulse to prevent any residual light
                in_dipole_trap=shot_globals.do_dipole_trap,
            )

            # t, _ = self.RydLasers_obj.do_rydberg_pulse(
            #     t,
            #     dur=shot_globals.ryd_456_duration,
            #     power_456=shot_globals.ryd_456_power,
            #     power_1064=shot_globals.ryd_1064_power, # use this to do A-T measurement when 1064 power is non-zero
            #     close_shutter=True,  # Close shutter after pulse to prevent any residual light
            #     in_dipole_trap=shot_globals.do_dipole_trap,
            # )

        t += 1e-3  #TODO: wait for extra time before killing, can be changed

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

    def _do_ryd_tweezer_check_sequence(self, t):
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

        # t += 1e-3
        if shot_globals.do_rearrangement:
            t += shot_globals.img_wait_time_between_shots
            t = self.image_tweezers(t, shot_number=2) # 2nd image taken after rearragnement

        t = self.pump_then_rotate(
            t,
            (shot_globals.ryd_bias_amp,
             shot_globals.ryd_bias_phi,
             shot_globals.ryd_bias_theta),
             polar=True) # trap is lowered when optical pump happens

        t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99) # ramp trap power back
        # Apply Rydberg pulse with both 456 and 1064 active
        t += 2.5e-6

        # if shot_globals.ryd_456_duration > 2.5e-6:
        #     t, t_aom_start= self.RydLasers_obj.do_rydberg_pulse(
        #         t,
        #         dur=shot_globals.ryd_456_duration,
        #         power_456=shot_globals.ryd_456_power,
        #         power_1064=shot_globals.ryd_1064_power,
        #         close_shutter=True  # Close shutter after pulse to prevent any residual light
        #     )
        # else:
        t += 3.1e-6
        # added to allow the short duration < 3us pulse
        # because the analog change from tweezer ramp power

        #Switch E_field
        if shot_globals.do_Efield_calib:
            voltage_diff_vector = (shot_globals.Efield_Vx,
                                   shot_globals.Efield_Vy,
                                   shot_globals.Efield_Vz)
            self.EField_obj.set_electric_field(t, voltage_diff_vector)
        else:
            E_field_shift_vec = (shot_globals.ryd_E_shift_amp,
                                 shot_globals.ryd_E_shift_theta,
                                 shot_globals.ryd_E_shift_phi)
            self.EField_obj.set_efield_shift(t, E_field_shift_vec, polar = True)

        t += 50e-3
        ls.add_time_marker(t, 'Rydberg physics')
        if shot_globals.do_ramsey:
            t, pulse_start_times = self.RydLasers_obj.do_rydberg_multipulses(
                t,
                n_pulses=2,
                pulse_dur= shot_globals.ryd_456_duration/2,
                pulse_wait_dur = shot_globals.t_ramsey_wait,
                power_456 = shot_globals.ryd_456_power,
                power_1064 = shot_globals.ryd_1064_power,
                close_shutter=True)
            t_aom_start = pulse_start_times[0]
            t_aom_stop = t_aom_start + shot_globals.ryd_456_duration + shot_globals.t_ramsey_wait
        else:
            t, t_aom_start = self.RydLasers_obj.do_rydberg_pulse_short(
                t,
                dur=shot_globals.ryd_456_duration,
                power_456 = shot_globals.ryd_456_power,
                power_1064 = shot_globals.ryd_1064_power,
                close_shutter=True,
                long_1064 = True,
                pd_analog_in = True)
            t_aom_stop = t_aom_start + shot_globals.ryd_456_duration

        if shot_globals.do_tw_trap_off:
            self.TweezerLaser_obj.aom_off(t_aom_start - 0.6e-6, digital_only=True)
            self.TweezerLaser_obj.aom_on(t_aom_stop, 0.99, digital_only=True)

        # Fudge time based on picoscope observation when NOT rearranging; depends on expt timing
        spectrum_card_delay = self.Microwave_obj.CONST_SPECTRUM_CARD_OFFSET - 30e-6

        if shot_globals.do_mmwave_kill:
            # start microwaves as soon as blue is off
            # 10 ms pulse length is unimportant
            # (just needs to be >> Rydberg lifetime)
            # detuning should just be away from any resonances
            _ = self.Microwave_obj.do_mmwave_pulse(t_aom_stop-spectrum_card_delay, shot_globals.mmwave_pulse_time)

        if shot_globals.do_microwave_kill:
            _ = self.Microwave_obj.do_pulse(t_aom_stop-self.Microwave_obj.CONST_SPECTRUM_CARD_OFFSET+3e-6, 10e-6)

        # t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99)
        t += 10e-3  # TODO: from the photodetector, the optical pumping beam shutter seems to be closing slower than others
        # that's why we add extra time here before imaging to prevent light leakage from optical pump beam
        # t += shot_globals.img_wait_time_between_shots
        # t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99) # ramp trap power back

        if shot_globals.do_rearrangement:
            t = self.image_tweezers(t, shot_number=3) # 3rd image (taken after rydberg if we do rearrangement)
        else:
            t = self.image_tweezers(t, shot_number=2)
        t = self.take_in_shot_background(t)
        t = self.reset_mot(t)

        return t

    def _do_ryd_mmwave_check_sequence(self, t):
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

        # t += 1e-3
        if shot_globals.do_rearrangement:
            t += shot_globals.img_wait_time_between_shots
            t = self.image_tweezers(t, shot_number=2) # 2nd image taken after rearragnement

        t = self.pump_then_rotate(
            t,
            (shot_globals.ryd_bias_amp,
             shot_globals.ryd_bias_phi,
             shot_globals.ryd_bias_theta),
             polar=True) # trap is lowered when optical pump happens

        t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99) # ramp trap power back
        t += 5e-3

        E_field_shift_vec = (shot_globals.ryd_E_shift_amp,
                             shot_globals.ryd_E_shift_theta,
                             shot_globals.ryd_E_shift_phi)
        self.EField_obj.set_efield_shift(t, E_field_shift_vec, polar = True)

        t += 50e-3

        ls.add_time_marker(t, 'Rydberg pulses')

        t, pulse_start_times = self.RydLasers_obj.do_rydberg_multipulses(
                t,
                n_pulses=2,
                pulse_dur= shot_globals.ryd_456_duration,
                pulse_wait_dur = shot_globals.ryd_state_wait_time,
                power_456 = shot_globals.ryd_456_power,
                power_1064 = shot_globals.ryd_1064_power,
                close_shutter=True,
                long_1064=True,
            )
        t_aom_start = pulse_start_times[0]
        t_aom_stop_0 = t_aom_start + shot_globals.ryd_456_duration
        t_aom_stop_1 = t_aom_start + shot_globals.ryd_456_duration * 2 + shot_globals.ryd_state_wait_time
        self.TweezerLaser_obj.aom_off(t_aom_start - 0.6e-6, digital_only=True)
        self.TweezerLaser_obj.aom_on(t_aom_stop_1, 0.99, digital_only=True)

        spectrum_card_delay = self.Microwave_obj.CONST_SPECTRUM_CARD_OFFSET - 29.30e-6
        # if shot_globals.do_mmwave_ramsey:
        #     ramsey_time = shot_globals.mmwave_pi_half_pulse_t*2 + shot_globals.mmwave_ramsey_wait_time
        #     mmwave_offset_t = (shot_globals.ryd_state_wait_time - ramsey_time)/2

        #     first_pulse_end_time = self.Microwave_obj.do_mmwave_pulse(
        #         t_aom_stop_0 - spectrum_card_delay + mmwave_offset_t,
        #         shot_globals.mmwave_pi_half_pulse_t,
        #         detuning=shot_globals.mmwave_spectrum_freq,
        #         phase=0,
        #         keep_switch_on=True,
        #         switch_offset = spectrum_card_delay,
        #     )
        #     phase_accumulation_degrees = 360 * (shot_globals.mmwave_spectrum_freq) * (shot_globals.mmwave_pi_half_pulse_t + shot_globals.mmwave_ramsey_wait_time)

        #     self.Microwave_obj.do_mmwave_pulse(
        #         first_pulse_end_time + shot_globals.mmwave_ramsey_wait_time,
        #         shot_globals.mmwave_pi_half_pulse_t,
        #         detuning=shot_globals.mmwave_spectrum_freq,
        #         phase=phase_accumulation_degrees,
        #         switch_offset = spectrum_card_delay,
        #     )
        # else:
        # Timing?
        mmwave_offset_t = (shot_globals.ryd_state_wait_time - shot_globals.mmwave_pi_pulse_t) / 2
        self.Microwave_obj.do_mmwave_pulse(
            t_aom_stop_0 - spectrum_card_delay + mmwave_offset_t,
            shot_globals.mmwave_pi_pulse_t,
            switch_offset = spectrum_card_delay,
        )

        if shot_globals.do_mmwave_kill:
            # start microwaves as soon as blue is off
            # 10 ms pulse length is unimportant
            # (just needs to be >> Rydberg lifetime)
            # detuning should just be away from any resonances
            self.Microwave_obj.do_mmwave_pulse(t_aom_stop_1-self.Microwave_obj.CONST_SPECTRUM_CARD_OFFSET+7e-6, 50e-6)

        if shot_globals.do_microwave_kill:
            _ = self.Microwave_obj.do_pulse(t_aom_stop_1-self.Microwave_obj.CONST_SPECTRUM_CARD_OFFSET+1e-6, 50e-6)

        # t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99)
        t += 10e-3  # TODO: from the photodetector, the optical pumping beam shutter seems to be closing slower than others
        # that's why we add extra time here before imaging to prevent light leakage from optical pump beam
        # t += shot_globals.img_wait_time_between_shots
        # t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99) # ramp trap power back

        if shot_globals.do_rearrangement:
            t = self.image_tweezers(t, shot_number=3) # 3rd image (taken after rydberg if we do rearrangement)
        else:
            t = self.image_tweezers(t, shot_number=2)
        t = self.take_in_shot_background(t)
        t = self.reset_mot(t)

        return t

    def _do_ryd_mmwave_ramsey_check_sequence(self, t):
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
        # devices.local_addr_1064_aom_digital.go_high(t) # temp
        # devices.local_addr_1064_aom_analog.constant(t, 0.05) # temp
        # devices.pulse_local_addr_1064_aom_digital.go_high(t) # temp
        # devices.pulse_local_addr_1064_aom_analog.constant(t, 1) # temp
        # devices.analog_test_32.constant(t, 1)
        # devices.analog_test_33.constant(t, -1)
        # devices.pb_test_9.go_high(t+50e-6)
        # devices.pb_test_9.go_low(t+250e-6)
        t = self.load_tweezers(t)
        t = self.image_tweezers(t, shot_number=1)

        # t += 1e-3
        if shot_globals.do_rearrangement:
            t += shot_globals.img_wait_time_between_shots
            t = self.image_tweezers(t, shot_number=2) # 2nd image taken after rearragnement

        t = self.pump_then_rotate(
            t,
            (shot_globals.ryd_bias_amp,
             shot_globals.ryd_bias_phi,
             shot_globals.ryd_bias_theta),
             polar=True) # trap is lowered when optical pump happens

        t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99) # ramp trap power back
        t += 5e-3

        E_field_shift_vec = (shot_globals.ryd_E_shift_amp,
                             shot_globals.ryd_E_shift_theta,
                             shot_globals.ryd_E_shift_phi)
        self.EField_obj.set_efield_shift(t, E_field_shift_vec, polar = True)

        t += 50e-3

        ls.add_time_marker(t, 'Rydberg pulses')

        t, pulse_start_times = self.RydLasers_obj.do_rydberg_multipulses(
                t,
                n_pulses=2,
                pulse_dur= shot_globals.ryd_456_duration,
                pulse_wait_dur = shot_globals.ryd_state_wait_time,
                power_456 = shot_globals.ryd_456_power,
                power_1064 = shot_globals.ryd_1064_power,
                close_shutter=True,
                long_1064=True,
            )
        t_aom_start = pulse_start_times[0]
        t_aom_stop_0 = t_aom_start + shot_globals.ryd_456_duration
        t_aom_stop_1 = t_aom_start + shot_globals.ryd_456_duration * 2 + shot_globals.ryd_state_wait_time
        self.TweezerLaser_obj.aom_off(t_aom_start - 0.6e-6, digital_only=True)
        self.TweezerLaser_obj.aom_on(t_aom_stop_1, 0.99, digital_only=True)

        spectrum_card_delay = self.Microwave_obj.CONST_SPECTRUM_CARD_OFFSET - 29.30e-6

        # do ramsey
        ramsey_time = shot_globals.mmwave_pi_half_pulse_t*2 + shot_globals.mmwave_ramsey_wait_time
        mmwave_offset_t = (shot_globals.ryd_state_wait_time - ramsey_time)/2

        def ensure_list(param):
            if np.isscalar(param):
                return [param]
            else:
                return list(param)
        
        num_of_tone= len(ensure_list(shot_globals.mmwave_spectrum_freq))

        first_pulse_end_time = self.Microwave_obj.do_mmwave_pulse(
            t_aom_stop_0 - spectrum_card_delay + mmwave_offset_t,
            shot_globals.mmwave_pi_half_pulse_t,
            detuning=shot_globals.mmwave_spectrum_freq,
            phase= [0]*num_of_tone,
            keep_switch_on=True,
            switch_offset = spectrum_card_delay,
        )

        if shot_globals.do_mmwave_spin_echo:
            phase_accumulation_degrees = 360 * (shot_globals.mmwave_spectrum_freq) * (shot_globals.mmwave_pi_half_pulse_t + shot_globals.mmwave_ramsey_wait_time/2)
            second_pulse_end_time = self.Microwave_obj.do_mmwave_pulse(
                first_pulse_end_time + shot_globals.mmwave_ramsey_wait_time/2,
                shot_globals.mmwave_pi_pulse_t,
                detuning=shot_globals.mmwave_spectrum_freq,
                phase=phase_accumulation_degrees,
                switch_offset = spectrum_card_delay,
            )
            pulse_start_time = second_pulse_end_time + shot_globals.mmwave_ramsey_wait_time/2
            accumulated_time = shot_globals.mmwave_pi_half_pulse_t + shot_globals.mmwave_ramsey_wait_time + shot_globals.mmwave_pi_pulse_t
        else:
            pulse_start_time = first_pulse_end_time + shot_globals.mmwave_ramsey_wait_time
            accumulated_time = (shot_globals.mmwave_pi_half_pulse_t + shot_globals.mmwave_ramsey_wait_time)

        phase_accumulation_degrees = 360 * (ensure_list(shot_globals.mmwave_spectrum_freq)[0]) * accumulated_time
        end_pulse_phase = phase_accumulation_degrees+shot_globals.mmwave_ramsey_extraphase if num_of_tone ==1 else [0, phase_accumulation_degrees+shot_globals.mmwave_ramsey_extraphase]

        self.Microwave_obj.do_mmwave_pulse(
            pulse_start_time,
            # shot_globals.ramsey_2nd_pulse_t,
            shot_globals.mmwave_pi_half_pulse_t,
            detuning=shot_globals.mmwave_spectrum_freq,
            phase= end_pulse_phase,
            switch_offset = spectrum_card_delay,
        )

        # t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99)
        t += 10e-3  # TODO: from the photodetector, the optical pumping beam shutter seems to be closing slower than others
        # that's why we add extra time here before imaging to prevent light leakage from optical pump beam
        # t += shot_globals.img_wait_time_between_shots
        # t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99) # ramp trap power back

        if shot_globals.do_rearrangement:
            t = self.image_tweezers(t, shot_number=3) # 3rd image (taken after rydberg if we do rearrangement)
        else:
            t = self.image_tweezers(t, shot_number=2)
        t = self.take_in_shot_background(t)
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
            ShutterConfig.MOT_REPUMP,
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

        t = self.take_in_shot_background(t)
        t = self.reset_mot(t)

        return t

    def _do_456_with_dark_state_sequence(self, t):
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

        t = self.pump_then_rotate(
            t,
            (shot_globals.ryd_bias_amp,
             shot_globals.ryd_bias_phi,
             shot_globals.ryd_bias_theta),
             polar=True) # trap is lowered when optical pump happens

        t += 20e-3 # increased this time from 10 ms to 20 ms just so the rydberg pulse will happen after the y coil is flipped to the new field
                    # but we should still debug the pump then rotate function, especially the coil flip to really fix this

        t, _ = self.RydLasers_obj.do_rydberg_pulse_short(
            t, #t_aom_start synchronize with repump pulse
            dur=shot_globals.ryd_456_duration,
            power_456=shot_globals.ryd_456_power,
            power_1064=shot_globals.ryd_1064_power, # use this to do A-T measurement when 1064 power is non-zero
            close_shutter=True  # Close shutter after pulse to prevent any residual light
        )

        t += 2e-3

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

        t = self.take_in_shot_background(t)
        t = self.reset_mot(t)

        return t

    def _do_456_light_shift_check_sequence(self, t):
        """Perform a 456 light shift check sequence.

        1. Load atoms into tweezers
        2. Take first image
        3. optical pump then rotate field for rydberg
        4. (killing pulse + blue) or (depump pulse + blue)
        5. (do killing pulse only if do depump)
        6. Take second image to check for atom loss
        7. Take 3rd image for bkg
        8. Reset MOT parameters

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

        # Apply kiiling pulse frequency scan or depump pulse frequency scan
        if shot_globals.do_killing_pulse and not shot_globals.do_dp:
            t, t_aom_off = self.kill_F4(t, close_all_shutters=False)
            t_aom_start = t_aom_off - shot_globals.op_killing_pulse_time
            ryd_pulse_duration = shot_globals.op_killing_pulse_time
        elif shot_globals.do_dp:
            t, t_aom_start = self.depump_ta_pulse(
                t, close_all_shutters=True
            )
            ryd_pulse_duration = shot_globals.op_depump_pulse_time
        else:
            t_aom_start = t
            ryd_pulse_duration = shot_globals.ryd_456_duration

        # Apply Rydberg pulse with only 456 active
        t, _ = self.RydLasers_obj.do_rydberg_pulse(
            # Should synchronize with killing pulse or depump pulse,
            # but turn on earlier to account for the small "blip" from TA atom
            # Turn off later so the blue would cover the entire depump or killing pulse
            t_aom_start-3e-6,
            dur = ryd_pulse_duration + 7e-6,
            power_456=shot_globals.ryd_456_power,
            power_1064=0,
            close_shutter=True  # Close shutter after pulse to prevent any residual light
        )

        #If you set the blue power to 0, the Rydberg shutter doesn't open, and the
        #time it returns is the pulse duration, which we usually have as too short
        #relative to the TA vco time, as kill_F4 immediately starts ramping the ta vco
        #even if the pulses don't start until the shutters have been handled
        t+=1e-3

        # do killing pulse when we do depump light shift measurement
        if shot_globals.do_killing_pulse and shot_globals.do_dp:
            t, _ = self.kill_F4(
                t, close_all_shutters=True
            )
        else:
            t += shot_globals.op_killing_pulse_time

        t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99)

        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
        t = self.take_in_shot_background(t)

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

        t += 1e-3

        t = self.pump_then_rotate(
            t,
            (shot_globals.mw_bias_amp,
             shot_globals.mw_bias_phi,
             shot_globals.mw_bias_theta),
             polar=True) # trap is lowered when optical pump happens

        # Apply Rydberg pulse with both 456 and 1064 active
        t+=2.5e-6

        t += shot_globals.mw_field_wait_dur  # 400e-6

        mw_buffer_t = 1e-3
        t, t_aom_start = self.RydLasers_obj.do_rydberg_pulse(
            t,
            dur=shot_globals.mw_pulse_time + 2*mw_buffer_t,
            power_456=shot_globals.ryd_456_power,
            power_1064=0,
            close_shutter=True  # Close shutter after pulse to prevent any residual light
        )

        if shot_globals.do_mw_pulse:
            t = self.Microwave_obj.do_pulse(t_aom_start-self.Microwave_obj.CONST_SPECTRUM_CARD_OFFSET + mw_buffer_t,
                                             shot_globals.mw_pulse_time)
        # elif shot_globals.do_mw_sweep:
        #     mw_sweep_start = (
        #         shot_globals.mw_detuning + shot_globals.mw_sweep_range / 2
        #     )
        #     mw_sweep_end = (
        #         shot_globals.mw_detuning - shot_globals.mw_sweep_range / 2
        #     )
        #     t = self.Microwave_obj.do_sweep(
        #         t, mw_sweep_start, mw_sweep_end, shot_globals.mw_sweep_duration
        #     )

        if shot_globals.do_killing_pulse:
            t, _ = self.kill_F4(
                t, close_all_shutters=False
            )

        else:
            t += shot_globals.op_killing_pulse_time

        t+= 1e-3
        t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99)
        t += 2e-3  # TODO: from the photodetector, the optical pumping beam shutter seems to be closing slower than others
        # that's why we add extra time here before imaging to prevent light leakage from optical pump beam
        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
        t = self.take_in_shot_background(t)
        t = self.reset_mot(t)

        return t

    # TODO: It's not yet tested!
    # TODO: why'd you write it then? Why didn't you test it?
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
            t, t_1st_end = self.Microwave_obj.do_ramsey_pulse(t, shot_globals.mw_pulse_time, shot_globals.ryd_456_duration)

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
