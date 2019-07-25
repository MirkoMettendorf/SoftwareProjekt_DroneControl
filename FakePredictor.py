# Author: Mirko Mettendorf, Sandro Günsche
# Version 1.0

#################################################################################
# Simulated Predictor process
#
# This process is intiailized and started in the Main file
# Change the import in Main.py from "from predictor import Predictor"
# to "from FakePredictor import Predictor" to use this


#################################################################################
# needed imports
#

import numpy as np
from struct import unpack
from multiprocessing import Process, JoinableQueue
import keyboard


#################################################################################
# Predictor class
#

class Predictor(Process):
    def __init__(self, data_input_queue, gesture_output_queue, direct_control_queue, earlyPredictors_3D, validationPredictors_3D, class_names_3D, earlyPredictors_2D = [], validationPredictors_2D = [], class_names_2D = []):
        super(Predictor, self).__init__()
        self.data_3d = Data3D()
        self.data_input_queue = data_input_queue
        self.gesture_output_queue = gesture_output_queue
        self.direct_control_queue = direct_control_queue


    def run(self):
        pressed_ = False
        pressedStrg = False
        pressedN = False
        pressedB = False
        pressedEnter = False
        pressedL = False
        while True:
            data = self.data_input_queue.get()
            mode = self.data_3d.check_mode(data)
            if mode == 1:
                if keyboard.is_pressed('Space'):
                    if not pressed_:
                        print("space")
                        self.gesture_output_queue.put([['vali', 'start'], [0, 0, 0, 0]])
                        self.gesture_output_queue.put([['vali', 'startR'], [0, 0, 0, 0]])
                        pressed_ = True
                else:
                    pressed_ = False
                if keyboard.is_pressed('Ctrl'):
                    if not pressedStrg:
                        print("strg")
                        self.gesture_output_queue.put([['vali', 'land'], [0, 0, 0, 0]])
                        self.gesture_output_queue.put([['vali', 'landR'], [0, 0, 0, 0]])
                        pressedStrg = True
                else:
                    pressedStrg = False
                if keyboard.is_pressed('n'):
                    if not pressedN:
                        print("n")
                        self.gesture_output_queue.put([['vali', 'wp_next'], [0, 0, 0, 0]])
                        self.gesture_output_queue.put([['vali', 'wp_nextR'], [0, 0, 0, 0]])
                    pressedN = True
                else:
                    pressedN = False
                if keyboard.is_pressed('b'):
                    if not pressedB:
                        print("b")
                        self.gesture_output_queue.put([['vali', 'wp_back'], [0, 0, 0, 0]])
                        self.gesture_output_queue.put([['vali', 'wp_backR'], [0, 0, 0, 0]])
                        pressedB = True
                else:
                    pressedB = False
                if keyboard.is_pressed('Enter'):
                    if not pressedEnter:
                        print("Enter")
                        self.gesture_output_queue.put([['vali', 'wp_set'], [0, 0, 0, 0]])
                        pressedEnter = True
                else:
                    pressedEnter = False
                if keyboard.is_pressed('l'):
                    if not pressedL:
                        print("l")
                        self.gesture_output_queue.put([['vali', 'wp_del'], [0, 0, 0, 0]])
                        pressedL = True
                else:
                    pressedL = False
            elif mode == 3:
                self.direct_control_queue.put(data)
            self.data_input_queue.task_done()




#################################################################################
# Helper class Data3D
#
# This class stores the incoming 3D data in a numpy array
# 3D consists of accX, accY, accZ, gyroX, gyroY, gyroZ
#

class Data3D:
    def __init__(self):
        self.dataframe = np.zeros(240, dtype=float)
        self.index = 0
        self.TACTI_ACC_COMPRESSION = 819
        self.TACTI_GYRO_COMPRESSION = 32
        self.buttons = []

    def read(self):
        return self.dataframe

    def check_mode(self, data):
        mode = data[19]
        return mode

    def write(self, data):
        timestamp = unpack('H', data[0:2])[0]

        accX = float(unpack('h', data[2:4])[0]) / self.TACTI_ACC_COMPRESSION
        accY = float(unpack('h', data[4:6])[0]) / self.TACTI_ACC_COMPRESSION
        accZ = float(unpack('h', data[6:8])[0]) / self.TACTI_ACC_COMPRESSION

        gyroX = float(unpack('h', data[8:10])[0]) / self.TACTI_GYRO_COMPRESSION
        gyroY = float(unpack('h', data[10:12])[0]) / self.TACTI_GYRO_COMPRESSION
        gyroZ = float(unpack('h', data[12:14])[0]) / self.TACTI_GYRO_COMPRESSION

        b1 = float(unpack('b', data[14:15])[0])
        b2 = float(unpack('b', data[15:16])[0])
        b3 = float(unpack('b', data[16:17])[0])
        b4 = float(unpack('b', data[17:18])[0])

        self.buttons = [b1, b2, b3, b4]

        if abs(accX) <= 0.5:
            accX = 0.0
        if abs(accY) <= 0.5:
            accY = 0.0
        if abs(accZ) <= 0.5:
            accZ = 0.0
        if abs(gyroX) <= 0.5:
            gyroX = 0.0
        if abs(gyroY) <= 0.5:
            gyroY = 0.0
        if abs(gyroZ) <= 0.5:
            gyroZ = 0.0

        if self.index >= 240:
            e = np.empty_like(self.dataframe)
            e[self.index - 6:] = np.nan
            e[:self.index - 6] = self.dataframe[-self.index + 6:]
            self.dataframe = e
            self.dataframe[self.index - 6] = accX
            self.dataframe[self.index - 5] = accY
            self.dataframe[self.index - 4] = accZ
            self.dataframe[self.index - 3] = gyroX
            self.dataframe[self.index - 2] = gyroY
            self.dataframe[self.index - 1] = gyroZ

        else:
            self.dataframe[self.index] = accX
            self.dataframe[self.index + 1] = accY
            self.dataframe[self.index + 2] = accZ
            self.dataframe[self.index + 3] = gyroX
            self.dataframe[self.index + 4] = gyroY
            self.dataframe[self.index + 5] = gyroZ
            self.index += 6

    def clear(self):
        self.dataframe = np.zeros(240, dtype=float)
        self.index = 0


