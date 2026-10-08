# scd30 module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import adafruit_scd30
from .classm_device import Device

def initialize_scd30_CO2_sensor( instrument ):
    scd30_CO2_sensor = Null_scd30_CO2_Sensor()
    try:
        scd30_CO2_sensor = scd30_CO2_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_scd30_CO2_sensor" )
        instrument.sensors_present.append( scd30_CO2_sensor )
    except:
        pass
    return scd30_CO2_sensor

class scd30_CO2_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "CO2", pn = "scd30", address = 0x61, swob = adafruit_scd30.SCD30(com_bus))
        self.temperature_C = None
        self.humidity = None
        self.co2_ppm = None
        self.co2_ppm_uncertainty = None
        self.parameters = [ "CO2_ppm", "+_-_ppm", "temperature_C", "humidity_pct" ]
        self.values = [0,0,0,0]
    def read(self):
         if self.swob.CO2 is not None:
            self.temperature_C = int(round(self.swob.temperature, 0))
            self.humidity = int(round(self.swob.relative_humidity, 0))
            self.co2_ppm = int(round(self.swob.CO2,0))
            self.co2_uncty_ppm = int(round(30 + self.co2_ppm * 0.03, 0))
            self.values = [self.co2_ppm, self.co2_uncty_ppm, self.temperature_C, self.humidity]

    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log

    def printlog(self):
        print( self.log())

class Null_scd30_CO2_Sensor(Device):
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
