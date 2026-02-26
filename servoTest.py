
import board
import time

from adafruit_pca9685 import PCA9685
from adafruit_motor import servo


i2c = board.I2C()

pca = PCA9685(i2c)

pca.frequency = 50

servo0 = servo.Servo(pca.channels[0], min_pulse=500, max_pulse = 2500, actuation_range=180)

range = 90

servo0.angle = 90
#servo0.angle = 70
time.sleep(2)

servo0.angle = 90-range
time.sleep(2)

servo0.angle = 90
time.sleep(2)

servo0.angle = 90+range
time.sleep(2)

servo0.angle = 90
time.sleep(2)

print("done")

exit()

servo0.angle = 90+range
time.sleep(1)
servo0.angle = 90
time.sleep(1)


exit()

for j in range(2):

  for i in range(180):
    servo0.angle = i
    time.sleep(0.5)

  for i in range(1800):
    servo0.angle = 180-i
    time.sleep(0.5)



print("done")

exit()
servo0.angle = 0
print("setting to -90") 
time.sleep(1)

servo0.angle = 180
print("setting to 0")
time.sleep(1)

servo.angle = 0
print("setting to 90")
time.sleep(1)

servo.angle = 180
time.sleep(1)
