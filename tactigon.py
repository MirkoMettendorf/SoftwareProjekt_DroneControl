#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2014 Bitcraze AB
#
#  Crazyflie Nano Quadcopter Client
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
#  USA.


#  Author: Thomas Schmidt, UAS Kaiserslautern, Working Group "Smart Machines"
#  Goal: prototype (proof of concept)
#  State: code running, functionality incomplete
#  Date: 09.09.2018
#   
#  Description:
#  This script serves as an input interface for the purpose of connecting the Tactigon/T-Skin 
#  from Next Industries to the Crazyflie Client from Bitcraze. It is automatically run when
#  the Crazyflie Client is started and connects to a given Tactigon/T-Skin via it's MAC adress.
#  It then continuously reads a stream of parameters sent by the Tactigon/T-Skin and maps the received 
#  values to variables which are then mapped to input parameters of the Crazyflie Client.
#
#  Architecture:
#  A callback handles received values and writes them to variables which are then read by the Cfclient.
#  Button-pressed on tactigon (T-Skin) activates hover mode (z-ranger deck)
#  
#  To be done:
#  - Implement Yaw steering, not working properly yet
#  - Implement functionality for different hover-heights (actual: z-ranger deck)
#  - Extend functionality: Include Loco positioning system for precise positioning in a given space

import logging
import struct
from threading import Thread
import binascii
import bluepy
from bluepy import btle

from cfclient.utils.config import Config

__author__ = "Thomas Schmidt"
__version__ = "1.0"
__date__ = "09.09.2018"
__all__ = ['tactigon']

logger = logging.getLogger(__name__)

MODULE_MAIN = "TactigonReader"
MODULE_NAME = "tactigon"

class _PullReader(Thread):
    def __init__(self, receiver, callback, *args):
        super(_PullReader, self).__init__(*args)
        self._receiver = receiver
        self._cb = callback
        self.daemon = True

    def run(self):
        while True:
            self._cb(self._receiver)

#DELEGATE CLASS FOR NOTIFICATION
class MyDelegate(btle.DefaultDelegate):
    def __init__(self):
        btle.DefaultDelegate.__init__(self)

class TactigonReader:
    def __init__(self):
        ble_uuid = btle.UUID("7ac71000-503d-4920-b000-acc000000001")
        service_uuid = btle.UUID("bea5760d-503d-4920-b000-101e7306b000") 
        # The following MAC address has to be changed your T-Skin's Mac address
        p = btle.Peripheral("BE:A5:7F:31:6A:4E")
        bleService = p.getServiceByUUID(service_uuid)
        bleSensorValue = bleService.getCharacteristics(ble_uuid)[0]
        receiver = bleSensorValue.read()
        p.setDelegate(MyDelegate())

        #Initialize parameters expected by the Cfclient
        self.name = MODULE_NAME
        self.limit_rp = False
        self.limit_thrust = False
        self.limit_yaw = False

        self.data = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0,
                     "thrust": -1.0, "estop": False, "exit": False,
                     "assistedControl": False, "alt1": False, "alt2": False,
                     "pitchNeg": False, "rollNeg": False,
                     "pitchPos": False, "rollPos": False}
        
        logger.info("Initialized Tactigon")

        self._receiver_thread = _PullReader(bleSensorValue, self._cmd_callback)
        self._receiver_thread.start()

    def _cmd_callback(self, cmd):
        i = cmd.read()
        sp, p, sr, r, sy, y = struct.unpack('6B', i)
        #   Unpacking variables sent by the Tactigon. As of now there are 6 variables sent.
        #   This is necessary because data is sent as unsigned chars. For the Cfclient we need
        #   positive and negative values in order to steer the Crazyflie correctly. To achieve this
        #   variables sp, sr and sy encode the sign of p, r and y values sent by the Tactigon. If one of those
        #   values is negative, the corresponding variable sp, sr or sy has the value 0. If this is the case
        #   the p, r or y value has to be multiplied by -1 in order to get negative values.
        #   sp          -> sign of pitch
        #   p           -> value of pitch
        #   sr          -> sign of roll
        #   r           -> value of roll
        #   sy          -> sign of yaw
        #   y           -> value of yaw
        if sp == 1:
            self.data["pitch"] = p/10
        if sp == 0:
            self.data["pitch"] = p/10 * (-1.0)
        if sr == 0:
            self.data["roll"] = (r/10) * (-1.0)
        if sr == 1:
            self.data["roll"] = r/10
       	if sy == 1:
          self.data["yaw"] = (y/10) * (-1.0)
        if sy == 0:
          self.data["yaw"] = y/10
                   

    def open(self, device_id):
        """
        Initialize the reading and open the device with deviceId and set the
        mapping for axis/buttons using the inputMap
        """
        return

    def read(self, device_id):
        """Read input from the selected device."""
        return self.data

    def close(self, device_id):
        return

    def devices(self):
        """List all the available connections"""
        # As a temporary workaround we always say we have ZMQ
        # connected. If it's not connected, there's just no data.
        return [{"id": 0, "name": "Tactigon"}]
