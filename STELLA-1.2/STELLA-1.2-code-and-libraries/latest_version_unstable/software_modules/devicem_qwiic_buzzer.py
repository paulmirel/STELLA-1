# qwiic buzzer module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import qwiic_buzzer
from .classm_device import Device

def initialize_qwiic_buzzer( i2c_bus ):
    buzzer = Null_Qwiic_Buzzer()
    try:
        buzzer = Qwiic_Buzzer( i2c_bus )
    except Exception as err:
        print( "buzzer failed to initialize: {}".format(err) )
        pass
    return buzzer

class Qwiic_Buzzer( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "qwiic_buzzer", pn = "BOB-24474", address = 0x34, swob = qwiic_buzzer.QwiicBuzzer(i2c_driver = com_bus))
        self.swob.configure( self.swob.VOLUME_MAX )
        self.mute = False
    def read(self):
        pass
    def beep(self):
        if self.mute:
            pass
        else:
            self.set(932, 130) # frequency in Hz, time in ms. 932 Hz is B flat in octave 5. Fairly pleasant through this piezo driver, though maybe a bit medical in tone.
            self.swob.on()
    def click(self):
        if self.mute:
            pass
        else:
            self.set(800, 12)
            self.swob.on()
    def stop(self):
        self.swob.off()
    def set(self, frequency_hz, time_ms ):
        self.swob.configure( frequency_hz, time_ms )
    def header(self):
        return ""
    def log(self):
        return ""
    def printlog(self):
        print( self.log())

class Null_Qwiic_Buzzer(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def beep(self):
        pass
    def stop(self):
        pass
    def set(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass
