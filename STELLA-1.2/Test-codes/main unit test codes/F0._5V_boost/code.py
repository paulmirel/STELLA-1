import time
import board
import digitalio
import analogio

# connect the battery to get consistent 5V output.
# connect a 1k resistor from 5V output to GND to bleed off the boost capacitor

try:
    enable_5V = digitalio.DigitalInOut( board.D10 )
    enable_5V.direction = digitalio.Direction.OUTPUT
    enable_5V.value = True #active low, True is off
    monitor_5V = analogio.AnalogIn( board.A1)
    print( "initialized" )
except:
    print( "Error: 5V pins init failed" )

def get_voltage(pin):
    return (pin.value * 3.3) / 65536 * 2

index = 0
while True:
    enable_5V.value = True
    time.sleep(0.2)
    print( "5V ON: voltage on the 5V line = ", get_voltage(monitor_5V))
    print( "loop count {}".format(index) )
    index += 1
    time.sleep( 2 )
    enable_5V.value = False
    time.sleep( 2 )
    print( "5V OFF: voltage on the 5V line = ", get_voltage(monitor_5V))
