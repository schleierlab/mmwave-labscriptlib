from __future__ import annotations

from scipy.constants import pi
import numpy as np

from labscriptlib.shot_globals import shot_globals
from labscriptlib.standard_operations.rydberg import RydbergOperations


def science_sequence(func):
    def wrapped_sequence(self: GHZSequences, t):
        t_science, t_end = self._prep_science_and_readout(t)
        self.t0 = t_science
        func(self, t_science)
        return t_end
    
    return wrapped_sequence

class GHZSequences(RydbergOperations):
    t0: float

    def __init__(self, t):
        super(GHZSequences, self).__init__(t)
    
        self.CONST_spectrum_card_delay = self.Microwave_obj.CONST_SPECTRUM_CARD_OFFSET - 24.65e-6#26.65e-6

    def ensure_list(param):
            if np.isscalar(param):
                return [param]
            else:
                return list(param)
    
    def rotate_about_phi(self, t, axis_azimuth_deg, rotation_angle_deg, keep_switch_on = True):
        """
        Perform a mm-wave rotation with an axis pointing on the Bloch sphere equator.
        The Bloch sphere is oriented with initial state |e> along the north pole.
        The phase is reference to the fixed time self.t0,
        which is defined by the @science_sequence decorator.

        Parameters
        ----------
        t : time
        axis_azimuth_deg : scalar
            Azimuthal angle of the rotation axis, in degrees.
            0 corresponds to the x-axis, and 90 corresponds to the y-axis.
        rotation_angle_deg : scalar
            Angle by which to rotate counterclockwise.
        """
        duration = rotation_angle_deg / 180 * shot_globals.mmwave_pi_pulse_t

        pulse_frequency = shot_globals.mmwave_spectrum_freq
        phase_accrual = 360 * (((t - self.t0) * pulse_frequency) % 1)
        print(f"phase is {phase_accrual}")
        _ = self.Microwave_obj.do_mmwave_pulse(
            t - self.CONST_spectrum_card_delay,
            duration,
            detuning=pulse_frequency,
            phase=(axis_azimuth_deg + phase_accrual),
            keep_switch_on=keep_switch_on,
            switch_offset=self.CONST_spectrum_card_delay,
        )

        return t + duration

    @science_sequence
    def variable_rotation_parity_fringe(self, t):
        """
        Docstring for variable_rotation_parity_fringe
        
        Yaxis (pi/2), Jt = pi/2, -Xaxis (\theta)
        """
        t = self.rotate_about_phi(
            t,
            axis_azimuth_deg=90, 
            rotation_angle_deg=90
        )

        t += shot_globals.interaction_time

        t = self.rotate_about_phi(
            t,
            axis_azimuth_deg=-180,
            rotation_angle_deg=shot_globals.mmwave_readout_pulse_phase,
            keep_switch_on=False,
        )

    @science_sequence
    def variable_readout_phase_parity_fringe(self, t):
        """
        Docstring for variable_readout_phase_parity_fringe
        
        Y(pi/2), Jt = pi/2, X(pi/4), (azimuthal \phi) (pi/2)
        """
        t = self.rotate_about_phi(
            t,
            axis_azimuth_deg=90,
            rotation_angle_deg=90,
        )

        t += shot_globals.interaction_time

        t = self.rotate_about_phi(
            t,
            axis_azimuth_deg=-180,
            rotation_angle_deg=45,
        )

        t = self.rotate_about_phi(
            t,
            axis_azimuth_deg=shot_globals.mmwave_readout_pulse_phase,
            rotation_angle_deg=90,
            keep_switch_on=False,
        )
        raise NotImplementedError

    @science_sequence
    def interaction_based_readout(self, t):
        """
        Docstring for interaction_based_readout
        
        Y (pi/2), Jt = pi/2, X(\theta), Jt = pi/2, Y(pi/2)
        """
        t = self.rotate_about_phi(
            t,
            axis_azimuth_deg=90, 
            rotation_angle_deg=90
        )

        t += shot_globals.interaction_time

        # t = self.rotate_about_phi(
        #     t,
        #     axis_azimuth_deg=180,
        #     rotation_angle_deg=shot_globals.mmwave_readout_pulse_phase,
        # )

        # t += shot_globals.interaction_time

        t = self.rotate_about_phi(
            t, 
            axis_azimuth_deg=-90, 
            rotation_angle_deg=90,
            keep_switch_on=False
        )
