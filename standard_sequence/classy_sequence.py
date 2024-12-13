from __future__ import annotations

root_path = r"X:\userlib\labscriptlib"
import sys

if root_path not in sys.path:
    sys.path.append(root_path)
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
        if shot_globals.mot_do_uv:
            t = self.UVLamps_obj.uv_pulse(t, dur=shot_globals.mot_uv_duration)
            # the uv duration should be determined for each dispenser current
            # generally, get superior loading in the 10s of milliseconds

        # if using a long UV duration, want to make sure that the MOT doesn't finish
        # loading leaving the UV is still on for imaging.
        dur = max(dur, shot_globals.mot_uv_duration)
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
            print("I'm using mot beams for optical pumping")

            op_biasx_field, op_biasy_field, op_biasz_field = (
                self.BField_obj.get_op_bias_fields()
            )
            t = self.BField_obj.ramp_bias_field(
                t, bias_field_vector=(op_biasx_field, op_biasy_field, op_biasz_field)
            )

            t, t_aom_start = self.D2Lasers_obj.do_pulse(
                t,
                shot_globals.op_MOT_op_time,
                ShutterConfig.MOT_REPUMP,
                0,
                1,
                close_all_shutters=close_all_shutters,
            )

            t_aom_off = t_aom_start + shot_globals.op_MOT_op_time
            return t, t_aom_off

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
                close_all_shutters=close_all_shutters
            )

            t_aom_off = t_aom_start + shot_globals.op_repump_time

            assert (
                shot_globals.op_ta_time < shot_globals.op_repump_time
            ), "TA time should be shorter than repump for pumping to F=4"
            # TODO: test this timing
            self.D2Lasers_obj.ta_aom_off(
                t_aom_start + shot_globals.op_ta_time
            )
            # Close the shutters
            return t, t_aom_off
        else:
            raise NotImplementedError("This optical pumping method is not implemented")



    def depump_ta_pulse(self, t, close_all_shutters = True):
        # This method is only depump pulse with ta alone to pump atom from F=4 -> F=3
        # This will determine the minimum time offset between repump and ta when doing depump_to_F3
        # This will also be used in dark state measurement
        if self.BField_obj.mot_coils_on:
            _ = self.BField_obj.switch_mot_coils(t)

        t = self.D2Lasers_obj.ramp_ta_freq(t, D2Lasers.CONST_TA_VCO_RAMP_TIME, CONST_TA_PUMPING_DETUNING)
        #t += max(D2Lasers.CONST_TA_VCO_RAMP_TIME, shot_globals.op_ramp_delay)

        # The shutter configuration needs to be optical_pumping_full
        # to make sure no shutter switch from the depump_to_F3/pump_to_F4
        # sequence, this allow the two pulse sequence purely switched
        # with aom so that they are next to each other
        t, _ = self.D2Lasers_obj.do_pulse(
                t,
                shot_globals.op_depump_pulse_time,
                ShutterConfig.OPTICAL_PUMPING_FULL,
                shot_globals.op_depump_power,
                0,
                close_all_shutters = close_all_shutters
            )


        return t

    def depump_to_F3(self, t, label, close_all_shutters = True):
        # This method should be quite similar to pump_to_F4, but trying to call pump_to_F4 with
        # different parameters would produce a very long argument list
        if self.BField_obj.mot_coils_on:
            _ = self.BField_obj.switch_mot_coils(t)
        if label == "mot":
            # Use the MOT beams for optical depumping
            # ramp detuning to 4 -> 4 for TA
            print("I'm using mot beams for depumping")
            self.D2Lasers_obj.ramp_ta_freq(t, D2Lasers.CONST_TA_VCO_RAMP_TIME, CONST_TA_PUMPING_DETUNING)
            t += D2Lasers.CONST_TA_VCO_RAMP_TIME
            # Do a TA pulse
            t, t_aom_start= self.D2Lasers_obj.do_pulse(
                t,
                shot_globals.op_MOT_odp_time,
                ShutterConfig.MOT_TA,
                1,
                0,
                close_all_shutters = close_all_shutters,
            )

            t_aom_off = t_aom_start + shot_globals.op_MOT_op_time
            return t, t_aom_off

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
            self.D2Lasers_obj.ramp_repump_freq(t, D2Lasers.CONST_TA_VCO_RAMP_TIME, 0)
            # 3-> 3
            # self.D2Lasers_obj.ramp_repump_freq(t, D2Lasers.CONST_TA_VCO_RAMP_TIME, CONST_REPUMP_DEPUMPING_DETUNING)
            # Do a sigma+ pulse
            # TODO: is shot_globals.op_ramp_delay just extra fudge time? can it be eliminated?
            t += max(D2Lasers.CONST_TA_VCO_RAMP_TIME, shot_globals.op_ramp_delay)
            t, t_aom_start = self.D2Lasers_obj.do_pulse(
                t,
                shot_globals.odp_ta_time,
                ShutterConfig.OPTICAL_PUMPING_FULL,
                shot_globals.odp_ta_power,
                shot_globals.odp_repump_power,
                close_all_shutters = close_all_shutters
            )

            t_aom_off = t_aom_start + shot_globals.odp_ta_time

            assert (
                shot_globals.odp_ta_time > shot_globals.odp_repump_time
            ), "TA time should be longer than repump for depumping to F = 3"
            # TODO: test this timing
            self.D2Lasers_obj.repump_aom_off(
                t_aom_start + shot_globals.odp_repump_time
            )


            return t, t_aom_off

        else:
            raise NotImplementedError(
                "This optical depumping method is not implemented"
            )

    # def kill_F4(self, t, close_all_shutters = True):
    #     """Push away atoms in F = 4"""
    #     # The shutter configuration can be optical_pumping_full or optical_pump_TA
    #     # optical_pumping_full allow the two pulse sequence purely switched with aom after
    #     # pump_to_F4 / depump_to_F3
    #     if self.D2Lasers_obj.shutter_config == ShutterConfig.OPTICAL_PUMPING_FULL:
    #         shutter_config = ShutterConfig.OPTICAL_PUMPING_FULL
    #     else:
    #         shutter_config = ShutterConfig.OPTICAL_PUMPING_TA

    #     # tune to resonance
    #     self.D2Lasers_obj.ramp_ta_freq(t, D2Lasers.CONST_TA_VCO_RAMP_TIME, shot_globals.killing_pulse_detuning)
    #     t += D2Lasers.CONST_TA_VCO_RAMP_TIME
    #     # do a ta pulse via optical pumping path
    #     t, _ = self.D2Lasers_obj.do_pulse(
    #         t,
    #         shot_globals.op_killing_pulse_time,
    #         shutter_config,
    #         shot_globals.op_killing_ta_power,
    #         0,
    #         close_all_shutters=close_all_shutters,
    #     )

    #     return t

    def kill_F4(self, t, close_all_shutters = True):
        """Push away atoms in F = 4"""
        # The shutter configuration can be optical_pumping_full or optical_pump_TA
        # optical_pumping_full allow the two pulse sequence purely switched with aom after
        # pump_to_F4 / depump_to_F3
        if self.D2Lasers_obj.shutter_config == ShutterConfig.OPTICAL_PUMPING_FULL:
            shutter_config = ShutterConfig.OPTICAL_PUMPING_FULL
        else:
            shutter_config = ShutterConfig.OPTICAL_PUMPING_TA

        # tune to resonance
        self.D2Lasers_obj.ramp_ta_freq(t-D2Lasers.CONST_TA_VCO_RAMP_TIME, D2Lasers.CONST_TA_VCO_RAMP_TIME, shot_globals.killing_pulse_detuning)
        # do a ta pulse via optical pumping path
        t, t_aom_start = self.D2Lasers_obj.do_pulse(
            t,
            shot_globals.op_killing_pulse_time,
            shutter_config,
            shot_globals.op_killing_ta_power,
            0,
            close_all_shutters=close_all_shutters,
        )

        t_aom_off = t_aom_start + shot_globals.op_killing_pulse_time

        return t, t_aom_off

    def kill_F3(self, t):
        raise NotImplementedError

    def _optical_pump_molasses_sequence(self, t, reset_mot=False):
        # MOT loading time 500 ms
        mot_load_dur = 0.5


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

    def _do_pump_debug_in_molasses(self, t, reset_mot=False):
        mot_load_dur = 0.5
        t = self.do_mot(t, mot_load_dur)
        t = self.do_molasses(t, shot_globals.bm_time)


        if shot_globals.do_dp:
            # do optical depumping to F=3
            t, t_aom_off= self.depump_to_F3(t, shot_globals.op_label)
        if shot_globals.do_op:
            # do optical pumping to F=4
            t, t_aom_off = self.pump_to_F4(t, shot_globals.op_label, close_all_shutters = False)
            t_aom_off+=50e-6

        if shot_globals.do_depump_pulse_after_pumping:
            # do depump pulse to meausre the dark state lifetime
            t = self.depump_ta_pulse(t_aom_off, close_all_shutters = True)
        if shot_globals.do_killing_pulse:
            # do kill pulse to remove all atom in F=4
            t, _ = self.kill_F4(t_aom_off)
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
            # do microwave in molasses
            t = self.Microwave_obj.do_pulse(t, shot_globals.mw_time)

        if shot_globals.do_killing_pulse:
            # do kill pulse after microwave to remove F=4 atom
            t, _ = self.kill_F4(t_aom_off)

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

    def _do_F4_microwave_spec_molasses(self, t, reset_mot=False):
        """ measuring the microwave transition with atom initially pumping to F=4
        OP + microwave + killing + imaging atom with repump"""
        mot_load_dur = 0.5
        t = self.do_mot(t, mot_load_dur)
        t = self.do_molasses(t, shot_globals.bm_time)
        t, t_aom_off = self.pump_to_F4(t, shot_globals.op_label, close_all_shutters = False)

        t = self.BField_obj.ramp_bias_field(
            t_aom_off + 200e-6,
            bias_field_vector=(
                shot_globals.mw_biasx_field,
                shot_globals.mw_biasy_field,
                shot_globals.mw_biasz_field,
            ),
            # dur = 2e-3
        )


        t += self.BField_obj.CONST_COIL_OFF_TIME

        if shot_globals.do_mw_pulse:
            t = self.Microwave_obj.do_pulse(t, shot_globals.mw_time)
        elif shot_globals.do_mw_sweep:
                mw_sweep_start = shot_globals.mw_detuning + shot_globals.mw_sweep_range/2
                mw_sweep_end = shot_globals.mw_detuning - shot_globals.mw_sweep_range/2
                t = self.Microwave_obj.do_sweep(t, mw_sweep_start, mw_sweep_end, shot_globals.mw_sweep_duration)


        t, _ = self.kill_F4(t, close_all_shutters = True)
        # This is the only place required for the special value of imaging
        # t += 1e-3 # TODO: from the photodetector, the optical pumping beam shutter seems to be closing slower than others
        # that's why we add extra time here before imaging to prevent light leakage from optical pump beam
        t = self.do_molasses_dipole_trap_imaging(
            t,
            ta_power=0.1,
            repump_power=1,
            exposure=10e-3,
            do_repump=True,
            close_all_shutters=True,
        )
        # Turn off MOT for taking background images
        t += 1e-1

        t = self.do_molasses_dipole_trap_imaging(
            t,
            ta_power=0.1,
            repump_power=1,
            exposure=10e-3,
            do_repump=True,
            close_all_shutters=True,
        )
        t += 1e-2
        if reset_mot:
            t = self.reset_mot(t)

        return t


