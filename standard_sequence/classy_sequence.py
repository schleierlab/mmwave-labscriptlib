from __future__ import annotations

from typing import Literal

root_path = r"X:\userlib\labscriptlib"
import sys

if root_path not in sys.path:
    sys.path.append(root_path)
import labscript
import numpy as np
from labscriptlib.shot_globals import shot_globals
from labscriptlib.standard_sequence.experiment_components import (
    BField,
    Camera,
    D2Lasers,
    EField,
    Microwave,
    RydLasers,
    ShutterConfig,
    TweezerLaser,
    UVLamps,
)

from connection_table import devices

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
    """Sequence for Magneto-Optical Trap (MOT) operations.

    This class manages the sequence of operations related to MOT loading, imaging,
    and manipulation. It coordinates multiple hardware components including D2 lasers,
    magnetic fields, microwave systems, UV lamps, and cameras.
    """

    def __init__(self, t):
        # Standard initialization for hardware objects puts everything in
        # correct state/tuning to start loading the MOT
        self.D2Lasers_obj = D2Lasers(t)
        self.BField_obj = BField(t)
        self.EField_obj = EField(t)
        self.Microwave_obj = Microwave(t)
        self.UVLamps_obj = UVLamps(t)
        self.Camera_obj = Camera(t)

    def do_mot(self, t, dur, close_all_shutters=False):
        """Execute MOT loading sequence.

        Performs a complete MOT loading sequence, including optional UV enhancement
        and proper timing coordination between different components.

        Args:
            t (float): Start time for MOT sequence
            dur (float): Duration of MOT loading
            close_all_shutters (bool, optional): Whether to close all shutters after sequence

        Returns:
            float: End time of the MOT sequence
        """
        if shot_globals.mot_do_uv:
            t = self.UVLamps_obj.uv_pulse(t, dur=shot_globals.mot_uv_duration)
            # the uv duration should be determined for each dispenser current
            # generally, get superior loading in the 10s of milliseconds

        # possibly extend MOT loading to ensure
        # that UV light is off by the time MOT loading is complete
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
        """Reset MOT parameters to default values.

        Resets magnetic fields, laser frequencies, and other MOT parameters to their
        default values for MOT operation.

        Args:
            t (float): Time to begin reset

        Returns:
            float: End time of the reset sequence
        """

        # extra delay accounts for
        # TODO: consider methodically incorporating different notions of "start"
        t += 10e-3

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

        t += 10e-3

        return t

    def image_mot(self, t, close_all_shutters=False):
        """Capture an image of the MOT.

        Configures imaging parameters and captures an image of the MOT using the
        camera system.

        Args:
            t (float): Time to begin imaging
            close_all_shutters (bool, optional): Whether to close all shutters after imaging

        Returns:
            float: End time of the imaging sequence
        """
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
        """Perform in-situ MOT loading and imaging sequence.

        This standalone sequence loads a MOT and images it in-situ, optionally
        including a background image and MOT reset.

        Args:
            t (float): Start time for sequence
            reset_mot (bool, optional): Whether to reset MOT parameters after sequence

        Returns:
            float: End time of the sequence
        """
        print("Running _do_mot_in_situ_sequence")

        print("MOT coils = ", self.BField_obj.mot_coils_on)
        mot_load_dur = shot_globals.mot_load_dur

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
        """Perform time-of-flight MOT imaging sequence.

        This sequence loads a MOT, releases it, and images after a time-of-flight
        period to measure temperature or expansion.

        Args:
            t (float): Start time for sequence
            reset_mot (bool, optional): Whether to reset MOT parameters after sequence

        Returns:
            float: End time of the sequence
        """
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

    def ramp_to_molasses(self, t):
        """Configure system for optical molasses.

        Ramps laser detunings and turns off magnetic fields to transition from
        MOT to optical molasses configuration.

        Args:
            t (float): Time to begin transition

        Returns:
            float: End time of the transition
        """
        # detuning is ramped slowly here (duration = 1e-3) because atoms
        # see the light during the frequency ramp.
        self.D2Lasers_obj.ramp_ta_freq(t, 1e-3, shot_globals.bm_ta_detuning)
        self.D2Lasers_obj.ramp_repump_freq(t, 1e-3, shot_globals.bm_repump_detuning)

        self.BField_obj.switch_mot_coils(t)
        self.BField_obj.ramp_bias_field(t, bias_field_vector=(0, 0, 0))

        return t

    def do_molasses(self, t, dur, close_all_shutters=False):
        """Execute optical molasses cooling sequence.

        Performs optical molasses cooling with specified parameters and beam
        configurations.

        Args:
            t (float): Start time for molasses
            dur (float): Duration of molasses cooling
            close_all_shutters (bool, optional): Whether to close shutters after sequence

        Returns:
            float: End time of the molasses sequence
        """
        assert (
            shot_globals.do_molasses_img_beam or shot_globals.do_molasses_mot_beam
        ), "either do_molasses_img_beam or do_molasses_mot_beam has to be on"
        assert (
            shot_globals.bm_ta_detuning != 0
        ), "bright molasses detuning = 0. TA detuning should be non-zero for bright molasses."
        # print(f"molasses detuning is {shot_globals.bm_ta_detuning}")

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
        ta_detuning = 0,
        repump_power=1,
        do_repump=True,
        exposure_time=shot_globals.bm_exposure_time,
        close_all_shutters=False,
    ):
        """Capture an image of the molasses or the dipole trap.

        Configures imaging parameters and captures an image of the molasses or the
        dipole trap using the camera system.

        Args:
            t (float): Time to begin imaging
            ta_power (float, optional): Power of the TA beam
            repump_power (float, optional): Power of the repump beam
            exposure (float, optional): Exposure time of the camera
            do_repump (bool, optional): Whether to use the repump beam
            close_all_shutters (bool, optional): Whether to close all shutters after imaging

        Returns:
            float: End time of the imaging sequence
        """
        # zero the field
        _ = self.BField_obj.ramp_bias_field(t, bias_field_vector=(0, 0, 0))

        # Ramp to imaging frequencies
        self.D2Lasers_obj.ramp_ta_freq(t, D2Lasers.CONST_TA_VCO_RAMP_TIME, ta_detuning)
        self.D2Lasers_obj.ramp_repump_freq(t, D2Lasers.CONST_TA_VCO_RAMP_TIME, 0)
        t += D2Lasers.CONST_TA_VCO_RAMP_TIME

        shutter_config = ShutterConfig.select_imaging_shutters(do_repump=do_repump)

        # full power ta and repump pulse
        t_pulse_end, t_aom_start = self.D2Lasers_obj.do_pulse(
            t,
            exposure_time,
            shutter_config,
            ta_power,
            repump_power,
            close_all_shutters=close_all_shutters,
        )

        # TODO: ask Lin and Michelle and max() logic and if we always want it there
        self.Camera_obj.set_type(shot_globals.camera_type)
        if self.Camera_obj.type == "MOT_manta" or "tweezer_manta":
            exposure_time = max(exposure_time, 50e-6)
        elif self.Camera_obj.type == "kinetix":
            exposure_time = max(exposure_time, 1e-3)
        else:
            raise ValueError(f"Camera type {self.Camera_obj.type} not recognized")

        # expose the camera
        self.Camera_obj.expose(t_aom_start, exposure_time)

        # Closes the aom and the specified shutters
        t += exposure_time
        t = max(t, t_pulse_end)

        return t

    def _do_molasses_in_situ_sequence(self, t, reset_mot=False):
        """Perform in-situ molasses loading and imaging sequence.

        This standalone sequence loads a molasses and images it in-situ, optionally
        including a background image and MOT reset.

        Args:
            t (float): Start time for sequence
            reset_mot (bool, optional): Whether to reset MOT parameters after sequence

        Returns:
            float: End time of the sequence
        """
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
        """Perform time-of-flight molasses imaging sequence.

        This sequence loads a molasses, releases it, and images after a time-of-flight
        period to measure temperature or expansion.

        Args:
            t (float): Start time for sequence
            reset_mot (bool, optional): Whether to reset MOT parameters after sequence

        Returns:
            float: End time of the sequence
        """
        mot_load_dur = shot_globals.mot_load_dur

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
    """Sequence for optical pumping operations.

    This class manages sequences related to optical pumping of atoms between different
    hyperfine states (F=3 and F=4) of the Cs ground state (6S) using either MOT beams or sigma-polarized light.
    It inherits from MOTSequence and adds specialized optical pumping capabilities.
    """

    def __init__(self, t):
        """Initialize the optical pumping sequence.

        Args:
            t (float): Initial time for the sequence
        """
        super(OpticalPumpingSequence, self).__init__(t)

    def pump_to_F4(self, t, label: Literal['mot', 'sigma'], close_all_shutters=True):
        """Pump atoms from F=3 to F=4 hyperfine state.

        Uses either MOT beams or sigma-polarized light to pump atoms from the F=3
        to F=4 ground state. The method configures the appropriate magnetic fields,
        laser frequencies, and timing sequences based on the chosen pumping method.

        Args:
            t (float): Start time for the pumping sequence
            label (str): Pumping method to use ('mot' or 'sigma')
            close_all_shutters (bool, optional): Whether to close all shutters after
                the sequence. Defaults to True.

        Returns:
            tuple[float, float]: End time of sequence and AOM turn-off time

        Raises:
            NotImplementedError: If an unsupported pumping method is specified
        """
        if self.BField_obj.mot_coils_on:
            _ = self.BField_obj.switch_mot_coils(t)

        # Change the field orientation to be the same way as Adam Kaufman's thesis,
        # which is the major qunatization axis x always fixed to 2.8G
        # while we vary the angle and amplitude of an added-on field

        op_fixed_field = np.array([shot_globals.op_bias_amp, 0, 0])

        op_added_field = np.array(
                self.BField_obj.convert_bias_fields_sph_to_cart(
                    shot_globals.op_bias_added_amp,
                    shot_globals.op_bias_phi,
                    shot_globals.op_bias_theta,
                )
            )

        op_total_field = op_fixed_field + op_added_field

        if label == "mot":
            # Use the MOT beams for optical pumping
            # Do a repump pulse
            # print("I'm using mot beams for optical pumping")
            t = self.BField_obj.ramp_bias_field(
                t, bias_field_vector=op_total_field
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

            _ = self.BField_obj.ramp_bias_field(
                t, bias_field_vector = op_total_field
            )
            # ramp detuning to 4 -> 4, 3 -> 4
            self.D2Lasers_obj.ramp_ta_freq(
                t, D2Lasers.CONST_TA_VCO_RAMP_TIME, shot_globals.op_ta_pumping_detuning
            )
            self.D2Lasers_obj.ramp_repump_freq(
                t,
                D2Lasers.CONST_TA_VCO_RAMP_TIME,
                shot_globals.op_repump_pumping_detuning,
            )
            # Do a sigma+ pulse
            # We added op_ramp_delay because in the case of tweezer microwave, we can wait for the bias field to stabilize
            # but we can't do this for molasses because we need small time of flight to detect signal
            t += max(D2Lasers.CONST_TA_VCO_RAMP_TIME, shot_globals.op_ramp_delay)

            # Turns on shutters early so that pumping pulse happens at the end of the shutter time window
            # This is the "late OP" referenced in the lab notebook (2025 week 10)
            self.D2Lasers_obj.ta_aom_off(t)
            self.D2Lasers_obj.repump_aom_off(t)
            t = self.D2Lasers_obj.update_shutters(t, ShutterConfig.OPTICAL_PUMPING_FULL)
            t += D2Lasers.CONST_MIN_SHUTTER_ON_TIME

            t, t_aom_start = self.D2Lasers_obj.do_pulse(
                t,
                shot_globals.op_repump_time,
                ShutterConfig.OPTICAL_PUMPING_FULL,
                shot_globals.op_ta_power,
                shot_globals.op_repump_power,
                close_all_shutters=close_all_shutters,
            )

            t_aom_off = t_aom_start + shot_globals.op_repump_time

            assert (
                shot_globals.op_ta_time < shot_globals.op_repump_time
            ), "TA time should be shorter than repump for pumping to F=4"
            # TODO: test this timing
            self.D2Lasers_obj.ta_aom_off(t_aom_start + shot_globals.op_ta_time)
            self.D2Lasers_obj.ramp_ta_freq(
                t_aom_start + shot_globals.op_ta_time,
                D2Lasers.CONST_TA_VCO_RAMP_TIME,
                CONST_TA_PUMPING_DETUNING/2, # move the detuning to -125 MHz relative to 4->5 transtion to avoid the leakage light on 4->4 transition doing depump, half way between 4->5 and 4->4
            )
            # Close the shutters
            t = np.max([t, t_aom_start + shot_globals.op_ta_time + D2Lasers.CONST_TA_VCO_RAMP_TIME])#+= 1e-3
            return t, t_aom_off
        else:
            raise NotImplementedError("This optical pumping method is not implemented")

    def depump_ta_pulse(self, t, close_all_shutters=False):
        """Execute a TA pulse to depump atoms from F=4 to F=3.

        Performs a standalone TA pulse for depumping atoms from F=4 to F=3. This method
        is used to determine minimum time offsets between repump and TA when doing
        depump_to_F3, and for dark state measurements.

        Args:
            t (float): Start time for the depumping pulse
            close_all_shutters (bool, optional): Whether to close all shutters after
                the sequence. Defaults to True.

        Returns:
            float: End time of the depumping sequence
        """
        if self.BField_obj.mot_coils_on:
            _ = self.BField_obj.switch_mot_coils(t)

        t = self.D2Lasers_obj.ramp_ta_freq(
            t, D2Lasers.CONST_TA_VCO_RAMP_TIME, shot_globals.op_depump_ta_detuning #CONST_TA_PUMPING_DETUNING
        )
        # t += max(D2Lasers.CONST_TA_VCO_RAMP_TIME, shot_globals.op_ramp_delay)

        # The shutter configuration needs to be optical_pumping_full
        # to make sure no shutter switch from the depump_to_F3/pump_to_F4
        # sequence, this allow the two pulse sequence purely switched
        # with aom so that they are next to each other
        t, t_aom_start = self.D2Lasers_obj.do_pulse(
            t,
            shot_globals.op_depump_pulse_time,
            ShutterConfig.OPTICAL_PUMPING_TA,
            shot_globals.op_depump_power,
            0,
            close_all_shutters=close_all_shutters,
        )

        self.D2Lasers_obj.ramp_ta_freq(
            t_aom_start + shot_globals.op_depump_pulse_time,
            D2Lasers.CONST_TA_VCO_RAMP_TIME,
            CONST_TA_PUMPING_DETUNING/2, # move the detuning to -125 MHz relative to 4->5 transtion to avoid the leakage light on 4->4 transition doing depump, half way between 4->5 and 4->4
        )

        t = np.max([t, t_aom_start + shot_globals.op_depump_pulse_time + D2Lasers.CONST_TA_VCO_RAMP_TIME])#+= 1e-3

        return t

    def depump_to_F3(self, t, label, close_all_shutters=True):
        """Pump atoms from F=4 to F=3 hyperfine state.

        Uses either MOT beams or sigma-polarized light to pump atoms from the F=4
        to F=3 ground state. Similar to pump_to_F4 but optimized for depumping
        to minimize parameter complexity.

        Args:
            t (float): Start time for the depumping sequence
            label (str): Depumping method to use ('mot' or 'sigma')
            close_all_shutters (bool, optional): Whether to close all shutters after
                the sequence. Defaults to True.

        Returns:
            tuple[float, float]: End time of sequence and AOM turn-off time

        Raises:
            NotImplementedError: If an unsupported depumping method is specified
        """
        if self.BField_obj.mot_coils_on:
            _ = self.BField_obj.switch_mot_coils(t)
        if label == "mot":
            # Use the MOT beams for optical depumping
            # ramp detuning to 4 -> 4 for TA
            # print("I'm using mot beams for depumping")
            self.D2Lasers_obj.ramp_ta_freq(
                t, D2Lasers.CONST_TA_VCO_RAMP_TIME, CONST_TA_PUMPING_DETUNING
            )
            t += D2Lasers.CONST_TA_VCO_RAMP_TIME
            # Do a TA pulse
            t, t_aom_start = self.D2Lasers_obj.do_pulse(
                t,
                shot_globals.op_MOT_odp_time,
                ShutterConfig.MOT_TA,
                1,
                0,
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
            self.D2Lasers_obj.ramp_ta_freq(
                t, D2Lasers.CONST_TA_VCO_RAMP_TIME, shot_globals.op_ta_pumping_detuning
            )
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
                close_all_shutters=close_all_shutters,
            )

            t_aom_off = t_aom_start + shot_globals.odp_ta_time

            assert (
                shot_globals.odp_ta_time > shot_globals.odp_repump_time
            ), "TA time should be longer than repump for depumping to F = 3"
            # TODO: test this timing
            self.D2Lasers_obj.repump_aom_off(t_aom_start + shot_globals.odp_repump_time)

            return t, t_aom_off

        else:
            raise NotImplementedError(
                "This optical depumping method is not implemented"
            )

    def kill_F4(self, t, close_all_shutters=True):
        """Remove atoms in the F=4 hyperfine state using resonant light.

        Uses a resonant TA pulse to push away atoms in the F=4 state while leaving
        F=3 atoms unaffected. The method configures the appropriate shutter and
        laser parameters for efficient state-selective removal.

        Args:
            t (float): Start time for the removal sequence
            close_all_shutters (bool, optional): Whether to close all shutters after
                the sequence. Defaults to True.

        Returns:
            tuple[float, float]: End time of sequence and AOM turn-off time
        """
        # The shutter configuration can be optical_pumping_full or optical_pump_TA
        # optical_pumping_full allow the two pulse sequence purely switched with aom after
        # pump_to_F4 / depump_to_F3
        if self.D2Lasers_obj.shutter_config == ShutterConfig.OPTICAL_PUMPING_FULL:
            shutter_config = ShutterConfig.OPTICAL_PUMPING_FULL
        else:
            shutter_config = ShutterConfig.OPTICAL_PUMPING_TA

        # tune to resonance
        t = self.D2Lasers_obj.ramp_ta_freq(
            t, D2Lasers.CONST_TA_VCO_RAMP_TIME, shot_globals.killing_pulse_detuning
        )
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
        """Remove atoms in the F=3 hyperfine state.

        This method is not yet implemented but will provide functionality to
        selectively remove atoms in the F=3 state.

        Args:
            t (float): Start time for the removal sequence

        Raises:
            NotImplementedError: This method is not yet implemented
        """
        raise NotImplementedError

    def _do_optical_pump_in_molasses_sequence(self, t, reset_mot=False):
        """Execute a complete optical pumping sequence in molasses.

        Performs a sequence of: MOT loading, molasses cooling, optical pumping to F=4,
        and imaging. Optionally includes background imaging and MOT reset.

        Args:
            t (float): Start time for the sequence
            reset_mot (bool, optional): Whether to reset MOT parameters after sequence.
                Defaults to False.

        Returns:
            float: End time of the sequence
        """
        # MOT loading time 500 ms
        mot_load_dur = 0.5

        t = self.do_mot(t, mot_load_dur)
        t = self.do_molasses(t, shot_globals.bm_time)

        if shot_globals.do_op:
            t = self.pump_to_F4(t)

        if shot_globals.do_killing_pulse:
            t, _ = self.kill_F4(t)

        t = self.do_molasses_dipole_trap_imaging(t, close_all_shutters=True)

        # Turn off MOT for taking background images
        t += 1e-1

        t = self.do_molasses_dipole_trap_imaging(t, close_all_shutters=True)
        t += 1e-2

        if reset_mot:
            t = self.reset_mot(t)

        return t

    def _do_pump_debug_in_molasses(self, t, reset_mot=False):
        """Debug optical pumping sequence in molasses.

        Executes a comprehensive debug sequence for optical pumping, including options
        for depumping, pumping, dark state measurements, and microwave transitions.
        The sequence can be configured through shot_globals parameters for:
        - Depumping to F=3
        - Optical pumping to F=4
        - Dark state lifetime measurements
        - Microwave transitions
        - State-selective removal
        - Imaging with variable parameters

        Args:
            t (float): Start time for the sequence
            reset_mot (bool, optional): Whether to reset MOT parameters after sequence.
                Defaults to False.

        Returns:
            float: End time of the sequence
        """
        mot_load_dur = 0.5
        t = self.do_mot(t, mot_load_dur)
        t = self.do_molasses(t, shot_globals.bm_time)

        if shot_globals.do_dp:
            # do optical depumping to F=3
            t, t_aom_off = self.depump_to_F3(t, shot_globals.op_label)
        if shot_globals.do_op:
            # do optical pumping to F=4
            t, t_aom_off = self.pump_to_F4(
                t, shot_globals.op_label, close_all_shutters=False
            )
            t_aom_off += 50e-6

        if shot_globals.do_depump_ta_pulse_after_pump:
            # do depump pulse to meausre the dark state lifetime
            t = self.depump_ta_pulse(t_aom_off, close_all_shutters=True)
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
            exposure_time=10e-3,
            do_repump=shot_globals.mw_imaging_do_repump,
            close_all_shutters=True,
        )

        # Turn off MOT for taking background images
        t += 1e-1

        t = self.do_molasses_dipole_trap_imaging(
            t,
            ta_power=0.1,
            repump_power=1,
            exposure_time=10e-3,
            do_repump=shot_globals.mw_imaging_do_repump,
            close_all_shutters=True,
        )
        t += 1e-2
        t = self.Microwave_obj.reset_spectrum(t)
        if reset_mot:
            t = self.reset_mot(t)

        return t

    def _do_F4_microwave_spec_molasses(self, t, reset_mot=False):
        """Measure microwave transitions with atoms initially in F=4.

        Performs a sequence to measure microwave transitions starting with atoms in F=4:
        1. Load MOT and cool to molasses
        2. Optically pump atoms to F=4
        3. Apply microwave pulse or frequency sweep
        4. Selectively remove F=4 atoms
        5. Image remaining atoms

        The sequence operates in molasses conditions for better control and can be
        configured for either fixed-frequency pulses or frequency sweeps through
        shot_globals parameters.

        Args:
            t (float): Start time for the sequence
            reset_mot (bool, optional): Whether to reset MOT parameters after sequence.
                Defaults to False.

        Returns:
            float: End time of the sequence
        """
        mot_load_dur = 0.5
        t = self.do_mot(t, mot_load_dur)
        t = self.do_molasses(t, shot_globals.bm_time)
        t, t_aom_off = self.pump_to_F4(
            t, shot_globals.op_label, close_all_shutters=False,
        )

        # [mw_biasx_field, mw_biasy_field, mw_biasz_field] = [
            #     shot_globals.mw_biasx_field,
            #     shot_globals.mw_biasy_field,
            #     shot_globals.mw_biasz_field,
            # ]

        t = self.BField_obj.ramp_bias_field(
                t_aom_off + 200e-6, #TODO: wait for 200e-6s extra time in optical pumping field, can be changed
                bias_field_vector=(shot_globals.mw_bias_amp,
                                   shot_globals.mw_bias_phi,
                                   shot_globals.mw_bias_theta),
                polar = True
            )

        t += self.BField_obj.CONST_COIL_OFF_TIME

        if shot_globals.do_mw_pulse:
            t = self.Microwave_obj.do_pulse(t, shot_globals.mw_time)
        elif shot_globals.do_mw_sweep:
            mw_sweep_start = shot_globals.mw_detuning + shot_globals.mw_sweep_range / 2
            mw_sweep_end = shot_globals.mw_detuning - shot_globals.mw_sweep_range / 2
            t = self.Microwave_obj.do_sweep(
                t, mw_sweep_start, mw_sweep_end, shot_globals.mw_sweep_duration
            )

        t += 3e-6 #TODO: wait for extra time before killing, can be changed
        if shot_globals.do_killing_pulse:
            t, _ = self.kill_F4(t, close_all_shutters=True)
        # This is the only place required for the special value of imaging
        # t += 1e-3 # TODO: from the photodetector, the optical pumping beam shutter seems to be closing slower than others
        # that's why we add extra time here before imaging to prevent light leakage from optical pump beam
        t = self.do_molasses_dipole_trap_imaging(
            t,
            ta_power=0.1,
            repump_power=1,
            exposure_time=10e-3,
            do_repump=True,
            close_all_shutters=True,
        )
        # Turn off MOT for taking background images
        t += 1e-1

        t = self.do_molasses_dipole_trap_imaging(
            t,
            ta_power=0.1,
            repump_power=1,
            exposure_time=10e-3,
            do_repump=True,
            close_all_shutters=True,
        )
        if reset_mot:
            t = self.reset_mot(t)

        return t


