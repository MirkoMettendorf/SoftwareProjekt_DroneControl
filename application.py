#Author: Alexander Schwarz
#Version 1.0

#################################################################################
# Application process
#
# Template for user Application.
#
# This process is intiailized and started in the Main file.
# Application code must be implemeted in the run function.
#


#################################################################################
# needed imports


import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger
import time
from transitions import Machine
from multiprocessing import Process, JoinableQueue
import enum
import keyboard
import os
import logging

from struct import *


TACTI_ACC_COMPRESSION = 819
TACTI_GYRO_COMPRESSION = 32

uri = 'radio://0/80/2M'


class StateMachine(object):


    def start_action(self, cf):
        cf.high_level_commander.takeoff(0.3,0.6)
        print("up")

    def land_action(self, cf):
        #sinke auf 30 centimeter
        cf.high_level_commander.land(0.3,2)
        time.sleep(5)
        cf.high_level_commander.stop()
        print("down")

    def wp_next_action(self, cf):
        self.waypoint_pos = self.waypoint_pos +1
        if self.waypoint_pos >= len(self.waypoints):
            self.waypoint_pos = 0
        wp = self.waypoints[self.waypoint_pos]
        print(wp)
        cf.high_level_commander.go_to(wp[0],wp[1],wp[2],0,5)
        print("wp_next")

    def wp_back_action(self, cf):
        self.waypoint_pos = self.waypoint_pos -1
        if self.waypoint_pos <0:
            self.waypoint_pos = len(self.waypoints)-1
        wp = self.waypoints[self.waypoint_pos]
        print(wp)
        cf.high_level_commander.go_to(wp[0], wp[1], wp[2],0,5)
        print("wp_back")

    def wp_set_action(self,position):
        self.waypoints.append(position)
        self.waypoint_pos=len(self.waypoints)-1
        print(self.waypoint_pos)
        print(self.waypoints)
        print("wp_set")

    def wp_del_action(self):
        del self.waypoints[-1]
        print(self.waypoints)
        print("wp_del")




    states = ['GestureMode', 'WpNext', 'WpBack', 'Start', 'Land']

    def __init__(self,position):
        self.waypoints = []
        self.waypoint_pos = 0
        self.position=position
        self.machine = Machine(model=self, states=StateMachine.states, initial='GestureMode',
                               ignore_invalid_triggers=True, )

        self.machine.add_transition(trigger='wp_next', source='GestureMode', dest='WpNext', after='wp_next_action')
        self.machine.add_transition(trigger='wp_next_retraction', source='WpNext', dest='GestureMode')

        self.machine.add_transition(trigger='wp_back', source='GestureMode', dest='WpBack', after='wp_back_action')
        self.machine.add_transition(trigger='wp_back_retraction', source='WpBack', dest='GestureMode')

        self.machine.add_transition(trigger='wp_set', source='GestureMode', dest='GestureMode', after='wp_set_action')
        self.machine.add_transition(trigger='wp_del', source='GestureMode', dest='GestureMode', after='wp_del_action')

        self.machine.add_transition(trigger='start', source='GestureMode', dest='Start', after='start_action')
        self.machine.add_transition(trigger='start_retraction', source='Start', dest='GestureMode')

        self.machine.add_transition(trigger='land', source='GestureMode', dest='Land', after='land_action')
        self.machine.add_transition(trigger='land_retraction', source='Land', dest='GestureMode')