# ExperimentalSequence > F4MicrowaveSpectrumMolasses: at the end of a seq, merge lists of cleanupabbles from Helpers, call cleanupabble.cleanup() for each
# MOTHelper, OPHelper: [TweezerLAser, Microwave, ...]
# TweezerLaser, Microwave,: cleanup()
# Spectrum (Jacob): stop()


# class ExperimentalSequence(ABC):
#     helpers: list

#     @abstractmethod
#     def sequence(self): ...

#     def run(self):
#         self.sequence()
#         cleanupabbles = set(
#             helper.cleanupabbles
#             for helper in self.helpers
#         )
#         for cleanupabble in cleanupabbles:
#             cleanupabble.cleanup()

# class F4MicrowaveSpectrumMolasses(ExperimentalSequence):
#     def __init__(self, spectrum_mgr):
#         self.spectrum_mgr = spectrum_mgr
#         self.helpers = []

#     def sequence(self):
#         ...

class TweezerSequence(OpticalPumpingSequence):
    def __init__(self, t):
        super(TweezerSequence, self).__init__(t)
        self.TweezerLaser_obj = TweezerLaser(t)

    def ramp_to_imaging_parameters(self, t):
        # ramping to imaging detuning and power, previously referred to as "pre_imaging"
        # also used for additional cooling
        t = self.BField_obj.ramp_bias_field(t, bias_field_vector=(0, 0, 0))
        t = self.D2Lasers_obj.ramp_ta_freq(t, D2Lasers.CONST_TA_VCO_RAMP_TIME, shot_globals.img_ta_detuning)
        self.D2Lasers_obj.ramp_repump_freq(t, D2Lasers.CONST_TA_VCO_RAMP_TIME, 0)
        assert shot_globals.img_ta_power != 0, "img_ta_power should not be zero"
        assert shot_globals.img_repump_power != 0, "img_repump_power should not be zero"

        return t


    def load_tweezers(self, t):
        t = self.do_mot(t, dur=0.5)
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
        t = self.ramp_to_imaging_parameters(t)
        if shot_number == 1:
            t = self.do_tweezer_imaging(
                t, close_all_shutters=shot_globals.do_shutter_close_after_first_shot
            )
        if shot_number == 2:
            # pulse for the second shots and wait for the first shot to finish the
            # first reading
            kinetix_readout_time = shot_globals.kinetix_roi_row[1] * 4.7065e-6
            # need extra 7 ms for shutter to close on the second shot
            # TODO: is shot_globals.kinetix_extra_readout_time always zero? Delete if so.
            t += kinetix_readout_time + shot_globals.kinetix_extra_readout_time
            t = self.do_tweezer_imaging(t, close_all_shutters=True)
        return t

    def do_tweezer_imaging(self, t, close_all_shutters=False):
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
        # t = self.TweezerLaser_obj.stop_tweezers(t)

        return t

    def _tweezer_release_recapture_sequence(self, t):
        pass

    def _tweezer_modulation_sequence(self, t):
        pass

    def _do_optical_pump_in_tweezer_check(self, t):
        t = self.load_tweezers(t)
        t = self.image_tweezers(t, shot_number=1)

        t+=3e-3

        if shot_globals.do_depump_pulse_before_pumping:
            t = self.depump_ta_pulse(t)

        if shot_globals.do_op:
            t, t_aom_off = self.pump_to_F4(t, shot_globals.op_label, close_all_shutters = False)
        elif shot_globals.do_dp:
            t, t_aom_off = self.depump_to_F3(t, shot_globals.op_label, close_all_shutters = False)

        if shot_globals.op_label =="mot":

            if shot_globals.do_depump_pulse_after_pumping:
                t_aom_off = self.depump_ta_pulse(t_aom_off)

            t = self.BField_obj.ramp_bias_field(
                t_aom_off,
                bias_field_vector=(
                    shot_globals.mw_biasx_field,
                    shot_globals.mw_biasy_field,
                    shot_globals.mw_biasz_field,
                ),
                dur = shot_globals.mw_bias_ramp_dur
            )

            #Making sure there is enough time between the MOT pumping pulse and the killing pulse to switch shutters
            t= t + max(D2Lasers.CONST_MIN_SHUTTER_ON_TIME + D2Lasers.CONST_SHUTTER_TURN_ON_TIME - shot_globals.tw_ramp_dur, 0)
            t += shot_globals.mw_field_wait_dur
            t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, shot_globals.tw_ramp_power)

            if shot_globals.do_mw_pulse:
                # self.TweezerLaser_obj.aom_off(t)
                t = self.Microwave_obj.do_pulse(t, shot_globals.mw_time)
                # self.TweezerLaser_obj.aom_on(t, shot_globals.tw_ramp_power)
            elif shot_globals.do_mw_sweep:
                mw_sweep_start = shot_globals.mw_detuning + shot_globals.mw_sweep_range/2
                mw_sweep_end = shot_globals.mw_detuning - shot_globals.mw_sweep_range/2
                t = self.Microwave_obj.do_sweep(t, mw_sweep_start, mw_sweep_end, shot_globals.mw_sweep_duration)

            if shot_globals.do_killing_pulse:
            #If we use the MOT beams for pumping we have to switch shutters
            #Our pulse function is set so that switching the shutters adds time before the pulse
            #Here though we want the shutter switching to overlap with the tweezer ramp rather than start after it
                t  = t - D2Lasers.CONST_SHUTTER_TURN_ON_TIME
                t, _ = self.kill_F4(t, close_all_shutters = False)
            else:
                t+= shot_globals.op_killing_pulse_time


        if shot_globals.op_label == "sigma":
            #Making sure the ramp ends right as the pumping is starting
            t_start_ramp = t_aom_off - shot_globals.tw_ramp_dur - shot_globals.op_repump_time
            _ = self.TweezerLaser_obj.ramp_power(t_start_ramp, shot_globals.tw_ramp_dur, shot_globals.tw_ramp_power)

            if shot_globals.do_depump_pulse_after_pumping:
                t = self.depump_ta_pulse(t)

            t = self.BField_obj.ramp_bias_field(
                t_aom_off + shot_globals.op_extra_fudge_time,
                bias_field_vector=(
                    shot_globals.mw_biasx_field,
                    shot_globals.mw_biasy_field,
                    shot_globals.mw_biasz_field,
                ),
            )

            t += shot_globals.mw_field_wait_dur #400e-6
            if shot_globals.do_mw_pulse:
                # self.TweezerLaser_obj.aom_off(t)
                t = self.Microwave_obj.do_pulse(t, shot_globals.mw_time)
                # self.TweezerLaser_obj.aom_on(t, shot_globals.tw_ramp_power)
            elif shot_globals.do_mw_sweep:
                mw_sweep_start = shot_globals.mw_detuning + shot_globals.mw_sweep_range/2
                mw_sweep_end = shot_globals.mw_detuning - shot_globals.mw_sweep_range/2
                t = self.Microwave_obj.do_sweep(t, mw_sweep_start, mw_sweep_end, shot_globals.mw_sweep_duration)

            if shot_globals.do_killing_pulse:
                t, _ = self.kill_F4(t, close_all_shutters = False)
            else:
                t+= shot_globals.op_killing_pulse_time

        t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99)
        t += 2e-3 # TODO: from the photodetector, the optical pumping beam shutter seems to be closing slower than others
            # that's why we add extra time here before imaging to prevent light leakage from optical pump beam
        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
        t = self.reset_mot(t)


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





