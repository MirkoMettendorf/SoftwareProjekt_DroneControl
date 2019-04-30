/*****************************
   Author: Thomas Schmidt, UAS Kaiserslautern, Working Group "Smart Machines"
   Goal: prototype (proof of concept)
   State: code running
   Date: 09.09.2018
   
   Description:
   This sketch is used in combination with a T-Skin device, the Crazyflie 2.0 quadcopter, a Crazyradio USB dongle and the Crazyflie client.
   The sketch is uploaded to the T-Skin and constantly updates an array with 7 unsigned chars with accData values and sends it via BLE. The Crazyflie client
   then reads those values and maps them to input parameters for the Crazyflie 2.0 quadcopter. 
  
   2 values per axis are needed because unsigned char is unable to encode negative values, in order to compensate this
   an additional value encodes the sign of each axis.
*/

#include <tactigon_led.h>
#include <tactigon_IMU.h>
#include <tactigon_BLE.h>
#include <tactigon_IO.h>
#include <tactigon_Env.h>

// THRESHOLDS
#define FS_PERIOD 20   //milliseconds; check sensors at 50Hz. Do not change.

T_Led rLed, bLed, gLed;
T_QUAT qMeter;
T_QData qData;



T_BLE bleManager;
UUID uuid;
T_BLE_Characteristic bleChar;
int ticks;

float threshold = 1.0;


void setup() {
  
  ticks = 0;
 
  
  //init leds
  rLed.init(T_Led::RED);
  gLed.init(T_Led::GREEN);
  bLed.init(T_Led::BLUE);
  rLed.off();
  gLed.off();
  bLed.off();
  
  //init BLE
  bleManager.InitRole(TACTIGON_BLE_PERIPHERAL);
  bleManager.setName("TTGPS");
  //add acc characteristic
  uuid.set("7ac71000-503d-4920-b000-acc000000001");
  bleChar = bleManager.addNewChar(uuid, 6); // new characteristic
}



//direct controll
void loop() {
  gLed.on();
  ticks = 0;
  // array for 6 unsigned char values
  unsigned char buffData[6] = {};
  //check sensors at 50Hz
  if (millis() >= (ticks + FS_PERIOD)) {
    ticks = millis();
    float roll, pitch, yaw;
    //get quaternions and Euler angles
    qData = qMeter.getQs();
    
    //Euler angles: rad/sec to degrees/sec
    roll = qData.roll * 360 / 6.28;
    pitch = qData.pitch * 360 / 6.28;
    yaw = qData.yaw * 360 / 6.28;

    

   /**  read roll pitch and yaw and write the data to unsigned char array. If the values are negative,
      the corresponding array indices are set to '0'. This way the Crazyflie client can handle the x, y and z 
      inclination accordingly. Threshold prevents a steering that is too sensitive to unwanted movement of the user's hand.
    */
    
  //pitch data   
   if ((fabs)(pitch)>threshold)
   {
    if (pitch < -threshold)
    {
      buffData[0]=0;
      buffData[1]= fabs(pitch + threshold);
    }
    else
    {
      buffData[0]=1;
      buffData[1]= pitch - threshold;
    }
  }
  
    
    //roll data   
   if ((fabs)(roll)>threshold)
   {
    if (roll < -threshold)
    {
      buffData[2]=0;
      buffData[3]= fabs(roll + threshold);
    }
    else
    {
      buffData[2]=1;
      buffData[3]= roll - threshold;
    }
  }
  

  /**yaw data TODO  
   if ((fabs)(yaw)>threshold)
   {
    if (yaw < -threshold)
    {
      buffData[4]=0;
      buffData[5]= fabs(yaw + threshold);
    }
    else
    {
      buffData[4]=1;
      buffData[5]= yaw - threshold;
    }
  }
  
  */
  } 
  //write char arry to characteristic
  bleChar.update(buffData);
}
