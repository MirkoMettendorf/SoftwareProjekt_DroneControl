#Author: Alexander Schwarz
#Version 1.0

#################################################################################
# Main file for the gesture recognizer
#
# In here the Bluetooth Low Energy (BLE) Communication to the Tactigon will be
# initialized. The callback of the streaming Characteristic is implemented in
# the myStreamCB() function and passed to the Tactigon-Wrapper.
# Also the predictor process and the application process will be initialized
# and started in here. The predictor and the application processes communicate
# over queues which are created here.
# The trained models for the gesture recognizer must be loaded here and then
# be passed to the predictor process.
#


#################################################################################
# needed imports
#

import struct
import binascii
import pandas as pd
import numpy as np
import math
import itertools
from sklearn.neural_network import MLPClassifier
from predictor import Data3D
from predictor import Predictor
from multiprocessing import JoinableQueue
from application import Application

from joblib import load

from TwoWayComm import BTCommunication, LED_COLOR, LED_MODE, DIMENSION, USAGE, MODE, GNORM
import time

TACTI_ACC_COMPRESSION = 819
TACTI_GYRO_COMPRESSION = 32


#################################################################################
# load trained models
#

#early predictors
start_clf_20 = load('./models/crazyFlyGestures/start_nn_20.joblib')
startR_clf_20 = load('./models/crazyFlyGestures/startR_nn_20.joblib')
land_clf_20 = load('./models/crazyFlyGestures/land_nn_20.joblib')
landR_clf_20 = load('./models/crazyFlyGestures/landR_nn_20.joblib')
wp_back_clf_20 = load('./models/crazyFlyGestures/wp_back_nn_20.joblib')
wp_backR_clf_20 = load('./models/crazyFlyGestures/wp_backR_nn_20.joblib')
wp_del_clf_20 = load('./models/crazyFlyGestures/wp_del_nn_20.joblib')
wp_next_clf_20 = load('./models/crazyFlyGestures/wp_next_nn_20.joblib')
wp_nextR_clf_20 = load('./models/crazyFlyGestures/wp_nextR_nn_20.joblib')
wp_set_clf_20 = load('./models/crazyFlyGestures/wp_set_nn_20.joblib')
stillGesture_clf_20 = load('./models/crazyFlyGestures/stillGesture_nn_20.joblib')

#moveDown_clf_20 = load('./models/crazyFlyGestures/moveDown_nn_20.joblib')
#moveUp_clf_20 = load('./models/crazyFlyGestures/moveUp_nn_20.joblib')
#pullUp_clf_20 = load('./models/crazyFlyGestures/pullUp_nn_20.joblib')
#swingAndPointForward_clf_20 = load('./models/crazyFlyGestures/swingAndPointForward_nn_20.joblib')
#rotateLeft_clf_20 = load('./models/crazyFlyGestures/rotateLeft_nn_20.joblib')
#rotateRight_clf_20 = load('./models/crazyFlyGestures/rotateRight_nn_20.joblib')
#stillGesture_clf_20 = load('./models/crazyFlyGestures/stillGesture_nn_20.joblib')

#validation predictores
start_clf_40 = load('./models/crazyFlyGestures/start_nn_40.joblib')
startR_clf_40 = load('./models/crazyFlyGestures/startR_nn_40.joblib')
land_clf_40 = load('./models/crazyFlyGestures/land_nn_40.joblib')
landR_clf_40 = load('./models/crazyFlyGestures/landR_nn_40.joblib')
wp_back_clf_40 = load('./models/crazyFlyGestures/wp_back_nn_40.joblib')
wp_backR_clf_40 = load('./models/crazyFlyGestures/wp_backR_nn_40.joblib')
wp_del_clf_40 = load('./models/crazyFlyGestures/wp_del_nn_40.joblib')
wp_next_clf_40 = load('./models/crazyFlyGestures/wp_next_nn_40.joblib')
wp_nextR_clf_40 = load('./models/crazyFlyGestures/wp_nextR_nn_40.joblib')
wp_set_clf_40 = load('./models/crazyFlyGestures/wp_set_nn_40.joblib')
stillGesture_clf_40 = load('./models/crazyFlyGestures/stillGesture_nn_40.joblib')

#moveDown_clf_40 = load('./models/crazyFlyGestures/moveDown_nn_40.joblib')
#moveUp_clf_40 = load('./models/crazyFlyGestures/moveUp_nn_40.joblib')
#pullUp_clf_40 = load('./models/crazyFlyGestures/pullUp_nn_40.joblib')
#swingAndPointForward_clf_40 = load('./models/crazyFlyGestures/swingAndPointForward_nn_40.joblib')
#rotateLeft_clf_40 = load('./models/crazyFlyGestures/rotateLeft_nn_40.joblib')
#rotateRight_clf_40 = load('./models/crazyFlyGestures/rotateRight_nn_40.joblib')
#stillGesture_clf_40 = load('./models/crazyFlyGestures/stillGesture_nn_40.joblib')

