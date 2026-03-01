import tm1637
from ds18b20 import DS18B20
import time
from simple_pid import PID
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import board
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
import autoUpdate as updater



updater.performAutoupdate()



sensor = DS18B20()

tm = tm1637.TM1637(clk=23, dio=24)

i2c = board.I2C()
pca = PCA9685(i2c)
pca.frequency = 50
servo0 = servo.Servo(pca.channels[0], min_pulse=500, max_pulse = 2500, actuation_range=180)

servo0.angle = 90

class temperatureController:
  targetTemperature = 35
  currentTemp = 30
  maxRange = 50
  mqttClient = mqtt.Client(client_id="ThermalController")
  mqttTopicIsAliveState = "thermalControl/isAlive"
  mqttTopic01 = "thermalControl/tempAnbauVorlauf"
  mqttTopic02 = "thermalControl/servoAngle"
  mqttTopicTempSetPoint = "thermalControl/tempSetPoint"
  mqttControlTopicTempSetPoint = "thermalControl/tempSetPoint/set"
  mqttTopicFineTune = "thermalControl/fineTune"
  mqttControlTopicFineTune = "thermalControl/fineTune/set"
  mqttBroker = "192.168.0.39"
  loopTime = 10

  def __init__(self):
    self.pid = PID(-10, -0.0, -0.0, setpoint=self.targetTemperature, starting_output = 90)
    self.pid.sample_time = self.loopTime
    self.pid.output_limits = (90-self.maxRange, 90+self.maxRange)
    self.mqttClient.on_connect = self.on_MqttConnect
    self.mqttClient.on_message = self.on_MqttMessage
    self.mqttClient.will_set(self.mqttTopicIsAliveState, '{"state": "OFF"}', qos=2)
    self.mqttClient.connect(self.mqttBroker, 1883, 60)
    self.mqttClient.loop_start()
    self.main()

  def readTemperature(self):
    #print("reading temperature...")
    #print("not implemented yet")
    self.currentTemp = sensor.get_temperature()
    return self.currentTemp

  def displayTemperature(self, temp):
    tm.temperature(round(temp))

  def publishTemp(self, temp, angle):
    self.mqttClient.publish(self.mqttTopic01, str(temp), qos=2)
    self.mqttClient.publish(self.mqttTopic02, str(angle), qos=2)
    self.mqttClient.publish(self.mqttTopicTempSetPoint, str(self.targetTemperature), qos=2)

    #publish.single(self.mqttTopic01, str(temp), hostname=self.mqttBroker)
    #publish.single(self.mqttTopic02, str(angle), hostname=self.mqttBroker)

  def on_MqttConnect(self,client, userdata, flags, rc):
    print("mqtt connected")
    print(rc)
    client.subscribe(self.mqttControlTopicTempSetPoint)
    client.subscribe(self.mqttControlTopicFineTune)

  def on_MqttMessage(self,client, userdata, message):
    print("gotMessage")
    print(message.topic)
    print(message.payload)
    
    match message.topic:
      case self.mqttControlTopicTempSetPoint:
        print("changing temperature set point to "+ str(float(message.payload)))
        #print(float(message.payload))
        self.targetTemperature = float(message.payload)
        #print(self.targetTemperature)
        self.pid.setpoint = self.targetTemperature
        client.publish(self.mqttTopicTempSetPoint, str(self.targetTemperature))
      case self.mqttControlTopicFineTune:
        print("finetuning PID parameters")
        print(message.payload[:1])
        match message.payload[:1]:
          case b'P':
            self.pid.Kp = float(message.payload[1:])
            #printMessage = "set Kp to "+str(float(message.payload[1:]))
            #print(printMessage)
            #client.publish(self.mqttTopicFineTune, printMessage)
          case b'I':
            self.pid.Ki = float(message.payload[1:])
            #printMessage = "set Ki to "+str(float(message.payload[1:]))
            #print(printMessage)
            #client.publish(self.mqttTopicFineTune, printMessage)
          case b'D':
            self.pid.Kd = float(message.payload[1:])
            #printMessage = "set Kd to "+str(float(message.payload[1:]))
            #print(printMessage)
            #client.publish(self.mqttTopicFineTune, printMessage)
          case _:
            #client.publish(self.mqttTopicFineTune, "invalid syntax")
            print("invalid syntax for finetuning")
        printMessage = "Current PID parameters= "+str(self.pid.Kp)+" / "+str(self.pid.Ki)+" / "+str(self.pid.Kd)
        print(printMessage)
        client.publish(self.mqttTopicFineTune, printMessage)
      case _:
        print("unknown topic, message is ignored")


  def main(self):
    print("main")

    while True:
      readTemp = self.readTemperature()
      self.displayTemperature(readTemp)
      #self.publishTemp(readTemp)
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


# legacy snippet here for reference

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
