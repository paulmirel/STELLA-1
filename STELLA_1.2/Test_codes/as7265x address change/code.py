print("as7265x address and driver change test code")
import busio
import board
import adafruit_tca9548a
from sparkfun_triad import AS7265x_I2C
import sys
import time




if False: #This works with the SparkFun QWIIC library with the sensor on the main bus without an address changer, creates its own i2c bus
    AS7265x = qwiic_as7265x.QwiicAS7265x()
    AS7265x.disable_indicator()
    time.sleep(4)
    AS7265x.enable_indicator()

if False: #sparkfun library: works with an address changer, provided that the new address is added to the library line 59 _AVAILABLE_I2C_ADDRESS = [0x49,0x39]
    i2c_bus = board.I2C()
    AS7265x = qwiic_as7265x.QwiicAS7265x(address=0x39)
    AS7265x.disable_indicator()
    time.sleep(4)
    AS7265x.enable_indicator()

if False: #this works using the premade i2c bus. Must be the board.I2C() version of the bus. The busio version doesn't work.
    i2c_bus = board.I2C()
    AS7265x = AS7265x_I2C(i2c_bus)
    AS7265x.indicator_led = True
    time.sleep(1)
    AS7265x.indicator_led = False
    time.sleep(4)
    AS7265x.indicator_led = True

if False: # this works with the third party library and the address changer
    i2c_bus = board.I2C()
    AS7265x = AS7265x_I2C(i2c_bus, address=0x39)
    AS7265x.indicator_led = True
    time.sleep(1)
    AS7265x.indicator_led = False
    time.sleep(4)
    AS7265x.indicator_led = True

if True:
    i2c_bus = board.I2C()
    mux_8_to_1 = adafruit_tca9548a.TCA9548A(i2c_bus)
    AS7265x = AS7265x_I2C(mux_8_to_1[0])
    AS7265x.indicator_led = True
    time.sleep(1)
    AS7265x.indicator_led = False
    time.sleep(4)
    AS7265x.indicator_led = True
