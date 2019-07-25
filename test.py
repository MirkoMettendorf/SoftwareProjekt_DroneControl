from multiprocessing import JoinableQueue
from application import Application
import time
import keyboard


gesture_output_queue = JoinableQueue()
direct_control_queue = JoinableQueue()

switch = 0
if keyboard.is_pressed('Space'):
    if(switch)==0:
        gesture_output_queue.put([['vali', 'start'], [0, 0, 0, 0]])
        gesture_output_queue.put([['vali', 'startR'], [0, 0, 0, 0]])
        switch = 1
if keyboard.is_pressed('Ctrl'):
    gesture_output_queue.put([['vali', 'land'], [0, 0, 0, 0]])
    gesture_output_queue.put([['vali', 'landR'], [0, 0, 0, 0]])
if keyboard.is_pressed('n'):
    gesture_output_queue.put([['vali', 'wp_next'], [0, 0, 0, 0]])
    gesture_output_queue.put([['vali', 'wp_nextR'], [0, 0, 0, 0]])
if keyboard.is_pressed('b'):
    gesture_output_queue.put([['vali', 'wp_back'], [0, 0, 0, 0]])
    gesture_output_queue.put([['vali', 'wp_backR'], [0, 0, 0, 0]])
if keyboard.is_pressed('s'):
    gesture_output_queue.put([['vali', 'wp_set'], [0, 0, 0, 0]])
if keyboard.is_pressed('d'):
    gesture_output_queue.put([['vali', 'wp_del'], [0, 0, 0, 0]])



app = Application(gesture_output_queue, direct_control_queue)
print("start")
app.start()
