# pcf8591 module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import adafruit_pcf8591.pcf8591 as PCF8591
from adafruit_pcf8591.analog_in import AnalogIn as PCF8591_AnalogIn
from adafruit_pcf8591.analog_out import AnalogOut as PCF8591_AnalogOut
from .classm_device import Device

def initialize_pcf8591_8_bit_adc_dac( instrument ):
    pcf8591_8_bit_adc_dac = Null_pcf8591_8_Bit_ADC_DAC()
    try:
        pcf8591_8_bit_adc_dac = pcf8591_8_Bit_ADC_DAC( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_pcf8591_8_bit_adc_dac" )
        instrument.sensors_present.append( pcf8591_8_bit_adc_dac )
    except Exception as err:
        pass
    return pcf8591_8_bit_adc_dac

class pcf8591_8_Bit_ADC_DAC( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "adc_dac_8_bits", pn = "pcf8591", address = 0x4f, swob = PCF8591.PCF8591( com_bus, address = 0x4f ))
        self.raw_0 = None
        self.raw_1 = None
        self.raw_2 = None
        self.raw_3 = None
        self.voltage_0 = None
        self.voltage_1 = None
        self.voltage_2 = None
        self.voltage_3 = None
        self.output_value = 0
        self.parameters = [ "output_counts", "ch0_counts", "ch0_volts", "ch1_counts", "ch1_volts","ch2_counts", "ch2_volts","ch3_counts", "ch3_volts"]
        self.values = [0,0,0,0,0,0,0,0,0]
    def read(self):
        self.raw_0 = PCF8591_AnalogIn(self.swob, PCF8591.A0).value >> 8
        self.raw_1 = PCF8591_AnalogIn(self.swob, PCF8591.A1).value >> 8
        self.raw_2 = PCF8591_AnalogIn(self.swob, PCF8591.A2).value >> 8
        self.raw_3 = PCF8591_AnalogIn(self.swob, PCF8591.A3).value >> 8
        self.voltage_0 = round((self.raw_0/ 256) * 3.3,2)
        self.voltage_1 = round((self.raw_1/ 256) * 3.3,2)
        self.voltage_2 = round((self.raw_2/ 256) * 3.3,2)
        self.voltage_3 = round((self.raw_3/ 256) * 3.3,2)
        self.values = [ self.output_value, self.raw_0, self.voltage_0, self.raw_1, self.voltage_1, self.raw_2, self.voltage_2, self.raw_3, self.voltage_3 ]
    def set(self, output_value):
        self.output_value = output_value
        PCF8591_AnalogOut(self.swob, PCF8591.OUT).value = self.output_value #32767 max
    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log
    def printlog(self):
        print( self.log())

class Null_pcf8591_8_Bit_ADC_DAC(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
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
