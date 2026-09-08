# STELLA-1.2 calibration test code i2c_bus_scan

# listing available at https://learn.adafruit.com/i2c-addresses/the-list

# 0x34 -- qwiic buzzer
# 0x36 -- max1704x battery monitor COLLISION AS5600 magnetic angle sensor
# 0x38 -- capacitive touch screen
# 0x40 -- PCA9685 servo driver
# 0x46 -- AS5600 magnetic angle sensor after address changer
# 0x68 -- PCF8523 real time clock
# 0x70 -- TCA9548 1-to-8 I2C multiplexer
# GPS sensor doesn't show because it's on a uart channel

import time
import board
import busio

i2c = busio.I2C(board.SCL, board.SDA)

while not i2c.try_lock():
    print( "i2c bus failure" )
    time.sleep(2)

while True:
    print("I2C addresses found:", [hex(device_address)
                                   for device_address in i2c.scan()])
    time.sleep(2)
