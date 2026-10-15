print("as7265x address and driver change test code")
import busio
import board
import qwiic_as7265x
import sys
import time




if False: #This works with sensor on the main bus without an address changer, creates its own i2c bus
    AS7265x = qwiic_as7265x.QwiicAS7265x()
    AS7265x.disable_indicator()
    time.sleep(4)
    AS7265x.enable_indicator()

if False: #this works using the premade i2c bus
    i2c_bus = board.I2C()
    AS7265x = qwiic_as7265x.QwiicAS7265x() #address = 0x39)#, i2c_driver=i2c_bus)
    AS7265x.disable_indicator()
    time.sleep(4)
    AS7265x.enable_indicator()

if True: #works with an address changer, provided that the new address is added to the library line 59 _AVAILABLE_I2C_ADDRESS = [0x49,0x39]
    i2c_bus = board.I2C()
    AS7265x = qwiic_as7265x.QwiicAS7265x(address=0x39)
    AS7265x.disable_indicator()
    time.sleep(4)
    AS7265x.enable_indicator()