#list of predictors
earlyPredictors = [start_clf_20, startR_clf_20, land_clf_20, landR_clf_20, wp_back_clf_20 , wp_backR_clf_20, wp_del_clf_20, wp_next_clf_20, wp_nextR_clf_20, wp_set_clf_20, stillGesture_clf_20]
validationPredictors = [start_clf_40, startR_clf_40, land_clf_40, landR_clf_40, wp_back_clf_40 , wp_backR_clf_40, wp_del_clf_40, wp_next_clf_40, wp_nextR_clf_40, wp_set_clf_40, stillGesture_clf_40]

#earlyPredictors = [moveDown_clf_20, moveUp_clf_20, pullUp_clf_20, swingAndPointForward_clf_20, rotateLeft_clf_20, rotateRight_clf_20, stillGesture_clf_20]
#validationPredictors = [moveDown_clf_40, moveUp_clf_40, pullUp_clf_40, swingAndPointForward_clf_40, rotateLeft_clf_40, rotateRight_clf_40, stillGesture_clf_40]

#class_names of the gestures
#these must be in the same order as the predictors
#class_names = ['movPosX', 'movPosY', 'movPosZ', 'movNegX', 'movNegY', 'movNegZ', 'stillGesture']

class_names = ['start', 'startR', 'land', 'landR', 'wp_back', 'wp_backR','wp_del','wp_next','wp_nextR', 'wp_set' 'stillGesture']


#################################################################################
# create communication queues
#

wrapper_to_predictor_queue = JoinableQueue()
predictor_to_application_queue = JoinableQueue()
direct_control_queue = JoinableQueue()

mode_switch_flag = False


#################################################################################
# BLE data streaming callback
#
# Handles a dataframe every 20ms
# There are different dataframes that can approach
#
# Application Mode 3D (mode == 1)
#
# -----------------------------------------------------------------------------------------------------
# |  0  |  1  | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 |   18   |  19  |
# -----------------------------------------------------------------------------------------------------
# | timestamp | accX  | accY  | accZ  | gyroX |  gyroY  |  gyroZ  | b1 | b2 | b3 | b4 | unused | mode |
# -----------------------------------------------------------------------------------------------------
#
# Application Mode 2D (mode == 2)
#
# -----------------------------------------------------------------------------------------------------
# |  0  |  1  | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 |   18   |  19  |
# -----------------------------------------------------------------------------------------------------
# | timestamp | accX  | accY  | gyroZ |           unused          | b1 | b2 | b3 | b4 | unused | mode |
# -----------------------------------------------------------------------------------------------------
#
# Direct Control Mode (mode == 3)
#
# ---------------------------------------------------------------------------------------------------------
# |   0   | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |   13   | 14 | 15 | 16 | 17 |   18   |  19  |
# ---------------------------------------------------------------------------------------------------------
# | event |     roll      |     pitch     |        yaw       | unused | b1 | b2 | b3 | b4 | unused | mode |
# ---------------------------------------------------------------------------------------------------------
#

def myStreamCB(cHandle, data):
    """ callback for new fresh data
        on streaming characteristic
    """
    global mode_switch_flag

    mode, switch = check_mode_switch(data)
    if not mode_switch_flag:
        if switch == 1:
            mode_switch_flag = True
            if mode == 1:
                btComm.setMode(MODE.DIRECT_CONTROL)
            elif mode == 3:
                btComm.setMode(MODE.APPLICATION)
    else:
        if switch == 0:
            mode_switch_flag = False

    wrapper_to_predictor_queue.put(data)
    

def check_mode_switch(data):
    mode = data[19]
    #button for mode switch
    #in the dataframe bytes 14 to 17 are mapped to the buttons of the T-Skin
    #byte 14 is button 1 ... byte 17 is button 4
    button = data[17]
    return mode, button


########################################################################
###############     execution starts here    ###########################
########################################################################


# create communication class
btComm = BTCommunication()

version = btComm.getVersion()
print("comm version: {}".format(version))


#set Call Back for data stream from TSkin
btComm.setStreamCallBack(myStreamCB)


#connect to TACTI
btComm.stayConnected()
#time.sleep(3)



#some inits
btComm.setMode(MODE.APPLICATION)
btComm.setDimension(DIMENSION.DIM_3D)
btComm.setUsage(USAGE.TSKIN_RIGHT)
btComm.setGNorm(GNORM.NORM)
#btComm.setThresholds(10, 20, 30)
btComm.setLed(LED_MODE.FAST_BLINK, LED_COLOR.RED) 
btComm.startSendingData()

#create and start processes for the predictor and the application
pred = Predictor(wrapper_to_predictor_queue, predictor_to_application_queue, direct_control_queue, earlyPredictors, validationPredictors, class_names)
pred.start()
app = Application(predictor_to_application_queue, direct_control_queue)
app.start()

#main loop
done = False
while not done:
    
    #automatically reconnect in case of connection lost
    #In case of reconnection, previous settings (mode, dimension, ...) 
    #are automatically re-applied
    btComm.stayConnected()