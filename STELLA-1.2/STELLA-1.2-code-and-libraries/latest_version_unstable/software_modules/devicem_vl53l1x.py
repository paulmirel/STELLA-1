# vl53l1x_module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

class Device: #parent class
    def __init__(self, name = None, pn = None, address = None, swob = None ):
        self.name = name
        self.swob = swob
        self.pn = pn
        self.address = address
    def report(self):
        found = False
        if self.swob is not None:
            print("report:", hex(self.address), self.pn, "\t", self.name, "found" )
            found = True
        return found
    def found(self):
        if self.swob is not None:
            return True
        else:
            return False

def initialize_vl53l1x_4m_range_sensor( instrument ):
    vl53l1x_4m_range_sensor = Null_vl53l1x_4m_Range_Sensor()
    try:
        vl53l1x_4m_range_sensor = vl53l1x_4m_Range_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_vl53l1x_4m_range_sensor" )
        instrument.sensors_present.append( vl53l1x_4m_range_sensor )
    except:
        pass
    return vl53l1x_4m_range_sensor

class vl53l1x_4m_Range_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "vl53l1x_4m_range_sensor", pn = "vl53l1x", address = 0x29, swob = adafruit_vl53l1x.VL53L1X( com_bus ))
        #self.model_id, self.module_type, self.mask_rev = self.swob.instrument_model_info
        #print("Model ID: 0x{:0X}".format(self.instrument_model_id))
        #print("Module Type: 0x{:0X}".format(self.module_type))
        #print("Mask Revision: 0x{:0X}".format(self.mask_rev))
        self.swob.start_ranging()
        self.swob.clear_interrupt()
        self.swob.distance_instrument_mode = 2 # long distance instrument_mode
        self.swob.timing_budget = 100
        self.range_m = None
    def read(self):
        if self.swob.data_ready:
            self.range_m = self.swob.distance/100 #reports in cm for whatever reason
    def header(self):
        return "vl53l1x_distance-!-m"
    def log(self):
        return "{}".format( self.range_m )
    def printlog(self):
        print( self.log())

class Null_vl53l1x_4m_Range_Sensor(Device):
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
