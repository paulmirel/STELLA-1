# hdc3022 module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import adafruit_hdc302x
from .classm_device import Device

def initialize_hdc3022_air_sensor( instrument ):
    hdc3022_air_sensor = Null_hdc3022_Air_Sensor()
    try:
        hdc3022_air_sensor = hdc3022_Air_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_hdc3022_air_sensor" )
        instrument.sensors_present.append( hdc3022_air_sensor )
    except Exception as err:
        pass
        #print("hdc3022 failed: {}".format(err))
    return hdc3022_air_sensor

class hdc3022_Air_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "hdc3022_air_sensor", pn = "hdc3022", address = 0x44, swob = adafruit_hdc302x.HDC302x( com_bus ))
        self.temperature_C = 0
        self.humidity_percent = 0
    def read(self):
        self.temperature_C = self.swob.temperature
        self.humidity_percent = self.swob.relative_humidity
        #print( self.temperature_C )
    def log(self):
        # name, units, value, +/-, uncertainty ## per datasheet
        return "{}, {}".format( round(self.temperature_C, 2), round(self.humidity_percent, 1) )
    def printlog(self):
        print( self.log())
    def header(self):
        return( "hdc3022_temperature_ambient-!-C, hdc3022_humidity_relative-!-percent" )

class Null_hdc3022_Air_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.temperature_C = 0
        self.humidity_percent = 0
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass
