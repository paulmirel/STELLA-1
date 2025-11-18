import rotaryio
import busio
import board
import digitalio
import time


pushbutton = digitalio.DigitalInOut( board.A2 )
pushbutton.direction = digitalio.Direction.INPUT
pushbutton.pull = digitalio.Pull.UP

encoder = rotaryio.IncrementalEncoder(board.A4, board.A3)

print( "\ntesting rotary encoder. give it a twist or push." )

last_position = None
while True:
    position = encoder.position
    if last_position is None or position != last_position:
        print(position)
    last_position = position
    if pushbutton.value == True:
        pass
    else:
        print ("pushed")
        time.sleep(0.2)