class TweezerSequence(OpticalPumpingSequence):
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
        super(TweezerSequence, self).__init__(t)
        self.TweezerLaser_obj = TweezerLaser(t)

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
            AssertionError: If imaging TA or repump powers are set to zero
        """
        t = self.BField_obj.ramp_bias_field(t, bias_field_vector=(0, 0, 0))
        t = self.D2Lasers_obj.ramp_ta_freq(
            t, D2Lasers.CONST_TA_VCO_RAMP_TIME, shot_globals.img_ta_detuning
        )
        self.D2Lasers_obj.ramp_repump_freq(t, D2Lasers.CONST_TA_VCO_RAMP_TIME, 0)
        assert shot_globals.img_ta_power != 0, "img_ta_power should not be zero"
        assert shot_globals.img_repump_power != 0, "img_repump_power should not be zero"

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
            AssertionError: If time-of-flight delay is too short
        """
        # TODO this still spends some time loading the MOT;
        # figure out whether we even need this here at all.
        t = self.do_mot(t, dur=0)  # MOT loads between shots, don't need to spend extra time

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
        """Rearrange atoms into a dense configuration.

        Not yet implemented. Will provide functionality to rearrange atoms
        in tweezers to form dense arrays or specific patterns.

        Args:
            t (float): Start time for rearrangement
        """
        pass

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
        if shot_number == 2:
            # pulse for the second shots and wait for the first shot to finish the
            # first reading
            # print(shot_globals.kinetix_roi_row)
            kinetix_readout_time = shot_globals.kinetix_roi_row[1] * 4.7065e-6
            # need extra 7 ms for shutter to close on the second shot
            # TODO: is shot_globals.kinetix_extra_readout_time always zero? Delete if so.
            t += kinetix_readout_time + shot_globals.kinetix_extra_readout_time
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

    def _do_tweezer_check_sequence(self, t):
        """Perform a basic tweezer loading and imaging check sequence.

        Executes a complete sequence to verify tweezer operation:
        1. Load atoms into tweezers
        2. Take first image
        3. Wait specified time
        4. Take second image
        5. Reset MOT parameters

        Args:
            t (float): Start time for the sequence

        Returns:
            float: End time of the sequence
        """
        t = self.load_tweezers(t)
        t = self.image_tweezers(t, shot_number=1)
        # TODO: add tweezer modulation here, or in a separate sequence?
        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
        t = self.reset_mot(t)
        # t = self.TweezerLaser_obj.stop_tweezers(t)

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

        if shot_globals.do_depump_ta_pulse_before_pump:
            t = self.depump_ta_pulse(t)

        if shot_globals.do_op:
            t, t_aom_off = self.pump_to_F4(
                t, shot_globals.op_label, close_all_shutters=True
            )
        elif shot_globals.do_dp:
            t, t_aom_off = self.depump_to_F3(
                t, shot_globals.op_label, close_all_shutters=False
            )

        if shot_globals.do_depump_ta_pulse_after_pump:
            t_aom_off = self.depump_ta_pulse(t)

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
            t = self.Microwave_obj.do_pulse(t, shot_globals.mw_time)
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
            t = self.depump_ta_pulse(t)

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
            t = self.depump_ta_pulse(t)

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
        if shot_globals.do_mw_pulse:
            # self.TweezerLaser_obj.aom_off(t)
            t = self.Microwave_obj.do_pulse(t, shot_globals.mw_time)
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
        t = self.TweezerLaser_obj.ramp_power(t_aom_off + 15e-3, shot_globals.tw_ramp_dur, 0.99)
        # t = self.TweezerLaser_obj.ramp_power(t, shot_globals.tw_ramp_dur, 0.99)

        t += 2e-3  # TODO: from the photodetector, the optical pumping beam shutter seems to be closing slower than others
        # that's why we add extra time here before imaging to prevent light leakage from optical pump beam
        t += shot_globals.img_wait_time_between_shots
        t = self.image_tweezers(t, shot_number=2)
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

        t = self.depump_ta_pulse(t, close_all_shutters=False)

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

