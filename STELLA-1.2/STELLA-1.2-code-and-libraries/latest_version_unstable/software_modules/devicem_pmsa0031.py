# pmsa0031 module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

from adafruit_pm25.i2c import PM25_I2C
from .classm_device import Device
            

def initialize_pmsa0031_particulates_sensor( instrument ):
    pmsa0031_particulates_sensor = Null_pmsa0031_Particulates_Sensor()
    try:
        pmsa0031_particulates_sensor = pmsa0031_Particulates_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_pmsa0031_particulates_sensor" )
        instrument.sensors_present.append( pmsa0031_particulates_sensor )
    except Exception as err:
        pass
        #print( "pmsa0031 particulates sensor fail: {}".format(err))
    return pmsa0031_particulates_sensor

class pmsa0031_Particulates_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "pmsa0031_particulates_sensor", pn = "pmsa0031", address = 0x12, swob = PM25_I2C( com_bus, reset_pin = None ))
        self.pm100 = None
        self.pm25 = None
        self.ratio = None
        self.parameters = []
        self.values = []
    def read(self):
        try:
            self.data = self.swob.read()
        except RuntimeError as err:
            self.data = None
            print( err )
        #if self.data is not None:
        #self.aqip = calculate_aqi_p( self.data["pm25 standard"], self.data["pm100 standard"] )
        self.pm25 = self.data["pm25 standard"]
        self.pm100 = self.data["pm100 standard"]
    def header(self):
        headers = "pmsa0031_pm2.5_over_pm10_ratio-!-, pmsa0031_pm1-!-ug_per_m_cubed"
        headers += ", pmsa0031_pm2.5-!-ug_per_m_cubed, pmsa0031_pm10-!-ug_per_m_cubed, pmsa0031_particle_count_0.3m-!-count_per_100mL"
        headers += ", pmsa0031_particle_count_0.5m-!-count_per_100mL, pmsa0031_particle_count_1m-!-count_per_100mL, pmsa0031_particle_count_2.5m-!-count_per_100mL"
        headers += ", pmsa0031_particle_count_5m-!-count_per_100mL, pmsa0031_particle_count_10m-!-count_per_100mL"
        return headers
    def obsolete_log(self):
        if self.data["pm100 standard"] > 0:
            self.ratio = round(self.data["pm25 standard"]/self.data["pm100 standard"], 2)
        else:
            self.ratio = 1
        self.datastring = "{}, {}, {}, {}, {}, {}, {}, {}, {}, {}".format(
                self.ratio,
                self.data["pm10 standard"],
                self.data["pm25 standard"],
                self.data["pm100 standard"],
                self.data["particles 03um"],
                self.data["particles 05um"],
                self.data["particles 10um"],
                self.data["particles 25um"],
                self.data["particles 50um"],
                self.data["particles 100um"])
        return self.datastring
    
    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log
    
    def printlog(self):
        print( self.log())

class Null_pmsa0031_Particulates_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.pm100 = None
        self.pm25 = None
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
