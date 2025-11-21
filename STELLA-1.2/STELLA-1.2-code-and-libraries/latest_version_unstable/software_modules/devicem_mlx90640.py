# mlx90640 module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import adafruit_mlx90640

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
            
def initialize_mlx90640_thermal_camera( instrument ):
    mlx90640_thermal_camera = Null_mlx90640_Thermal_Camera()
    try:
        mlx90640_thermal_camera = mlx90640_Thermal_Camera( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_mlx90640_thermal_camera" )
        instrument.sensors_present.append( mlx90640_thermal_camera )
    except:
        pass
    return mlx90640_thermal_camera

class mlx90640_Thermal_Camera( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "mlx90640_thermal_camera", pn = "mlx90640", address = 0x33, swob = adafruit_mlx90640.MLX90640( com_bus ))
        # TBD self.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
        # TBD self.refresh_rate = self.swob.RefreshRate.REFRESH_4_HZ
    def read(self):
        pass
        #self.t_surface_C = self.swob.object_temperature
    def header(self):
        return ""
    def log(self):
        pass
        #return "{}".format( self.t_surface_C )
    def printlog(self):
        print( self.log())

class Null_mlx90640_Thermal_Camera(Device):
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
