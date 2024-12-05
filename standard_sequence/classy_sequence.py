from __future__ import annotations

import labscript

from connection_table import devices
from labscriptlib.shot_globals import shot_globals
from labscriptlib.standard_sequence.experiment_components import (
    BField,
    Camera,
    D2Lasers,
    Microwave,
    RydLasers,
    ShutterConfig,
    TweezerLaser,
    UVLamps,
)

spcm_sequence_mode = shot_globals.do_sequence_mode

# TODO is this necessary?
if __name__ == "__main__":
    devices.initialize()



# fixed parameters in the script
CONST_TA_PUMPING_DETUNING = -251  # MHz 4->4 tansition
CONST_REPUMP_DEPUMPING_DETUNING = -201.24  # MHz 3->3 transition


# lasers_852 =  D2Lasers()
# lasers_852.pulse_imaging(t=300e-6, duration=100e-6)
# lasers_852.pulse_ta(t=450e-6, duration=100e-6, hold_shutter_open = True)
# pulser_ta(t=600e-6, duration=100e-6)


# MOTconfig = {shutter1: True, shutter2: False, shutter3: True}
# imagconfig = {shutter1: False, shutter2: True, }



# Sequence Classes
# -------------------------------------------------------------------------------


class MOTSequence:
    def __init__(self, t):
        # Standard initialization for hardware objects puts everything in
        # correct state/tuning to start loading the MOT
        self.D2Lasers_obj = D2Lasers(t)
        self.BField_obj = BField(t)
        self.Microwave_obj = Microwave(t)
        self.UVLamps_obj = UVLamps(t)
        self.Camera_obj = Camera(t)

    def do_mot(self, t, dur, close_all_shutters=False):
        if shot_globals.do_uv:
            t = self.UVLamps_obj.uv_pulse(t, dur=shot_globals.uv_duration)
            # the uv duration should be determined for each dispenser current
            # generally, get superior loading in the 10s of milliseconds

        # if using a long UV duration, want to make sure that the MOT doesn't finish
        # loading leaving the UV is still on for imaging.
        dur = max(dur, shot_globals.uv_duration)
        t, _ = self.D2Lasers_obj.do_pulse(
            t,
            dur,
            ShutterConfig.MOT_FULL,
            shot_globals.mot_ta_power,
            shot_globals.mot_repump_power,
            close_all_shutters=close_all_shutters,
        )

        return t

    def reset_mot(self, t):
        # B fields
        if not self.BField_obj.mot_coils_on:
            t = self.BField_obj.switch_mot_coils(t)

        mot_bias_voltages = (
            shot_globals.mot_x_coil_voltage,
            shot_globals.mot_y_coil_voltage,
            shot_globals.mot_z_coil_voltage,
        )

        t = self.BField_obj.ramp_bias_field(t, voltage_vector=mot_bias_voltages)

        # Reset laser frequency and configuration
        t = self.D2Lasers_obj.reset_to_mot_freq(t)
        t = self.D2Lasers_obj.reset_to_mot_on(t)

        t += 1e-2

        return t

    def image_mot(self, t, close_all_shutters=False):
        # Move to on resonance, make sure AOM is off
        self.D2Lasers_obj.ramp_ta_freq(t, D2Lasers.CONST_TA_VCO_RAMP_TIME, 0)
        t += D2Lasers.CONST_TA_VCO_RAMP_TIME

        # Make sure coils are off
        if self.BField_obj.mot_coils_on:
            t = self.BField_obj.switch_mot_coils(t)

        self.Camera_obj.set_type("MOT_manta")
        self.Camera_obj.expose(t, shot_globals.mot_exposure_time)

        t, _ = self.D2Lasers_obj.do_pulse(
            t,
            shot_globals.mot_exposure_time,
            ShutterConfig.MOT_FULL,
            shot_globals.mot_ta_power,
            shot_globals.mot_repump_power,
            close_all_shutters=close_all_shutters,
        )

        return t

    def _do_mot_in_situ_sequence(self, t, reset_mot=False):
        """
        <describe what this does>
        This is a standalone sequence not intended to be called as a part of a large sequence.
        """
        print("Running _do_mot_in_situ_sequence")

        print("MOT coils = ", self.BField_obj.mot_coils_on)
        # MOT loading time 500 ms
        mot_load_dur = 0.5
        t += D2Lasers.CONST_SHUTTER_TURN_ON_TIME
        t = self.do_mot(t, mot_load_dur)

        t = self.image_mot(t)
        # Shutter does not need to be held open

        # Wait until the MOT disappear for background image
        t += 0.1
        t = self.image_mot(t)

        # Reset laser frequency so lasers do not jump frequency and come unlocked
        t = self.D2Lasers_obj.reset_to_mot_freq(t)

        if reset_mot:
            t = self.reset_mot(t)

        return t

    # TODO: Needs more experimental debugging. When should the shutter close? What timescales should we expect the MOT to disperse in?
    def _do_mot_tof_sequence(self, t, reset_mot=False):
        print("Running _do_mot_tof_sequence")

        print("MOT coils = ", self.BField_obj.mot_coils_on)
        # MOT loading time 500 ms
        mot_load_dur = 0.5

        t += D2Lasers.CONST_SHUTTER_TURN_ON_TIME

        t = self.do_mot(t, mot_load_dur)

        # assert shot_globals.mot_tof_imaging_delay > CONST_MIN_SHUTTER_OFF_TIME, "time of flight too short for shutter"
        t += shot_globals.mot_tof_imaging_delay

        t = self.image_mot(t)
        # Shutter does not need to be held open

        # Wait until the MOT disappear for background image
        t += 0.1
        t = self.image_mot(t)

        # Reset laser frequency so lasers do not jump frequency and come unlocked
        t = self.D2Lasers_obj.reset_to_mot_freq(t)

        if reset_mot:
            t = self.reset_mot(t)

        return t

    # Molasses sequences
    def ramp_to_molasses(self, t):
        # detuning is ramped slowly here (duration = 1e-3) because atoms
        # see the light during the frequency ramp.
        self.D2Lasers_obj.ramp_ta_freq(t, 1e-3, shot_globals.bm_ta_detuning)
        self.D2Lasers_obj.ramp_repump_freq(t, 1e-3, shot_globals.bm_repump_detuning)

        self.BField_obj.switch_mot_coils(t)
        self.BField_obj.ramp_bias_field(t, bias_field_vector=(0, 0, 0))

        return t

    def do_molasses(self, t, dur, close_all_shutters=False):
        assert (
            shot_globals.do_molasses_img_beam or shot_globals.do_molasses_mot_beam
        ), "either do_molasses_img_beam or do_molasses_mot_beam has to be on"
        assert (
            shot_globals.bm_ta_detuning != 0
        ), "bright molasses detuning = 0. TA detuning should be non-zero for bright molasses."
        print(f"molasses detuning is {shot_globals.bm_ta_detuning}")

        _ = self.ramp_to_molasses(t)

        if shot_globals.do_molasses_mot_beam:
            t, _ = self.D2Lasers_obj.do_pulse(
                t,
                dur,
                ShutterConfig.MOT_FULL,
                shot_globals.bm_ta_power,
                shot_globals.bm_repump_power,
                close_all_shutters=close_all_shutters,
            )

        if shot_globals.do_molasses_img_beam:
            t, _ = self.D2Lasers_obj.do_pulse(
                t,
                dur,
                ShutterConfig.IMG_FULL,
                shot_globals.bm_ta_power,
                shot_globals.bm_repump_power,
                close_all_shutters=close_all_shutters,
            )
        return t

    # Which arguments are actually necessary to pass or even set as a defualt?
    # How many of them can just be set to globals?
    # TODO: Maybe pass the shutter config into here? This would get rid of all the if statements?
    def do_molasses_dipole_trap_imaging(
        self,
        t,
        ta_power=1,
        repump_power=1,
        do_repump=True,
        exposure=shot_globals.bm_exposure_time,
        close_all_shutters=False,
    ):
        # zero the field
        _ = self.BField_obj.ramp_bias_field(t, bias_field_vector=(0, 0, 0))

        # Ramp to imaging frequencies
        self.D2Lasers_obj.ramp_ta_freq(t, D2Lasers.CONST_TA_VCO_RAMP_TIME, 0)
        self.D2Lasers_obj.ramp_repump_freq(t, D2Lasers.CONST_TA_VCO_RAMP_TIME, 0)
        t += D2Lasers.CONST_TA_VCO_RAMP_TIME

        shutter_config = ShutterConfig.select_imaging_shutters(do_repump=do_repump)

        # full power ta and repump pulse
        t_pulse_end, t_aom_start = self.D2Lasers_obj.do_pulse(
            t,
            exposure,
            shutter_config,
            ta_power,
            repump_power,
            close_all_shutters=close_all_shutters,
        )

        # TODO: ask Lin and Michelle and max() logic and if we always want it there
        self.Camera_obj.set_type(shot_globals.camera_type)
        if self.Camera_obj.type == "MOT_manta" or "tweezer_manta":
            exposure = max(exposure, 50e-6)
        if self.Camera_obj.type == "kinetix":
            exposure = max(exposure, 1e-3)

        # expose the camera
        self.Camera_obj.expose(t_aom_start, exposure)

        # Closes the aom and the specified shutters
        t += exposure
        t = max(t, t_pulse_end)

        return t

    def _do_molasses_in_situ_sequence(self, t, reset_mot=False):
        # MOT loading time 500 ms
        mot_load_dur = 0.5

        t += D2Lasers.CONST_SHUTTER_TURN_ON_TIME

        t = self.do_mot(t, mot_load_dur)
        t = self.do_molasses(t, shot_globals.bm_time)
        t = self.do_molasses_dipole_trap_imaging(t, close_all_shutters=True)

        # Turn off MOT for taking background images
        t += 1e-1

        t = self.do_molasses_dipole_trap_imaging(t, close_all_shutters=True)
        t += 1e-2

        if reset_mot:
            t = self.reset_mot(t)

        return t

    def _do_molasses_tof_sequence(self, t, reset_mot=False):
        mot_load_dur = 0.5
        t += D2Lasers.CONST_SHUTTER_TURN_ON_TIME

        t = self.do_mot(t, mot_load_dur)

        t = self.do_molasses(t, shot_globals.bm_time)

        assert (
            shot_globals.bm_tof_imaging_delay > D2Lasers.CONST_MIN_SHUTTER_OFF_TIME
        ), "time of flight too short for shutter"
        t += shot_globals.bm_tof_imaging_delay
        t = self.do_molasses_dipole_trap_imaging(t, close_all_shutters=True)

        # Turn off MOT for taking background images
        t += 1e-1

        t = self.do_molasses_dipole_trap_imaging(t)

        t += 1e-2
        if reset_mot:
            t = self.reset_mot(t)

        return t


