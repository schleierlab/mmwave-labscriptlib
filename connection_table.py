from labscript import ClockLine, DigitalOut, AnalogOut, Shutter
import labscript

from labscript_devices.PulseBlasterUSB import PulseBlasterUSB
from user_devices.NI_PXIe_6363 import NI_PXIe_6363
from user_devices.NI_PXIe_6739 import NI_PXIe_6739
from user_devices.manta419b.manta419b import Manta419B
from user_devices.spcm.Spectrum_bk import Spectrum
# from user_devices.spcm.Spectrum import Spectrum
from user_devices.DDS.AD_DDS import AD_DDS
from user_devices.DDS.AD9914 import AD9914
from user_devices.kinetix.Kinetix import Kinetix
import labscript_devices as labscript_devices
import labscript_devices.FunctionRunner
import labscript_devices.FunctionRunner.labscript_devices



# please name devices with lower_case_with_underscores (uwave_absorp_switch)
# NOT Capitalized_Words_With_Underscores

class LabDevices():
    def __init__(self):
        pass

    def __getattr__(self, name):
        raise AttributeError(f'Device {name} not defined. Did you forget to call initialize()?')

    def initialize(self):
        print('Initializing connection table')

        pb = PulseBlasterUSB(name='pb', board_number=0)

        clockline_6363 = ClockLine(
            name='clockline_6363',
            pseudoclock=pb.pseudoclock,
            connection='flag 16',
        )
        ni_6363_0 = NI_PXIe_6363(
            name='ni_6363_0',
            parent_device=clockline_6363,
            clock_terminal='/ni_6363_0/PFI0',
            MAX_name='ni_6363_0',
        )

        # ClockLine(name="clockline_spectrum", pseudoclock=pb.pseudoclock, connection="flag 18")   #for testing spectrum card when directly connected to pulseblaster
        aom_delay = 0  # 630e-9 #delay time between the pulse and AOM
        aom_delays = (aom_delay, aom_delay)

        self.ta_aom_digital = Shutter(
            name='ta_aom_digital',
            parent_device=ni_6363_0,
            connection='port0/line0',
            delay=aom_delays,
            open_state=1,
        )


        self.repump_aom_digital = Shutter(
            name='repump_aom_digital',
            parent_device=ni_6363_0,
            connection='port0/line1',
            delay=aom_delays,
            open_state=1,
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
            connection='port0/line12',
        )

        # port 2 is camera
        # should this be deprecated?
        self.mot_camera_trigger = DigitalOut(
            name='mot_camera_trigger',
            parent_device=ni_6363_0,
            connection='port0/line2',
        )

        self.uwave_dds_switch = DigitalOut(
            name='uwave_dds_switch',
            parent_device=ni_6363_0,
            connection='port0/line3',
        )

        # self.uwave_absorp_switch = DigitalOut(
        #     name='uwave_absorp_switch',
        #     parent_device=ni_6363_0,
        #     connection='port0/line4',
        # )

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



        self.tweezer_aom_digital = DigitalOut(
            name='tweezer_aom_digital',
            parent_device = pb.direct_outputs,
            connection='flag 12',
        )

        # self.tweezer_aom_digital = DigitalOut(
        #     name='tweezer_aom_digital',
        #     parent_device = ni_6363_0,
        #     connection='port0/line12',
        # )

        self.tweezer_camera_trigger = DigitalOut(
            name='tweezer_camera_trigger',
            parent_device=ni_6363_0,
            connection='port0/line13',
        )
        self.ipg_1064_aom_digital = DigitalOut(
            name='ipg_1064_aom_digital',
            parent_device = pb.direct_outputs,
            connection='flag 13',
        )

        # self.ipg_1064_aom_digital = DigitalOut(
        #     name='ipg_1064_aom_digital',
        #     parent_device = ni_6363_0,
        #     connection='port0/line14',
        # )

        self.kinetix_camera_trigger = DigitalOut( #use this when not using kinetix server
            name='kinetix_camera_trigger',
            parent_device=ni_6363_0,
            connection='port0/line15',
        )

        self.moglabs_456_aom_digital = DigitalOut(
            name='moglabs_456_aom_digital',
            parent_device = pb.direct_outputs,
            connection='flag 14',
        )

        # self.moglabs_456_aom_digital = DigitalOut(
        #     name='moglabs_456_aom_digital',
        #     parent_device = ni_6363_0,
        #     connection='port0/line16',
        # )

        self.octagon_456_aom_digital = DigitalOut(
            name='octagon_456_aom_digital',
            parent_device = pb.direct_outputs,
            connection='flag 15',
        )

        self.pulse_1064_digital = DigitalOut(
            name='pulse_1064_digital',
            parent_device = pb.direct_outputs,
            connection='flag 10',
        )

        self.local_addr_1064_aom_digital = DigitalOut(
            name='local_addr_1064_aom_digital',
            parent_device = pb.direct_outputs,
            connection='flag 11',
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

        self.digital_out_ch22 = DigitalOut(
            name='digital_out_ch22',
            parent_device=ni_6363_0,
            connection='port0/line22',
        )

        self.mmwave_switch = DigitalOut(
            name='mmwave_switch',
            parent_device=ni_6363_0,
            connection='port0/line23',
        )

        self.blue_456_shutter = Shutter(
            name='blue_456_shutter',
            parent_device=ni_6363_0,
            connection='port0/line18',
            delay=ta_shutter_delays,
            open_state=1,
        )

        # self.digital_out_ch26 = DigitalOut(
        #     name='digital_out_ch26',
        #     parent_device=ni_6363_0,
        #     connection='port0/line26',
        # )



        clockline_6739 = ClockLine(name='clockline_6739', pseudoclock=pb.pseudoclock, connection='flag 17')
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


        self.ta_vco = AnalogOut(name='ta_vco', parent_device=ni_6739_0, connection='ao2')
        self.repump_vco = AnalogOut(name='repump_vco', parent_device=ni_6739_0, connection='ao3')
        self.mot_coil_current_ctrl = AnalogOut(name='mot_coil_current_ctrl', parent_device=ni_6739_0, connection='ao4')
        self.x_coil_current = AnalogOut(name='x_coil_current', parent_device=ni_6739_0, connection='ao5')
        self.y_coil_current = AnalogOut(name='y_coil_current', parent_device=ni_6739_0, connection='ao6')
        self.z_coil_current = AnalogOut(name='z_coil_current', parent_device=ni_6739_0, connection='ao7')
        self.tweezer_aom_analog = AnalogOut(name='tweezer_aom_analog', parent_device=ni_6739_0, connection='ao8', limits=(0, 1))
        self.ipg_1064_aom_analog = AnalogOut(name='notconnected_ipg_1064_aom_analog', parent_device=ni_6739_0, connection='ao9', limits=(0, 1))
        self.moglabs_456_aom_analog = AnalogOut(name='notconnected_moglabs_456_aom_analog', parent_device=ni_6739_0, connection='ao10', limits=(0, 1))

        self.mirror_1_vertical = AnalogOut(
            name='mirror_1_vertical',
            parent_device=ni_6739_0,
            connection='ao11',
            limits=(0, 10),
        )

        self.mirror_1_horizontal = AnalogOut(
            name='mirror_1_horizontal',
            parent_device=ni_6739_0,
            connection='ao12',
            limits=(0, 10),
        )

        self.mirror_2_vertical = AnalogOut(
            name='mirror_2_vertical',
            parent_device=ni_6739_0,
            connection='ao13',
            limits=(0, 10),
        )

        self.mirror_2_horizontal = AnalogOut(
            name='mirror_2_horizontal',
            parent_device=ni_6739_0,
            connection='ao14',
            limits=(0, 10),
        )

        self.octagon_456_aom_analog = AnalogOut(name='octagon_456_aom_analog', parent_device=ni_6739_0, connection='ao15', limits=(0, 1))

        self.local_addr_1064_aom_analog = AnalogOut(name='local_addr_1064_aom_analog', parent_device=ni_6739_0, connection='ao16', limits=(0, 1))

        self.pulse_1064_analog = AnalogOut(name='pulse_1064_analog', parent_device=ni_6739_0, connection='ao17', limits=(0, 1))

        # self.dummy = AnalogOut(name='dummy', parent_device=ni_6739_0, connection='ao17', limits=(0, 1))



        self.runner = labscript_devices.FunctionRunner.labscript_devices.FunctionRunner(
            name = 'runner')


        #==============================================================================
        # Cameras
        #==============================================================================

        self.manta419b_mot = Manta419B(
            'manta419b_mot',
            parent_device=ni_6363_0,
            connection="port0/line2",
            BIAS_port=54321,
        )

        # self.manta419b_tweezer = Manta419B(
        #     'manta419b_tweezer',
        #     parent_device=ni_6363_0,
        #     connection="port0/line13",
        #     BIAS_port=54324,
        # )

        # self.manta419b_blue_laser = Manta419B(
        #     'manta419b_blue_laser',
        #     parent_device=ni_6363_0,
        #     connection="port0/line2",
        #     BIAS_port=54323,
        # )

        # self.manta419b_dipole_trap = Manta419B(
        #     'manta419b_dipole_trap',
        #     parent_device=ni_6363_0,
        #     connection="port0/line2",
        #     BIAS_port=54323,
        # )

        # self.kinetix = Kinetix(
        #     name='kinetix',
        #     parent_device=ni_6363_0,
        #     connection='port0/line15',
        #     BIAS_port=27171,
        # )

        #================================================================================
        # Spectrum Instrumentation Cards for microwaves
        #================================================================================
        self.spectrum_uwave = Spectrum(name='spectrum_uwave', parent_device=clockline_6363,
                    trigger={'device': ni_6363_0, 'connection': 'port0/line21'},
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

        # self.spectrum_1 = Spectrum(
        #     name='spectrum_1',
        #     parent_device=clockline_6363,
        #     trigger={'device': ni_6363_0, 'connection': 'port0/line21'},
        #     BIAS_port=8771,
        #     serial_number=19621,
        #     handle_name = b'/dev/spcm1',
        # )

        ## for testing spectrum card when directly connected to pulseblaster
        # self.spectrum_1 = Spectrum(
        #     name='spectrum_1',
        #     parent_device=clockline_spectrum,
        #     trigger={'device': pb.direct_outputs, 'connection': 'flag 19'},
        #     BIAS_port=8771,
        #     serial_number=19621,
        #     handle_name = b'/dev/spcm1',
        # )

        # #==============================================================================
        # # Y AOD DDS: AD9914 0
        # #==============================================================================
        # ad99140 = AD9914('AD99140', parent_device=clockline_6363, com_port=54322)
        # self.dds0 = AD_DDS(
        #     name='dds0',
        #     parent_device=ad99140,
        #     connection='p0',
        #     profileControls ={
        #         'PS0': {'device': ni_6363_0, 'connection': 'port0/line27'},
        #         'PS1': {'device': ni_6363_0, 'connection': 'port0/line28'},
        #         'PS2': {'device': ni_6363_0, 'connection': 'port0/line29'},
        #     },
        #     sweepControls = {
        #         'DRCTL': {'device': ni_6363_0, 'connection': 'port0/line30'},
        #         'DRHOLD': {'device': ni_6363_0, 'connection': 'port0/line31'},
        #     },

        # )
        # #==============================================================================
        # # 456 DDS: AD9914 1
        # #==============================================================================

        # ad9914_1 = AD9914('AD9914_1', parent_device=clockline_6363, com_port=54320)
        # self.dds1 = AD_DDS(
        #     name='dds1',
        #     parent_device=ad9914_1,
        #     connection='p1',
        #     profileControls = {
        #         'PS0': {'device': ni_6363_0, 'connection': 'port0/line27'},
        #         'PS1': {'device': ni_6363_0, 'connection': 'port0/line28'},
        #         'PS2': {'device': ni_6363_0, 'connection': 'port0/line29'},
        #     },
        #     sweepControls = {
        #         'DRCTL': {'device': ni_6363_0, 'connection': 'port0/line30'},
        #         'DRHOLD': {'device': ni_6363_0, 'connection': 'port0/line31'},
        #     },
        # )

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

    labscript.stop(1.0)