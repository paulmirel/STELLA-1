# pcf8591 module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

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
        super().__init__(name = "pcf8591_8_bit_adc_dac", pn = "pcf8591", address = 0x4f, swob = PCF8591.PCF8591( com_bus, address = 0x4f ))
        self.raw_0 = None
        self.raw_1 = None
        self.raw_2 = None
        self.raw_3 = None
        self.voltage_0 = None
        self.voltage_1 = None
        self.voltage_2 = None
        self.voltage_3 = None
    def read(self):
        self.raw_0 = PCF8591_AnalogIn(self.swob, PCF8591.A0).value
        self.raw_1 = PCF8591_AnalogIn(self.swob, PCF8591.A1).value
        self.raw_2 = PCF8591_AnalogIn(self.swob, PCF8591.A2).value
        self.raw_3 = PCF8591_AnalogIn(self.swob, PCF8591.A3).value
        self.voltage_0 = (self.raw_0/ 65535) * 3.3
        self.voltage_1 = (self.raw_1/ 65535) * 3.3
        self.voltage_2 = (self.raw_2/ 65535) * 3.3
        self.voltage_3 = (self.raw_3/ 65535) * 3.3
    def set(self, value):
        PCF8591_AnalogOut(self.swob, PCF8591.OUT).value = value #32767 max
    def header(self):
        headers = "pcf8591_channel_0_digital_number-!-counts, pcf8591_channel_1_digital_number-!-counts, pcf8591_channel_2_digital_number-!-counts, pcf8591_channel_3_digital_number-!-counts"
        headers += ", pcf8591_channel_0_voltage-!-V, pcf8591_channel_1_voltage-!-V, pcf8591_channel_2_voltage-!-V, pcf8591_channel_3_voltage-!-V"
        return headers
    def log(self):
        return "{}, {}, {}, {}, {}, {}, {}, {}".format( self.raw_0, self.raw_1, self.raw_2, self.raw_3, self.voltage_0, self.voltage_1, self.voltage_2, self.voltage_3 )
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
