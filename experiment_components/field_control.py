import logging
from typing import ClassVar, Literal

import numpy as np
from numpy.typing import NDArray

from labscript import AnalogOut, DigitalOut
from labscriptlib.calibration import (
    bfield_to_voltages,
    voltages_to_bfield,
    Ex_calib,
    Ey_calib,
    Ez_calib,
)
from labscriptlib.connection_table import devices


logger = logging.getLogger(__name__)


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

    bias_voltages: tuple[float, float, float]
    mot_coils_on: bool
    mot_coils_on_current: float
    current_outputs: tuple[AnalogOut, AnalogOut, AnalogOut]
    feedback_disable_ttls: tuple[DigitalOut, DigitalOut, DigitalOut]


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

    def _flip_coil_polarity(
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

    @staticmethod
    def _check_voltage_limits(voltage_vector):
        """
        Parameters
        ----------
        voltage_vector : array_like, shape (..., 3)
        """
        coil_control_voltage_limits = np.array([5.05, 2.7, 3.5])
        if np.any(np.abs(voltage_vector) > coil_control_voltage_limits):
            raise ValueError(
                'Cannot drive coils beyond limit set by power supply voltages. '
                f'Drive voltages: {voltage_vector}; '
                f'Limit absolute voltages: {coil_control_voltage_limits}'
            )

    def ramp_bias_field(
            self,
            t,
            dur = 100e-6,
            bias_field_vector=None,
            voltage_vector=None,
            polar: bool = False,
    ):
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
        # require field changes to be programmed in sequence
        if t <= self.t_last_change:
            raise ValueError

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

        if dur < self.CONST_COIL_RAMP_TIME:
            logger.info(f"Lengthening spec'd field ramp duration {dur} to minimum value of {self.CONST_COIL_RAMP_TIME}.")
        dur = np.max([dur, self.CONST_COIL_RAMP_TIME])
        if field_vector is not None:
            voltage_vector = bfield_to_voltages(field_vector)
            
        self._check_voltage_limits(voltage_vector)

        if np.all(self.bias_voltages == voltage_vector):
            logger.debug("bias field initial and final are the same, skip ramp")
            return t

        sign_flip_in_ramp = voltage_vector * np.asarray(self.bias_voltages) < 0
        coil_ramp_start_times = (
            t - self.CONST_BIPOLAR_COIL_FLIP_TIME * sign_flip_in_ramp
        )

        for i in range(3):
            if sign_flip_in_ramp[i]:
                coil_ramp_start_times[i] = np.max(
                    [self.t_last_change + 100e-6, coil_ramp_start_times[i]]
                )
                _ = self._flip_coil_polarity(
                    coil_ramp_start_times[i], voltage_vector[i], component=i
                )
            else:
                self.current_outputs[i].ramp(
                    coil_ramp_start_times[i],
                    duration=dur,
                    initial=self.bias_voltages[i],
                    final=voltage_vector[i],
                    samplerate=1e5,
                )
        end_time = (
            np.min(coil_ramp_start_times)
            + dur
            + self.CONST_BIPOLAR_COIL_FLIP_TIME
        )
        self.t_last_change = end_time

        # TODO: add the inverse function of bias_i_calib
        # otherwise, if only voltage vector is provided on input, the bias field will not be updated
        # if bias_field_vector is not None:

        self.bias_voltages = tuple(voltage_vector)

        return t + dur

    @staticmethod
    def _cart2sph(cartesian_coords):
        xyz = np.asarray(cartesian_coords)
        x2y2 = xyz[..., 0]**2 + xyz[..., 1]**2

        spherical_coords = np.empty_like(xyz)

        # radial coordinate
        spherical_coords[..., 0] = np.sqrt(x2y2 + xyz[..., 2]**2)

        # polar angle
        spherical_coords[..., 1] = np.arctan2(np.sqrt(x2y2), xyz[..., 2])

        # azimuthal angle
        spherical_coords[..., 2] = np.arctan2(xyz[..., 1], xyz[..., 0])

        return spherical_coords

    @classmethod
    def _slerp_ramp(cls, initial, final, ramp_progress) -> NDArray:
        """
        initial, final : array_like, (3,)
            Starting and ending point in Cartesian coordinates with shape (3,).
        ramp_progress : array_like, shape (...,)
            Progress parameter from 0 to 1, where 0 represents the initial point
            and 1 represents the final point. Any shape.
        Returns
        -------
        ndarray
            Interpolated points along the great circle ramp in Cartesian coordinates.
            Shape (..., 3). The radial distance varies linearly from the initial
            to the final radius, while the angular trajectory follows a great circle
            on the sphere.
        Notes
        -----
        This method performs spherical interpolation (slerp) on the angular components
        while maintaining linear interpolation of the radial component. The resulting
        trajectory lies on a sphere of varying radius centered at the origin.
        Compute a ramp between two specified points in Cartesian coordinates
        such that the radial distance along the ramp varies linearly
        and such that the projection of the trajectory on a sphere at the origin
        uniformly follows a great circle.
        """
        ((r1, theta1, phi1), (r2, theta2, phi2)) = cls._cart2sph([initial, final])

        # arc angle between two points
        # (may be ill-conditioned for nearby points; can use haversine formula there)
        d = np.arccos(np.cos(theta1) * np.cos(theta2) + np.sin(theta1) * np.sin(theta2) * np.cos(phi1 - phi2))

        # shape: (...,)
        a_sin_d = np.sin((1 - ramp_progress) * d)
        b_sin_d = np.sin(ramp_progress * d)

        # shape: (..., 3)
        great_circle_points_cartesian = (a_sin_d[..., np.newaxis] * initial/r1 + b_sin_d[..., np.newaxis] * final/r2) / np.sin(d)
        radial_coords = r1 + ramp_progress * (r2 - r1)

        return radial_coords[..., np.newaxis] * great_circle_points_cartesian

    def ramp_bias_field_slerp(
            self,
            t,
            duration,
            final_bias_field: tuple[float, float, float],
            sample_points: int = 11,
    ):
        """
        Ramp the bias field to a final value over a specified duration.
        The ramp linearly interpolates between initial and final fields
        in polar coordinates in the plane defined by the two endpoint fields.

        Parameters
        ----------
        t : float
            The time at which to start the ramp (in seconds).
        duration : float
            The duration of the ramp (in seconds).
        final_bias_field : tuple or array-like
            The final bias field values in Cartesian coordinates.
        """
        if t <= self.t_last_change:
            raise ValueError
        if duration / (sample_points - 1) < 2.5e-6:
            raise ValueError(f'Ramp sample rate too fast: {duration=}, {sample_points=}')

        ramp_progress = np.linspace(0, 1, sample_points)[1:]
        times = np.linspace(t, t + duration, sample_points)[1:]

        initial_bias_field = voltages_to_bfield(self.bias_voltages)
        field_points = self._slerp_ramp(initial_bias_field, final_bias_field, ramp_progress)
        control_voltages = bfield_to_voltages(field_points)
        if np.any(control_voltages[-1] / self.bias_voltages < 0):
            logger.warning('Switching bias coil drive sign')
        self._check_voltage_limits(control_voltages)

        for time, control_voltages_single in zip(times, control_voltages):
            for i, current_output in enumerate(self.current_outputs):
                current_output.constant(time, control_voltages_single[i])

        endtime = t + duration
        self.t_last_change = endtime
        self.bias_voltages = control_voltages[-1]

        return endtime

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
            bias_phi (float): Azimuthal angle in degrees
            bias_theta (float): Polar angle in degrees

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

        self.voltage_diffs = (0,0,0)

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

        self.set_efield_shift(t, init_voltage_diffs)

    def convert_fields_sph_to_cart(self, amp, theta, phi):
        """Convert spherical coordinates to Cartesian for bias field control.

        Args:
            bias_amp (float): Amplitude of the bias field
            bias_phi (float): Azimuthal angle in radians
            bias_theta (float): Polar angle in radians

        Returns:
            tuple: Cartesian coordinates (x, y, z) for the bias field
        """
        x_field = (
            amp
            * np.cos(np.deg2rad(phi))
            * np.sin(np.deg2rad(theta))
        )
        y_field = (
            amp
            * np.sin(np.deg2rad(phi))
            * np.sin(np.deg2rad(theta))
        )
        z_field = amp * np.cos(
            np.deg2rad(theta),
        )

        return (x_field, y_field, z_field)

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

    def set_efield_shift(self, t, shift_vector: tuple[float, float, float], polar = False):
        if polar:
            shift_vec_cart = self.convert_fields_sph_to_cart(shift_vector[0], shift_vector[1], shift_vector[2])
        else:
            shift_vec_cart = shift_vector
        print(shift_vec_cart)
        voltage_vec = np.array(
                [
                    Ex_calib(shift_vec_cart[0]),
                    Ey_calib(shift_vec_cart[1]),
                    Ez_calib(shift_vec_cart[2]),
                ]
            )
        print(voltage_vec)

        self.set_electric_field(t, voltage_vec)







