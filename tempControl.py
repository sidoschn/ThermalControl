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
from string import ascii_uppercase
import threading
import configparser
import os.path
import RPi.GPIO as GPIO
import os

updater.performAutoupdate()



nServos = 1
# #legacy
# sensors = []
# sensorList = DS18B20.get_available_sensors()
# for sensor_id in sensorList:
#     sensors.append(DS18B20(sensor_id))
#     print("sensor: "+ str(sensor_id))

# sensor = sensors[0]

tm = tm1637.TM1637(clk=23, dio=24)

i2c = board.I2C()
pca = PCA9685(i2c)
pca.frequency = 50
servo0 = servo.Servo(pca.channels[0], min_pulse=500, max_pulse = 2500, actuation_range=180)

servo0.angle = 90

class temperatureController:
  configFileName = "thermalControlConfig.ini"
  currentTemps = []
  angles = [None] * nServos
  #targetTemperature = 35 # legacy
  currentTemp = 30
  maxRange = 50 #
  sensors = []
  
  mqttTopicIsAliveState = "thermalControl/isAlive"
  #mqttTopic01 = "thermalControl/tempAnbauVorlauf" #legacy
  mqttTopic02 = "thermalControl/servoAngle" #not really legacy yet
  mqttTopicTempSetPoint = "thermalControl/tempSetPoint"
  mqttControlTopicTempSetPoint = "thermalControl/tempSetPoint/set"
  mqttTopicFineTune = "thermalControl/fineTune"
  mqttControlTopicFineTune = "thermalControl/fineTune/set"
  
  mqttBroker = "192.168.0.39"
  loopTime = 10
  flag_MQTTconnected = False

  #defining the default config dict the config.ini is generated from
  defaultConfig = configparser.ConfigParser()
  configSectionGeneral = "General"
  configSectionMQTT = "MQTT"
  configSectionSensors = "Sensors"

  defaultConfig[configSectionGeneral] = {}
  defaultConfig[configSectionGeneral]["targetTemperature01"] = str(35)
  defaultConfig[configSectionGeneral]["maxAngleRange"] = str(50)
  defaultConfig[configSectionGeneral]["samplingLoopTime"] = str(10)
  defaultConfig[configSectionGeneral]["displayLoopTime"] = str(5)
  defaultConfig[configSectionGeneral]["PIDp"] = str(-30)
  defaultConfig[configSectionGeneral]["PIDi"] = str(-0.5)
  defaultConfig[configSectionGeneral]["PIDd"] = str(0)
  defaultConfig[configSectionGeneral]["PIDsensor"] = "A"

  
  defaultConfig[configSectionMQTT] = {}
  defaultConfig[configSectionMQTT]["clientID"] = "ThermalController"
  defaultConfig[configSectionMQTT]["brokerIP"] = "192.168.0.39"
  defaultConfig[configSectionMQTT]["brokerPort"] = str(1883)
  defaultConfig[configSectionMQTT]["brokerIP"] = "192.168.0.39"
  defaultConfig[configSectionMQTT]["topicIsAlive"] = "thermalControl/isAlive"
  defaultConfig[configSectionMQTT]["topicTempSetPoint"] = "thermalControl/tempSetPoint"
  defaultConfig[configSectionMQTT]["controlTopicTempSetPoint"] = "thermalControl/tempSetPoint/set"
  defaultConfig[configSectionMQTT]["topicFineTune"] = "thermalControl/fineTune"
  defaultConfig[configSectionMQTT]["controlTopicFineTune"] = "thermalControl/fineTune/set"
  defaultConfig[configSectionMQTT]["thermalSensorBaseTopic"] = "thermalControl/thermalSensors/"

  defaultConfig[configSectionSensors] = {}

  ## -- pump controlls
  nPumps = 4

  mqttTopicsPumps = [None]*nPumps
  mqttTopicsPumpsSet = [None]*nPumps
  for i in range(nPumps):
    mqttTopicsPumps[i] = "thermalControl/pumps/pumpRelais"+str(i)
    mqttTopicsPumpsSet[i] = "thermalControl/pumps/pumpRelais"+str(i)+"/set"
  
  outputPins = {
    0:'17',
    1:'27',
    2:'22',
    3:'25'
  }
  pumpStates = ["off","off","off","off"]



  # sensor structure:
  # #problably unneccessarily complex {sensorID : {shortId:"short ID(eg. A, B,...)", description:"some description"}}
  # {sensorID : shortId}


  # #legacy
  # iterator = 0
  
  # for sensor in sensors:
  #   sensorId = sensor.get_id()
  #   shortID = ascii_uppercase[iterator]

  #   mqttSensorTopic = "thermalControl/thermalSensors/" + shortID+ str(sensorId)
  #   #mqttSensorTopics.append(mqttSensorTopic)
  #   sensor.mqttTopic = mqttSensorTopic
  #   #sensor.lastReadTemp = 0
    
  #   sensor.shortID = shortID
  #   iterator = iterator + 1



  def __init__(self):

    ## -- loading config
    self.configData = self.loadConfig()
    
    self.sensors = self.loadThermalSensors()
    self.initializeThermalSensors()

    #print(self.configData[self.configSectionGeneral]["PIDp"])
    #print(self.configData[self.configSectionGeneral]["PIDi"])
    #print(float(self.configData[self.configSectionGeneral]["PIDi"]))

    
    self.pid = PID(float(self.configData[self.configSectionGeneral]["PIDp"]), float(self.configData[self.configSectionGeneral]["PIDi"]), float(self.configData[self.configSectionGeneral]["PIDd"]), setpoint=float(self.configData[self.configSectionGeneral]["targetTemperature01"]), starting_output = 90)
    self.pid.sample_time = float(self.configData[self.configSectionGeneral]["samplingLoopTime"])
    self.pid.output_limits = (90-int(self.configData[self.configSectionGeneral]["maxAngleRange"]), 90+int(self.configData[self.configSectionGeneral]["maxAngleRange"]))
    print("setpoint temperature: "+str(self.pid.setpoint))

    self.pid.sensor = self.assignSensorToPID(self.pid)

    ## -- initializing mqtt client
    self.mqttClient = mqtt.Client(client_id="ThermalController")
    self.mqttClient.on_connect = self.on_MqttConnect
    self.mqttClient.on_disconnect = self.on_MqttDisconnect
    self.mqttClient.on_message = self.on_MqttMessage
    self.mqttClient.will_set(self.configData[self.configSectionMQTT]["topicIsAlive"], '{"state": "OFF"}', qos=2)

    ## -- initializing the relais pins
    self.initOutputPins(self.outputPins)

    ## this has been moved to main() to account for missing or changing network connections
    # self.mqttClient.connect(self.configData[self.configSectionMQTT]["brokerIP"], int(self.configData[self.configSectionMQTT]["brokerPort"]), 60)
    # self.mqttClient.loop_start()

    self.main()

  def loadConfig(self):

    if not os.path.isfile(self.configFileName):
      print("generating new config file from defaults")
      with open(self.configFileName, 'w') as configFile:
        self.defaultConfig.write(configFile)

    print("reading config from file: "+ self.configFileName)
    configData = configparser.ConfigParser()
    configData.read(self.configFileName)

    return configData

  def updateConfig(self):
    with open(self.configFileName, 'w') as configFile:
      self.configData.write(configFile)

  def loadThermalSensors(self):
    sensorList = DS18B20.get_available_sensors()
    sensors = []
    for sensor_id in sensorList:
      sensors.append(DS18B20(sensor_id))
      print("sensor: "+ str(sensor_id))
    return sensors
  
  def initializeThermalSensors(self):
        
    for sensor in self.sensors:
      sensorId = sensor.get_id()
      if sensorId in self.configData[self.configSectionSensors]:
        print("sensor is known")
        shortID = self.configData[self.configSectionSensors][sensorId]
        print("assigning short ID: "+shortID+" to sensor "+sensorId+" (change associations in config.ini)")
      else:
        print("sensor is new")
        shortID = ascii_uppercase[len(self.configData[self.configSectionSensors])]
        print("assigning short ID: "+shortID+" to sensor "+sensorId+" (change associations in config.ini)")
        self.configData[self.configSectionSensors][sensorId] = shortID
        self.updateConfig()
        
      mqttSensorTopic = self.configData[self.configSectionMQTT]["thermalSensorBaseTopic"] + shortID
      sensor.mqttTopic = mqttSensorTopic
      sensor.shortID = shortID
      
  def assignSensorToPID(self, pid):
    
    for sensor in self.sensors:
      if sensor.shortID == self.configData[self.configSectionGeneral]["PIDsensor"]:
        return sensor
      
    print("ERROR: NO SENSOR IS ASSOCIATED WITH THE PID CONTROLLER")
    print("!!check associations in the config.ini!!")
    print("exiting...")
    exit()
        



  
  # # legacy
  # def readTemperature(self):
  #   #print("reading temperature...")
  #   #print("not implemented yet")
  #   self.currentTemp = sensor.get_temperature()
  #   return self.currentTemp
  
  def readTemperatures(self):
    for sensor in self.sensors:
      sensor.lastReadTemp = sensor.get_temperature()
      
    #print("reading temperature...")
    #print("not implemented yet")
    #self.currentTemp = sensor.get_temperature()
  
  # #legacy
  # def displayTemperature(self, temp):
  #   tm.temperature(round(temp))
  
  def displayTemperatures(self):
    while True:
      for sensor in self.sensors:
        if len(sensor.shortID)>2:
          prefix = str(sensor.shortID)[:2]
        else:
          if len(sensor.shortID) == 2:
            prefix = str(sensor.shortID) # if short ID is exactly 2 characters long
          else:
            prefix = str(sensor.shortID) + " " # if short ID is exactly 1 charater long (or zero but that should be impractical)

        try:
          #tm.temperature(round(sensor.lastReadTemp))
          tm.show(prefix+str(round(sensor.lastReadTemp)))
          time.sleep(float(self.configData[self.configSectionGeneral]["displayLoopTime"]))
          #print("Display: "+str(sensor.shortID)+" "+str((sensor.lastReadTemp)))
        except:
          tm.show("----")
          time.sleep(float(self.configData[self.configSectionGeneral]["displayLoopTime"]))
          print("temperature has not been read/short ID was not yet assigned")

  def publishTemps(self):
    if self.flag_MQTTconnected:
      for sensor in self.sensors:
        self.mqttClient.publish(sensor.mqttTopic , str(sensor.lastReadTemp), qos=2)
      
      self.mqttClient.publish(self.configData[self.configSectionMQTT]["topicTempSetPoint"], str(self.pid.setpoint), qos=2)

  def publishAngles(self, angles):
    if self.flag_MQTTconnected:
      for angle in angles:
        self.mqttClient.publish(self.mqttTopic02, str(angle), qos=2)
    #publish.single(self.mqttTopic01, str(temp), hostname=self.mqttBroker)
    #publish.single(self.mqttTopic02, str(angle), hostname=self.mqttBroker)

  # #legacy
  # def publishTemp(self, temp, angle):
  #   self.mqttClient.publish(self.mqttTopic01, str(temp), qos=2)
  #   self.mqttClient.publish(self.mqttTopic02, str(angle), qos=2)
  #   self.mqttClient.publish(self.mqttTopicTempSetPoint, str(self.targetTemperature), qos=2)

  #   #publish.single(self.mqttTopic01, str(temp), hostname=self.mqttBroker)
  #   #publish.single(self.mqttTopic02, str(angle), hostname=self.mqttBroker)

  def on_MqttConnect(self,client, userdata, flags, rc):
    print("mqtt connected")
    self.flag_MQTTconnected = True
    print(rc)
    client.subscribe(self.mqttControlTopicTempSetPoint)
    client.subscribe(self.mqttControlTopicFineTune)
    for topic in self.mqttTopicsPumpsSet:
      client.subscribe(topic)

    client.publish(self.configData[self.configSectionMQTT]["topicIsAlive"], '{"state": "ON"}', qos=2)
    print(self.configData[self.configSectionMQTT]["topicTempSetPoint"])
    print(str(self.pid.setpoint))
    client.publish(self.configData[self.configSectionMQTT]["topicTempSetPoint"], str(self.pid.setpoint) , qos=2)

    for i in range(self.nPumps):
      client.publish(self.mqttTopicsPumps[i], self.pumpStates[i] )

    printMessage = "Current PID parameters "+str(self.pid.Kp)+" "+str(self.pid.Ki)+" "+str(self.pid.Kd)
    print(printMessage)
    client.publish(self.configData[self.configSectionMQTT]["topicFineTune"], printMessage)

  def on_MqttDisconnect(self,client, userdata, flags, rc):
    print("mqtt disconnected")
    self.flag_MQTTconnected = False

  def on_MqttMessage(self,client, userdata, message):
    print("gotMessage")
    print(message.topic)
    print(message.payload)

    match message.topic:
      case self.mqttControlTopicTempSetPoint:
        print("changing temperature set point to "+ str(float(message.payload)))
        #print(float(message.payload))
        
        #print(self.targetTemperature)
        self.pid.setpoint = float(message.payload)

        self.configData[self.configSectionGeneral]["targetTemperature01"] = str(self.pid.setpoint)
        self.updateConfig()
        client.publish(self.mqttTopicTempSetPoint, str(self.pid.setpoint))

      case self.mqttControlTopicFineTune:
        print("finetuning PID parameters")
        print(message.payload[:1])
        match message.payload[:1]:
          case b'P':
            self.pid.Kp = float(message.payload[1:])
            self.configData[self.configSectionGeneral]["PIDp"] = str(self.pid.Kp)
            self.updateConfig()
            #printMessage = "set Kp to "+str(float(message.payload[1:]))
            #print(printMessage)
            #client.publish(self.mqttTopicFineTune, printMessage)
          case b'I':
            self.pid.Ki = float(message.payload[1:])
            self.configData[self.configSectionGeneral]["PIDi"] = str(self.pid.Ki)
            self.updateConfig()
            #printMessage = "set Ki to "+str(float(message.payload[1:]))
            #print(printMessage)
            #client.publish(self.mqttTopicFineTune, printMessage)
          case b'D':
            self.pid.Kd = float(message.payload[1:])
            self.configData[self.configSectionGeneral]["PIDd"] = str(self.pid.Kd)
            self.updateConfig()
            #printMessage = "set Kd to "+str(float(message.payload[1:]))
            #print(printMessage)
            #client.publish(self.mqttTopicFineTune, printMessage)
          case _:
            #client.publish(self.mqttTopicFineTune, "invalid syntax")
            print("invalid syntax for finetuning")
        printMessage = "Current PID parameters "+str(self.pid.Kp)+" "+str(self.pid.Ki)+" "+str(self.pid.Kd)
        print(printMessage)
        client.publish(self.mqttTopicFineTune, printMessage)

      case x if x in self.mqttTopicsPumpsSet:
        print("pump command received")
        messageParts = message.topic.split("/")
        relaisIdxString = messageParts[-2]
        relaisIdx = int(relaisIdxString[-1:])
        print("command for pump "+str(relaisIdx))
        self.switchRelais(relaisIdx, message.payload, client)
        
      case _:
        print("unknown topic, message is ignored")

  def initOutputPins(self, pinDict):
    for outPin in pinDict.values():
        os.system('pinctrl '+ outPin +' op dh')

  def switchRelais(self, pinChannel, bEnable, client):
    print("switching pump " +str(bEnable))
    if str(bEnable) == "ON":
        os.system('pinctrl '+ self.outputPins[pinChannel]+' dl')
        print("Started pump")        
        self.pumpStates[pinChannel] = bEnable
        client.publish(self.mqttTopicsPumps[pinChannel], '{"state": "ON"}', qos=2)
    elif str(bEnable) == "OFF":
        os.system('pinctrl '+self.outputPins[pinChannel]+' dh')
        print("Stopped pump")
        self.pumpStates[pinChannel] = bEnable
        client.publish(self.mqttTopicsPumps[pinChannel], '{"state": "OFF"}', qos=2)
    


  def main(self):
    print("main")

    displayTemperaturesThread = threading.Thread(target=self.displayTemperatures, daemon=True)
    displayTemperaturesThread.start()

    while True:
      
      if not self.flag_MQTTconnected:
        print("mqtt not connected, attempting re-connect")
        try:
          self.mqttClient.connect(self.configData[self.configSectionMQTT]["brokerIP"], int(self.configData[self.configSectionMQTT]["brokerPort"]), 60)
          self.mqttClient.loop_start()
        except:
          print("mqtt connection failed")


      self.readTemperatures()
      #self.displayTemperatures()
      #self.publishTemp(readTemp)
      self.angles[0] = self.pid(self.pid.sensor.lastReadTemp)

      self.publishAngles(self.angles)
      self.publishTemps()
      
      #print(str(self.angles[0])+" "+str(self.pid.sensor.lastReadTemp))
      try:
        servo0.angle = float(self.angles[0])
      except:
        print("i2c com failure")

      time.sleep(float(self.configData[self.configSectionGeneral]["samplingLoopTime"]))

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
