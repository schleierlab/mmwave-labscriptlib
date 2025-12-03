import labscript
import labscript_devices as labscript_devices
import labscript_devices.FunctionRunner
import labscript_devices.FunctionRunner.labscript_devices
from labscript import AnalogIn, AnalogOut, ClockLine, DigitalOut, Shutter
from labscript_devices.NI_DAQmx.models.NI_PXIe_6363 import NI_PXIe_6363
from labscript_devices.PulseBlasterESRPro500 import PulseBlasterESRPro500
from labscript_devices.PrawnBlaster.labscript_devices import PrawnBlaster
from user_devices.DDS.AD9914 import AD9914

from user_devices.DDS.AD_DDS import AD_DDS
# from user_devices.spcm.Spectrum_sequence import Spectrum # Use Spectrum.py for when we don't run tweezers or when we run sequence mode. This is the old Spectrum.py code before we added fifo capability
from user_devices.spcm.Spectrum import Spectrum # Use Spectrum.py for fifo mode or sequence mode. This doesn't work when we don't run tweezers.
# TODO need to fix the issues in Spectrum for it to be able to run when we don't assign any waveform to specturm card

from user_devices.manta419b.manta419b import Manta419B  # noqa:F401
from user_devices.kinetix.Kinetix import Kinetix  # noqa:F401
from user_devices.NI_PXIe_6739 import NI_PXIe_6739

# please name devices with lower_case_with_underscores (uwave_absorp_switch)
# NOT Capitalized_Words_With_Underscores

