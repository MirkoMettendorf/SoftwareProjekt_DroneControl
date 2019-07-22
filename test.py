from multiprocessing import JoinableQueue
from application import Application
import time


predictor_to_application_queue = JoinableQueue()
direct_control_queue = JoinableQueue()

predictor_to_application_queue.put(['start', [0,0,0,0]])
predictor_to_application_queue.put(['startR', [0,0,0,0]])
predictor_to_application_queue.put(['wp_set', [0,0,0,0]])
#predictor_to_application_queue.put(['land', [0,0,0,0]])
#predictor_to_application_queue.put(['landR', [0,0,0,0]])
predictor_to_application_queue.put(['wp_set', [0,0,0,0]])
predictor_to_application_queue.put(['wp_set', [0,0,0,0]])
predictor_to_application_queue.put(['wp_del', [0,0,0,0]])
direct_control_queue.put()


app = Application(predictor_to_application_queue, direct_control_queue)
print("start")
app.start()
