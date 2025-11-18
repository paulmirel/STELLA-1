# lis3mdl module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

class Device: #parent class
    def __init__(self, name = None, pn = None, address = None, swob = None ):
        self.name = name
        self.swob = swob
        self.pn = pn
        self.address = address
    def report(self):
        found = False
        if self.swob is not None:
            print("report:", hex(self.address), self.pn, "\t", self.name, "found" )
            found = True
        return found
    def found(self):
        if self.swob is not None:
            return True
        else:
            return False
            
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
        super().__init__(name = "lis3mdl_magnetic_field_sensor", pn = "lis3mdl", address = 0x6a, swob = LIS3MDL(com_bus ))
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
        return( "lis3mdl_magnetic_field_x-!-uT, lis3mdl_magnetic_field_y-!-uT, lis3mdl_magnetic_field_z-!-uT" )

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