if __name__ == "__main__":
    labscript.start()
    t = 0

    # Insert "stay on" statements for alignment here...


    if shot_globals.do_mot_in_situ_check:
        MOTSeq_obj = MOTSequence(t)
        t = MOTSeq_obj._do_mot_in_situ_sequence(t, reset_mot=True)

    elif shot_globals.do_mot_tof_check:
        MOTSeq_obj = MOTSequence(t)
        t = MOTSeq_obj._do_mot_tof_sequence(t, reset_mot=True)

    elif shot_globals.do_molasses_in_situ_check:
        MOTSeq_obj = MOTSequence(t)
        t = MOTSeq_obj._do_molasses_in_situ_sequence(t, reset_mot=True)

    elif shot_globals.do_molasses_tof_check:
        MOTSeq_obj = MOTSequence(t)
        t = MOTSeq_obj._do_molasses_tof_sequence(t, reset_mot=True)

    elif shot_globals.do_pump_debug_in_molasses:
        OPSeq_obj = OpticalPumpingSequence(t)
        t = OPSeq_obj._do_pump_debug_in_molasses(t, reset_mot=True)

    elif shot_globals.do_F4_microwave_spec_molasses:
        OPSeq_obj = OpticalPumpingSequence(t)
        t = OPSeq_obj._do_F4_microwave_spec_molasses(t, reset_mot=True)

    # if shot_globals.do_dipole_trap_tof_check:
    #     t = do_dipole_trap_tof_check(t)

    # if shot_globals.do_img_beam_alignment_check:
    #     t = do_img_beam_alignment_check(t)

    # if shot_globals.do_tweezer_position_check:
    #     t = do_tweezer_position_check(t)

    elif shot_globals.do_tweezer_check:
        TweezerSequence_obj = TweezerSequence(t)
        t = TweezerSequence_obj._do_tweezer_check_sequence(t)

    # if shot_globals.do_tweezer_check_fifo:
    #     t = do_tweezer_check_fifo(t)

    elif shot_globals.do_optical_pump_in_tweezer_check:
        TweezerSequence_obj = TweezerSequence(t)
        t = TweezerSequence_obj._do_optical_pump_in_tweezer_check(t)

    # if shot_globals.do_optical_pump_in_microtrap_check:
    #     t = do_optical_pump_in_microtrap_check(t)


    """ Here doing all the finish up quirk for spectrum cards """
    try:
        current_obj = MOTSeq_obj
    except:
        try:
            current_obj = OPSeq_obj
        except:
            try:
                current_obj = TweezerSequence_obj
            except:
                raise NotImplementedError
            t = current_obj.TweezerLaser_obj.stop_tweezers(t)

    t = current_obj.Microwave_obj.reset_spectrum(t)

    labscript.stop(t + 1e-2)
