# scd30 module
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
        super().__init__(name = "scd30_CO2_sensor", pn = "scd30", address = 0x61, swob = adafruit_scd30.SCD30(com_bus))
        self.temperature_C = None
        self.humidity = None
        self.co2_ppm = None
        self.co2_ppm_uncertainty = None
    def read(self):
        if self.swob.data_available:
            self.temperature_C = self.swob.temperature
            self.humidity = self.swob.relative_humidity
            self.co2_ppm = self.swob.CO2
            self.co2_ppm_uncertainty = 30 + self.co2_ppm * 0.03
    def header(self):
        return "scd30_co2_ambient-!-ppm, scd30_co2_uncertainty-!-ppm, scd30_temperature_ambient-!-C, scd30_humidity_relative-!-percent"
    def log(self):
        return "{}, {}, {}, {}".format( round (self.co2_ppm, 1), round(self.co2_ppm_uncertainty, 1), round(self.temperature_C, 1) , int(round(self.humidity, 0)))
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
