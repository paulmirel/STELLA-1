# ads1015 module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import adafruit_ads1x15.ads1015 as ADS1015
from adafruit_ads1x15.analog_in import AnalogIn as ADS1x15_AnalogIn
from .classm_device import Device


def initialize_ads1015_12_bit_adc( instrument ):
    ads1015_12_bit_adc = Null_ads1015_12_Bit_ADC()
    try:
        ads1015_12_bit_adc = ads1015_12_Bit_ADC( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_ads1015_12_bit_adc" )
        instrument.sensors_present.append( ads1015_12_bit_adc )
    except Exception as err:
        print( "failed to initialize_ads1015_12_bit_adc: ", err )
        pass
    return ads1015_12_bit_adc

class ads1015_12_Bit_ADC( Device ):
    #https://learn.adafruit.com/adafruit-4-channel-adc-breakouts/python-circuitpython
    def __init__( self, com_bus ):
        super().__init__(name = "adc_12_bit", pn = "ads1015", address = 0x48, swob = ADS1015.ADS1015( com_bus ))
        self.channel_0 = ADS1x15_AnalogIn(self.swob, ADS1015.P0)
        self.channel_1 = ADS1x15_AnalogIn(self.swob, ADS1015.P1)
        self.channel_2 = ADS1x15_AnalogIn(self.swob, ADS1015.P2)
        self.channel_3 = ADS1x15_AnalogIn(self.swob, ADS1015.P3)
        self.parameters = [ "gain", "ch0_counts", "ch0_volts", "ch1_counts", "ch1_volts","ch2_counts", "ch2_volts","ch3_counts", "ch3_volts"]
        self.values = [0,0,0,0,0,0,0,0,0]
        # set up a differential channel like this self.channel_0-1 = ADS1x15_AnalogIn(swob, ADS1015.P0, ADS1015.P1)
        # self.swob.instrument_mode = self.Mode.SINGLE # this is the default instrument_mode. I don't know where to find Mode. Waits for completed conversion to read the value TBD implement this.
        # Mode.CONTINUOUS # read the latest value that's been converted. TBD look into this and explain
        self.gain_number = 5
        self.gain_list = [0.666667, 1, 2, 4, 8, 16]
        self.swob.gain = self.gain_list[self.gain_number]
        # gain:
        # setting, full scale voltage
        # 2/3 (how do we enter a fraction?), +/- 6.144V
        # 1, +/- 4.096V
        # 2, +/- 2.048V
        # 4, +/- 1.024V
        # 8, +/- 0.512V
        # 16, +/- 0.256V
    def found(self):
        print("found", self.pn, self.swob)
    def read(self):
        # reports 16 bit values even though the conversion is only 12 bits. Least significant four bits (LSBs) should all be 0
        self.raw = [self.channel_0.value, self.channel_1.value, self.channel_2.value, self.channel_3.value]
        #print( self.raw )
        self.voltage = [self.channel_0.voltage, self.channel_1.voltage, self.channel_2.voltage, self.channel_3.voltage]
        self.values = []
        self.values.append( self.swob.gain ) #lookup gain
        for index in range (0, len(self.raw)):
            self.values.append( self.raw[index] )
            self.values.append( round(self.voltage[index],3) )

    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log

    def printlog(self):
        print( self.log())

class Null_ads1015_12_Bit_ADC(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def found( self ):
        pass
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
