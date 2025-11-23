# focaltouch module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel
import adafruit_focaltouch
from /classm_device import Device

            
def initialize_touch_screen( bus ):
    touch_screen = Null_Touch_Screen()
    try:
        touch_screen = Focal_Touch_Screen( bus )
    except Exception as err:
        print( "touch screen fail: {}".format(err))
    return touch_screen

class Focal_Touch_Screen( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "touch_screen", pn = "FocalTouch", address = 0x38, swob = adafruit_focaltouch.Adafruit_FocalTouch(com_bus, debug=False))
        self.flag = False
    def read(self):
        try:
            self.is_touched = self.swob.touched
            if self.is_touched:
                #print( "touched" )
                self.dict = self.swob.touches
                self.tx = 320 - self.dict[0]['y'] #transform
                self.ty = self.dict[0]['x'] #transform
        except Exception as err:
            print( err )
    def log(self):
        pass
    def printlog(self):
        print( self.log())

class Null_Touch_Screen(Device):
    def __init__( self ):
        self.swob = None
        self.is_touched = False
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
