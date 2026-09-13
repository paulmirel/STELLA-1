import board
import time
import adafruit_bus_device
import adafruit_register
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

i2c_bus = board.I2C()
pca = PCA9685(i2c_bus)



sensor_fractions = [0, 0.175, 0.345, 0.510, 0.666, 0.833, 1]
pca.frequency = 60

#filter_servo = servo.Servo(pca.channels[0])
sensor_servo = servo.Servo(pca.channels[15], min_pulse=570, max_pulse=2424)#, actuation_range= 180)

#filter_servo.angle = 90
while True:

    for fraction in sensor_fractions:
        print( "go to fraction:",fraction)
        sensor_servo.fraction = 1-fraction
        time.sleep(6)


print("moving")
time.sleep(2)








pca.deinit()
print( "done" )

