# lsm6ds module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

from adafruit_lsm6ds.lsm6ds3 import LSM6DS3 as LSM6DS
from /classm_device import Device

            
def initialize_lsm6ds_accel_gyro_sensor( instrument ):
    lsm6ds_accel_gyro_sensor = Null_lsm6ds_Accel_Gyro_Sensor()
    try:
        lsm6ds_accel_gyro_sensor = lsm6ds_Accel_Gyro_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_lsm6ds_accel_gyro_sensor" )
        instrument.sensors_present.append( lsm6ds_accel_gyro_sensor )
    except NameError as err:
        pass
        #print( "library missing:", err )
    except Exception:
        pass
    return lsm6ds_accel_gyro_sensor

class lsm6ds_Accel_Gyro_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "lsm6ds_accel_gyro_sensor", pn = "lms6ds", address = 0x1c, swob = LSM6DS( com_bus ))
        self.Ax_m_per_s2 = 0
        self.Ay_m_per_s2 = 0
        self.Az_m_per_s2 = 0
        self.wx_deg_per_s = 0
        self.wy_deg_per_s = 0
        self.wz_deg_per_s = 0
        self.A_uncertainty_m_per_s2= 0.4
    def read(self):
        self.Ax_m_per_s2, self.Ay_m_per_s2, self.Az_m_per_s2 = self.swob.acceleration
        self.wx_deg_per_s, self.wy_deg_per_s, self.wz_deg_per_s = self.swob.gyro
        #print( self.wx_rad_per_s, self.wy_rad_per_s, self.wz_rad_per_s  )
    def log(self):
        return "{}, {}, {}, {}, {}, {}".format(
            round(self.Ax_m_per_s2, 3),
            round(self.Ay_m_per_s2, 3),
            round(self.Az_m_per_s2, 3),
            round(self.wx_deg_per_s, 3),
            round(self.wy_deg_per_s, 3),
            round(self.wz_deg_per_s, 3)
            )
    def printlog(self):
        print( self.log())
    def header(self):
        headers = "lsm6ds_acceleration_x-!-m_per_s_sq, lsm6ds_acceleration_y-!-m_per_s_sq, lsm6ds_acceleration_z-!-m_per_s_sq"
        headers += "lsm6ds_rotation_x-!-degrees_per_s, lsm6ds_rotation_x-!-degrees_per_s, lsm6ds_rotation_x-!-degrees_per_s"
        return headers

class Null_lsm6ds_Accel_Gyro_Sensor(Device):
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
