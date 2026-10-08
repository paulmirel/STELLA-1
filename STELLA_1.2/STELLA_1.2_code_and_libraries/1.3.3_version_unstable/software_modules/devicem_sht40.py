# sht40 module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import adafruit_sht4x
from .classm_device import Device

def initialize_sht40_air_sensor( instrument ):
    sht40_air_sensor = False
    try:
        sht40_air_sensor = sht40_Air_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_sht40_air_sensor" )
        instrument.sensors_present.append( sht40_air_sensor )
    except Exception as err:
        pass
        print("sht40 failed: {}".format(err))
    return sht40_air_sensor

class sht40_Air_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "air", pn = "sht40", address = 0x44, swob = adafruit_sht4x.SHT4x( com_bus ))
        self.temperature_C = 0
        self.humidity_percent = 0
        self.parameters = [ "temperature_C", "humidity_pct" ]
        self.values = [0,0]
    def read(self):
        self.temperature_C = round( self.swob.temperature, 1 )
        self.humidity_percent = round( self.swob.relative_humidity, 1 )
        self.values = [self.temperature_C,self.humidity_percent]
        #print( self.temperature_C )

    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log

    def printlog(self):
        print( self.log())

    def get_values( self ):
        return( self.values )

