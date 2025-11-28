# max1704x module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import adafruit_max1704x
from .classm_device import Device

            
def initialize_battery_monitor( instrument ):
    battery_monitor = Null_Battery_Monitor()
    try:
        battery_monitor = max1704x_Battery_Monitor( instrument )
        instrument.welcome_page.announce( "initialize_battery_monitor" )
        instrument.sensors_present.append( battery_monitor )
    except Exception as err:
        print( "failed to initialize_battery_monitor: ", err)
        pass
    return battery_monitor

class max1704x_Battery_Monitor( Device ):
    def __init__( self, instrument ):
        self.instrument = instrument
        super().__init__(name = "battery", pn = "max1704x", address = 0x36, swob = adafruit_max1704x.MAX17048( instrument.i2c_bus ))
        self.voltage = self.swob.cell_voltage
        self.percentage = round(self.swob.cell_percent, 1)
        self.instrument.welcome_page.announce( "initialize_battery_monitor" )
        #self.instrument.sensors_present.append( battery_monitor )
        self.parameters = ["voltage_volts", "energy_percent"]
        self.values = []
    def read(self):
        self.voltage = self.swob.cell_voltage
        self.percentage = round(self.swob.cell_percent, 1)
        self.values = [self.voltage, self.percentage]
        #print( self.percentage )
    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log
    def printlog(self):
        print( self.log())

class Null_Battery_Monitor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        self.voltage = 0
        self.percentage = 0
    def log(self):
        return "{}, {}".format( self.voltage, self.percentage )
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass
