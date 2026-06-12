from ds18b20 import DS18B20


sensorList = DS18B20.get_available_sensors()




print(str(len(sensorList))+" Sensors found")

for sensor in sensorList:
    #id = sensor.get_id()
    #temp = sensor.get_temperature()
    print("Sensor with ID: " +sensor)

    #print("reading temperature: "+ temp)



