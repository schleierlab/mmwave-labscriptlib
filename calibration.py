import numpy as np


def ta_freq_calib(detuning_mhz):
    '''
    Yield the control voltage required to set the TA to a desired detuning
    from the 4 -> 5 transition in the cesium D2 line.

    Parameters
    ----------
    detuning_mhz : array_like
        Detuning in MHz from the cesium D2 4 -> 5 hyperfine transition.

    Returns
    -------
    voltage
        Control voltage needed to produce desired optical frequency.
    '''
    if not (-438 <= detuning_mhz <= 121):
        raise ValueError("TA frequency detuning must be within [-438, 121] MHz")


    # f = np.poly1d(np.array([
    #     1.09188604e-15,
    #     1.23734055e-12,
    #     4.72307811e-10,
    #     1.31827284e-08,
    #    -1.21333912e-05,
    #    -1.42724971e-02,
    #    1.69243194e+00
    # ]))

    # 2024/01/04
    # f = np.poly1d(np.array([1.69904275e-15,
    #                         1.86873771e-12,
    #                         6.70317726e-10,
    #                         2.33845162e-08,
    #                         -1.52527834e-05,
    #                         -1.44239092e-02,
    #                         1.70416960e+00]))

    # 2024/11/11
    f = np.poly1d(np.array([1.29077826e-15,
                            1.38450146e-12,
                            4.77126509e-10,
                            -1.66416905e-09,
                            -1.31919006e-05,
                            -1.39610019e-02,
                            1.67363876e+00]))

    off_set_freq = 3 #10 #-6 # MHz measued using 0.1V ta AOM atom imaging response

    return f(detuning_mhz + off_set_freq)


def generate_ta_freq_calib_coeff():
    ta_voltage = np.array([
        1.825,
        1.5,
        1,
        0.5,
        0,
        2,
        2.05,
        2.3,
        2.5,
        3,
        3.5,
        4,
        4.5,
        5,
        5.5,
        6,
        6.5,
        7,
        7.5,
        8,
        8.5,
        9,
        9.5,
        10,
    ]) # Volts

    # beat note freq in MHz
    # Measured with frequency counter

    # 20241111
    beat_note = np.array([
       264.8,
       245.1,
       204.5,
       176.5,
       138.06,
       275.8,
       279.8,
       301.8,
       317.8,
       355.7,
       394.8,
       430.9,
       462.4,
       493.3,
       520.5,
       546,
       569.9,
       592.6,
       613.7,
       632.8,
       651,
       668.1,
       684.4,
       699.3,
    ])

    # beat_note = np.array([
    #     262.38,
    #     242.62,
    #     203.37,
    #     177.11,
    #     134.74,
    #     273.12,
    #     277.10,
    #     298.82,
    #     314.28,
    #     351.59,
    #     391.71,
    #     428.94,
    #     461.18,
    #     493.07,
    #     520.23,
    #     546.27,
    #     570.48,
    #     593.53,
    #     614.82,
    #     634.50,
    #     653.20,
    #     670.52,
    #     686.55,
    #     701.72
    # ])

    # beat_note = np.array([
    #     263.60,
    #     240.09,
    #     204.95,
    #     176.164,
    #     136.67,
    #     276.16,
    #     279.81,
    #     313.71,
    #     353.06,
    #     392.46,
    #     424.09,
    #     462.44,
    #     493.07,
    #     520.87,
    #     546.78,
    #     571.08,
    #     593.92,
    #     615.338,
    #     635.18,
    #     653.62,
    #     670.93,
    #     687.16,
    #     702.38,
    # ])

    reflaser_doublepass_freq_mhz = 400
    ta_switch_aom_freq_mhz = 80

    # optical frequencies measured relative to 4 -> 5 D2 transition
    threefive_crossover_freq_mhz = 38 - 264  # relative to 4 -> 5 transition
    ta_freq_mhz = threefive_crossover_freq_mhz + reflaser_doublepass_freq_mhz + ta_switch_aom_freq_mhz - beat_note

    coeff = np.polyfit(ta_freq_mhz, ta_voltage, 6)  # fitted to the 6th order
    print(repr(coeff))


