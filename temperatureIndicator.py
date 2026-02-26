import tm1637
from ds18b20 import DS18B20
import time

sensor = DS18B20()
tm = tm1637.TM1637(clk=23, dio=24)

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
