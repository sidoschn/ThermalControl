from ds18b20 import DS18B20

import time

sensor = DS18B20()


while True:

	temp = sensor.get_temperature()

	print(temp)

	time.sleep(1)
