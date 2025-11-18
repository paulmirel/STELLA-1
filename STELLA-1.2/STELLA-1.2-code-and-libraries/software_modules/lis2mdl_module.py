# lis2mdl module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

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
        super().__init__(name = "lis2mdl_magnetic_field_sensor", pn = "lis2mdl", address = 0x1E, swob = adafruit_lis2mdl.LIS2MDL(com_bus ))
        self.Bx_uT = None
        self.By_uT = None
        self.Bz_uT = None
        self.B_uncertainty_uT = 0.3 #TBD how close is this uncertainty to actual performance
    def read(self):
        self.Bx_uT, self.By_uT, self.Bz_uT = self.swob.magnetic
        #print( self.Bx_uT, self.By_uT, self.Bz_uT )
    def log(self):
        return "{}, {}, {}".format(
            round(self.Bx_uT, 3),
            round(self.By_uT, 3),
            round(self.Bz_uT, 3))
    def printlog(self):
        print( self.log())
    def header(self):
        return( "lis2mdl_magnetic_field_x-!-uT, lis2mdl_magnetic_field_y-!-uT, lis2mdl_magnetic_field_z-!-uT" )

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
