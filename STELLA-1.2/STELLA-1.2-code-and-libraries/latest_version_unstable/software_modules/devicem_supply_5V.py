# supply_5V module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import board
import digitalio
from analogio import AnalogIn
from .classm_device import Device


def initialize_supply_5V( instrument ):
    supply_5V = Null_Supply_5V()
    try:
        supply_5V = Supply_5V()
        instrument.welcome_page.announce( "initialize_supply_5V" )
        instrument.sensors_present.append( supply_5V )
    except Exception as err:
        pass
    return supply_5V

class Supply_5V( Device ):
    def __init__( self ):
        super().__init__(name = "supply_5V", pn = "tps61023")
        self.enable_5V = digitalio.DigitalInOut( board.D10 )
        self.enable_5V.direction = digitalio.Direction.OUTPUT
        self.enable_5V.value = False
        self.voltage = 0
        self.pin = AnalogIn(board.A1)
        self.parameters = [ "counts", "voltage" ]
        self.values = [0,0]
    def read(self):
        field_cal_slope = 1
        field_cal_offset = 0.000
        self.counts = self.pin.value
        self.voltage = round((2 * (self.counts * 3.3) / 65536)*field_cal_slope-field_cal_offset,2)
        self.values[0] = self.counts
        self.values[1] = self.voltage
    def enable(self):
        self.enable_5V.value = True
    def disable(self):
        self.enable_5V.value = False
    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log
    def printlog(self):
        print( self.log())



    '''
    sense_5V = AnalogIn(board.A1)
    analog_in_0 = AnalogIn(board.A0)
    if mlx90614_surface_thermometer.pn and as7265x_spectrometer.pn:
        lv_ez_mb1013_rangefinder = initialize_lv_ez_mb1013_rangefinder( instrument, analog_in_0, sense_5V )
    else:
        lv_ez_mb1013_rangefinder = False
    #plus_5v_supply = False #TBD make a device object with digital out and analog in, check it for rising and falling

    # plus_5v_supply.enable(), .read(), .log(), .enable()
    '''

class Null_Supply_5V(Device):
    def __init__( self ):
        super().__init__(name = None, pn = None)
    def read(self):
        pass
    def read(self, value):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass
