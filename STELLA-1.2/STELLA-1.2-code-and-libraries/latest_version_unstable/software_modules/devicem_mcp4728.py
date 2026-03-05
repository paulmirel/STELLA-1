# mcp4728 module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import adafruit_mcp4728
from .classm_device import Device

MCP4728_DEFAULT_ADDRESS = 0x60
MCP4728A4_DEFAULT_ADDRESS = 0x64

def initialize_mcp4728_quad_dac( instrument ):
    mcp4728_quad_dac = Null_MCP4728_Quad_DAC()
    try:
        mcp4728_quad_dac = MCP4728_Quad_DAC( instrument )
        instrument.welcome_page.announce( "initialize_mcp4728_quad_dac" )
        instrument.sensors_present.append( mcp4728_quad_dac )
    except Exception as err:
        pass
    return mcp4728_quad_dac

class MCP4728_Quad_DAC( Device ):
    def __init__( self, instrument ):
        try:
            super().__init__(name = "quad_dac_12_bits", pn = "mcp4728", address = 0x60, swob = adafruit_mcp4728.MCP4728(instrument.i2c_bus, adafruit_mcp4728.MCP4728_DEFAULT_ADDRESS))
        except:
            try:
                super().__init__(name = "quad_dac_12_bits", pn = "mcp4728", address = 0x64, swob = adafruit_mcp4728.MCP4728(instrument.i2c_bus, adafruit_mcp4728.MCP4728A4_DEFAULT_ADDRESS))
            except Exception as err:
                print("Failed to find MCP4728 at either address:", err)
        self.instrument = instrument
        self.swob.channel_a.value = 0
        self.swob.channel_b.value = 0
        self.swob.channel_c.value = 0
        self.swob.channel_d.value = 0
        self.parameters = ["chA_setting", "chB_setting", "chC_setting", "chD_setting"]
        self.values = [0,0,0,0]
    def read(self):
        pass
    def set(self, channel, output_value):
        if channel == "a":
            self.swob.channel_a.value = output_value
            self.values[0] = output_value
        if channel == "b":
            self.swob.channel_b.value = output_value
            self.values[1] = output_value
        if channel == "c":
            self.swob.channel_c.value = output_value
            self.values[2] = output_value
        if channel == "d":
            self.swob.channel_d.value = output_value
            self.values[3] = output_value

    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log
    def printlog(self):
        print( self.log())

class Null_MCP4728_Quad_DAC(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def read(self, value):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass
