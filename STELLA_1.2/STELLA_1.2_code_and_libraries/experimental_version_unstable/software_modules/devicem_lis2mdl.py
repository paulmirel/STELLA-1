# lis2mdl module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import adafruit_lis2mdl
from .classm_device import Device


def initialize_lis2mdl_magnetic_field_sensor( instrument ):
    lis2mdl_magnetic_field_sensor = Null_lis2mdl_Magnetic_Field_Sensor()
    try:
        lis2mdl_magnetic_field_sensor = lis2mdl_Magnetic_Field_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_lis2mdl_magnetic_field_sensor" )
        instrument.sensors_present.append( lis2mdl_magnetic_field_sensor )
    except NameError as err:
        pass
        #print( "library missing:", err )
    except Exception:
        pass
    return lis2mdl_magnetic_field_sensor

class lis2mdl_Magnetic_Field_Sensor( Device ):
    #https://www.st.com/en/mems-and-sensors/lis2mdl.html#documentation
    def __init__( self, com_bus ):
        super().__init__(name = "magnetic", pn = "lis2mdl", address = 0x1E, swob = adafruit_lis2mdl.LIS2MDL(com_bus ))
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


class Null_lis2mdl_Magnetic_Field_Sensor(Device):
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
