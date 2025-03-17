from labscriptlib.connection_table import devices


class UVLamps:
    """Controls for UV LED lamps used in the experiment.

    This class manages the UV LED lamps, which are typically used for MOT loading
    enhancement through light-induced atom desorption.
    """

    def __init__(self, t):
        """Initialize the UV lamp system.

        Args:
            t (float): Time to start the UV lamps
        """
        # Turn off UV lamps
        devices.uv_switch.go_low(t)

    def uv_pulse(self, t, dur):
        """Flash the UV LED lamps for a specified duration.

        Args:
            t (float): Start time for the UV pulse
            dur (float): Duration of the UV pulse

        Returns:
            float: End time of the UV pulse
        """
        devices.uv_switch.go_high(t)
        t += dur
        devices.uv_switch.go_low(t)
        return t
