# STELLA-1.2 wheel positions


import time
import board
import busio
import adafruit_tca9548a
import adafruit_as5600
from adafruit_as7343 import AS7343
from adafruit_as7341 import AS7341
import adafruit_ds3231
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

i2c_bus = busio.I2C(board.SCL, board.SDA)

mux_8_to_1 = adafruit_tca9548a.TCA9548A(i2c_bus)

print( "Check raw wheel angles:")
sensor_wheel_angle_sensor = adafruit_as5600.AS5600(mux_8_to_1[7])
sensor_wheel_angle_raw = sensor_wheel_angle_sensor.raw_angle
sensor_wheel_angle = sensor_wheel_angle_sensor.angle
print( "sensor_wheel_angle_sensor raw angle =", sensor_wheel_angle_raw, "sensor_wheel_angle_sensor angle =", sensor_wheel_angle)

if sensor_wheel_angle_sensor.magnet_detected:
    if sensor_wheel_angle_sensor.max_gain_overflow is True:
        print("Magnet is too weak")
    if sensor_wheel_angle_sensor.min_gain_overflow is True:
        print("Magnet is too strong")
    print(f"Raw angle: {sensor_wheel_angle_sensor.raw_angle}")
    print(f"Scaled angle: {sensor_wheel_angle_sensor.angle}")
    print(f"Magnitude: {sensor_wheel_angle_sensor.magnitude}")

if True:
    filter_wheel_angle_sensor = adafruit_as5600.AS5600(i2c_bus, address = 0x46)
    filter_wheel_angle_raw = filter_wheel_angle_sensor.raw_angle
    print( "filter_wheel_angle_sensor angle =", filter_wheel_angle_raw)

if filter_wheel_angle_sensor.magnet_detected:
    if filter_wheel_angle_sensor.max_gain_overflow is True:
        print("Magnet is too weak")
    if filter_wheel_angle_sensor.min_gain_overflow is True:
        print("Magnet is too strong")
    print(f"Raw angle: {filter_wheel_angle_sensor.raw_angle}")
    print(f"Scaled angle: {filter_wheel_angle_sensor.angle}")
    print(f"Magnitude: {filter_wheel_angle_sensor.magnitude}")

print("done")


