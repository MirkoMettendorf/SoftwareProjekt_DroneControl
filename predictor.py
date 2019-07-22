# Author: Alexander Schwarz
# Version 1.0

#################################################################################
# Predictor process
#
# This process is intiailized and started in the Main file
#


#################################################################################
# needed imports
#

import numpy as np
import binascii, sys, json, logging
from struct import unpack
from multiprocessing import Process, JoinableQueue
import enum


#################################################################################
# Predictor class
#

class Predictor(Process):
    def __init__(self, data_input_queue, gesture_output_queue, direct_control_queue, earlyPredictors_3D,
                 validationPredictors_3D, class_names_3D, earlyPredictors_2D=[], validationPredictors_2D=[],
                 class_names_2D=[]):
        super(Predictor, self).__init__()
        self.data_3d = Data3D()
        self.data_2d = Data2D()
        self.data_input_queue = data_input_queue
        self.gesture_output_queue = gesture_output_queue
        self.direct_control_queue = direct_control_queue
        self.state = STATE.EARLY_PREDICTION
        self.earlyClf_3d = earlyPredictors_3D
        self.validationClf_3d = validationPredictors_3D
        self.class_names_3d = class_names_3D
        self.earlyClf_2d = earlyPredictors_2D
        self.validationClf_2d = validationPredictors_2D
        self.class_names_2d = class_names_2D
        self.predictionvalue = 'none'
        self.pred_20_timer = 0
        self.pred_40_timer = 0
        self.pred_end_timer = 0
        self.count = 0
        self.pred = 'none'
        self.previous_gesture = 'none'
        self.is3d = True

    def run(self):
        while True:
            data = self.data_input_queue.get()
            mode = self.data_3d.check_mode(data)
            if mode == 1:
                if not self.is3d:
                    self.is3d = True
                self.data_3d.write(data)
                self.state_machine()
                self.gesture_output_queue.put([self.pred, self.data_3d.buttons])
            elif mode == 2:
                if len(self.earlyClf_2d) == 0:
                    # error this needs another predictor
                    print('Dimension change from 3D to 2D not allowed during runtime')
                    print('Application Mode 2D needs another predictor')
                    break
                else:
                    self.is3d = False
                    self.data_2d.write(data)
                    self.state_machine()
                    self.gesture_output_queue.put([self.pred, self.data_2d.buttons])
            elif mode == 3:
                self.direct_control_queue.put(data)
            self.data_input_queue.task_done()

    # predicts a gesture
    def prediction(self, data, predictors):
        i = 0
        imax = 0
        max_value = 0

        for predictor in predictors:
            index = np.where(predictor.classes_ == 'unknown')[0]
            if index == 0:
                pred = predictor.predict_proba(data)[0][1]
            else:
                pred = predictor.predict_proba(data)[0][0]

            if pred > max_value:
                max_value = pred
                imax = i

            i += 1

        if max_value < 0.3:
            return ['unknown']
        if not self.is3d:
            return [self.class_names_2d[imax]]
        return [self.class_names_3d[imax]]

    def state_machine(self):
        if self.state == STATE.EARLY_PREDICTION:
            if self.predictionvalue == 'none' or self.predictionvalue == 'unknown' or self.predictionvalue == 'stillGesture':
                if self.pred_20_timer >= 5:
                    if self.is3d:
                        pred = self.prediction([self.data_3d.read()[0:120]], self.earlyClf_3d)
                    else:
                        pred = self.prediction([self.data_2d.read()[0:60]], self.earlyClf_2d)
                    self.predictionvalue = pred[0]
                    self.pred = ['early', pred[0]]

                    if pred[0] != 'unknown' and pred[0] != 'stillGesture':
                        # print('early prediction: ', pred[0])
                        self.pred_20_timer = 0
                        self.state = STATE.VALIDATION

                else:
                    self.pred_20_timer += 1

        elif self.state == STATE.VALIDATION:
            if self.predictionvalue != 'none' and self.predictionvalue != 'unknown' and self.predictionvalue != 'stillGesture':
                if self.pred_40_timer >= 10:
                    if self.is3d:
                        pred = self.prediction([self.data_3d.read()[0:240]], self.validationClf_3d)
                    else:
                        pred = self.prediction([self.data_2d.read()[0:120]], self.validationClf_2d)
                    if pred[0] == self.predictionvalue:
                        print('gesture validated: ', pred[0])
                        # uncomment to detect retractions
                        # bad approach should be in application
                        # if self.previous_gesture != 'none':
                        #    self.pred, self.previous_gesture = self.check_retraction(pred[0])
                        # else:
                        #    self.pred = pred[0]
                        #    self.previous_gesture = pred[0]
                        self.predictionvalue = 'none'
                        self.state = STATE.VALIDATED
                        self.pred_40_timer = 0
                        self.count = 0
                        self.pred = ['vali', pred[0]]
                        # self.gesture_output_queue.put([pred[0], self.data.buttons])
                    else:
                        self.pred = 'none'
                        if self.count >= 9:
                            # print('false prediction: ', pred[0])
                            self.predictionvalue = 'none'
                            self.state = STATE.EARLY_PREDICTION
                            self.pred_40_timer = 0
                            self.count = 0
                        self.count += 1
                else:
                    self.pred_40_timer += 1

        elif self.state == STATE.VALIDATED:
            self.pred = 'none'
            if self.pred_end_timer >= 5:
                if self.is3d:
                    pred = self.prediction([self.data_3d.read()[0:120]], self.earlyClf_3d)
                else:
                    pred = self.prediction([self.data_2d.read()[0:60]], self.earlyClf_2d)
                if pred[0] == 'stillGesture':
                    print('end of gesture detected')
                    self.pred = ['end', 'none']
                    # state = 'end'
                    self.state = STATE.EARLY_PREDICTION
                    self.pred_end_timer = 0
                    if self.is3d:
                        self.data_3d.clear()
                    else:
                        self.data_2d.clear()
            else:
                self.pred_end_timer += 1

        # elif state == 'end':

    # THIS SHOULD NOT BE IN HERE
    # the check if a gesture is the retraction of a previous gesture
    # should be in the application. The gestures that are predicted by
    # the gesture recognizer can differ in every application.
    def check_retraction(self, pred):
        if self.previous_gesture != 'none':
            if self.previous_gesture == 'linMoveNegX':
                if pred == 'linMovePosX':
                    return 'retraction', 'none'
                else:
                    return pred, pred
            elif self.previous_gesture == 'linMovePosX':
                if pred == 'linMoveNegX':
                    return 'retraction', 'none'
                else:
                    return pred, pred
            elif self.previous_gesture == 'linMoveNegY':
                if pred == 'linMovePosY':
                    return 'retraction', 'none'
                else:
                    return pred, pred
            elif self.previous_gesture == 'linMovePosY':
                if pred == 'linMoveNegY':
                    return 'retraction', 'none'
                else:
                    return pred, pred
            elif self.previous_gesture == 'linMoveNegZ':
                if pred == 'linMovePosZ':
                    return 'retraction', 'none'
                else:
                    return pred, pred
            elif self.previous_gesture == 'linMovePosZ':
                if pred == 'linMoveNegZ':
                    return 'retraction', 'none'
                else:
                    return pred, pred


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


