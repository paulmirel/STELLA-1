# bme280 module
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

def initialize_bme280_air_sensor( instrument ):
    bme280_air_sensor = Null_bme280_Air_Sensor()
    try:
        bme280_air_sensor = bme280_Air_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_bme280_air_sensor" )
        instrument.sensors_present.append( bme280_air_sensor )
    except Exception as err:
        pass
        #print("bme280 failed: {}".format(err))
    return bme280_air_sensor

class bme280_Air_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "bme280_air_sensor", pn = "bme280", address = 0x77, swob = adafruit_bme280.Adafruit_BME280_I2C( com_bus ))
        self.temperature_C = None
        self.pressure = None
        self.altitude = None
        self.humidity = None
    def read(self):
        self.temperature_C = self.swob.temperature
        self.pressure = self.swob.pressure
        self.humidity = self.swob.relative_humidity
        self.altitude = self.swob.altitude
        #print( self.altitude )
        # TBD calculate dewpoint, but do that in an auxilliary function, because I'll have many sources of T and RH
        # TD: =243.04*(LN(RH/100)+((17.625*T)/(243.04+T)))/(17.625-LN(RH/100)-((17.625*T)/(243.04+T)))
        # from https://bmcnoldy.earth.miami.edu/Humidity.html
        #self.dewpoint = 0 #self.temperature -((100-self.humidity)/5) #update this to the formula above.
        #self.dp_uncty = 3.2
    def log(self):
        # name, units, value, +/-, uncertainty ## per datasheet
        return "{}, {}, {}, {}".format( self.pressure, round(self.altitude, 3), round(self.humidity, 1), round(self.temperature_C, 3) )
    def printlog(self):
        print( self.log())
    def header(self):
        return( "bme280_barometric_pressure-!-hPa, bme280_altitude_relative-!-m, bme280_humidity_relative-!-percent, bme280_temperature_ambient-!-C" )

class Null_bme280_Air_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.swob = None
        self.temperature_C = None
        self.pressure = None
        self.altitude = None
        self.humidity = None
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
