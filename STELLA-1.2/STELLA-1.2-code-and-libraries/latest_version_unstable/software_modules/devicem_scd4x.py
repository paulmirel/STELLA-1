# scd40 module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import adafruit_scd4x
from .classm_device import Device

def initialize_scd4x_co2_sensor( instrument ):
    scd4x_co2_sensor = Null_scd4x_CO2_Sensor()
    try:
        scd4x_co2_sensor = scd4x_CO2_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_scd4x_co2_sensor" )
        instrument.sensors_present.append( scd4x_co2_sensor )
    except:
        pass
    return scd4x_co2_sensor

class scd4x_CO2_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "scd4x_co2_sensor", pn = "scd4x", address = 0x62, swob = adafruit_scd4x.SCD4X( com_bus ))
        if self.swob:
            self.swob.start_periodic_measurement()
        self.temperature_C = None
        self.humidity = None
        self.co2_ppm = None
        self.parameters = []
        self.values = []
        
    def read(self):
        self.co2_ppm = self.swob.CO2
        if self.co2_ppm is not None:
            self.co2_uncty_ppm = 50 + self.co2_ppm * 0.05
            self.temperature_C = self.swob.temperature
            self.humidity = self.swob.relative_humidity
        else:
            self.co2_ppm = 0.0
            self.co2_uncty_ppm = 50.0
            self.temperature_C = 0.0
            self.humidity = 0.0
        
    def header(self):
        return "scd4x_co2_ambient-!-ppm, scd30_co2_uncertainty-!-ppm, scd4x_temperature_ambient-!-C, scd4x_humidity_relative-!-percent"
    
    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log
        
    def printlog(self):
        print( self.log())

class Null_scd4x_CO2_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.temperature_C = None
        self.humidity = None
        self.co2_ppm = None
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