class OpticalPumpingSequence(MOTSequence):
    def __init__(self, t):
        super(OpticalPumpingSequence, self).__init__(t)

    def pump_to_F4(self, t, label, close_all_shutters = True):
        if self.BField_obj.mot_coils_on:
            _ = self.BField_obj.switch_mot_coils(t)
        if label == "mot":
            # Use the MOT beams for optical pumping
            # Do a repump pulse
            t, _ = self.D2Lasers_obj.do_pulse(
                t,
                shot_globals.op_MOT_op_time,
                ShutterConfig.MOT_REPUMP,
                0,
                1,
                close_all_shutters=True,
            )
            return t

        elif label == "sigma":
            # Use the sigma+ beam for optical pumping
            op_biasx_field, op_biasy_field, op_biasz_field = (
                self.BField_obj.get_op_bias_fields()
            )
            _ = self.BField_obj.ramp_bias_field(
                t, bias_field_vector=(op_biasx_field, op_biasy_field, op_biasz_field)
            )
            # ramp detuning to 4 -> 4, 3 -> 4
            self.D2Lasers_obj.ramp_ta_freq(t, D2Lasers.CONST_TA_VCO_RAMP_TIME, shot_globals.op_ta_pumping_detuning)
            self.D2Lasers_obj.ramp_repump_freq(
                t, D2Lasers.CONST_TA_VCO_RAMP_TIME, shot_globals.op_repump_pumping_detuning
            )
            # Do a sigma+ pulse
            # TODO: is shot_globals.op_ramp_delay just extra fudge time? can it be eliminated?
            t += max(D2Lasers.CONST_TA_VCO_RAMP_TIME, shot_globals.op_ramp_delay)
            t, t_aom_start = self.D2Lasers_obj.do_pulse(
                t,
                shot_globals.op_repump_time,
                ShutterConfig.OPTICAL_PUMPING_FULL,
                shot_globals.op_ta_power,
                shot_globals.op_repump_power,
            )

            assert (
                shot_globals.op_ta_time < shot_globals.op_repump_time
            ), "TA time should be shorter than repump for pumping to F=4"
            # TODO: test this timing
            self.D2Lasers_obj.ta_aom_off(
                t_aom_start + shot_globals.op_ta_time
            )
            # Close the shutters
            if close_all_shutters:
                self.D2Lasers_obj.update_shutters(t, ShutterConfig.NONE)
                t += D2Lasers.CONST_SHUTTER_TURN_OFF_TIME

            return t

        else:
            raise NotImplementedError("This optical pumping method is not implemented")

    def depump_to_F3(self, t, label, close_all_shutters = True):
        # This method should be quite similar to pump_to_F4, but trying to call pump_to_F4 with
        # different parameters would produce a very long argument list
        if self.BField_obj.mot_coils_on:
            _ = self.BField_obj.switch_mot_coils(t)
        if label == "mot":
            # Use the MOT beams for optical depumping
            # ramp detuning to 4 -> 4 for TA
            self.D2Lasers_obj.ramp_ta_freq(t, 0, CONST_TA_PUMPING_DETUNING)
            # Do a TA pulse
            t, _ = self.D2Lasers_obj.do_pulse(
                t,
                shot_globals.op_MOT_odp_time,
                ShutterConfig.MOT_TA,
                1,
                0,
                close_all_shutters=True,
            )
            return t

        elif label == "sigma":
            # Use the sigma+ beam for optical pumping
            op_biasx_field, op_biasy_field, op_biasz_field = (
                self.BField_obj.get_op_bias_fields()
            )
            _ = self.BField_obj.ramp_bias_field(
                t, bias_field_vector=(op_biasx_field, op_biasy_field, op_biasz_field)
            )
            # ramp detuning to 4 -> 4, 3 -> 3
            self.D2Lasers_obj.ramp_ta_freq(t, D2Lasers.CONST_TA_VCO_RAMP_TIME, CONST_TA_PUMPING_DETUNING)
            self.D2Lasers_obj.ramp_repump_freq(t, D2Lasers.CONST_TA_VCO_RAMP_TIME, CONST_REPUMP_DEPUMPING_DETUNING)
            # Do a sigma+ pulse
            # TODO: is shot_globals.op_ramp_delay just extra fudge time? can it be eliminated?
            t += max(D2Lasers.CONST_TA_VCO_RAMP_TIME, shot_globals.op_ramp_delay)
            t, t_aom_start = self.D2Lasers_obj.do_pulse(
                t,
                shot_globals.odp_ta_time,
                ShutterConfig.OPTICAL_PUMPING_FULL,
                shot_globals.odp_ta_power,
                shot_globals.odp_repump_power,
            )

            assert (
                shot_globals.odp_ta_time > shot_globals.odp_repump_time
            ), "TA time should be longer than repump for depumping to F = 3"
            # TODO: test this timing
            self.D2Lasers_obj.repump_aom_off(
                t_aom_start + shot_globals.odp_repump_time
            )
            # Close the shutters
            if close_all_shutters:
                self.D2Lasers_obj.update_shutters(t, ShutterConfig.NONE)
                t += D2Lasers.CONST_SHUTTER_TURN_OFF_TIME

            return t

        else:
            raise NotImplementedError(
                "This optical depumping method is not implemented"
            )

    def kill_F4(self, t):
        """Push away atoms in F = 4"""
        # tune to resonance
        self.D2Lasers_obj.ramp_ta_freq(t, 0, 0)
        t += D2Lasers.CONST_TA_VCO_RAMP_TIME
        # do a ta pulse via optical pumping path
        t, _ = self.D2Lasers_obj.do_pulse(
            t,
            shot_globals.op_killing_pulse_time,
            ShutterConfig.OPTICAL_PUMPING_TA,
            shot_globals.op_killing_ta_power,
            0,
            close_all_shutters=True,
        )

        return t

    def kill_F3(self, t):
        pass

    def _optical_pump_molasses_sequence(self, t, reset_mot=False):
        # MOT loading time 500 ms
        mot_load_dur = 0.5

        t += D2Lasers.CONST_SHUTTER_TURN_ON_TIME

        t = self.do_mot(t, mot_load_dur)
        t = self.do_molasses(t, shot_globals.bm_time)

        t = self.pump_to_F4(t)

        t = self.do_molasses_dipole_trap_imaging(t, close_all_shutters=True)

        # Turn off MOT for taking background images
        t += 1e-1

        t = self.do_molasses_dipole_trap_imaging(t, close_all_shutters=True)
        t += 1e-2

        if reset_mot:
            t = self.reset_mot(t)

        return t

    def _do_field_calib_in_molasses(self, t, reset_mot=False):
        mot_load_dur = 0.5
        t += D2Lasers.CONST_SHUTTER_TURN_ON_TIME  # TODO: is this necessary?
        t = self.do_mot(t, mot_load_dur)
        t = self.do_molasses(t, shot_globals.bm_time)


        if shot_globals.do_dp:
            t = self.depump_to_F3(t, shot_globals.op_label)
        if shot_globals.do_op:
            t = self.pump_to_F4(t, shot_globals.op_label)
        t_depump = t
        t = self.BField_obj.ramp_bias_field(
            t,
            bias_field_vector=(
                shot_globals.mw_biasx_field,
                shot_globals.mw_biasy_field,
                shot_globals.mw_biasz_field,
            ),
        )

        if shot_globals.do_mw_pulse:
            t = self.Microwave_obj.do_pulse(t, shot_globals.mw_time)

        # postpone next sequence until shutter off time reached
        t = max(t, t_depump + D2Lasers.CONST_MIN_SHUTTER_OFF_TIME)

        # This is the only place required for the special value of imaging
        t = self.do_molasses_dipole_trap_imaging(
            t,
            ta_power=0.1,
            repump_power=1,
            exposure=10e-3,
            do_repump=shot_globals.mw_imaging_do_repump,
            close_all_shutters=True,
        )

        # Turn off MOT for taking background images
        t += 1e-1

        t = self.do_molasses_dipole_trap_imaging(
            t,
            ta_power=0.1,
            repump_power=1,
            exposure=10e-3,
            do_repump=shot_globals.mw_imaging_do_repump,
            close_all_shutters=True,
        )
        t += 1e-2
        t = self.Microwave_obj.reset_spectrum(t)
        if reset_mot:
            t = self.reset_mot(t)

        return t


