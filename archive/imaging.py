# -*- coding: utf-8 -*-
"""
Created on Tue Feb 21 11:52:40 2023

@author: sslab
"""

import sys
root_path = r"C:\Users\sslab\labscript-suite\userlib\labscriptlib"

if root_path not in sys.path:
    sys.path.append(root_path)

from connection_table import devices
from labscriptlib.shot_globals import shot_globals


def mot_imaging_aom(t, repump=True):
    beam_on_aom(t, repump)
    # this 'exposure time' sets the length of the trigger pulse to the manta, which
    #  MAY be the exposure time in one operating mode, but in general does not set
    #  the actual exposure time
    devices.manta419b_mot.expose('manta419b', t, 'atoms', exposure_time=1e-3)

    # Turn beam off after the waiting for the global exposure time
    t += shot_globals.manta_exposure
    beam_off_aom(t)

    return t


# def mot_imaging(t, repump=True):
#     beam_on(t, repump)
#     # this 'exposure time' sets the length of the trigger pulse to the manta, which
#     #  MAY be the exposure time in one operating mode, but in general does not set
#     #  the actual exposure time
#     manta419b_mot.expose('manta419b', t, 'atoms', exposure_time=5e-3)

#     # Turn beam off after the waiting for the global exposure time
#     t += manta_exposure
#     beam_off(t)


#     #raise NotImplementedError()
#     return t

def repump_off(t):
    devices.repump_aom_digital.close(t)
    devices.repump_shutter.close(t)
    return t


def ta_on(t):
    devices.ta_aom_digital.open(t)
    devices.ta_shutter.open(t)
    return t


def ta_off(t):
    devices.ta_aom_digital.close(t)
    devices.ta_shutter.close(t)
    return t


def beam_off_aom(t):
    devices.ta_aom_digital.close(t)
    devices.repump_aom_digital.close(t)
    return t


def beam_on_aom(t, repump: bool):
    devices.ta_aom_digital.open(t)
    if repump:
        devices.repump_aom_digital.open(t)
    else:
        devices.repump_aom_digital.close(t)

    return t


def beam_off(t):
    beam_off_aom(t)

    # Using MOT beams for imaging
    shutters = [
        devices.ta_shutter,
        devices.repump_shutter,
        devices.mot_xy_shutter,
        devices.mot_z_shutter,
    ]
    for shutter in shutters:
        shutter.close(t)

    return t


def beam_on(t, repump: bool):
    beam_on_aom(t, repump)

    # Imaging with MOT beams
    shutters = [
        devices.ta_shutter,
        devices.repump_shutter,
        devices.mot_xy_shutter,
        devices.mot_z_shutter,
    ]
    for shutter in shutters:
        shutter.open(t)

    return t
