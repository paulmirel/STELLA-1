print("as7265x address and driver change test code")
import busio
import board
import qwiic_as7265x
import sys
import time


#i2c_bus = busio.I2C( board.SCL, board.SDA )

if True: #This works with sensor on the main bus without an address changer
    AS7265x = qwiic_as7265x.QwiicAS7265x() #address = 0x39)#, i2c_driver=i2c_bus)
    AS7265x.disable_indicator()
    time.sleep(4)
    AS7265x.enable_indicator()
