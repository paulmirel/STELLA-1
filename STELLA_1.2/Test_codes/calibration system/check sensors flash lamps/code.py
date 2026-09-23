# STELLA-1.2 calibration test code i2c_bus_scan

# listing available at https://learn.adafruit.com/i2c-addresses/the-list

# 0x18 -- DS3231 real time clock after address changer
# 0x34 -- qwiic buzzer
# 0x36 -- max1704x battery monitor COLLISION AS5600 magnetic angle sensor
# 0x38 -- capacitive touch screen
# 0x40 -- PCA9685 servo driver
# 0x46 -- AS5600 magnetic angle sensor after address changer
# 0x68 -- PCF8523 real time clock
# 0x70 -- TCA9548 1-to-8 I2C multiplexer

import time
import board
import busio
import adafruit_tca9548a
import adafruit_as5600
from adafruit_as7343 import AS7343
from adafruit_as7341 import AS7341

i2c_bus = busio.I2C(board.SCL, board.SDA)



main_bus_addresses = []
if i2c_bus.try_lock():
    print()
    print( "Check main i2c_bus:")
    main_bus_addresses = i2c_bus.scan()
    #for item in main_bus_addresses:
    #    print( hex(item ) )
    if 0x18 in main_bus_addresses:
        print( "    precision real time clock found" )
    if 0x40 in main_bus_addresses:
        print( "    servo driver found" )
    if 0x46 in main_bus_addresses:
        print( "    filter wheel angle sensor found" )
    if 0x70 in main_bus_addresses:
        print( "    mux_8_to_1 found" )
    i2c_bus.unlock()

mux_8_to_1 = adafruit_tca9548a.TCA9548A(i2c_bus)

spectral_sensors = []
for index in range (0,7):
    try:
        active_sensor = AS7343(mux_8_to_1[index])
        sensor_kind = 7343
    except Exception as err:
        pass
        try:
            active_sensor = AS7341(mux_8_to_1[index])
            sensor_kind = 7341
        except Exception as err:
            pass
    spectral_sensors.append ( active_sensor )
    if sensor_kind == 7343:
        active_sensor.led_current_ma = 20
        active_sensor.led_enabled = True
        time.sleep(1)
        active_sensor.led_enabled = False
    if sensor_kind == 7341:
        active_sensor.led_current = 20
        active_sensor.led = True
        time.sleep(1)
        active_sensor.led = False

print( "Check raw wheel angles:")
sensor_wheel_angle_sensor = adafruit_as5600.AS5600(mux_8_to_1[7])
sensor_wheel_angle_raw = sensor_wheel_angle_sensor.raw_angle
print( "sensor_wheel_angle_sensor angle =", sensor_wheel_angle_raw)
filter_wheel_angle_sensor = adafruit_as5600.AS5600(i2c_bus, address = 0x46)
filter_wheel_angle_raw = filter_wheel_angle_sensor.raw_angle
print( "filter_wheel_angle_sensor angle =", filter_wheel_angle_raw)