def repump_freq_calib(detuning_mhz):
    # this detuning is relative to F = 3 -> F' = 4 tranisition
    # f = np.poly1d(np.array([ 3.05390232e-14,  2.18562217e-11,  5.45062179e-09,  4.01536932e-07,
    #    -3.64452729e-05, -3.21551810e-02,  2.24658348e+00]))

    #20241112
    f = np.poly1d(np.array([2.93833235e-14,
                            2.12699651e-11,
                            5.39636666e-09,
                            4.15169376e-07,
                            -3.41448762e-05,
                            -3.21482962e-02,
                            2.21019254e+00]))


    if (detuning_mhz < -275 or detuning_mhz > 76):
        raise RuntimeError("Repump frequency detuning must be in the range of (-275MHz, 76MHz)")
    else:
        voltage = f(detuning_mhz)

    return voltage


def generate_repump_freq_calib_coeff():
    repump_voltage = np.array([2.3,2,1,0,3,4,5,6,7,8,9,10]) # Volts

    # beat_note = np.array([
    #     399.89,
    #     389.85,
    #     362.11,
    #     321.92,
    #     424.26,
    #     459.62,
    #     496.39,
    #     534.89,
    #     574.27,
    #     610.80,
    #     643.95,
    #     674.44
    # ]) # Measured with frequency counter

    #20241111
    beat_note = np.array([
        401.14,
        390.89,
        363.12,
        323.13,
        425.43,
        460.75,
        497.50,
        536.01,
        575.29,
        611.77,
        644.90,
        675.40
    ]) # Measured with frequency counter
    repump_frequency = -9.192e3 + 38 - 13 + 80 - (beat_note - 9.486e3) # MHz frequency relative to F = 3 -> F' = 4 transition 13 MHz, 3/5 cross over 38MHz, Switch AOM 80 MHz, 6S1/2 hyperfine splitting -9.192e3, LO = 9.486e3

    coeff = np.polyfit(repump_frequency, repump_voltage, 6) # fitted to the 6th order
    print(repr(coeff))

def spec_freq_calib(mw_detuning):
    """ convert microwave detuning to spectrum card frequency """
    uwave_clock = 9.192631770e3  # clock frequency 4,0 -> 5,0 in unit of MHz
    local_oscillator_freq_mhz = 9486  # in unit of MHz MKU LO 8-13 PLL setting
    spec_freq = (local_oscillator_freq_mhz -uwave_clock -mw_detuning)*1e6 # in unit of Hz
    return spec_freq


def biasx_calib(field):
    # unit: V, mG
    V0 = 0.6134 #0.5243 # V
    Bp = 842.47 #546.8 # mG/V
    voltage = V0 +1/Bp*field
    return voltage

def biasy_calib(field):
    V0 =  0.0678 # V
    Bp = 1193.4 # mG/V
    voltage = V0 +1/Bp*field
    return voltage

def biasz_calib(field):
    V0 = -0.6682 # V
    Bp = 1096.9 # mG/V
    voltage = V0 + 1/Bp * field
    return voltage

# unit: V, MHz shift on 41S state
def Ex_calib(shift):
    V0 = 0.29 #0.5243 # V
    a = 0.09 #546.8 # MHz/V^2
    voltage = np.sign(shift)*np.sqrt(np.abs(shift)/a) + V0
    return voltage

def Ey_calib(shift):
    V0 = 0 #0.5243 # V
    a = 0.35 #546.8 # MHz/V^2
    voltage = np.sign(shift)*np.sqrt(np.abs(shift)/a) + V0
    return voltage


def Ez_calib(shift):
    V0 = -0.01 #0.5243 # V
    a = 0.41 #546.8 # MHz/V^2
    voltage = np.sign(shift)*np.sqrt(np.abs(shift)/a) + V0
    return voltage


def tweezer_power_calib(power_W):
    f = np.poly1d(np.array([-3.69348513e+00,  2.31281736e+01, -4.15014983e+01,  3.26061566e+01,
       -1.20376660e+01,  2.30540602e+00,  3.74047483e-02]))


    if (power_W < 0 or power_W > 1):
        raise RuntimeError("Power must be in the range of (0, 1)")
    else:
        voltage = f(power_W)

    return voltage


def generate_tweezer_power_calib_coeff():
    power = np.array([
        6.5,
        6.54,
        6.55,
        6.58,
        6.31,
        5.59,
        5.35,
        4.86,
        4.48,
        3.63,
        2.83,
        1.988,
        1.172,
        0.438,
        0.054,
        0.014
        ]) # Watts

    voltage = np.array([
        1,
        0.9,
        0.8,
        0.7,
        0.6,
        0.55,
        0.5,
        0.45,
        0.4,
        0.35,
        0.3,
        0.25,
        0.2,
        0.15,
        0.1,
        0
    ]) # voltage


    coeff = np.polyfit(power, voltage, 6) # fitted to the 6th order
    print(repr(coeff))



