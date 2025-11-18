# soil capacitance module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

def initialize_capacitive_soil_moisture_sensor( instrument ):
    capacitive_soil_moisture_sensor = Null_Capacitive_Soil_Moisture_Sensor()
    try:
        capacitive_soil_moisture_sensor = Capacitive_Soil_Moisture_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_capacitive_soil_moisture_sensor" )
        instrument.sensors_present.append( capacitive_soil_moisture_sensor )
    except:
        pass
    return capacitive_soil_moisture_sensor

class Capacitive_Soil_Moisture_Sensor( Device ):
    # https://learn.adafruit.com/adafruit-stemma-soil-sensor-i2c-capacitive-moisture-sensor/python-circuitpython-test
    def __init__( self, com_bus ):
        super().__init__(name = "capacitive_soil_moisture_sensor", pn = "cap_sm", address = 0x37, swob = Seesaw(com_bus, addr=0x37))
    def read(self):
        self.soil_capacitance = self.swob.moisture_read()
        #print( self.soil_capacitance )
    def header(self):
        return "capacitive_soil_moisture_signal-!-"
    def log(self):
        return "{}".format( self.soil_capacitance )
    def printlog(self):
        print( self.log())

class Null_Capacitive_Soil_Moisture_Sensor(Device):
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
