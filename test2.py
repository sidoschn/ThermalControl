import tm1637
from ds18b20 import DS18B20
import time

tm = tm1637.TM1637(clk=23, dio=24)



while True:

  temp = sensor.get_temperature()
  print(temp)
  tm.temperature(temp)
  time.sleep(1)
