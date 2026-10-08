# neopixel module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import neopixel

BLUE = ( 0, 0, 255 )
GREEN = ( 255, 0, 0 )
YELLOW = ( 127, 255, 0 )
WHITE = ( 100, 100, 100 )
RED = ( 0, 255, 0 )
OFF = ( 0, 0, 0 )

def initialize_neopixel( pin ):
    try:
        num_pixels = 1
        ORDER = neopixel.RGB
        neopixel_instance = neopixel.NeoPixel( pin, num_pixels, brightness=0.3, auto_write=True, pixel_order=ORDER )
        print( "neopixel initialized" )
    except Exception as err:
        neopixel_instance = False
        print( "neopixel failed to initialize:", err )
    return neopixel_instance
