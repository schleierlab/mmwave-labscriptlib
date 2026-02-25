from __future__ import annotations

from scipy.constants import pi

from labscriptlib.shot_globals import shot_globals
from labscriptlib.standard_operations.rydberg import RydbergOperations


def science_sequence(func):
    def wrapped_sequence(self: GHZSequences, *args, **kwargs):
        prep_science(t)
        func(self, *args, **kwargs)
        finish_science(t)
    
    return wrapped_sequence

class GHZSequences(RydbergOperations):
    def rotate_about_phi(self, t, axis_azimuth_deg, rotation_angle_deg):
        """
        Perform a mm-wave rotation with an axis pointing on the Bloch sphere equator.
        The Bloch sphere is oriented with initial state |e> along the north pole.

        Parameters
        ----------
        t : time
        axis_azimuth_deg : scalar
            Azimuthal angle of the rotation axis, in degrees.
            0 corresponds to the x-axis, and 1 corresponds to the y-axis.
        rotation_angle_deg : scalar
            Angle by which to rotate counterclockwise.
        """
        duration = rotation_angle_deg / 180 * shot_globals.mmwave_pi_pulse_t
        self.Microwave_obj.do_mmwave_pulse(
            t,
            duration,
            phase=axis_azimuth_deg,
        )

    @science_sequence
    def variable_rotation_parity_fringe(self):
        """
        Docstring for variable_rotation_parity_fringe
        
        Yaxis (pi/2), Jt = pi/2, -Xaxis (\theta)
        """
        # load, state prep, excite

        t_sequence_start = start_time
        self.rotate_about_phi(t_sequence_start, axis_azimuth_deg=90, rotation_angle_deg=90)
        t_second_pulse = t_sequence_start + shot_globals.mmwave_pi_pulse_t / 2 + interaction_time

        self.rotate_about_phi(
            t_second_pulse,
            axis_azimuth_deg=180,
            rotation_angle_deg=shot_globals.mmwave_readout_pulse_phase,
        )

        # deexcite

    def variable_readout_phase_parity_fringe(self):
        """
        Docstring for variable_readout_phase_parity_fringe
        
        Y(pi/2), Jt = pi/2, X(pi/4), (azimuthal \phi) (pi/2)
        """
        raise NotImplementedError

    def interaction_based_readout(self):
        """
        Docstring for interaction_based_readout
        
        Y (pi/2), Jt = pi/2, X(\theta), Jt = pi/2, Y(pi/2)
        """
        raise NotImplementedError
