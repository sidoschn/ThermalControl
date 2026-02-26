import tm1637
from ds18b20 import DS18B20
import time
from simple_pid import PID
import paho.mqtt.publish as publish
import board
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
import autoUpdate as updater



updater.performAutoupdate()



#sensor = DS18B20()

tm = tm1637.TM1637(clk=23, dio=24)

i2c = board.I2C()
pca = PCA9685(i2c)
pca.frequency = 50
servo0 = servo.Servo(pca.channels[0], min_pulse=500, max_pulse = 2500, actuation_range=180)

servo0.angle = 90

class temperatureController:
  targetTemperature = 40
  currentTemp = 30
  maxRange = 50
  mqttTopic01 = "thermalControl/tempAnbauVorlauf"
  mqttTopic02 = "thermalControl/servoAngle"
  mqttBroker = "192.168.0.39"
  loopTime = 10

  def __init__(self):
    self.pid = PID(-1, -0.01, -0.5, setpoint=self.targetTemperature, starting_output = 90)
    self.pid.sample_time = self.loopTime
    self.pid.output_limits = (90-self.maxRange, 90+self.maxRange)
    self.main()

  def readTemperature(self):
    #print("reading temperature...")
    #print("not implemented yet")
    self.currentTemp = sensor.get_temperature()
    return self.currentTemp

  def displayTemperature(self, temp):
    tm.temperature(round(temp))

  def publishTemp(self, temp, angle):
    publish.single(self.mqttTopic01, str(temp), hostname=self.mqttBroker)
    publish.single(self.mqttTopic02, str(angle), hostname=self.mqttBroker)

  def main(self):
    print("main")
    while True:
      readTemp = 50
      #readTemp = self.readTemperature()
      self.displayTemperature(readTemp)
#      self.publishTemp(readTemp)
      control = self.pid(readTemp)
      self.publishTemp(readTemp, control)
      print(str(control)+" "+str(readTemp))
      try:
        servo0.angle = float(control)
      except:
        print("i2c com failure")
      time.sleep(self.loopTime)

temperatureController()

exit()


while True:

  temp = sensor.get_temperature()
  print(temp)
  #strTemp = '%.2f' % temp
  #strTemp = str(temp)
  #print(strTemp) 
  #number = '%.0f' % temp
  #tempParts = strTemp.split(".")
  #decimals = tempParts[1]
  #number = tempParts[0]
  #print(number)
  #print(decimals)
  tm.temperature(round(temp))
  #tm.show(strTemp)
  time.sleep(1)
