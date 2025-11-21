# mlx90614 module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import adafruit_mlx90614

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
            
            
            
def initialize_mlx90614_surface_thermometer( instrument ):
    mlx90614_surface_thermometer = Null_mlx90614_Surface_Thermometer()
    try:
        mlx90614_surface_thermometer = mlx90614_Surface_Thermometer( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_mlx90614_surface_thermometer" )
        instrument.sensors_present.append( mlx90614_surface_thermometer )
    except:
        pass
    return mlx90614_surface_thermometer

class mlx90614_Surface_Thermometer( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "mlx90614_surface_thermometer", pn = "mlx90614", address = 0x5A, swob = adafruit_mlx90614.MLX90614( com_bus ))
        self.surface_temperature_C = 0
        self.ambient_temperature_C = 0
    def read(self):
        self.surface_temperature_C = self.swob.object_temperature
        self.ambient_temperature_C = self.swob.ambient_temperature
    def header(self):
        return "mlx90614_temperature_surface-!-C, mlx90614_temperature_local-!-C"
    def log(self):
        return "{}, {}".format( round(self.surface_temperature_C,1), round(self.ambient_temperature_C,1) )
    def printlog(self):
        print( self.log())

class Null_mlx90614_Surface_Thermometer(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.surface_temperature_C = 0
        self.ambient_temperature_C = 0
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
