from dataclasses import dataclass

from labscriptlib.experiment_components import (
    BField,
    Camera,
    D2Config,
    D2Lasers,
    EField,
    ParityProjectionConfig,
    ShutterConfig,
    UVLamps,
)
from labscriptlib.shot_globals import shot_globals


@dataclass
class MOTConfig:
    # TODO rename these variables
    mot_ta_power: float
    mot_ta_detuning: float
    mot_repump_power: float
    bm_parity_projection_ta_power: float
    bm_parity_projection_ta_detuning: float
    mot_bias_coil_ctrl_voltages: tuple[float, float, float]
    mot_do_coil: bool
    zero_efield_voltages: tuple[float, float, float]

    @property
    def mot_d2_config(self) -> D2Config:
        return D2Config(
            self.mot_ta_power,
            self.mot_ta_detuning,
            self.mot_repump_power,
            repump_detuning=0,
        )


class MOTOperations:
    """Sequence for Magneto-Optical Trap (MOT) operations.

    This class manages the sequence of operations related to MOT loading, imaging,
    and manipulation. It coordinates multiple hardware components including D2 lasers,
    magnetic fields, microwave systems, UV lamps, and cameras.
    """

    def __init__(self, t):
        # Standard initialization for hardware objects puts everything in
        # correct state/tuning to start loading the MOT

        mot_config = D2Config(
            shot_globals.mot_ta_power,
            shot_globals.mot_ta_detuning,
            shot_globals.mot_repump_power,
        )
        pp_config = ParityProjectionConfig(
            shot_globals.bm_parity_projection_ta_power,
            shot_globals.bm_parity_projection_ta_detuning,
        )
        self.D2Lasers_obj = D2Lasers(
            t,
            mot_config,
            pp_config,
        )

        init_coil_ctrl_voltages = (
            shot_globals.mot_x_coil_voltage,
            shot_globals.mot_y_coil_voltage,
            shot_globals.mot_z_coil_voltage,
        )
        self.BField_obj = BField(
            t,
            init_coil_ctrl_voltages,
            enable_mot_coils=shot_globals.mot_do_coil,
        )

        init_electrode_voltage_diffs = (
            shot_globals.zero_Efield_Vx,
            shot_globals.zero_Efield_Vy,
            shot_globals.zero_Efield_Vz,
        )
        self.EField_obj = EField(t, init_electrode_voltage_diffs)

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

        # extra delay accounts for shutter closing of whatever comes before this.
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
        assert shot_globals.do_molasses_img_beam or shot_globals.do_molasses_mot_beam, (
            "either do_molasses_img_beam or do_molasses_mot_beam has to be on"
        )
        assert shot_globals.bm_ta_detuning != 0, (
            "bright molasses detuning = 0. TA detuning should be non-zero for bright molasses."
        )
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
        ta_detuning=0,
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

        shutter_config = ShutterConfig.select_imaging_shutters(
            imaging_label=shot_globals.imaging_label,
            beam_choice=shot_globals.imaging_beam_choice(),
            do_repump=do_repump,
        )

        # full power ta and repump pulse
        t_pulse_end, t_aom_start = self.D2Lasers_obj.do_pulse(
            t,
            exposure_time,
            shutter_config,
            ta_power,
            repump_power,
            close_all_shutters=close_all_shutters,
        )

        # TODO: store the min exposure times with the camera object and eventually get rid of this
        self.Camera_obj.set_type(shot_globals.camera_type)
        min_exposure_times = {
            "MOT_manta": 50e-6,
            "tweezer_manta": 50e-6,
            "kinetix": 1e-3,
        }
        if self.Camera_obj.type not in min_exposure_times.keys():
            raise ValueError(f"Camera type {self.Camera_obj.type} not recognized")

        min_exposure_time = min_exposure_times[self.Camera_obj.type]
        if exposure_time < min_exposure_time:
            raise ValueError(
                f"Exposure time {exposure_time} shorter than "
                f"minimum {min_exposure_time} for camera {self.Camera_obj.type}",
            )

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
        t += 100e-3

        t = self.do_molasses_dipole_trap_imaging(t)

        t += 10e-3
        if reset_mot:
            t = self.reset_mot(t)

        return t
