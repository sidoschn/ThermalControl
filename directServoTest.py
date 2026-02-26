import RPi.GPIO as GPIO
import time



GPIO.setmode(GPIO.BOARD)
#26
GPIO.setup(32, GPIO.OUT)

pwm_pin = GPIO.PWM(32, 50)
pwm_pin.start(20)
#time.sleep(5)
#pwm_pin.ChangeDutyCycle(4)
#time.sleep(5)
#pwm_pin.ChangeDutyCycle(12)
time.sleep(5)
pwm_pin.stop()
GPIO.cleanup()
