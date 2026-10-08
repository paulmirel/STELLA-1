# Calibration main code

# imports
import time
import board
import busio
import adafruit_tca9548a
import adafruit_as5600
from adafruit_as7343 import AS7343
from adafruit_as7341 import AS7341
import adafruit_ds3231
from adafruit_pca9685 import PCA9685
import rotaryio
from software_modules import devicem_rotary_encoder

#initialize
# init neopixel
# init SD card, set neopixel accordingly

i2c_bus = busio.I2C(board.SCL, board.SDA)
# init precision clock
# set system time to precision clock

# init motion hardware
pca = PCA9685(i2c_bus)
pca.frequency = 60
mux_8_to_1 = adafruit_tca9548a.TCA9548A(i2c_bus)
sensor_wheel_angle_sensor = adafruit_as5600.AS5600(mux_8_to_1[7])
rotary_encoder = devicem_rotary_encoder.initialize_rotary_encoder( pin_a = board.A3, pin_b = board.A4, pin_button = board.A2 )
encoder_increment = 0
button_pressed = False
filter_servo = pca.channels[0]
sensor_servo = pca.channels[15]
filter_servo.duty_cycle = 0
sensor_servo.duty_cycle = 0

# set constants
wheel_5_angle_values = 3057, 2719, 2380, 2038, 1695, 1353, 1009
wheel_5_servo_setpoints = 9440, 8352, 6976, 5872, 4640, 3360, 2224
wheel_5_servo_waypoints = []
for index in range (0, len(wheel_5_servo_setpoints)-1):
    wheel_5_servo_waypoints.append(int((wheel_5_servo_setpoints[index]+wheel_5_servo_setpoints[index+1])/2))


# make display


print("choose starting position")
print("enter loop")
print("   move wheels to chosen position")
print("   run measurement sequence")
print("   write data to file")
print("   increment position")







print( "done" )
