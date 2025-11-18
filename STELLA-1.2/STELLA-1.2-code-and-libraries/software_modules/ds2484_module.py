# ds2484 module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel


def initialize_ds2484_1_wire_thermometer( instrument ):
    ds2484_1_wire_thermometer = Null_ds2484_1_Wire_Thermometer_Reader()
    try:
        ds2484_1_wire_thermometer = ds2484_1_Wire_Thermometer_Reader( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_ds2484_1_wire_thermometer" )
        instrument.sensors_present.append( ds2484_1_wire_thermometer )
    except:
        pass
    return ds2484_1_wire_thermometer

class ds2484_1_Wire_Thermometer_Reader( Device ):
    #https://learn.adafruit.com/adafruit-ds2484-i2c-to-1-wire-bus-adapter-breakout/circuitpython-and-python
    def __init__( self, com_bus ):
        super().__init__(name = "ds2484_1_wire_thermometer", pn = "ds2484", address = 0x18, swob = Adafruit_DS248x( com_bus ))
        self.rom = bytearray(8)
        if not self.swob.onewire_search(self.rom):
            pass
            #print( "no 1-wire thermometers found" )
    def read(self):
        self.temperature_C = self.swob.ds18b20_temperature(self.rom)
        #print( self.temperature_C )
    def header(self):
        return "ds2484_temperature_material-!-C"
    def log(self):
        return "{}".format( round(self.temperature_C,1))
    def printlog(self):
        print( self.log())

class Null_ds2484_1_Wire_Thermometer_Reader(Device):
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
