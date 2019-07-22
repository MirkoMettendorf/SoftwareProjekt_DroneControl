#Author: Alexander Schwarz
#Version 1.0

from TwoWayComm import BTCommunication, LED_COLOR, LED_MODE, DIMENSION, USAGE, MODE
import time
from struct import unpack


TACTI_ACC_COMPRESSION = 819
TACTI_GYRO_COMPRESSION = 32

def myStreamCB(cHandle, data):
    """ callback for new fresh data
        on streaming characteristic
    """    
    
    
    unpack3Dformat(data)
    #unpackDirectControFormat(data)
    #unpack2Dformat(data)



def unpack2Dformat(data):
    global f

    timestamp = unpack('H', data[0:2])[0]

    accX = float(unpack('h', data[2:4])[0]) / TACTI_ACC_COMPRESSION
    accY = float(unpack('h', data[4:6])[0]) / TACTI_ACC_COMPRESSION

    gyroZ = float(unpack('h', data[6:8])[0]) / TACTI_GYRO_COMPRESSION
    
    b1 = float(unpack('b', data[14:15])[0])
    b2 = float(unpack('b', data[15:16])[0])
    b3 = float(unpack('b', data[16:17])[0])
    b4 = float(unpack('b', data[17:18])[0])
    
    
    f.write("{0}, {1}, {2}, {3}, {4}\n".format(timestamp, accX, accY, gyroZ, b4))
    #print("stream: {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}".format(timestamp, accX, accY, accZ, gyroX, gyroY, gyroZ, b1, b2, b3, b4))
    print("stream: ",b4)



def unpack3Dformat(data):
    """ example of data unpack for the following settings:
    
        mode:      application
        dimensio:  3D
        usage:     TSKIN (left or right)
    
        expected data:     time stamp(2) | acc.x(2) | acc.y(2) | acc.z(2) | giro.x(2) | gyro.y(2) | gyro.z(2) | btn_1(1) | btn_2(1) | btn_3(1) | btn_4(1)        
    """
    global f
    
    timestamp = unpack('H', data[0:2])[0]
    
    accX = float(unpack('h', data[2:4])[0]) / TACTI_ACC_COMPRESSION
    accY = float(unpack('h', data[4:6])[0]) / TACTI_ACC_COMPRESSION
    accZ = float(unpack('h', data[6:8])[0]) / TACTI_ACC_COMPRESSION
    
    gyroX = float(unpack('h', data[8:10])[0]) / TACTI_GYRO_COMPRESSION
    gyroY = float(unpack('h', data[10:12])[0]) / TACTI_GYRO_COMPRESSION
    gyroZ = float(unpack('h', data[12:14])[0]) / TACTI_GYRO_COMPRESSION
    
    b1 = float(unpack('b', data[14:15])[0])
    b2 = float(unpack('b', data[15:16])[0])
    b3 = float(unpack('b', data[16:17])[0])
    b4 = float(unpack('b', data[17:18])[0])
    
    
    f.write("{0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}\n".format(timestamp, accX, accY, accZ, gyroX, gyroY, gyroZ, b4))
    #print("stream: {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}".format(timestamp, accX, accY, accZ, gyroX, gyroY, gyroZ, b1, b2, b3, b4))
    print("stream: ",b4)


########################################################################
###############     execution starts here    ###########################
########################################################################


# create communication class
btComm = BTCommunication()

version = btComm.getVersion()
print("comm version: {}".format(version))

f = open('./data/raw/data.csv', 'wt')

#use for 3D data
f.write("timestamp, accX, accY, accZ, gyroX, gyroY, gyroZ, button\n")

#for 2D data uncomment
#f.write("timestamp, accX, accY, gyroZ, button\n")


#set Call Back for data stream from TSkin
btComm.setStreamCallBack(myStreamCB)


#connect to TACTI
btComm.stayConnected()
time.sleep(3)



#some inits
btComm.setMode(MODE.TRAINING)
btComm.setDimension(DIMENSION.DIM_3D)
btComm.setUsage(USAGE.TSKIN_RIGHT)
#btComm.setThresholds(10, 20, 30)
btComm.setLed(LED_MODE.FAST_BLINK, LED_COLOR.RED) 
btComm.startSendingData()




#main loop
done = False
while not done:
    
    #automatically reconnect in case of connection lost
    #In case of reconnection, previous settings (mode, dimension, ...)
    #are automatically re-applied
    btComm.stayConnected()