#################################################################################
# Helper class Data2D
#
# This class stores the incoming 3D data in a numpy array
# 2D consists of accX, accY, gyroZ
#

class Data2D:
    def __init__(self):
        self.dataframe = np.zeros(120, dtype=float)
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

        gyroZ = float(unpack('h', data[6:8])[0]) / self.TACTI_GYRO_COMPRESSION

        b1 = float(unpack('b', data[14:15])[0])
        b2 = float(unpack('b', data[15:16])[0])
        b3 = float(unpack('b', data[16:17])[0])
        b4 = float(unpack('b', data[17:18])[0])

        self.buttons = [b1, b2, b3, b4]

        if abs(accX) <= 0.5:
            accX = 0.0
        if abs(accY) <= 0.5:
            accY = 0.0
        if abs(gyroZ) <= 0.5:
            gyroZ = 0.0

        if self.index >= 120:
            e = np.empty_like(self.dataframe)
            e[self.index - 3:] = np.nan
            e[:self.index - 3] = self.dataframe[-self.index + 3:]
            self.dataframe = e
            self.dataframe[self.index - 3] = accX
            self.dataframe[self.index - 2] = accY
            self.dataframe[self.index - 1] = gyroZ

        else:
            self.dataframe[self.index] = accX
            self.dataframe[self.index + 1] = accY
            self.dataframe[self.index + 2] = gyroZ
            self.index += 3

    def clear(self):
        self.dataframe = np.zeros(120, dtype=float)
        self.index = 0


# enum for state_machine
class STATE(enum.Enum):
    EARLY_PREDICTION = 1
    VALIDATION = 2
    VALIDATED = 3