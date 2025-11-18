import time
import board
import analogio

analog_input_A0 = analogio.AnalogIn( board.A0)

index = 0
while True:
    print( "loop count {}".format(index) )
    index += 1
    print( "Analog Input reading in counts, should be 0< counts <65535: ", analog_input_A0.value )
    time.sleep( 2 )
