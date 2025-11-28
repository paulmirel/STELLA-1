# ultrasonic rangefinder module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

from .classm_device import Device

def initialize_lv_ez_mb1013_rangefinder( instrument, analog_in_0, sense_5V ):
    lv_ez_mb1013_rangefinder = Null_Lv_ez_mb1013_Rangefinder()
    try:
        lv_ez_mb1013_rangefinder = Lv_ez_mb1013_Rangefinder( analog_in_0, sense_5V )
        instrument.sensors_present.append( lv_ez_mb1013_rangefinder )
    except Exception as err:
        pass
        #print( "error:", err )
    return lv_ez_mb1013_rangefinder

class Lv_ez_mb1013_Rangefinder( Device ):
    def __init__( self, analog_in_0, sense_5V):
        super().__init__(name = "lv_ez_mb1013_rangefinder", pn = "lv_ez_mb1013", address = 0x00, swob = True)
        self.range_m = None
        self.analog_in_0 = analog_in_0
        self.sense_5V = sense_5V
        self.parameters = []
        self.values = []
    def read(self):
        supply_v = 2 * (self.sense_5V.value * 3.3) / 65536
        range_m =self.analog_in_0.value * 8.312 / 100000 - 0.05 # offset
        self.range_m = round(range_m, 3)
    
    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log
    
    def header(self):
        return "analog_input_0_digital_number-!-counts, hrlv-ez-mb1013_range-!-m"

class Null_Lv_ez_mb1013_Rangefinder(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.range_m = None
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
