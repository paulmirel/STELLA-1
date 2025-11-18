# lsm303 module
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
            
def initialize_lsm303_acceleration_sensor( instrument ):
    lsm303_acceleration_sensor = Null_lsm303_Acceleration_Sensor()
    try:
        lsm303_acceleration_sensor = lsm303_Acceleration_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_lsm303_acceleration_sensor" )
        instrument.sensors_present.append( lsm303_acceleration_sensor )
    except NameError as err:
        pass
        #print( "library missing:", err )
    except Exception:
        pass
    return lsm303_acceleration_sensor

class lsm303_Acceleration_Sensor( Device ):
    #https://www.st.com/resource/en/datasheet/lsm303agr.pdf
    def __init__( self, com_bus ):
        super().__init__(name = "lsm303_acceleration_sensor", pn = "lms303", address = 0x19, swob = adafruit_lsm303_accel.LSM303_Accel( com_bus ))
        self.Ax_m_per_s2 = None
        self.Ay_m_per_s2 = None
        self.Az_m_per_s2 = None
        self.A_uncertainty_m_per_s2= 0.4
    def read(self):
        self.Ax_m_per_s2, self.Ay_m_per_s2, self.Az_m_per_s2 = self.swob.acceleration
        #print( self.Ax_m_per_s2, self.Ay_m_per_s2, self.Az_m_per_s2 )
    def log(self):
        return "{}, {}, {}".format(
            round(self.Ax_m_per_s2, 3),
            round(self.Ay_m_per_s2, 3),
            round(self.Az_m_per_s2, 3))
    def printlog(self):
        print( self.log())
    def header(self):
        return( "lsm303_acceleration_x-!-m_per_s_sq, lsm303_acceleration_y-!-m_per_s_sq, lsm303_acceleration_z-!-m_per_s_sq" )

class Null_lsm303_Acceleration_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.Ax_m_per_s2 = None
        self.Ay_m_per_s2 = None
        self.Az_m_per_s2 = None
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
