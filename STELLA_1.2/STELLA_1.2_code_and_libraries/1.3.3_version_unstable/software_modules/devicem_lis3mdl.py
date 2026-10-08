# lis3mdl module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

from adafruit_lis3mdl import LIS3MDL
from .classm_device import Device


def initialize_lis3mdl_magnetic_field_sensor( instrument ):
    lis3mdl_magnetic_field_sensor = Null_lis3mdl_Magnetic_Field_Sensor()
    try:
        lis3mdl_magnetic_field_sensor = lis3mdl_Magnetic_Field_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_lis3mdl_magnetic_field_sensor" )
        instrument.sensors_present.append( lis3mdl_magnetic_field_sensor )
    except NameError as err:
        pass
        #print( "library missing:", err )
    except Exception:
        #print( "Exception:", err )
        pass
    return lis3mdl_magnetic_field_sensor

class lis3mdl_Magnetic_Field_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "magnetic", pn = "lis3mdl", address = 0x6a, swob = LIS3MDL(com_bus ))
        self.Bx_uT = None
        self.By_uT = None
        self.Bz_uT = None
        self.B_uncertainty_uT = 0.3 #TBD how close is this uncertainty to actual performance
        self.parameters = [ "Bx_uT", "By_uT", "Bz_uT" ]
        self.values = [0,0,0]
    def read(self):
        self.Bx_uT, self.By_uT, self.Bz_uT = self.swob.magnetic
        #print( self.Bx_uT, self.By_uT, self.Bz_uT )
        self.values = [ round(self.Bx_uT,3), round(self.By_uT,3), round(self.Bz_uT,3) ]

    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log

    def printlog(self):
        print( self.log())


class Null_lis3mdl_Magnetic_Field_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.Bx = None
        self.By = None
        self.Bz = None
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
