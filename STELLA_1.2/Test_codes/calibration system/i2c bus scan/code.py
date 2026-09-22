# STELLA-1.2 calibration test code i2c_bus_scan

# listing available at https://learn.adafruit.com/i2c-addresses/the-list

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


i2c_bus = busio.I2C(board.SCL, board.SDA)

mux_8_to_1 = adafruit_tca9548a.TCA9548A(i2c_bus)

while True:
    if i2c_bus.try_lock():
        main_bus_addresses = i2c_bus.scan()
        print("addresses found on main i2c_bus:")
        for address in main_bus_addresses:
            print(hex(address), end = ", ")
        print()
    i2c_bus.unlock()
    for channel in range(0,8):
        if mux_8_to_1[channel].try_lock():
            print(f"Channel {channel}:", end="")
            addresses = mux_8_to_1[channel].scan()
            print([hex(address) for address in addresses if address != 0x70])
            mux_8_to_1[channel].unlock()
    time.sleep(2)
