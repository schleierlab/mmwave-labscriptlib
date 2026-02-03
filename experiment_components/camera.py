from labscriptlib.connection_table import devices


class Camera:
    """Controls for experimental imaging cameras.

    This class manages the camera systems used for imaging atoms in the experiment,
    including exposure timing and triggering.
    """

    def __init__(self, t):
        """Initialize the camera system.

        Args:
            t (float): Time to start the camera
        """
        self.type = None

    def set_type(self, type):
        """Set the type of imaging to be performed.

        Args:
            type (str): Type of imaging configuration to use, "MOT_manta" or
            "tweezer_manta" or "kinetix" or "local_addr_manta"
        """
        self.type = type

    def expose(self, t, exposure_time, trigger_local_manta=False):
        """Trigger camera exposure.

        Args:
            t (float): Start time for the exposure
            exposure_time (float): Duration of the exposure
            trigger_local_manta (bool, optional): Whether to trigger local Manta camera
        """
        if trigger_local_manta:
            devices.mot_camera_trigger.go_high(t)
            devices.mot_camera_trigger.go_low(t + exposure_time)

        if self.type == "MOT_manta":
            devices.manta419b_mot.expose(
                "manta419b", t, "atoms", exposure_time=exposure_time,
            )

        if self.type == "tweezer_manta":
            devices.manta419b_tweezer.expose(
                "manta419b",
                t,
                "atoms",
                exposure_time=exposure_time,
            )
        
        if self.type == "local_addr_manta":
            devices.manta419b_local_addr.expose(
                "manta419b",
                t,
                "atoms",
                exposure_time=exposure_time,
            )

        if self.type == "kinetix":
            devices.kinetix.expose(
                "Kinetix",
                t,
                "atoms",
                exposure_time=exposure_time,
            )
