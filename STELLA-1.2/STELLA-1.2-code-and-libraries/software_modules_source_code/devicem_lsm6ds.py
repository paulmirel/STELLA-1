# lsm6ds module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

from adafruit_lsm6ds.lsm6ds3 import LSM6DS3 as LSM6DS
from .classm_device import Device


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
        super().__init__(name = "accel_gyro", pn = "lms6ds", address = 0x1c, swob = LSM6DS( com_bus ))
        self.Ax_m_per_s2 = 0
        self.Ay_m_per_s2 = 0
        self.Az_m_per_s2 = 0
        self.wx_deg_per_s = 0
        self.wy_deg_per_s = 0
        self.wz_deg_per_s = 0
        self.A_uncertainty_m_per_s2= 0.4
        self.parameters = [ "ax_m_per_s2","ay_m_per_s2","az_m_per_s2","wx_deg_per_s","wy_deg_per_s","wz_deg_per_s" ]
        self.values = [0,0,0,0,0,0]
    def read(self):
        self.Ax_m_per_s2, self.Ay_m_per_s2, self.Az_m_per_s2 = self.swob.acceleration
        self.wx_deg_per_s, self.wy_deg_per_s, self.wz_deg_per_s = self.swob.gyro
        #print( self.wx_rad_per_s, self.wy_rad_per_s, self.wz_rad_per_s  )
        self.values = [round(self.Ax_m_per_s2,3), round(self.Ay_m_per_s2,3), round(self.Az_m_per_s2,3),
                        round(self.wx_deg_per_s,3), round(self.wy_deg_per_s,3), round(self.wz_deg_per_s,3)]
    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log

    def printlog(self):
        print( self.log())


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
