import busio
import board
import digitalio

import time

pushbutton = digitalio.DigitalInOut( board.D12 )
pushbutton.direction = digitalio.Direction.INPUT
pushbutton.pull = digitalio.Pull.UP

TOUCH_TIME_CONSTANT_S = 0.100 # secs, time it takes the button to "cycle"

print( "Ready: push record/pause button to test it" )

press_state = 0
last_press_state = 0
number_of_modes = 2
mode = 0
while True:
    press_state = 0
    #print("pushbutton == {}".format(pushbutton.value))
    while pushbutton.value:
        press_state = 1
    if not pushbutton.value and (press_state == 1):
        print("Hey, pushbutton was pressed!")
        mode = (mode + 1) % number_of_modes
        print("Mode == ", mode)
    last_press_state = press_state
    time.sleep( TOUCH_TIME_CONSTANT_S )