class TweezerSequence(OpticalPumpingSequence):
    def __init__(self, t):
        super(TweezerSequence, self).__init__(t)
        self.TweezerLaser_obj = TweezerLaser(t)

    def ramp_to_imaging_parameters(self, t):
        # ramping to imaging detuning and power, previously referred to as "pre_imaging"
        # also used for additional cooling
        self.BField_obj.ramp_bias_field(t, bias_field_vector=(0, 0, 0))
        self.D2Lasers_obj.ramp_ta_freq(t, 0, shot_globals.img_ta_detuning)
        self.D2Lasers_obj.ramp_repump_freq(t, 0, 0)
        assert shot_globals.img_ta_power != 0, "img_ta_power should not be zero"
        assert shot_globals.img_repump_power != 0, "img_repump_power should not be zero"
        self.D2Lasers_obj.ramp_ta_aom(t, 0, shot_globals.img_ta_power)
        self.D2Lasers_obj.ramp_repump_aom(t, 0, shot_globals.img_repump_power)

        return t

    def load_tweezers(self, t):
        t = self.do_mot(t, dur=0.5)
        t = self.do_molasses(t, dur=shot_globals.bm_time, close_all_shutters=True)
        # TODO: does making this delay longer make the background better when using UV?
        t += 7e-3
        # ramp to full power and parity projection
        if shot_globals.do_parity_projection_pulse:
            _, t_aom_start = self.D2Lasers_obj.parity_projection_pulse(
                t, dur=shot_globals.bm_parity_projection_pulse_dur
            )
            # if doing parity projection, synchronize with power ramp
            t = t_aom_start

        self.TweezerLaser_obj.ramp_power(
            t, dur=shot_globals.bm_parity_projection_pulse_dur, final_power=1
        )
        # TODO: Does it make sense that parity projection and tweezer ramp should have same duration?

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
                shot_globals.img_ta_power,
                shot_globals.img_repump_power,
                close_all_shutters=True,
            )

        assert (
            shot_globals.img_tof_imaging_delay > D2Lasers.CONST_MIN_SHUTTER_OFF_TIME
        ), "time of flight needs to be greater than CONST_MIN_SHUTTER_OFF_TIME"
        t += shot_globals.img_tof_imaging_delay

        return t

    def tweezer_modulation(self, t, label="sine"):
        pass

    def rearrange_to_dense(self, t):
        pass

    def image_tweezers(self, t, shot_number):
        if shot_number == 1:
            t = self.do_kinetix_imaging(
                t, close_all_shutters=shot_globals.do_shutter_close_after_first_shot
            )
        if shot_number == 2:
            # pulse for the second shots and wait for the first shot to finish the
            # first reading
            kinetix_readout_time = shot_globals.kinetix_roi_row[1] * 4.7065e-6
            # need extra 7 ms for shutter to close on the second shot
            # TODO: is shot_globals.kinetix_extra_readout_time always zero? Delete if so.
            t += kinetix_readout_time + shot_globals.kinetix_extra_readout_time
            t = self.do_kinetix_imaging(t, close_all_shutters=True)
        return t

    def do_kinetix_imaging(self, t, close_all_shutters=False):
        shutter_config = ShutterConfig.select_imaging_shutters(do_repump=True)

        t_pulse_end, t_aom_start = self.D2Lasers_obj.do_pulse(
            t,
            shot_globals.img_exposure_time,
            shutter_config,
            shot_globals.img_ta_power,
            shot_globals.img_repump_power,
            close_all_shutters=close_all_shutters,
        )

        self.Camera_obj.set_type("kinetix")
        exposure_time = max(shot_globals.img_exposure_time, 1e-3)

        # expose the camera
        self.Camera_obj.expose(t_aom_start, exposure_time)

        # Closes the aom and the specified shutters
        t += exposure_time
        t = max(t, t_pulse_end)

        return t

    def _do_tweezer_check_sequence(self, t):
        t = self.load_tweezers(t)
        t = self.image_tweezers(t, shot_number=1)
        # TODO: add tweezer modulation here, or in a separate sequence?
        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
        t = self.reset_mot(t)
        t = self.TweezerLaser_obj.stop_tweezers(t)

        return t

    def _tweezer_release_recapture_sequence(self, t):
        pass

    def _tweezer_modulation_sequence(self, t):
        pass

    def _tweezer_basic_pump_kill_sequence(self, t):
        t = self.load_tweezers(t)
        t = self.image_tweezers(t, shot_number=1)
        t += 10e-3

        t = self.pump_to_F4(t, label="sigma")
        # t, _ = self.D2Lasers_obj.do_pulse(t, shot_globals.op_depump_pulse_time,
        #                                ShutterConfig.OPTICAL_PUMPING_TA,
        #                                shot_globals.op_depump_power,
        #                                0,
        #                                close_all_shutters=True)
        # t = self.kill_F4(t)

        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
        t = self.reset_mot(t)
        t = self.TweezerLaser_obj.stop_tweezers(t)

        return t


