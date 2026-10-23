# rotary encoder module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import rotaryio
import digitalio
import time
from .classm_device import Device
            
def increment_select( page ):
    select_value = (page.select_value + encoder_move) % page.number_of_select_positions

def initialize_rotary_encoder( pin_a, pin_b, pin_button ):
    encoder = Null_Rotary_Encoder()
    try:
        encoder = Rotary_Encoder( pin_a, pin_b, pin_button )
    except Exception as err:
        print( "encoder failed: {}".format(err))
    return encoder

class Rotary_Encoder( Device ):
    def __init__( self, pin_a, pin_b, pin_button ):
        super().__init__(name = "rotary_encoder", pn = "encoder", address = 00, swob = rotaryio.IncrementalEncoder( pin_b, pin_a ))
        self.button = digitalio.DigitalInOut( pin_button )
        self.button.direction = digitalio.Direction.INPUT
        self.button.pull = digitalio.Pull.UP
        self.button_pressed = False
        self.button_last_pressed = False
        self.encoder_flag = False
        self.button_flag = False
        self.last_position = None
        self.last_value = 0
        self.last_button_read = time.monotonic()
        self.button_cycle_time_s = 0
        self.slowest_button_cycle_time_s = 0
    def read_encoder(self):
        try:
            self.position = self.swob.position
            if not self.encoder_flag:
                if self.last_position is not None and self.position != self.last_position:
                    self.last_value = self.position - self.last_position
                    if self.last_value > 1:
                        self.last_value = 1
                    if self.last_value < -1:
                        self.last_value = -1
                    if self.last_value != 0:
                        self.encoder_flag = True
                self.last_position = self.position
        except Exception as err:
            print( err )
    def read_button(self):
        self.last_button_read = time.monotonic()
        try:
            self.button_pressed = not self.button.value
            if self.button_pressed:
                if self.button_last_pressed:
                    pass
                else:
                    self.button_flag = True
                self.button_last_pressed = True
            else:
                self.button_last_pressed = False
        except Exception as err:
            print( err )
    def log(self):
        pass
    def printlog(self):
        pass

class Null_Rotary_Encoder(Device):
    def __init__( self ):
        self.swob = None
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        print( "encoder failed to initialize" )
    def printlog(self):
        pass

