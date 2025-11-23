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
        super().__init__(name = "battery_monitor", pn = "max1704x", address = 0x36, swob = adafruit_max1704x.MAX17048( instrument.i2c_bus ))
        self.voltage = self.swob.cell_voltage
        self.percentage = round(self.swob.cell_percent, 1)
        self.instrument.welcome_page.announce( "initialize_battery_monitor" )
        #self.instrument.sensors_present.append( battery_monitor )
    def read(self):
        self.voltage = self.swob.cell_voltage
        self.percentage = round(self.swob.cell_percent, 1)
        #print( self.percentage )
    def header(self):
        return "max1704x_battery_voltage-!-V, max1704x_battery_energy-!-percent"
    def log(self):
        return "{}, {}".format( self.voltage, self.percentage )
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
