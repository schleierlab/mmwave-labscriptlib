
from typing import Literal
import numpy as np

from labscriptlib.experiment_components import D2Lasers, Microwave, ShutterConfig
from labscriptlib.shot_globals import shot_globals
from .mot import MOTOperations


class OpticalPumpingOperations(MOTOperations):
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
        super(OpticalPumpingOperations, self).__init__(t)
        self.Microwave_obj = Microwave(t, init_detuning=shot_globals.mw_detuning)

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
            # We have to write it in this order so that the aom_off functions get passed the t the shutters are open
            # open by, and then that they turn off the aoms CONST_SHUTTER_TURN_ON_TIME before that.
            t = self.D2Lasers_obj.update_shutters(t, ShutterConfig.OPTICAL_PUMPING_FULL)
            self.D2Lasers_obj.ta_aom_off(t - D2Lasers.CONST_SHUTTER_TURN_ON_TIME)
            self.D2Lasers_obj.repump_aom_off(t - D2Lasers.CONST_SHUTTER_TURN_ON_TIME)
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

            if shot_globals.op_ta_time >= shot_globals.op_repump_time:
                raise ValueError("TA time should be shorter than repump for pumping to F=4")

            # TODO: test this timing
            self.D2Lasers_obj.ta_aom_off(t_aom_start + shot_globals.op_ta_time)
            self.D2Lasers_obj.ramp_ta_freq(
                t_aom_start + shot_globals.op_ta_time,
                D2Lasers.CONST_TA_VCO_RAMP_TIME,
                # move the detuning to -125 MHz relative to 4->5 transtion
                # to avoid leakage light on the 4->4 transition doing depump.
                # this is half way between 4->5 and 4->4
                D2Lasers.CONST_TA_PUMPING_DETUNING/2,
            )
            # Close the shutters
            t = np.max([t, t_aom_start + shot_globals.op_ta_time + D2Lasers.CONST_TA_VCO_RAMP_TIME])#+= 1e-3
            return t, t_aom_off
        else:
            raise NotImplementedError("This optical pumping method is not implemented")

    #TODO: We have 2 depumping sequence. We need to consolidate this.
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
            # move the detuning to -125 MHz relative to 4->5 transtion
            # to avoid leakage light on the 4->4 transition doing depump.
            # this is half way between 4->5 and 4->4
            D2Lasers.CONST_TA_PUMPING_DETUNING/2,
        )

        t = np.max([t, t_aom_start + shot_globals.op_depump_pulse_time + D2Lasers.CONST_TA_VCO_RAMP_TIME])#+= 1e-3

        return t, t_aom_start

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
                t, D2Lasers.CONST_TA_VCO_RAMP_TIME, D2Lasers.CONST_TA_PUMPING_DETUNING
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

            if shot_globals.odp_ta_time <= shot_globals.odp_repump_time:
                raise ValueError("TA time should be longer than repump for depumping to F = 3")
            # TODO: test this timing
            self.D2Lasers_obj.repump_aom_off(t_aom_start + shot_globals.odp_repump_time)

            return t, t_aom_off

        else:
            raise NotImplementedError(
                "This optical depumping method is not implemented"
            )

    def wipe_them_out___all_of_them(self, t, close_all_shutters=True):
        self.kill_all(t, close_all_shutters=close_all_shutters)

    def kill_all(self, t, close_all_shutters=True):
        """
        Remove atoms in both the F=3 and F=4 hyperfine manifolds
        using a resonant TA pulse and repump light.

        Parameters
        ----------
        t: float
            Start time for the sequence.

        Returns
        -------
        float
            Sequence end time.
        """
        # ramp laser to resonance
        t = self.D2Lasers_obj.ramp_ta_freq(
            t, D2Lasers.CONST_TA_VCO_RAMP_TIME, final=0
        )

        # can consider making this configurable
        kill_pulse_duration = 1e-3
        t, t_aom_start = self.D2Lasers_obj.do_pulse(
            t,
            kill_pulse_duration,
            ShutterConfig.OPTICAL_PUMPING_FULL,
            ta_power=1,
            repump_power=1,
            close_all_shutters=close_all_shutters,
        )

        t_aom_off = t_aom_start + kill_pulse_duration

        return t, t_aom_off

    def kill_F4(self, t: float, close_all_shutters: bool = True):
        """Remove atoms in the F=4 hyperfine state using resonant light.

        Uses a resonant TA pulse to push away atoms in the F=4 state while leaving
        F=3 atoms unaffected. The method configures the appropriate shutter and
        laser parameters for efficient state-selective removal.

        Parameters
        ----------
        t: float
            Start time for the removal sequence
        close_all_shutters: bool, optional
            Whether to close all shutters after the sequence. Defaults to True.

        Returns
        -------
        t_end, t_aom_off: tuple[float, float]
            End time of sequence and AOM turn-off time
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
            t, _ = self.depump_ta_pulse(t_aom_off, close_all_shutters=True)
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
            t = self.Microwave_obj.do_pulse(t, shot_globals.mw_pulse_time)

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

        t += 5e-3 # Added for field stabilization. CONST_COIL_OFF_TIME is too short
        #self.BField_obj.CONST_COIL_OFF_TIME

        #TODO: We have this copied and pasted all over the place, so put this into one function.
        if shot_globals.do_mw_pulse:
            t = self.Microwave_obj.do_pulse(t, shot_globals.mw_pulse_time)
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

