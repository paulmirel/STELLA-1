# STELLA-R test code i2c_bus_scan

# STELLA bus addresses
# listing available at https://learn.adafruit.com/i2c-addresses/the-list

# 0x18 -- AT Air Temperature - MCP9808 - 0x18 to 0x1F address, choose 1
# 0x29 -- LiDAR range sensor
# 0x38 -- capacitive touch screen
# 0x49 -- VIS 6 channel Spectrometer - AS7262 - 0x49 address
# 0x5a -- TIR Surface Temperature - Melexis MLX90614 3V - 0x5a address
# 0x68 -- clock: Real time clock - PCF8523 - 0x68
# 0x77 -- WX weather BME280
# NIR sensor doesn't show because it's on a uart channel
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
