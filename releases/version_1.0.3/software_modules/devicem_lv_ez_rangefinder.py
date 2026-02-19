# lv_ez_rangefinder module
# version 1.0
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel


import analogio
from .classm_device import Device

def initialize( instrument, analog_in_0, supply_5V ):
    lv_ez_rangefinder = False
    try:
        lv_ez_rangefinder = Lv_ez_Rangefinder( analog_in_0, supply_5V )
        instrument.welcome_page.announce( "initialize_lv_ez_rangefinder" )
        instrument.sensors_present.append( lv_ez_rangefinder )
    except Exception as err:
        pass
        print( "error:", err )
    return lv_ez_rangefinder

class Lv_ez_Rangefinder( Device ):
    def __init__( self, analog_in_0, supply_5V):
        super().__init__(name = "rangefinder", pn = "lv_ez_mb1013", address = 0x00, swob = True)
        self.range_m = None
        self.analog_in_0 = analog_in_0
        self.supply_5V = supply_5V
        self.parameters = ["range_m"]
        self.values = [0]
    def read(self):
        supply_v = self.supply_5V.voltage
        range_m = self.analog_in_0.value * 8.312 / 100000 - 0.05 # offset
        self.range_m = round(range_m, 3)
        self.values[0] = self.range_m

        if self.range_m < 0.3:
            self.range_text = "<0.3m"
        elif self.range_m > 2.5:
            self.range_text = ">2.5m"
        else:
            self.range_text = "{}m".format(round(self.range_m,2))

    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log
    def printlog(self):
        print( self.log())

