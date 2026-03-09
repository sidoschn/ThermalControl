from ds18b20 import DS18B20

sensors = []
for sensor_id in DS18B20.get_available_sensors():
    sensors.append(DS18B20(sensor_id))

print (len(sensors))

for sensor in sensors:
    print("Sensor %s has temperature %.2f" % (sensor.get_id(), sensor.get_temperature()))