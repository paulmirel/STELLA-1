SOFTWARE_VERSION_NUMBER = "0.0.2"
DEVICE_TYPE = "STELLA-Appetizer"
# copyright NASA under MIT open source software license
# author Paul Mirel

# hardware:
# Adafruit QTpy RP2040
# SparkFun Qwiic LED stick
# Adafruit Gamepad
# 2x qwiic/stemma-qt cables

# import libraries needed for the program to interact with the hardware
import board
import time
import qwiic_led_stick
from micropython import const
from adafruit_seesaw.seesaw import Seesaw

# Define the main function in the software
def main():
    time.sleep(0.1)
# Set up the software resources

# Set up the LED stick

# Run a test pattern on the LED stick to demonstrate that the LEDs are working

# Set up the gamepad buttons

# Start a program loop

# Check for button presses

# Check for joystick movements

# Decide what to do given the button presses and joystick movements

# Make changes to the color and brightness of the LEDs according to the decisions

# Wait for a short amount of time so that the program can be stopped by a ctrl-c in the REPL dialogue. (Read, Evaluate, Print Loop)

# Below here, define all the other functions we need to make the main function simpler and easier to read and understand

# After all the function definitions, we can run the main function
main()



'''






i2c_bus = board.STEMMA_I2C()

BUTTON_X = const(6)
BUTTON_Y = const(2)
BUTTON_A = const(5)
BUTTON_B = const(1)
BUTTON_SELECT = const(0)
BUTTON_START = const(16)
button_mask = const(
    (1 << BUTTON_X)
    | (1 << BUTTON_Y)
    | (1 << BUTTON_A)
    | (1 << BUTTON_B)
    | (1 << BUTTON_SELECT)
    | (1 << BUTTON_START)
)

gamepad = Seesaw(i2c_bus, addr=0x50)
gamepad.pin_mode_bulk(button_mask, gamepad.INPUT_PULLUP)

length = 10
stick = qwiic_led_stick
stick.change_length(length)
stick.set_LED_color(0,0,0)
time.sleep(0.1)
stick.set_LED_color(0,0,0) # run the first command a second time, the first received command is incomplete
time.sleep(0.1)
print( "initialized" )

# Probably too bright
stick.set_LED_brightness(5) # all

RED =   255,0,0
GREEN = 0,255,0
BLUE =  0,0,255
WHITE = 255, 255, 255
OFF =   0,0,0
color = [RED, GREEN, BLUE, WHITE]



def main():
    last_x = 0
    last_y = 0
    stick.set_LED_color(0,0,0)
    led_stick_self_test( stick )
    start_pressed = False
    last_start_pressed = False
    while True:

        x = 1023 - gamepad.analog_read(14)
        y = 1023 - gamepad.analog_read(15)

        if (abs(x - last_x) > 3) or (abs(y - last_y) > 3):
            print(x, y)
            last_x = x
            last_y = y

        buttons = gamepad.digital_read_bulk(button_mask)

        if not buttons & (1 << BUTTON_X):
            print("Button x pressed")

        if not buttons & (1 << BUTTON_Y):
            print("Button Y pressed")

        if not buttons & (1 << BUTTON_A):
            print("Button A pressed")

        if not buttons & (1 << BUTTON_B):
            print("Button B pressed")

        if not buttons & (1 << BUTTON_SELECT):
            print("Button Select pressed")

        if not buttons & (1 << BUTTON_START):
            print("Button Start pressed")
            if not last_start_pressed:
                led_stick_self_test( stick )
            last_start_pressed = True
        else:
            last_start_pressed = False

        time.sleep(0.01)


def led_stick_self_test( stick ):
    coms_wait = 0.02
    wait = 0.1
    for n in range (0, len(color)):
        for index in range ( 1, 11 ):
            print( "working on pixel {}".format( index ))
            red, green, blue = OFF
            stick.set_LED_color(red,green,blue,index-1)
            time.sleep( coms_wait )
            red, green, blue = color[n]
            stick.set_LED_color(red,green,blue,index)
            time.sleep( wait )
    stick.set_LED_color(0,0,0)

main()

'''
