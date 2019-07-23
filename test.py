from multiprocessing import JoinableQueue
from application import Application
import time


predictor_to_application_queue = JoinableQueue()
direct_control_queue = JoinableQueue()



predictor_to_application_queue.put([['vali','start'], [0,0,0,0]])
predictor_to_application_queue.put([['vali','startR'], [0,0,0,0]])
predictor_to_application_queue.put([['vali','wp_set'], [0,0,0,0]])
predictor_to_application_queue.put([['vali','wp_del'], [0,0,0,0]])
predictor_to_application_queue.put([['vali','wp_next'], [0,0,0,0]])
predictor_to_application_queue.put([['vali','wp_nextR'], [0,0,0,0]])
predictor_to_application_queue.put([['vali','wp_next'], [0,0,0,0]])
predictor_to_application_queue.put([['vali','wp_nextR'], [0,0,0,0]])
predictor_to_application_queue.put([['vali','wp_next'], [0,0,0,0]])
predictor_to_application_queue.put([['vali','wp_nextR'], [0,0,0,0]])
predictor_to_application_queue.put([['vali','wp_next'], [0,0,0,0]])
predictor_to_application_queue.put([['vali','wp_nextR'], [0,0,0,0]])
predictor_to_application_queue.put([['vali','wp_back'], [0,0,0,0]])
predictor_to_application_queue.put([['vali','wp_backR'], [0,0,0,0]])
predictor_to_application_queue.put([['vali','wp_back'], [0,0,0,0]])
predictor_to_application_queue.put([['vali','wp_backR'], [0,0,0,0]])
#predictor_to_application_queue.put(['wp_set', [0,0,0,0]])
#predictor_to_application_queue.put(['none', [0,0,0,1]])
predictor_to_application_queue.put([['vali','land'], [0,0,0,0]])
predictor_to_application_queue.put([['vali','landR'], [0,0,0,0]])
#predictor_to_application_queue.put(['wp_set', [0,0,0,0]])
#predictor_to_application_queue.put(['wp_set', [0,0,0,0]])
#predictor_to_application_queue.put(['wp_next',[0,0,0,0]])




app = Application(predictor_to_application_queue, direct_control_queue)
print("start")
app.start()
