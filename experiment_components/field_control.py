from typing import ClassVar, Literal

import logging
import numpy as np

from labscript import AnalogOut, DigitalOut
from labscriptlib.calibration import (
    biasx_calib,
    biasy_calib,
    biasz_calib,
)
from labscriptlib.connection_table import devices


class BField:
    """Controls for magnetic field generation and manipulation.

    This class manages the magnetic field coils used in the experiment, including MOT coils
    and bias field coils. It provides methods for switching coils, ramping fields, and
    converting between spherical and Cartesian coordinates for field control.

    Attributes:
        CONST_COIL_OFF_TIME (float): Time required for coils to turn off (1.4e-3 s)
        CONST_COIL_RAMP_TIME (float): Standard time for ramping coil currents (100e-6 s)
        CONST_BIPOLAR_COIL_FLIP_TIME (float): Time required to flip coil polarity (10e-3 s)
        CONST_COIL_FEEDBACK_OFF_TIME (float): Time for coil feedback to turn off (4.5e-3 s)
    """
    CONST_COIL_OFF_TIME: ClassVar[float] = 1.4e-3
    CONST_COIL_RAMP_TIME: ClassVar[float] = 100e-6
    CONST_BIPOLAR_COIL_FLIP_TIME: ClassVar[float] = 10e-3
    CONST_COIL_FEEDBACK_OFF_TIME: ClassVar[float] = 4.5e-3

    bias_voltages = tuple[float, float, float]
    mot_coils_on: bool
    mot_coils_on_current: float
    current_outputs = tuple[AnalogOut, AnalogOut, AnalogOut]
    feedback_disable_ttls = tuple[DigitalOut, DigitalOut, DigitalOut]


    def __init__(
            self,
            t: float,
            init_ctrl_voltages: tuple[float, float, float],
            enable_mot_coils: bool,
    ):
        """Initialize the magnetic field system.

        Parameters
        ----------
        t: float
            Time to start the magnetic field
        init_ctrl_voltages: tuple, shape (3,)
            Initial coil control voltages.
        enable_mot_coils: bool
            Whether MOT coils are initially turned on.
        """
        self.bias_voltages = init_ctrl_voltages
        self.mot_coils_on = enable_mot_coils
        self.mot_coils_on_current = 10 / 6

        self.t_last_change = 0

        self.current_outputs = (
            devices.x_coil_current,
            devices.y_coil_current,
            devices.z_coil_current,
        )

        self.feedback_disable_ttls = (
            devices.x_coil_feedback_off,
            devices.y_coil_feedback_off,
            devices.z_coil_feedback_off,
        )

        for current_output, bias_voltage_cmpnt in zip(
            self.current_outputs, self.bias_voltages
        ):
            current_output.constant(t, bias_voltage_cmpnt)

        if self.mot_coils_on:
            devices.mot_coil_current_ctrl.constant(t, self.mot_coils_on_current)
        else:
            devices.mot_coil_current_ctrl.constant(
                t, 0
            )  # when changing bias field make sure the magnetic field gradient is off

    def flip_coil_polarity(
        self, t: float, final_voltage: float, component: Literal[0, 1, 2]
    ):
        """
        Flip the polarity of a specified magnetic field coil.

        Performs a controlled polarity flip of a magnetic field coil by ramping through
        an intermediate voltage state. The process involves:
        1. Ramping to a small intermediate voltage
        2. Disabling feedback during the polarity change
        3. Waiting for the flip to complete
        4. Ramping to the final voltage

        Args:
            t (float): Time to begin coil polarity flipping
            final_voltage (float): Target control voltage for the coil after polarity flip
            component (Literal[0, 1, 2]): Field component to flip (0=x, 1=y, 2=z)

        Returns:
            float: Start time for parallel operations (accounts for flip duration)

        Note:
            The method returns the start time instead of end time to allow parallel
            operations on other coils. Total operation time is CONST_BIPOLAR_COIL_FLIP_TIME
            plus CONST_COIL_RAMP_TIME.
        """
        coil_voltage_mid_abs = 0.03
        coil_voltage_mid = np.sign(final_voltage) * coil_voltage_mid_abs
        total_coil_flip_ramp_time = (
            self.CONST_BIPOLAR_COIL_FLIP_TIME + self.CONST_COIL_RAMP_TIME
        )

        current_output = self.current_outputs[component]
        feedback_disable_ttl = self.feedback_disable_ttls[component]

        t += current_output.ramp(
            t,
            duration=self.CONST_COIL_RAMP_TIME / 2,
            initial=self.bias_voltages[component],
            final=coil_voltage_mid,  # sligtly negative voltage to trigger the polarity change
            samplerate=1e5,
        )
        # print(f"feed_disable_ttl in coil {component}")
        feedback_disable_ttl.go_high(t)
        feedback_disable_ttl.go_low(t + self.CONST_COIL_FEEDBACK_OFF_TIME)
        self.current_outputs[component].constant(t, coil_voltage_mid)
        t += self.CONST_BIPOLAR_COIL_FLIP_TIME

        t += current_output.ramp(
            t,
            duration=self.CONST_COIL_RAMP_TIME / 2,
            initial=coil_voltage_mid,
            final=final_voltage,  # 0 mG
            samplerate=1e5,
        )

        t -= total_coil_flip_ramp_time  # subtract to the begining to set other coils

        # Update internal state
        bias_voltages = [voltage for voltage in self.bias_voltages]
        bias_voltages[component] = final_voltage
        self.bias_voltages = tuple(bias_voltages)
        return t

    def ramp_bias_field(self, t, dur = 100e-6,  bias_field_vector=None, voltage_vector=None, polar = False):
        """Ramp the bias field to new values.

        Args:
            t (float): Start time for the ramp
            dur (float, optional): Duration of the ramp. Defaults to 100e-6 s
            bias_field_vector (tuple, optional): Target bias field values in Gauss
            voltage_vector (tuple, optional): Target voltage values for coils
            polar (boolean): using the spherical coordinate for the magnetic fields or cartiesain

        Returns:
            float: End time of the ramp
        """
        # bias_field_vector should be a tuple of the form (x,y,z)
        # Need to start the ramp earlier if the voltage changes sign
        if polar:
            field_vector = (
                self.convert_bias_fields_sph_to_cart(
                    bias_field_vector[0],
                    bias_field_vector[1],
                    bias_field_vector[2],
                )
            )
        else:
            field_vector = bias_field_vector


        dur = np.max([dur, self.CONST_COIL_RAMP_TIME])
        if field_vector is not None:
            voltage_vector = np.array(
                [
                    biasx_calib(field_vector[0]),
                    biasy_calib(field_vector[1]),
                    biasz_calib(field_vector[2]),
                ]
            )

        if np.all(self.bias_voltages == voltage_vector):
            logging.debug("bias field initial and final are the same, skip ramp")
            return t

        sign_flip_in_ramp = voltage_vector * np.asarray(self.bias_voltages) < 0
        coil_ramp_start_times = (
            t - self.CONST_BIPOLAR_COIL_FLIP_TIME * sign_flip_in_ramp
        )

        # print(coil_ramp_start_times)

        for i in range(3):
            if sign_flip_in_ramp[i]:
                coil_ramp_start_times[i] = np.max(
                    [self.t_last_change + 100e-6, coil_ramp_start_times[i]]
                )
                _ = self.flip_coil_polarity(
                    coil_ramp_start_times[i], voltage_vector[i], component=i
                )
            else:
                self.current_outputs[i].ramp(
                    coil_ramp_start_times[i],
                    duration= dur,
                    initial=self.bias_voltages[i],
                    final=voltage_vector[i],
                    samplerate=1e5,
                )
        # print(coil_ramp_start_times)
        end_time = (
            np.min(coil_ramp_start_times)
            + dur
            + self.CONST_BIPOLAR_COIL_FLIP_TIME
        )
        self.t_last_change = end_time
        # print(coil_ramp_start_times)

        # TODO: add the inverse function of bias_i_calib
        # otherwise, if only voltage vector is provided on input, the bias field will not be updated
        # if bias_field_vector is not None:

        self.bias_voltages = tuple(voltage_vector)

        return t + dur

    def switch_mot_coils(self, t):
        """Switch the MOT coils on or off.

        Args:
            t (float): Time to switch the coils

        Returns:
            float: End time after switching operation is complete
        """
        if self.mot_coils_on:
            devices.mot_coil_current_ctrl.ramp(
                t,
                duration=self.CONST_COIL_RAMP_TIME,
                initial=self.mot_coils_on_current,
                final=0,
                samplerate=1e5,
            )
            self.mot_coils_on = False
        else:
            devices.mot_coil_current_ctrl.ramp(
                t,
                duration=self.CONST_COIL_RAMP_TIME,
                initial=0,
                final=self.mot_coils_on_current,
                samplerate=1e5,
            )
            self.mot_coils_on = True

        endtime = t + self.CONST_COIL_RAMP_TIME + self.CONST_COIL_OFF_TIME
        return endtime

    def convert_bias_fields_sph_to_cart(self, bias_amp, bias_phi, bias_theta):
        """Convert spherical coordinates to Cartesian for bias field control.

        Args:
            bias_amp (float): Amplitude of the bias field
            bias_phi (float): Azimuthal angle in radians
            bias_theta (float): Polar angle in radians

        Returns:
            tuple: Cartesian coordinates (x, y, z) for the bias field
        """
        biasx_field = (
            bias_amp
            * np.cos(np.deg2rad(bias_phi))
            * np.sin(np.deg2rad(bias_theta))
        )
        biasy_field = (
            bias_amp
            * np.sin(np.deg2rad(bias_phi))
            * np.sin(np.deg2rad(bias_theta))
        )
        biasz_field = bias_amp * np.cos(
            np.deg2rad(bias_theta),
        )

        return biasx_field, biasy_field, biasz_field


