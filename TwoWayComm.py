import bluepy
from bluepy.btle import Scanner, DefaultDelegate, Peripheral, AssignedNumbers, BTLEException
import threading, binascii, sys, json, logging
from configparser import SafeConfigParser
from struct import *
import time
import math
import enum




VERSION = "1.0"

_DEVICE_TO_FIND = ""
_STREAM_CHAR = ""
_CFG_CHAR = ""



def log_it(*args):
    msg = " ".join([str(a) for a in args])
    logging.debug(msg)



class COMMANDS(enum.Enum):
	ASK_USER_FOR_CALIBRATION = 1
	START_SENDING_DATA = 2
	STOP_SENDING_DATA = 3

	RESET_TS = 4
	DEFAULT_SETTINGS = 5
	DIMENSION_SET = 6
	USAGE_SET = 7
	MODE_SET = 8

	NORM_G = 9
	LED_CTRL = 10
	SET_THRESHOLDS = 11

	NOT_A_CMD = 0xffff
	

class LED_COLOR(enum.Enum): 
    RED = 0
    GREEN = 1
    BLUE = 2
    PURPLE = 3 
    CYANO = 4


class LED_MODE(enum.Enum): 
	SHORT_FLASH = 0
	LONG_FLASH = 1
	SLOW_BLINK = 2
	FAST_BLINK = 3
	NO_LIGHT = 4


class DIMENSION(enum.Enum):
	DIM_3D = 0
	DIM_2D5 = 1
	DIM_2D = 2
	

class USAGE(enum.Enum):
	TSKIN_RIGHT = 0
	TSKIN_LEFT = 1
	TACTIGON = 2
	OBJECT_ATTACHED = 3


class MODE(enum.Enum):
	TRAINING = 0
	APPLICATION = 1
	DIRECT_CONTROL = 2


class GNORM(enum.Enum):
	NO_NORM = 0
	NORM = 1


DEFAULT_MODE = MODE.APPLICATION
DEFAULT_DIMENSION = DIMENSION.DIM_3D
DEFAULT_USAGE = USAGE.TSKIN_RIGHT
DEFAULT_DATA_SENDING = False
DEFAULT_LED_MODE = LED_MODE.FAST_BLINK
DEFAULT_LED_COLOR = LED_COLOR.RED
DEFAULT_GNORM = GNORM.NORM
DEFAULT_R_TH = 30
DEFAULT_P_TH = 30
DEFAULT_Y_TH = 30


