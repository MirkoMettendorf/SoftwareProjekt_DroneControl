import enum

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger
import keyboard
import time
from transitions import Machine
from multiprocessing import Process, JoinableQueue

uri = 'radio://0/80/2M'


class StateMachine(object):


    def start_action(self, cf):
        cf.commander.send_velocity_world_setpoint(0, 0, 0.3, 0)
        print("up")

    def land_action(self, cf):
        cf.commander.send_velocity_world_setpoint(0, 0, -0.3, 0)
        cf.commander.send_stop_setpoint()
        print("down")

    def forward_action(self, cf):
        cf.commander.send_velocity_world_setpoint(0.1, 0, 0, 0)
        print("forward")

    def back_action(self, cf):
        cf.commander.send_velocity_world_setpoint(-0.1, 0, 0, 0)
        print("back")

    def left_action(self, cf):
        cf.commander.send_velocity_world_setpoint(0, 0.1, 0, 0)
        print("left")

    def right_action(self, cf):
        cf.commander.send_velocity_world_setpoint(0, -0.1, 0, 0)
        print("right")

    def wp_next_action(self, cf):
        wp = divmod(self.waypoint_pos,len(self.waypoints))
        cf.commander.send_position_setpoint(self.waypoints[wp])
        self.waypoint_pos = divmod((self.waypoint_pos + 1),len(self.waypoints))
        print("wp_next")

    def wp_back_action(self, cf):
        wp = divmod(self.waypoint_pos, len(self.waypoints))
        cf.commander.send_position_setpoint(self.waypoints[wp])
        self.waypoint_pos = divmod((self.waypoint_pos - 1), len(self.waypoints))
        print("wp_back")

    def wp_set_action(self, cf,position):
        self.waypoints.append(position)
        self.waypoint_pos=0
        print("wp_set")

    def wp_del_action(self):
        del self.waypoints[-1]
        print("wp_del")

    def switch(self):
        print("AngleMode")

    states = ['GestureMode', 'AngleMode', 'WpNext', 'WpBack', 'Start', 'Land', 'Stop', 'Forward', 'Back', 'Left',
              'Right']

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

        self.machine.add_transition(trigger='forward', source='AngleMode', dest='AngleMode', after='forward_action')
        self.machine.add_transition(trigger='forward_left', source='AngleMode', dest='AngleMode',
                                    after='forward_left_action')
        self.machine.add_transition(trigger='forward_right', source='AngleMode', dest='AngleMode',
                                    after='forward_right_action')

        self.machine.add_transition(trigger='back', source='AngleMode', dest='AngleMode', after='back_action')
        self.machine.add_transition(trigger='back_left', source='Back', dest='AngleMode', after='back_left_action')
        self.machine.add_transition(trigger='back_right', source='AngleMode', dest='AngleMode',
                                    after='back_right_action')

        self.machine.add_transition(trigger='left', source='AngleMode', dest='Left', after='left_action')

        self.machine.add_transition(trigger='right', source='AngleMode', dest='Right', after='right_action')

        self.machine.add_transition('switch_mode', source='GestureMode', dest='Stop', after='switch')
        self.machine.add_transition('switch_mode', source='AngleMode', dest='GestureMode', after='switch')






class controller(Process):

    def __init__(self, gesture_input_queue,direct_control_queue):
        super(controller, self).__init__()
        self.gesture_input_queue = gesture_input_queue
        self.direct_control_queue = direct_control_queue
        self.position=[]


    def run(self):
        while True:
            data = self.gesture_input_queue.get()
            cflib.crtp.init_drivers(enable_debug_driver=False)
            with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
                self.reset_estimator(scf)
                self.start_position_printing(cf)
                cf = scf.cf
                cf.param.set_value('flightmode.posSet', '1')
                self.stateMachine= StateMachine(self.position)
                self.gesture_input_queue.task_done()

    def position_callback(self,timestamp, data, logconf):
        x = data['kalman.stateX']
        y = data['kalman.stateY']
        z = data['kalman.stateZ']
        self.position.append([x, y, z, 0])

    def start_position_printing(self,cf):
        log_conf = LogConfig(name='Position', period_in_ms=500)
        log_conf.add_variable('kalman.stateX', 'float')
        log_conf.add_variable('kalman.stateY', 'float')
        log_conf.add_variable('kalman.stateZ', 'float')

        cf.log.add_config(log_conf)
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

                print("{} {} {}".
                      format(max_x - min_x, max_y - min_y, max_z - min_z))

                if (max_x - min_x) < threshold and (
                        max_y - min_y) < threshold and (
                        max_z - min_z) < threshold:
                    break


    def reset_estimator(self,scf):
        cf = scf.cf
        cf.param.set_value('kalman.resetEstimation', '1')
        time.sleep(0.1)
        cf.param.set_value('kalman.resetEstimation', '0')
        self.wait_for_position_estimator(scf)