class EField:
    """Control for electric field generation and manipulation.

    This class manages the 8 electrodes in the glass cell.
    For now, we work in a restricted 3D subspace of the full 8D state space
    of the electrodes, as follows. The electrodes are roughly located at the
    vertices of a cube; therefore, choose coordinates such that the vertices
    are at the points {0, 1}^3 and label the electrodes as triples (b1, b2, b3)
    where the b_i are drawn from {0, 1}. Then the electrode voltages are sum_i b_i v_i
    where the v_i are the three degrees of freedom here.
    """

    voltage_diffs: tuple[float, float, float]

    def __init__(self, t, init_voltage_diffs: tuple[float, float, float]):

        self.voltage_diffs = init_voltage_diffs

        self.electrodes = (
            devices.electrode_T1,
            devices.electrode_T2,
            devices.electrode_T3,
            devices.electrode_T4,
            devices.electrode_B1,
            devices.electrode_B2,
            devices.electrode_B3,
            devices.electrode_B4,
        )

        self.set_electric_field(t, self.voltage_diffs)

    def convert_electrodes_voltages(self, voltage_diff_vector: tuple[float, float, float]):
        """
        Convert the voltage drop along the cube axes into individual electrode voltages.

        Parameters
        ----------
        voltage_diff_vector: tuple, shape (3,)

        Returns
        -------
        electrode_voltages: tuple, shape (8,)
        """
        vx, vy, vz = voltage_diff_vector

        electrode_voltages = (
            vx + vy,
            vy,
            vx + vy + vz,
            vy + vz,
            vx,
            0,
            vx + vz,
            vz,
        )

        return electrode_voltages

    def set_electric_field(self, t, voltage_diff_vector):
        """
        set electrodes to constant voltages. No ramp.
        """
        electrode_voltages = self.convert_electrodes_voltages(voltage_diff_vector)

        for voltage, electrode in zip(electrode_voltages, self.electrodes):
            electrode.constant(t, voltage)

        self.voltage_diffs = tuple(voltage_diff_vector)
