# mcp9808 module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import adafruit_mcp9808
from .classm_device import Device


def initialize_mcp9808_air_thermometer( instrument ):
    mcp9808_air_thermometer = Null_mcp9808_Air_Thermometer()
    try:
        mcp9808_air_thermometer = mcp9808_Air_Thermometer( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_mcp9808_air_thermometer" )
        instrument.sensors_present.append( mcp9808_air_thermometer )
    except Exception as err:
        #print( "MCP9808 fail: {}".format(err))
        pass
    return mcp9808_air_thermometer

class mcp9808_Air_Thermometer( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "thermometer", pn = "mcp9808", address = 0x1f, swob = adafruit_mcp9808.MCP9808( com_bus, address = 0x1f ))
        self.temperature_C = None
        self.parameters = [ "temperature_C" ]
        self.values = [0]
    def read(self):
        self.temperature_C = round(self.swob.temperature,2)
        self.values = [self.temperature_C]
        #print( self.temperature_C )

    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log


    def printlog(self):
        print( self.log())

class Null_mcp9808_Air_Thermometer(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.temperature_C = None
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