class RydSequence(TweezerSequence):
    def __init__(self, t):
        super(RydSequence, self).__init__(t)
        self.RydLasers_obj = RydLasers(t)

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
            ta_power=shot_globals.dp_img_ta_power,
            ta_detuning = shot_globals.dp_img_ta_detuning,
            repump_power=shot_globals.dp_img_repump_power,
            do_repump=True,
            exposure_time=shot_globals.dp_img_exposure_time,
            close_all_shutters=False,
        )

        self.RydLasers_obj.pulse_1064_aom_off(t)

        t+= 1e-1
        # Background image
        t = self.do_molasses_dipole_trap_imaging(
            t,
            ta_power=shot_globals.dp_img_ta_power,
            ta_detuning = shot_globals.dp_img_ta_detuning,
            repump_power=shot_globals.dp_img_repump_power,
            do_repump=True,
            exposure_time=shot_globals.dp_img_exposure_time,
            close_all_shutters=False,
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

    # if shot_globals.do_dipole_trap_tof_check:
    #     t = do_dipole_trap_tof_check(t)

    # if shot_globals.do_img_beam_alignment_check:
    #     t = do_img_beam_alignment_check(t)

    elif shot_globals.do_tweezer_check:
        TweezerSequence_obj = TweezerSequence(t)
        sequence_objects.append(TweezerSequence_obj)
        t = TweezerSequence_obj._do_tweezer_check_sequence(t)

    elif shot_globals.do_tweezer_position_check:
        TweezerSequence_obj = TweezerSequence(t)
        sequence_objects.append(TweezerSequence_obj)
        t = TweezerSequence_obj._do_tweezer_position_check_sequence(t)

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