class BTCommunication():
	""" class constructor
    """
	def __init__(self):
        		
		global _DEVICE_TO_FIND
		global _STREAM_CHAR
		global _CFG_CHAR	
        		
		
        
		# Get the configuration info
		parser = SafeConfigParser()
		parser.read('twc.cfg')
		_DEVICE_TO_FIND = parser.get('ble', 'devicesToFind')
		_STREAM_CHAR = parser.get('ble', 'streamChar')
		_CFG_CHAR = parser.get('ble', 'cfgChar')

		# print target in fo
		print("Target device: {}, stream char UUID = {}  --  cmd chat UUID = {}".format(_DEVICE_TO_FIND, _STREAM_CHAR, _CFG_CHAR))


		# Initialize Peripheral scanner
		self.connectedPeripheral = Peripheral
		self.connectedPeripheral.connected = False
		self.firstTime = True
		self.scanner = Scanner(0)				
		self.peripherals = {}
		self.lock = threading.RLock()
		
		
		#current config
		self.mode = DEFAULT_MODE
		self.dimension = DEFAULT_DIMENSION
		self.usage = DEFAULT_USAGE
		self.ledMode = DEFAULT_LED_MODE
		self.ledColor = DEFAULT_LED_COLOR
		self.rTh = DEFAULT_R_TH
		self.pTh = DEFAULT_P_TH
		self.yTh = DEFAULT_Y_TH
		self.gnorm = DEFAULT_GNORM
		self.dataSending = False
		
		
		
		#initialize debugger
		logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] (%(threadName)-10s) %(message)s')
		
		
		
				
	def stayConnected(self):				
		""" scan, connect, keep connected to TACTI
			BLE name and UUID characteristic are specified in twc.cfg file
		"""
		
		devices = self.scanner.scan(2)
		for d in devices:
			try:
				# If scan returns a known addr that's already in the collection, it means it disconnected
				# Remove record and treat it as new
				# Note, it would be nice to remove a device when it goes offline as opposed to when it comes back
				# To do this I'd need something like a ping...dunno what best practice is
				if d.addr in self.peripherals:
					with self.lock:
						del self.peripherals[d.addr]                    

				for (adtype, desc, value) in d.getScanData():
												
					#search for Tactigon devices
					if(value.find(_DEVICE_TO_FIND) == 0):	
																						
						#create peripheral
						logging.info("Starting Thread for %s", d.addr)
						self.connectedPeripheral = BleThread(d.addr, self.lock, _STREAM_CHAR, _CFG_CHAR, self.userStreamCB)
																		
						#start thread to get notifications
						with self.lock:
							self.peripherals[d.addr] = self.connectedPeripheral
						self.connectedPeripheral.daemon = True
						self.connectedPeripheral.start()
						
						#set current config
						self.setToCurrentCfg()
							
			except Exception as e:            
				logging.debug("Unknown error %s", e)
                    
   




    
        
	 
	def getVersion(self):
		""" retrun wrapper version        
		"""
		return VERSION

								
	def setLed(self, mode, color):	
		""" set LED mode. Refer to LED_COLOR and LED_MOD enum
		"""
		self.ledMode = mode
		self.ledColor = color
		message = pack('bbb', COMMANDS.LED_CTRL.value, mode.value, color.value)		
		self.connectedPeripheral.msgToWrite = message
		

	def setMode(self, mode):
		""" set LED mode. Refer to MODE enum
		"""
		self.mode = mode
		message = pack('bb', COMMANDS.MODE_SET.value, mode.value)		
		self.writeToTacti(message)
		
		
	def setUsage(self, usage):
		""" set USAGE mode. Refer to USAGE enum
		"""
		self.usage = usage
		message = pack('bb', COMMANDS.USAGE_SET.value, usage.value)		
		self.writeToTacti(message)
		
	
	def setDimension(self, dimension):
		""" set DIMENSION mode. Refer to DIMENSION enum
		"""
		self.dimension = dimension
		message = pack('bb', COMMANDS.DIMENSION_SET.value, dimension.value)
		self.writeToTacti(message)
		
	
	def setGNorm(self, gnorm):
		""" Activate/deactivate G force compensation. Refer to GNORM enum
		"""
		self.gnorm = gnorm
		message = pack('bb', COMMANDS.NORM_G.value, gnorm.value)
		self.writeToTacti(message)
	
	
	def setThresholds(self, rTh, pTh, yTh):
		""" Set angles threshold for Direct Control mode
			Angle must be passed as float
		"""
		self.rTh = rTh
		self.pTh = pTh
		self.yTh = yTh
		message = pack('bHHH', COMMANDS.SET_THRESHOLDS.value, rTh, pTh, yTh)
		self.writeToTacti(message)
	
	
	def startSendingData(self):
		""" Start streaming
		"""
		self.dataSending = True
		message = pack('b', COMMANDS.START_SENDING_DATA.value)
		self.writeToTacti(message)
		
	
	def stopSendingData(self):
		""" Stop streaming
		"""
		self.dataSending = False
		message = pack('b', COMMANDS.STOP_SENDING_DATA.value)
		self.writeToTacti(message)
		
				
	def resetTimeStamp(self):
		""" reset time stamp
		"""
		message = pack('b', COMMANDS.RESET_TS.value)
		self.writeToTacti(message)
	
	
	def	setToCurrentCfg(self):
		self.resetTimeStamp()
		self.setMode(self.mode)
		self.setUsage(self.usage)
		self.setDimension(self.dimension)
		self.setLed(self.ledMode, self.ledColor)
		self.setThresholds(self.rTh, self.pTh, self.yTh)
		self.setGNorm(self.gnorm)
		if self.dataSending == True:
			self.startSendingData()
		else:
			self.stopSendingData()
		
	
	
		
	def resetToDefault(self):
		""" Set defaul value:
			dimesion: 3D
			usage: TSkin right
			mode: application
			gnorm: no
			thresholds: 30, 30, 30 deg
			led: green slow blink
		"""
		message = pack('b', COMMANDS.DEFAULT_SETTINGS.value)
		self.writeToTacti(message)	
		
		
		
	def setStreamCallBack(self, cbFunc):
		""" Set call back for data stream
			This function will be called at every new BLE data packet
			received
			
			Function prototype must be as following:
						
				def myStreamCB(cHandle, data):
					
					.... do something
					.... do something
						
			where:
				cHandle: 	characteristic identifier
				data: 		the data packet
		"""
		self.userStreamCB = cbFunc
		
		
		
		
	####################################################################	
	### reserved func: user shouldn't use these
	
	
	def writeToTacti(self, message):
		if self.connectedPeripheral.connected == True:
			if self.waitWriteQueue() == True:
				self.connectedPeripheral.msgToWrite = message
				return True
			else:
				return False
				
				
	def waitWriteQueue(self):
		timeout = 2  #sec
		mustend = time.time() + timeout
		while time.time() < mustend:
			if self.connectedPeripheral.msgToWrite == "": 
				return True
			time.sleep(0.2)
		return False
	
	

