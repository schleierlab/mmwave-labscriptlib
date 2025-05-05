
from labscriptlib.experiment_components import D2Lasers, ShutterConfig, TweezerLaser
from labscriptlib.shot_globals import shot_globals
from .optical_pumping import OpticalPumpingOperations


class TweezerOperations(OpticalPumpingOperations):
    """Sequence for optical tweezer operations.

    This class manages sequences related to loading, manipulating, and imaging atoms
    in optical tweezers. It inherits from OpticalPumpingSequence to combine optical
    pumping capabilities with tweezer operations. The class coordinates multiple
    hardware components including tweezer lasers, imaging systems, and atom manipulation
    tools.
    """

    def __init__(self, t):
        """Initialize the tweezer sequence.

        Args:
            t (float): Initial time for the sequence
        """
        super(TweezerOperations, self).__init__(t)

        spectrum_mode = 'sequence' if shot_globals.do_sequence_mode else 'fifo'
        tw_y_use_dds = shot_globals.TW_y_use_dds
        if tw_y_use_dds:
            tw_y_freq = shot_globals.TW_y_freqs
        else:
            tw_y_freq = None
        # other DDS parameters need to be set in start_tweezers function in lasers.py.
        self.TweezerLaser_obj = TweezerLaser(t, shot_globals.tw_power, spectrum_mode, tw_y_use_dds, tw_y_freq)

    def ramp_to_imaging_parameters(self, t):
        """Configure laser parameters for imaging or additional cooling.

        Ramps the laser detunings and powers to values optimized for imaging.
        Also used for additional cooling of atoms in tweezers. Sets bias fields
        to zero and configures both TA and repump frequencies.

        Args:
            t (float): Start time for parameter ramping

        Returns:
            float: End time of the ramping sequence

        Raises:
            ValueError: If imaging TA or repump powers are set to zero
        """
        t = self.BField_obj.ramp_bias_field(t, bias_field_vector=(0, 0, 0))
        t = self.D2Lasers_obj.ramp_ta_freq(
            t, D2Lasers.CONST_TA_VCO_RAMP_TIME, shot_globals.tw_img_ta_detuning
        )
        self.D2Lasers_obj.ramp_repump_freq(t, D2Lasers.CONST_TA_VCO_RAMP_TIME, 0)

        if shot_globals.tw_img_ta_power == 0:
            raise ValueError("tw_img_ta_power should not be zero")
        if shot_globals.tw_img_repump_power == 0:
            raise ValueError("img_repump_power should not be zero")

        return t

    def load_tweezers(self, t):
        """Load atoms into optical tweezers.

        Executes a complete sequence to load atoms from MOT into optical tweezers:
        1. Load MOT and cool to molasses
        2. Ramp up tweezer power
        3. Optional parity projection pulse
        4. Configure imaging parameters
        5. Optional robust loading pulse for additional cooling

        Args:
            t (float): Start time for the loading sequence

        Returns:
            float: End time of the loading sequence

        Raises:
            ValueError: If time-of-flight delay is too short
        """
        # TODO this still spends some time loading the MOT;
        # figure out whether we even need this here at all.
        t = self.do_mot(t, dur=1)  # MOT loads between shots, don't need to spend extra time

        t = self.do_molasses(t, dur=shot_globals.bm_time, close_all_shutters=True)

        # TODO: does making this delay longer make the background better when using UV?
        t += 7e-3
        t = self.TweezerLaser_obj.ramp_power(
            t, dur=TweezerLaser.CONST_TWEEZER_RAMPING_TIME, final_power=1
        )
        # ramp to full power and parity projection
        if shot_globals.do_parity_projection_pulse:
            _, t_aom_start = self.D2Lasers_obj.parity_projection_pulse(
                t, dur=shot_globals.bm_parity_projection_pulse_dur
            )
            # if doing parity projection, synchronize with power ramp
            t = t_aom_start
            t += shot_globals.bm_parity_projection_pulse_dur

        # t = self.do_molasses(t, dur=shot_globals.bm_time, close_all_shutters=True)
        # t += shot_globals.bm_time

        t = self.ramp_to_imaging_parameters(t)

        if shot_globals.do_robust_loading_pulse:
            # additional cooling, previously referred to as "robust_loading"
            # sometimes don't use this when tweezer debugging is needed?
            t, _ = self.D2Lasers_obj.do_pulse(
                t,
                shot_globals.bm_robust_loading_pulse_dur,
                ShutterConfig.IMG_FULL,
                shot_globals.tw_img_ta_power,
                shot_globals.tw_img_repump_power,
                close_all_shutters=True,
            )

        if shot_globals.tw_img_tof_imaging_delay <= D2Lasers.CONST_MIN_SHUTTER_OFF_TIME:
            raise ValueError("time of flight needs to be greater than CONST_MIN_SHUTTER_OFF_TIME")
        t += shot_globals.tw_img_tof_imaging_delay

        return t

    def tweezer_modulation(self, t, label="sine"):
        pass

    def rearrange_to_dense(self, t):
        """Rearrange atoms into a dense configuration.

        Not yet implemented. Will provide functionality to rearrange atoms
        in tweezers to form dense arrays or specific patterns.

        Args:
            t (float): Start time for rearrangement
        """
        pass

    # TODO make Camera object intelligently bump camera exposures in quick succession
    def image_tweezers(self, t, shot_number):
        """Image atoms in optical tweezers.

        Captures images of atoms in tweezers with proper timing for different shots.
        Handles both first and second imaging shots with appropriate delays for
        camera readout and shutter operations.

        Args:
            t (float): Start time for imaging
            shot_number (int): Which shot in the imaging sequence (1 or 2)

        Returns:
            float: End time of the imaging sequence
        """
        t = self.ramp_to_imaging_parameters(t)
        if shot_number == 1:
            t = self.do_tweezer_imaging(
                t, close_all_shutters=shot_globals.do_shutter_close_after_first_shot
            )
        elif shot_number > 1:
            # pulse for the second shots and wait for the first shot to finish the
            # first reading
            kinetix_readout_time = shot_globals.kinetix_roi_row[1] * 4.7065e-6
            t += kinetix_readout_time
            t = self.do_tweezer_imaging(t, close_all_shutters=True)
        return t

    def do_tweezer_imaging(self, t, close_all_shutters=False):
        """Execute the tweezer imaging sequence.

        Configures and executes the imaging sequence for atoms in tweezers:
        1. Set up imaging shutters and laser pulses
        2. Configure camera parameters
        3. Synchronize camera exposure with laser pulses

        Args:
            t (float): Start time for imaging
            close_all_shutters (bool, optional): Whether to close all shutters after
                imaging. Defaults to False.

        Returns:
            float: End time of the imaging sequence
        """
        shutter_config = ShutterConfig.select_imaging_shutters(
            imaging_label=shot_globals.imaging_label,
            beam_choice=shot_globals.imaging_beam_choice,
            do_repump=True,
        )
        t_pulse_end, t_aom_start = self.D2Lasers_obj.do_pulse(
            t,
            shot_globals.tw_img_exposure_time,
            shutter_config,
            shot_globals.tw_img_ta_power,
            shot_globals.tw_img_repump_power,
            close_all_shutters=close_all_shutters,
        )

        self.Camera_obj.set_type("kinetix")
        exposure_time = max(shot_globals.tw_img_exposure_time, 1e-3)

        # expose the camera
        self.Camera_obj.expose(t_aom_start, exposure_time)

        # Closes the aom and the specified shutters
        t += exposure_time
        t = max(t, t_pulse_end)

        return t

    def take_in_shot_background(self, t):
        """
        Taking background in the shot,
        the tweezer will be turned off first
        and a kill all pulse will be applied to remove all atoms
        then tweezer back on for same imaging condition
        """
        self.TweezerLaser_obj.aom_off(t)
        t, _ = self.kill_all(t, close_all_shutters=False)
        self.TweezerLaser_obj.aom_on(t, const=1)
        t = self.image_tweezers(t, shot_number=3)
        return t

    def pump_then_rotate(self, t, B_field, polar = False):
        """Pumps to stretched state then rotates the field
        Also lowers the trap, but doesn't raise it back.

        Args:
            t (float): Start time (modulo shutter handling)
            B_field (tuple): Final B field. Must be in cartesian form
        """

        t, t_aom_off = self.pump_to_F4(
            t, shot_globals.op_label, close_all_shutters=True
        )

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
            bias_field_vector=B_field,
            polar = polar,
        )

        return t

    def _do_tweezer_check(self, t, check_rearrangement_position = False) -> float:
        t = self.load_tweezers(t)
        t = self.image_tweezers(t, shot_number=1)
        # t += shot_globals.img_wait_time_between_shots
        t += 95e-3
        t = self.image_tweezers(t, shot_number=2)
        t += shot_globals.img_wait_time_between_shots

        self.TweezerLaser_obj.aom_off(t)
        t, _ = self.kill_all(t, close_all_shutters=False)
        self.TweezerLaser_obj.aom_on(t, const=1)

        t = self.image_tweezers(t, shot_number=3)
        t = self.reset_mot(t)

        # Here is the check with manta camera to make sure the tweezer rearrangement waveform is correct
        if check_rearrangement_position:
            t_rearrangement = (
                t
                - shot_globals.TW_rearrangement_time_offset
                + shot_globals.TW_rearrangement_fine_time_offset)

            self.Camera_obj.set_type("tweezer_manta")
            self.Camera_obj.expose(t_rearrangement,
                                shot_globals.tw_exposure_time)

        return t

    def _do_tweezer_position_check_sequence(self, t, check_with_vimba=True):
        """Perform a basic tweezer position check sequence.

        There are two possibilities:
        1. Run a complete sequence and examine the Manta camera image with Lyse
        2. Run a dummy sequence that leaves the tweezers on (for 10 s)

        Args:
            t (float): Start time for the sequence
            check_with_vimba (bool, defaults to True):
                If enabled, run the dummy sequence (for use with monitoring
                tweezer image in Vimba Viewer instead of Lyse)

        Returns:
            float: End time of the sequence
        """
        t += 1e-5
        self.TweezerLaser_obj.aom_on(t, shot_globals.tw_power)

        if check_with_vimba:
            t += 10
        else:
            t += 1e-3
            t = self.do_molasses_dipole_trap_imaging(t, close_all_shutters=True)

            # taking background images
            t += 1e-1
            self.TweezerLaser_obj.aom_off(t)
            t = self.do_molasses_dipole_trap_imaging(t, close_all_shutters=True)
            t += 1e-2

        t += 1

        return t

    def _tweezer_release_recapture_sequence(self, t):
        """Execute a release and recapture sequence.

        Not yet implemented. Will provide functionality to release atoms
        from tweezers and recapture them after a specified time.

        Args:
            t (float): Start time for the sequence
        """
        raise NotImplementedError

    def _tweezer_modulation_sequence(self, t):
        """Execute a tweezer modulation sequence.

        Not yet implemented. Will provide functionality to perform
        a complete sequence involving tweezer modulation.

        Args:
            t (float): Start time for the sequence
        """
        raise NotImplementedError

    #TODO: Rename this? A little confusing title. Maybe something like:
    # _do_op_with_mot_beams_in_tweezers_check
    def _do_optical_pump_mot_in_tweezer_check(self, t):
        """Check optical pumping using mot beams for atoms in tweezers.

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

        #TODO: This logic is super convoluted, we need to clean this up.
        #Is there ever a situation where we do depump before pump, then dp, then depump after pump? Probably not.
        if shot_globals.do_depump_ta_pulse_before_pump:
            t, _ = self.depump_ta_pulse(t)

        if shot_globals.do_op:
            t, t_aom_off = self.pump_to_F4(
                t, shot_globals.op_label, close_all_shutters=True
            )
        elif shot_globals.do_dp:
            t, t_aom_off = self.depump_to_F3(
                t, shot_globals.op_label, close_all_shutters=False
            )

        if shot_globals.do_depump_ta_pulse_after_pump:
            t_aom_off, _ = self.depump_ta_pulse(t)

        # We use Cartiesan to zero the field and polar for the other instance

        # [mw_biasx_field, mw_biasy_field, mw_biasz_field] = [
            #     shot_globals.mw_biasx_field,
            #     shot_globals.mw_biasy_field,
            #     shot_globals.mw_biasz_field,
            # ]

        t = self.BField_obj.ramp_bias_field(
                t_aom_off,
                bias_field_vector=(shot_globals.mw_bias_amp,
                                   shot_globals.mw_bias_phi,
                                   shot_globals.mw_bias_theta),
                dur=shot_globals.mw_bias_ramp_dur,
                polar = True
            )


        # This is trying to make sure when the ramp of tweezer end (it reaches the minimum power), the shutter config is already switched to optical pumping
        # if the tweezer ramp is too quick, it will wait extra time at high power before the shutter switching finishes
        t = t + max(
            D2Lasers.CONST_MIN_SHUTTER_ON_TIME
            + D2Lasers.CONST_SHUTTER_TURN_ON_TIME
            - shot_globals.tw_ramp_dur,
            0,
        )


        t += shot_globals.mw_field_wait_dur
        t = self.TweezerLaser_obj.ramp_power(
            t, shot_globals.tw_ramp_dur, shot_globals.tw_ramp_power
        )

        if shot_globals.do_mw_pulse:
            # self.TweezerLaser_obj.aom_off(t)
            t = self.Microwave_obj.do_pulse(t, shot_globals.mw_pulse_time)
            # self.TweezerLaser_obj.aom_on(t, shot_globals.tw_ramp_power)
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
            # If we use the MOT beams for pumping we have to switch shutters
            # Our pulse function is set so that switching the shutters adds time before the pulse
            # Here though we want the shutter switching to overlap with the tweezer ramp rather than start after it
            t = t - D2Lasers.CONST_SHUTTER_TURN_ON_TIME
            t, _ = self.kill_F4(t, close_all_shutters=False)
        else:
            t += shot_globals.op_killing_pulse_time

        t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99)
        t += 2e-3  # TODO: from the photodetector, the optical pumping beam shutter seems to be closing slower than others
        # that's why we add extra time here before imaging to prevent light leakage from optical pump beam
        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
        t = self.reset_mot(t)

        return t

    def _do_optical_pump_sigma_in_tweezer_check(self, t):
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


        if shot_globals.do_depump_ta_pulse_before_pump:
            t, _ = self.depump_ta_pulse(t)

        if shot_globals.do_op:
            t, t_aom_off = self.pump_to_F4(
                t, shot_globals.op_label, close_all_shutters=True
            )


        # Making sure the ramp ends right as the pumping is starting
        t_start_ramp = (
            t_aom_off - shot_globals.tw_ramp_dur - shot_globals.op_repump_time
        )

        # ramp down the tweezer power before optical pumping
        _ = self.TweezerLaser_obj.ramp_power(
            t_start_ramp, shot_globals.tw_ramp_dur, shot_globals.tw_ramp_power
        )

        # ramp up the tweezer power after optical pumping
        # _ = self.TweezerLaser_obj.ramp_power(
        #     t_aom_off, shot_globals.tw_ramp_dur, 0.99
        # )

        if shot_globals.do_depump_ta_pulse_after_pump:
            t, _ = self.depump_ta_pulse(t)



        # [mw_biasx_field, mw_biasy_field, mw_biasz_field] = [
        #     shot_globals.mw_biasx_field,
        #     shot_globals.mw_biasy_field,
        #     shot_globals.mw_biasz_field,
        # ]

        t = self.BField_obj.ramp_bias_field(
            t, # extra time to wait for 5e-3s extra time in optical pumping field
            bias_field_vector=(shot_globals.mw_bias_amp,
                                   shot_globals.mw_bias_phi,
                                   shot_globals.mw_bias_theta),
            # dur=shot_globals.mw_bias_ramp_dur,
            polar = True,
        )

        t += shot_globals.mw_field_wait_dur  # 400e-6
        # t = self.TweezerLaser_obj.ramp_power(
        #     t, shot_globals.tw_ramp_dur, shot_globals.tw_ramp_power
        # )

        #TODO: It seems like the added time here will be wrong if we do the sweep, so
        # lets refactor this (already mentioned in optical_pumping file)
        if shot_globals.do_mw_pulse:
            # self.TweezerLaser_obj.aom_off(t)
            t = self.Microwave_obj.do_pulse(t, shot_globals.mw_pulse_time)
            # self.TweezerLaser_obj.aom_on(t, shot_globals.tw_ramp_power)
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
        else:
            t+= shot_globals.mw_pulse_time

        if shot_globals.do_killing_pulse:
            t, _ = self.kill_F4(
                t, close_all_shutters=False
            )
            # t, _ = self.kill_F4(
            #     t - D2Lasers.CONST_SHUTTER_TURN_ON_TIME, close_all_shutters=False
            # )
        else:
            t += shot_globals.op_killing_pulse_time


        # hold the tweezers low for a constant length of time
        # contrasts with following line (ramp up after the kill pulse)
        # t = self.TweezerLaser_obj.ramp_power(t_aom_off + 15e-3, shot_globals.tw_ramp_dur, 0.99)
        t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99)

        t += 2e-3  # TODO: from the photodetector, the optical pumping beam shutter seems to be closing slower than others
        # that's why we add extra time here before imaging to prevent light leakage from optical pump beam
        t += shot_globals.img_wait_time_between_shots

        t = self.image_tweezers(t, shot_number=2)

        # TODO: the following code unlock the D2 laser, need to debug
        # self.TweezerLaser_obj.aom_off(t)
        # t, _ = self.kill_all(t, close_all_shutters=False)
        # self.TweezerLaser_obj.aom_on(t, const=1)
        # t = self.image_tweezers(t, shot_number=3) # take in shot background

        t = self.reset_mot(t)

        return t

    def _do_dark_state_lifetime_in_tweezer_check(self, t):
        """Check optical pumping using sigma+ beam for atoms in tweezers.

        Performs a comprehensive sequence to verify optical pumping in tweezers:
        1. Load atoms and take initial image
        3. Perform main optical pumping (to F=4) or depumping (to F=3)
        4. depumping TA pulse to measure dark state decay back to F=3
        5. Optional: killing pulse (remove F=4 atoms) to do state dependent measurement

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

        t, t_aom_off = self.pump_to_F4(
            t, shot_globals.op_label, close_all_shutters=False
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

        # ramp up the tweezer power after optical pumping
        # _ = self.TweezerLaser_obj.ramp_power(
        #     t_aom_off, shot_globals.tw_ramp_dur, 0.99
        # )

        t, _ = self.depump_ta_pulse(t, close_all_shutters=False)

        # t = self.BField_obj.ramp_bias_field(t, bias_field_vector=(0, 0, 0))

        t = self.TweezerLaser_obj.ramp_power(
            t, shot_globals.tw_ramp_dur, shot_globals.tw_ramp_power
        )


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
        t += 2e-3  # TODO: from the photodetector, the optical pumping beam shutter seems to be closing slower than others
        # that's why we add extra time here before imaging to prevent light leakage from optical pump beam
        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
        t = self.reset_mot(t)

        return t
