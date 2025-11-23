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
        super().__init__(name = "ads1015_12_bit_adc", pn = "ads1015", address = 0x48, swob = ADS1015.ADS1015( com_bus ))
        self.channel_0 = ADS1x15_AnalogIn(self.swob, ADS1015.P0)
        self.channel_1 = ADS1x15_AnalogIn(self.swob, ADS1015.P1)
        self.channel_2 = ADS1x15_AnalogIn(self.swob, ADS1015.P2)
        self.channel_3 = ADS1x15_AnalogIn(self.swob, ADS1015.P3)
        # set up a differential channel like this self.channel_0-1 = ADS1x15_AnalogIn(swob, ADS1015.P0, ADS1015.P1)
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
    def found(self):
        print("found", self.pn, self.swob)
    def read(self):
        # reports 16 bit values even though the conversion is only 12 bits. Least significant four bits (LSBs) should all be 0
        self.raw = (self.channel_0.value, self.channel_1.value, self.channel_2.value, self.channel_3.value)
        #print( self.raw )
        self.voltage = (self.channel_0.voltage, self.channel_1.voltage, self.channel_2.voltage, self.channel_3.voltage)
        #print( self.voltage )
    def header(self):
        headers = "ads1015_channel_0_voltage-!-V, ads1015_channel_1_voltage-!-V, ads1015_channel_2_voltage-!-V, ads1015_channel_3_voltage-!-V"
        headers += ", ads1015_channel_0_digital_number-!-counts, ads1015_channel_1_digital_number-!-counts, ads1015_channel_2_digital_number-!-counts, ads1015_channel_3_digital_number-!-counts"
        headers += ", ads1015_gain-!-"
        return headers
    def log(self):
        log_values = "{}, {}, {}, {}".format( *self.voltage )
        log_values += ", {}, {}, {}, {}".format( *self.raw)
        log_values += ", {}".format(self.swob.gain)
        return log_values

    def printlog(self):
        print( self.log())

class Null_ads1015_12_Bit_ADC(Device):
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