############################################################################################################
class BleThread(Peripheral, threading.Thread):
    ## @var WAIT_TIME
    # Time of waiting for notifications in seconds
    WAIT_TIME = 0.1
    
    ## @var EXCEPTION_WAIT_TIME
    # Time of waiting after an exception has been raiesed or connection lost
    EXCEPTION_WAIT_TIME = 10
    
    
    

    def __init__(self, peripheral_addr, lock, streamChar, cfgChar, streamCB):
        try:            
            Peripheral.__init__(self, peripheral_addr)
        except Exception as e:
            logging.warning("Problem initializing Peripheral %s", e)
            raise
            

        threading.Thread.__init__(self)
        self.lock = lock
        self.msgToWrite = ""
       
        
        
        # Set up our WRITE characteristic
        try:
            self.cfgChar = self.getCharacteristics(uuid=cfgChar)[0]
        except Exception as e:
            logging.debug("Problem getting characteristics from %s. %s", self.addr, e)

		
        
        # Create a delegate folr streaming char                      
        self.delegate = MyDelegate(peripheral_addr, self.lock)        
        self.delegate.handleNotification = streamCB        
        self.withDelegate(self.delegate)
        self.connected = True
        

		# register on NOTIFICATION for streaming char
        logging.info("Configuring RX to notify me on change")
        try:
            streamChar_Hnd = self.getCharacteristics(uuid=streamChar)[0].getHandle()
            self.writeCharacteristic(streamChar_Hnd+1, b"\x01\x00", withResponse=True)
        except Exception as e:
            logging.debug("Problem subscribing to RX notifications: %s", e)


	

    def run(self):
        while self.connected:
            try:
                self.waitForNotifications(self.WAIT_TIME)
				
				#check for message to write from user
                if self.msgToWrite != "":
                    self.cfgChar.write(self.msgToWrite, withResponse=False)						
                    self.msgToWrite = ""
					
																	
                                                                
							
            except BaseException as be:
                logging.debug("BaseException caught: %s", be)
                self.connected = False
                
            except BTLEException as te:
                logging.debug("BTLEException caught for %s. %s", self.addr, te)
                if str(te.message) == 'Device disconnected':
                    logging.debug("Device disconnected: %s", self.addr)
                    self.connected = False
                    # We don't want to call waitForNotifications and fail too often
                    time.sleep(self.EXCEPTION_WAIT_TIME)
                else:
                    raise
                    
            except Exception as e:
                logging.debug("Peripheral exception for %s. %s", self.addr, e)
                self.connected = False
	
	
	
############################################################################################################
#
# Callback called on new data on BLE characteristic (Notification)
#
############################################################################################################
class MyDelegate(DefaultDelegate):

    def __init__(self, addr, lock):
        DefaultDelegate.__init__(self)
        self.id = addr
        self.lock = lock
        

    # Called by BluePy when an event was received.
    
    #def handleNotification(self, cHandle, data):
                        
        
        #do something with fresh data
        

      	
	
	
	

	
