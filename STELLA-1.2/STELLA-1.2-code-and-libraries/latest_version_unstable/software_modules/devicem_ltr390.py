# ltr390 module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import adafruit_ltr390
from .classm_device import Device

            
def initialize_ltr390_uva_sensor( instrument ):
    ltr390_uva_sensor = Null_ltr390_UVA_Sensor()
    try:
        ltr390_uva_sensor = ltr390_UVA_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_ltr390_uva_sensor" )
        instrument.sensors_present.append( ltr390_uva_sensor )
    except:
        pass
    return ltr390_uva_sensor

class ltr390_UVA_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "ltr390_uva_sensor", pn = "ltr390", address = 0x53, swob = adafruit_ltr390.LTR390( com_bus ))
    def read(self):
        self.UVA = self.swob.uvs
        self.uv_index = self.swob.uvi
        self.light_raw = self.swob.light
        self.lux = self.swob.lux
        #print( self.lux )
    def header(self):
        return "ltr390_illumination-!-counts, ltr390_illumination-!-lux, ltr390_uva-!-counts, ltr390_uv_index-!-"
    def log(self):
        return "{}, {}, {}, {}".format( self.light_raw, self.lux, self.UVA, self.uv_index )
    def printlog(self):
        print( self.log())

class Null_ltr390_UVA_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
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