class LabDevices():
    def __init__(self):
        pass

    def __getattr__(self, name):
        raise AttributeError(f'Device {name} not defined. Did you forget to call initialize()?')

    def initialized(self) -> bool:
        return hasattr(self, 'pb')

    def initialize(self):
        print('Initializing connection table')

        pb = PulseBlasterESRPro500(name='pb', board_number=0)
        # pb = PrawnBlaster(name='pb', com_port='COM4', num_pseudoclocks=2)

        clockline_6363 = ClockLine(
            name='clockline_6363',
            pseudoclock=pb.pseudoclock,
            connection='flag 16',
        )
        # clockline_6363 = pb.clocklines[0] # for PrawnBlaster

        ni_6363_0 = NI_PXIe_6363(
            name='ni_6363_0',
            parent_device=clockline_6363,
            clock_terminal='/ni_6363_0/PFI0',
            MAX_name='ni_6363_0',
            acquisition_rate=2.5e5
        )

        self.x_coil_feedback_off = DigitalOut(
            name='x_coil_feedback_off',
            parent_device=ni_6363_0,
            connection='port0/line4',
        )

        self.y_coil_feedback_off = DigitalOut(
            name='y_coil_feedback_off',
            parent_device=ni_6363_0,
            connection='port0/line12',
        )

        self.z_coil_feedback_off = DigitalOut(
            name='z_coil_feedback_off',
            parent_device=ni_6363_0,
            connection='port0/line14',
        )

        self.uwave_dds_switch = DigitalOut(
            name='uwave_dds_switch',
            parent_device=ni_6363_0,
            connection='port0/line3',
        )

        self.uwave_absorp_switch = DigitalOut(
            name='uwave_absorp_switch',
            parent_device = pb.direct_outputs,
            connection='flag 8',
        )

        # *_shutter_on_t: delay between pulse edge and fully-on state
        # *_shutter_off_t: delay between pulse edge and starting to close

        ta_shutter_off_t = 1.74e-3
        ta_shutter_on_t = 3.66e-3
        ta_shutter_delays = (ta_shutter_on_t, ta_shutter_off_t)

        repump_shutter_off_t = 1.984e-3
        repump_shutter_on_t = 3.442e-3
        repump_shutter_delays = (repump_shutter_on_t, repump_shutter_off_t)

        self.ta_shutter = Shutter(
            name='ta_shutter',
            parent_device=ni_6363_0,
            connection='port0/line5',
            delay=ta_shutter_delays,
            open_state=1,
        )
        self.repump_shutter = Shutter(
            name='repump_shutter',
            parent_device=ni_6363_0,
            connection='port0/line6',
            delay=repump_shutter_delays,
            open_state=1,
        )
        self.mot_xy_shutter = Shutter(
            name='mot_xy_shutter',
            parent_device=ni_6363_0,
            connection='port0/line7',
            delay=ta_shutter_delays,
            open_state=1,
        )
        self.mot_z_shutter = Shutter(
            name='mot_z_shutter',
            parent_device=ni_6363_0,
            connection='port0/line8',
            delay=ta_shutter_delays,
            open_state=1,
        )
        self.img_xy_shutter = Shutter(
            name='img_xy_shutter',
            parent_device=ni_6363_0,
            connection='port0/line9',
            delay=ta_shutter_delays,
            open_state=1,
        )
        self.img_z_shutter = Shutter(
            name='img_z_shutter',
            parent_device=ni_6363_0,
            connection='port0/line10',
            delay=ta_shutter_delays,
            open_state=1,
        )

        self.uv_switch = DigitalOut(
            name='uv_switch',
            parent_device=ni_6363_0,
            connection='port0/line11',
        )

        self.ta_aom_digital = DigitalOut(
            name='ta_aom_digital',
            parent_device=ni_6363_0,
            connection='port0/line0',
        )

        self.repump_aom_digital = DigitalOut(
            name='repump_aom_digital',
            parent_device=ni_6363_0,
            connection='port0/line1',
        )

        self.tweezer_aom_digital = DigitalOut(
            name='tweezer_aom_digital',
            parent_device = pb.direct_outputs,
            connection='flag 12',
        )

        self.servo_1064_aom_digital = DigitalOut(
            name='servo_1064_aom_digital',
            parent_device = pb.direct_outputs,
            connection='flag 13',
        )

        self.servo_456_aom_digital = DigitalOut(
            name='servo_456_aom_digital',
            parent_device = pb.direct_outputs,
            connection='flag 14',
        )


        self.pulse_456_aom_digital = DigitalOut(
            name='pulse_456_aom_digital',
            parent_device = pb.direct_outputs,
            connection='flag 15',
        )

        self.pulse_1064_aom_digital = DigitalOut(
            name='pulse_1064_aom_digital',
            parent_device = pb.direct_outputs,
            connection='flag 10',
        )

        self.local_addr_1064_aom_digital = DigitalOut(
            name='local_addr_1064_aom_digital',
            parent_device = pb.direct_outputs,
            connection='flag 11',
        )

        self.pulse_local_addr_1064_aom_digital = DigitalOut(
            name='pulse_local_addr_1064_aom_digital',
            parent_device=pb.direct_outputs,
            connection='flag 20',
        )

        self.ta_relock = DigitalOut(
            name='ta_relock',
            parent_device=ni_6363_0,
            connection='port0/line16',
        )

        self.dispenser_off_trigger = DigitalOut(
            name='dispenser_off_trigger',
            parent_device=ni_6363_0,
            connection='port0/line17',
        )

        self.optical_pump_shutter = Shutter(
            name='optical_pump_shutter',
            parent_device=ni_6363_0,
            connection='port0/line19',
            delay=ta_shutter_delays,
            open_state=1,
        )

        # Dummy digital out to keep even number for Blacs

        self.mmwave_switch = DigitalOut(
            name='mmwave_switch',
            parent_device = pb.direct_outputs,
            connection='flag 18',
        )

        self.blue_456_shutter = Shutter(
            name='blue_456_shutter',
            parent_device=ni_6363_0,
            connection='port0/line18',
            delay=ta_shutter_delays,
            open_state=1,
        )

        # dummy channel. Not connected to anything but enable/ disable to meet the even-number-channel requirement
        # self.digital_out_ch26 = DigitalOut(
        #     name='digital_out_ch26',
        #     parent_device=ni_6363_0,
        #     connection='port0/line26',
        # )

        clockline_6739 = ClockLine(name='clockline_6739', pseudoclock=pb.pseudoclock, connection='flag 17')
        # clockline_6739 = pb.clocklines[1]# for PrawnBlaster

        ni_6739_0 = NI_PXIe_6739(
            name='ni_6739_0',
            parent_device=clockline_6739,
            clock_terminal='/ni_6739_0/PFI0',
            MAX_name='ni_6739_0',
        )

        # G&H AOM driver AM inputs cannot exceed 1 V
        self.ta_aom_analog = AnalogOut(
            name='ta_aom_analog',
            parent_device=ni_6739_0,
            connection='ao0',
            limits=(0, 1),
        )
        self.repump_aom_analog = AnalogOut(
            name='repump_aom_analog',
            parent_device=ni_6739_0,
            connection='ao1',
            limits=(0, 1),
        )

        self.ta_vco = AnalogOut(
            name='ta_vco',
            parent_device=ni_6739_0,
            connection='ao2'
        )
        self.repump_vco = AnalogOut(
            name='repump_vco',
            parent_device=ni_6739_0,
            connection='ao3'
        )
        self.mot_coil_current_ctrl = AnalogOut(
            name='mot_coil_current_ctrl',
            parent_device=ni_6739_0,
            connection='ao4'
        )
        self.x_coil_current = AnalogOut(
            name='x_coil_current',
            parent_device=ni_6739_0,
            connection='ao5'
        )
        self.y_coil_current = AnalogOut(
            name='y_coil_current',
            parent_device=ni_6739_0,
            connection='ao6'
        )
        self.z_coil_current = AnalogOut(
            name='z_coil_current',
            parent_device=ni_6739_0,
            connection='ao7'
        )
        self.tweezer_aom_analog = AnalogOut(
            name='tweezer_aom_analog',
            parent_device=ni_6739_0,
            connection='ao8',
            limits=(0, 1)
        )
        self.pulse_local_addr_1064_aom_analog = AnalogOut(
            name='pulse_local_addr_1064_aom_analog',
            parent_device=ni_6739_0,
            connection='ao9',
            limits=(0, 1)
        )
        self.servo_456_aom_analog = AnalogOut(
            name='notconnected_servo_456_aom_analog',
            parent_device=ni_6739_0,
            connection='ao10',
            limits=(0, 1)
        )

        #Mirror 1 is upstream mirror 2 is downstream
        self.mirror_456_1_v = AnalogOut(
            name='mirror_456_1_v',
            parent_device=ni_6739_0,
            connection='ao11',
            limits=(0, 10),
        )

        self.mirror_456_1_h = AnalogOut(
            name='mirror_456_1_h',
            parent_device=ni_6739_0,
            connection='ao12',
            limits=(0, 10),
        )

        self.mirror_456_2_v = AnalogOut(
            name='mirror_456_2_v',
            parent_device=ni_6739_0,
            connection='ao13',
            limits=(0, 10),
        )

        self.mirror_456_2_h = AnalogOut(
            name='mirror_456_2_h',
            parent_device=ni_6739_0,
            connection='ao14',
            limits=(0, 10),
        )

        self.mirror_1064_1_v = AnalogOut(
            name='mirror_1064_1_v',
            parent_device=ni_6739_0,
            connection='ao19',
            limits=(0, 10),
        )

        self.mirror_1064_1_h = AnalogOut(
            name='mirror_1064_1_h',
            parent_device=ni_6739_0,
            connection='ao18',
            limits=(0, 10),
        )

        self.mirror_1064_2_v = AnalogOut(
            name='mirror_1064_2_v',
            parent_device=ni_6739_0,
            connection='ao21',
            limits=(0, 10),
        )

        self.mirror_1064_2_h = AnalogOut(
            name='mirror_1064_2_h',
            parent_device=ni_6739_0,
            connection='ao20',
            limits=(0, 10),
        )

        self.pulse_456_aom_analog = AnalogOut(
            name='pulse_456_aom_analog',
            parent_device=ni_6739_0,
            connection='ao15',
            limits=(0, 1)
        )

        self.local_addr_1064_aom_analog = AnalogOut(
            name='local_addr_1064_aom_analog',
            parent_device=ni_6739_0,
            connection='ao16',
            limits=(0, 1)
        )

        self.pulse_1064_aom_analog = AnalogOut(
            name='pulse_1064_aom_analog',
            parent_device=ni_6739_0,
            connection='ao17',
            limits=(0, 1)
        )

        self.local_addr_piezo_mirror_x1 = AnalogOut(
            name='local_addr_piezo_mirror_x1',
            parent_device=ni_6739_0,
            connection='ao32',
            limits=(-10, 10)
        )

        self.local_addr_piezo_mirror_x2 = AnalogOut(
            name='local_addr_piezo_mirror_x2',
            parent_device=ni_6739_0,
            connection='ao33',
            limits=(-10, 10)
        )

        self.local_addr_piezo_mirror_y1 = AnalogOut(
            name='local_addr_piezo_mirror_y1',
            parent_device=ni_6739_0,
            connection='ao34',
            limits=(-10, 10)
        )

        self.local_addr_piezo_mirror_y2 = AnalogOut(
            name='local_addr_piezo_mirror_y2',
            parent_device=ni_6739_0,
            connection='ao35',
            limits=(-10, 10)
        )

        #==============================================================================
        # Electrodes
        #==============================================================================
        self.electrode_T1 = AnalogOut(
            name='electrode_T1',
            parent_device=ni_6739_0,
            connection='ao22'
        )

        self.electrode_T2 = AnalogOut(
            name='electrode_T2',
            parent_device=ni_6739_0,
            connection='ao23'
        )

        self.electrode_T3 = AnalogOut(
            name='electrode_T3',
            parent_device=ni_6739_0,
            connection='ao24'
        )

        self.electrode_T4 = AnalogOut(
            name='electrode_T4',
            parent_device=ni_6739_0,
            connection='ao25'
        )

        self.electrode_B1 = AnalogOut(
            name='electrode_B1',
            parent_device=ni_6739_0,
            connection='ao26'
        )

        self.electrode_B2 = AnalogOut(
            name='electrode_B2',
            parent_device=ni_6739_0,
            connection='ao27'
        )

        self.electrode_B3 = AnalogOut(
            name='electrode_B3',
            parent_device=ni_6739_0,
            connection='ao28'
        )

        self.electrode_B4 = AnalogOut(
            name='electrode_B4',
            parent_device=ni_6739_0,
            connection='ao29'
        )

        # self.runner = labscript_devices.FunctionRunner.labscript_devices.FunctionRunner(
        #     name = 'runner'
        # )

        #==============================================================================
        # Analog Inputs
        #==============================================================================

        self.monitor_1064 = AnalogIn(
            name='monitor_1064',
            parent_device=ni_6363_0,
            connection='ai0',
        )

        self.monitor_456 = AnalogIn(
            name='monitor_456',
            parent_device=ni_6363_0,
            connection='ai1',
        )


        #==============================================================================
        # Cameras
        #==============================================================================

        # self.manta419b_mot = Manta419B(
        #     'manta419b_mot',
        #     parent_device=ni_6363_0,
        #     connection="port0/line2",
        #     BIAS_port=54321,
        # )

        # self.manta419b_tweezer = Manta419B(
        #     'manta419b_tweezer',
        #     parent_device=ni_6363_0,
        #     connection="port0/line13",
        #     BIAS_port=54324,
        # )

        # self.manta419b_local_addr = Manta419B(
        #     'manta419b_local_addr',
        #     parent_device=ni_6363_0,
        #     connection="port0/line21",
        #     BIAS_port=54325,
        # )

        # self.manta419b_dipole_trap = Manta419B(
        #     'manta419b_dipole_trap',
        #     parent_device=ni_6363_0,
        #     connection="port0/line2",
        #     BIAS_port=54323,
        # )

        self.kinetix = Kinetix(
            name='kinetix',
            parent_device=ni_6363_0,
            connection='port0/line15',
            BIAS_port=27171,
        )

        #================================================================================
        # Spectrum Instrumentation Cards for microwaves
        #================================================================================

        self.spectrum_uwave = Spectrum(
            name='spectrum_uwave',
            parent_device=clockline_6363,
            trigger={'device': pb.direct_outputs, 'connection': 'flag 19'},
            BIAS_port = 8771,
            serial_number = 19621,
            handle_name = b'/dev/spcm0',
            triggerDur=10e-3
        )

        #==============================================================================
        # Spectrum Instrumentation Cards
        #==============================================================================

        self.spectrum_0 = Spectrum(
            name='spectrum_0',
            parent_device=clockline_6363,
            trigger={'device': ni_6363_0, 'connection': 'port0/line20'},
            BIAS_port=8770,
            serial_number=19620,
            handle_name = b'/dev/spcm0',
        )

        # self.spectrum_la = Spectrum(
        #     name='spectrum_la',
        #     parent_device=clockline_6363,
        #     trigger={'device': ni_6363_0, 'connection': 'port0/line21'},
        #     BIAS_port=8772,
        #     serial_number=22134,
        #     handle_name = b'/dev/spcm1',
        # )

        ## connected to pulseblaster
        self.spectrum_la = Spectrum(
            name='spectrum_la',
            parent_device= clockline_6363,
            trigger={'device': pb.direct_outputs, 'connection': 'flag 9'},
            BIAS_port=8772,
            serial_number=22134,
            handle_name = b'/dev/spcm1',
        )

        # #==============================================================================
        # # Y AOD DDS: AD9914 0
        # #==============================================================================
        ad99140 = AD9914('AD99140', parent_device=clockline_6363, com_port=54322)
        self.dds0 = AD_DDS(
            name='dds0',
            parent_device=ad99140,
            connection='p0',
            profileControls ={
                'PS0': {'device': ni_6363_0, 'connection': 'port0/line27'},
                'PS1': {'device': ni_6363_0, 'connection': 'port0/line28'},
                'PS2': {'device': ni_6363_0, 'connection': 'port0/line29'},
            },
            sweepControls = {
                'DRCTL': {'device': ni_6363_0, 'connection': 'port0/line30'},
                'DRHOLD': {'device': ni_6363_0, 'connection': 'port0/line31'},
            },

        )
        # #==============================================================================
        # # 456 DDS: AD9914 1
        # #==============================================================================

        # commenting out because 9914 temporarily not working 4/7
        ad9914_1 = AD9914('AD9914_1', parent_device=clockline_6363, com_port=54320)
        self.dds1 = AD_DDS(
            name='dds1',
            parent_device=ad9914_1,
            connection='p1',
            profileControls = {
                'PS0': {'device': ni_6363_0, 'connection': 'port0/line27'},
                'PS1': {'device': ni_6363_0, 'connection': 'port0/line28'},
                'PS2': {'device': ni_6363_0, 'connection': 'port0/line29'},
            },
            sweepControls = {
                'DRCTL': {'device': ni_6363_0, 'connection': 'port0/line30'},
                'DRHOLD': {'device': ni_6363_0, 'connection': 'port0/line31'},
            },
        )

    # def checkChannelParity(device):
    #     analogs = {}
    #     digitals = {}
    #     inputs = {}
    #     for device in device.child_devices:
    #         if isinstance(device, (AnalogOut, StaticAnalogOut)):
    #             analogs[device.connection] = device
    #         elif isinstance(device, (DigitalOut, StaticDigitalOut, Shutter)):
    #             digitals[device.connection] = device
    #         elif isinstance(device, AnalogIn):
    #             inputs[device.connection] = device
    #         else:
    #             raise TypeError(device)

    #     dParity = len(digitals)%2
    #     aParity = len(analogs)%2
    #     parity = aParity | dParity

    #     return parity

devices = LabDevices()

# for connection table compilation
if __name__ == '__main__':
    devices.initialize()
    labscript.start()

    # relock the TA
    devices.ta_relock.go_high(0.1)
    devices.ta_relock.go_low(0.9)

    labscript.stop(1.0)