def ta_aom_calib(power):

    if not (0 <= power <= 1):
        raise ValueError("TA relative power must be within [0, 1]")


    f = np.poly1d(np.array([
         11.80562729,
         -22.27668541,
         8.40931054,
         6.91228052,
        -5.98887408,
        2.0012694 ,
        0.0467131 ]))

    return f(power)


def repump_aom_calib(power):

    if not (0 <= power <= 1):
        raise ValueError("repump relative power must be within [0, 1]")


    f = np.poly1d(np.array([
        -4.37130432,
        21.73516051,
        -35.6730173 ,
        26.8234801 ,
       -10.09196713,
       2.43904316,
       0.05066173]))

    return f(power)

def img_z_ta_calib(power):
    #input: optical power, output: the AOM voltage at this optical power
    power_max = 2.28 # mW the max power at 1V analog control
    return ta_aom_calib(power/power_max)

def img_z_repump_calib(power):
    power_max = 0.255 # mW the max power at 1V analog control
    return repump_aom_calib(power/power_max)

def img_x_ta_calib(power):
    power_max = 2.32 # mW the max power at 1V analog control
    return ta_aom_calib(power/power_max)

def img_x_repump_calib(power):
    power_max = 0.255 # mW the max power at 1V analog control
    return repump_aom_calib(power/power_max)

def img_y_ta_calib(power):
    power_max = 2.25 # mW the max power at 1V analog control
    return ta_aom_calib(power/power_max)

def img_y_repump_calib(power):
    power_max = 0.73 # mW the max power at 1V analog control
    return repump_aom_calib(power/power_max)

def mot_z_ta_calib(power):
    power_max = 30.3 # mW the max power at 1V analog control
    return ta_aom_calib(power/power_max)

def mot_z_repump_calib(power):
    power_max = 3.8 # mW the max power at 1V analog control
    return repump_aom_calib(power/power_max)

def mot_x_ta_calib(power):
    power_max = 47 # mW the max power at 1V analog control
    return ta_aom_calib(power/power_max)

def mot_x_repump_calib(power):
    power_max = 7.9 # mW the max power at 1V analog control
    return repump_aom_calib(power/power_max)

def mot_y_ta_calib(power):
    power_max = 33 # mW the max power at 1V analog control
    return ta_aom_calib(power/power_max)

def mot_y_repump_calib(power):
    power_max = 5.4 # mW the max power at 1V analog control
    return repump_aom_calib(power/power_max)


def local_addr_move_cal(displacement):
    #Maybe makes more sense to calibrate the velocities...?

    piezo_V_to_v = np.array([
        [matrix]
    ])



    #_______________________________________________________


    cal_disp_dur = 1
    piezo_cal_v = 5

    piezo_to_disp = np.array([
        [matrix]
    ])

    #Inverting the displacement matrix to give some piezo 
    disp_to_piezo = np.linalg.inv(matrix)
    piezo_unnorm = disp_to_piezo @ np.array(displacement)

    #Rescaling so the fastest piezo goes at the voltage used for the calibration
    #and then the duration of the move is also scaled accordingly
    piezo_rescaled = piezo_unnorm * (piezo_cal_v / max(piezo_unnorm))
    dur = cal_disp_dur / (piezo_cal_v / max(piezo_unnorm))

    #Accounting for different speeds in different directions
    sign_factor = 0.1
    piezo_voltages = [p * ((p<0)*sign_factor + 1) for p in piezo_rescaled]

    return displacement#, dur


if __name__ == '__main__':

    # generate_ta_freq_calib_coeff()
    # print(ta_freq_calib(-13))

    generate_repump_freq_calib_coeff()
    print(repump_freq_calib(0))

    # x_lst = np.arange(0, 2.2, 0.01) #optical power
    # y_lst = []
    # for i in x_lst:
    #     aom_vol = img_x_ta_calib(i)
    #     y_lst.append()
    # imgy = img_y_ta_calib(1.13)
    # imgz = img_z_ta_calib(1.26)

    # print(imgx, imgy, imgz, '1V')