class Application(Process):
    def __init__(self, gesture_input_queue, direct_control_queue):
        super(Application, self).__init__()
        self.gesture_input_queue = gesture_input_queue
        self.direct_control_queue = direct_control_queue
        self.position = []
        print("init")

    def run(self):
        while True:
            logging.warning('run')
            print("run")
            cflib.crtp.init_drivers(enable_debug_driver=False)
            with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
                logging.warning('connected')
                print("connectet")
                cf = scf.cf
                self.activate_high_level_commander(cf)
                #self.reset_estimator(cf)
                self.start_position_printing(scf)
                print(self.position)
                self.stateMachine = StateMachine(self.position)
                logging.warning('statemachine')
                print("statemachine")
                self.queueHandler(cf)



    ########################################################################
    def unpackDirectControFormat(self,data):
        """ example of data unpack for the following settings:

            mode:      application
            dimensio:  3D
            usage:     TSKIN (left or right)

            expected data:     event(1) | roll(4) | pitch(4) | yaw(4) | btn_1(1) | btn_2(1) | btn_3(1) | btn_4(1)
        """

        self.evt = unpack('B', data[0:1])[0]

        self.roll = unpack('f', data[1:5])[0]
        self.pitch = unpack('f', data[5:9])[0]
        self.yaw = unpack('f', data[9:13])[0]

        self.b1 = float(unpack('b', data[14:15])[0])
        self.b2 = float(unpack('b', data[15:16])[0])
        self.b3 = float(unpack('b', data[16:17])[0])
        self.b4 = float(unpack('b', data[17:18])[0])

        #print("stream: {}, {}, {}, {}".format(evt, roll, pitch, yaw))

    def queueHandler(self,cf):
        self.mode =1
        switch_mode = False
        print("handlerrun")
        logging.warning('handlerrun')
        while True:
            if not self.gesture_input_queue.empty():
                    print("gesture mode")
                    #self.beep()
                    #self.beep()
                    data = self.gesture_input_queue.get()
                    if (data[0][1] != 'none') and (data[0][0]== 'vali'):
                        print(data)
                        if data[0][1]=='start':
                            #self.beep()
                            self.stateMachine.start(cf)
                            #time.sleep(5)
                        if data[0][1]=='startR':
                            #self.beep()
                            self.stateMachine.start_retraction()
                        if data[0][1]=='land':
                            #self.beep()
                            self.stateMachine.land(cf)
                            #time.sleep(5)
                            print(self.stateMachine.waypoints)
                        if data[0][1]=='landR':
                            #self.beep()
                            self.stateMachine.land_retraction()
                        if data[0][1]=='wp_back':
                            #self.beep()
                            self.stateMachine.wp_back(cf)
                            #time.sleep(5)
                        if data[0][1]=='wp_backR':
                            #self.beep()
                            self.stateMachine.wp_back_retraction()
                        if data[0][1]=='wp_del':
                            #self.beep()
                            self.stateMachine.wp_del()
                        if data[0][1]=='wp_next':
                            #self.beep()
                            self.stateMachine.wp_next(cf)
                            #time.sleep(5)
                        if data[0][1]=='wp_nextR':
                            #self.beep()
                            self.stateMachine.wp_next_retraction()
                        if data[0][1]=='wp_set':
                            #self.beep()
                            self.stateMachine.wp_set(self.position)
                    self.gesture_input_queue.task_done()
            if not self.direct_control_queue.empty():
                    print("direct Mode")
                    #self.beep()
                    #self.beep()
                    #self.beep()
                    data = self.direct_control_queue.get()
                    self.unpackDirectControFormat(data)
                    if(self.position==[]):
                        cf.high_level_commander.takeoff(0.3, 0.6)
                        print("takeoff")
                        time.sleep(1)
                    if(self.evt==1):
                        #self.beep()
                        #print(self.position)
                        cf.high_level_commander.go_to(0.0, 0.3, 0.0, 0.0, duration_s=0.3, relative=True)
                        time.sleep(1)
                        print("right")
                        print(self.position)
                    if (self.evt == 2):
                        #self.beep()
                        cf.high_level_commander.go_to(0.0, -0.1, 0.0, 0.0, duration_s=0.1, relative=True)
                        print("left")
                        logging.warning('left')
                        time.sleep(1)
                    if (self.evt == 4):
                        #self.beep()
                        cf.high_level_commander.go_to(-0.1, 0.0, 0.0, 0.0, duration_s=0.1, relative=True)
                        print("back")
                        logging.warning('back')
                        time.sleep(1)
                    if (self.evt == 8):
                        #self.beep()
                        cf.high_level_commander.go_to(0.1,0.0,0.0,0.0,duration_s=0.1,relative=True)
                        print("forward")
                        logging.warning('forward')
                        time.sleep(1)
                    if (self.evt == 5):
                        #self.beep()
                        cf.high_level_commander.go_to(-0.1, 0.1, 0.0, 0.0, duration_s=0.1, relative=True)
                        print("back_right")
                        time.sleep(1)
                    if (self.evt == 6):
                        #self.beep()
                        cf.high_level_commander.go_to(-0.1, -0.1, 0.0, 0.0, duration_s=0.1, relative=True)
                        print("back_left")
                        time.sleep(1)
                    if (self.evt == 9):
                        #self.beep()
                        cf.high_level_commander.go_to(0.1, 0.1, 0.0, 0.0, duration_s=0.1, relative=True)
                        print("forward_right")
                        time.sleep(1)
                    if (self.evt == 10):
                        #self.beep()
                        cf.high_level_commander.go_to(0.1, 0.0, 0.0, 0.0, duration_s=0.1, relative=True)
                        print("forward_left")
                        time.sleep(1)
                    if (self.b3==1.0):
                        #self.beep()
                        cf.high_level_commander.go_to(0, 0, 0.1, 0.0, duration_s=0.1, relative=True)
                        print("up")
                        logging.warning('up')
                        time.sleep(1)
                    if (self.b2==1.0):
                        #self.beep()
                        cf.high_level_commander.go_to(0, 0, -0.1, 0.0, duration_s=0.1, relative=True)
                        print("down")
                        logging.warning('down')
                        time.sleep(1)
                    if (self.b1 ==1.0):
                        #self.beep()
                        self.stateMachine.land_action(cf)
                        print(self.stateMachine.waypoints)
                        break
                    self.direct_control_queue.task_done()

    def position_callback(self,timestamp, data, logconf):
        x = data['kalman.stateX']
        y = data['kalman.stateY']
        z = data['kalman.stateZ']
        self.position =[x, y, z, 0]

    def start_position_printing(self,scf):
        log_conf = LogConfig(name='Position', period_in_ms=500)
        log_conf.add_variable('kalman.stateX', 'float')
        log_conf.add_variable('kalman.stateY', 'float')
        log_conf.add_variable('kalman.stateZ', 'float')

        scf.cf.log.add_config(log_conf)
        log_conf.data_received_cb.add_callback(self.position_callback)
        log_conf.start()

    def wait_for_position_estimator(self,scf):
        print('Waiting for estimator to find position...')

        log_config = LogConfig(name='Kalman Variance', period_in_ms=500)
        log_config.add_variable('kalman.varPX', 'float')
        log_config.add_variable('kalman.varPY', 'float')
        log_config.add_variable('kalman.varPZ', 'float')

        var_y_history = [1000] * 10
        var_x_history = [1000] * 10
        var_z_history = [1000] * 10

        threshold = 0.001

        with SyncLogger(scf, log_config) as logger:
            for log_entry in logger:
                data = log_entry[1]

                var_x_history.append(data['kalman.varPX'])
                var_x_history.pop(0)
                var_y_history.append(data['kalman.varPY'])
                var_y_history.pop(0)
                var_z_history.append(data['kalman.varPZ'])
                var_z_history.pop(0)

                min_x = min(var_x_history)
                max_x = max(var_x_history)
                min_y = min(var_y_history)
                max_y = max(var_y_history)
                min_z = min(var_z_history)
                max_z = max(var_z_history)

                # print("{} {} {}".
                #       format(max_x - min_x, max_y - min_y, max_z - min_z))

                if (max_x - min_x) < threshold and (
                        max_y - min_y) < threshold and (
                        max_z - min_z) < threshold:
                    break

    def reset_estimator(self,cf):
        cf.param.set_value('kalman.resetEstimation', '1')
        time.sleep(0.1)
        cf.param.set_value('kalman.resetEstimation', '0')

        self.wait_for_position_estimator(cf)

    def activate_high_level_commander(self,cf):
        cf.param.set_value('commander.enHighLevel', '1')

    def beep(self):
        # 1sek,440hz
        os.system('play -nq -t alsa synth {} sine {}'.format(1, 440))
