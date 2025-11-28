# ads1115 module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel
 
### connect ADDR to SDA to set address
import adafruit_ads1x15.ads1115 as ADS1115
from adafruit_ads1x15.analog_in import AnalogIn as ADS1x15_AnalogIn
from .classm_device import Device

def initialize_ads1115_16_bit_adc( instrument ):
    ads1115_16_bit_adc = Null_ads1115_16_Bit_ADC()
    try:
        ads1115_16_bit_adc = ads1115_16_Bit_ADC( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_ads1115_16_bit_adc" )
        instrument.sensors_present.append( ads1115_16_bit_adc )
    except Exception as err:
        #print( err )
        pass
    return ads1115_16_bit_adc

class ads1115_16_Bit_ADC( Device ):
    # to prevent address collision, connect SDA to ADDR to set the address to 0x4a
    # https://learn.adafruit.com/adafruit-4-channel-adc-breakouts/python-circuitpython
    def __init__( self, com_bus ):
        super().__init__(name = "ads1115_16_bit_adc", pn = "ads1115", address = 0x4a, swob = ADS1115.ADS1115( com_bus, address = 0x4a ))
        self.channel_0 = ADS1x15_AnalogIn(self.swob, ADS1115.P0)
        self.channel_1 = ADS1x15_AnalogIn(self.swob, ADS1115.P1)
        self.channel_2 = ADS1x15_AnalogIn(self.swob, ADS1115.P2)
        self.channel_3 = ADS1x15_AnalogIn(self.swob, ADS1115.P3)
        # set up a differential channel like this self.channel_0-1 = ADS1x15_AnalogIn(swob, ADS1115.P0, ADS1115.P1)
        # self.swob.instrument_mode = self.Mode.SINGLE # this is the default instrument_mode. I don't know where to find Mode. Waits for completed conversion to read the value TBD implement this.
        # Mode.CONTINUOUS # read the latest value that's been converted. TBD look into this and explain
        self.swob.gain = 1
        # gain:
        # setting, full scale voltage
        # 2/3 (how do we enter a fraction?), +/- 6.144V
        # 1, +/- 4.096V
        # 2, +/- 2.048V
        # 4, +/- 1.024V
        # 8, +/- 0.512V
        # 16, +/- 0.256V
        self.parameters = []
        self.values = []
    def found(self):
        print("found", self.pn, self.swob)
    def read(self):
        self.raw = (self.channel_0.value, self.channel_1.value, self.channel_2.value, self.channel_3.value)
        #print( self.raw )
        self.voltage = (self.channel_0.voltage, self.channel_1.voltage, self.channel_2.voltage, self.channel_3.voltage)
        #print( self.voltage )
    
    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log
    def printlog(self):
        print( self.log())

class Null_ads1115_16_Bit_ADC(Device):
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