# I think we should leave both 456 and 1064 stuff here because really the only debugging
# we would need to do is checking their overlap or looking for a Rydberg loss signal in the dipole trap
class RydSequence(TweezerSequence):
    def __init__(self):
        super(RydSequence, self).__init__()
        self.RydLasers_obj = RydLasers()

    def pulse_blue(self, t, dur):
        pass

    def pulse_1064(self, t, dur):
        pass


# Full Sequences, we'll see if we really want all these in a class or just separate sequence files?
class ScienceSequence(RydSequence):
    def __init__(self):
        super(ScienceSequence, self).__init__()


# Should we separate this from ScienceSequence?
class DiagnosticSequence(RydSequence):
    def __init__(self):
        super(DiagnosticSequence, self).__init__()


if __name__ == "__main__":
    labscript.start()
    t = 0

    # Insert "stay on" statements for alignment here...

    if shot_globals.do_mot_in_situ_check:
        MOTSeq_obj = MOTSequence(t)
        t = MOTSeq_obj._do_mot_in_situ_sequence(t, reset_mot=True)

    if shot_globals.do_mot_tof_check:
        MOTSeq_obj = MOTSequence(t)
        t = MOTSeq_obj._do_mot_tof_sequence(t, reset_mot=True)

    if shot_globals.do_molasses_in_situ_check:
        MOTSeq_obj = MOTSequence(t)
        t = MOTSeq_obj._do_molasses_in_situ_sequence(t, reset_mot=True)

    if shot_globals.do_molasses_tof_check:
        MOTSeq_obj = MOTSequence(t)
        t = MOTSeq_obj._do_molasses_tof_sequence(t, reset_mot=True)

    if shot_globals.do_field_calib_in_molasses_check:
        OPSeq_obj = OpticalPumpingSequence(t)
        t = OPSeq_obj._do_field_calib_in_molasses(t, reset_mot=True)

    # if shot_globals.do_dipole_trap_tof_check:
    #     t = do_dipole_trap_tof_check(t)

    # if shot_globals.do_img_beam_alignment_check:
    #     t = do_img_beam_alignment_check(t)

    # if shot_globals.do_tweezer_position_check:
    #     t = do_tweezer_position_check(t)

    if shot_globals.do_tweezer_check:
        TweezerSequence_obj = TweezerSequence(t)
        t = TweezerSequence_obj._do_tweezer_check_sequence(t)

    # if shot_globals.do_tweezer_check_fifo:
    #     t = do_tweezer_check_fifo(t)

    if shot_globals.do_optical_pump_in_tweezer_check:
        TweezerSequence_obj = TweezerSequence(t)
        t = TweezerSequence_obj._tweezer_basic_pump_kill_sequence(t)

    # if shot_globals.do_optical_pump_in_microtrap_check:
    #     t = do_optical_pump_in_microtrap_check(t)

    labscript.stop(t + 1e-2)
