SOFTWARE_VERSION_NUMBER = "0.0.3"
DEVICE_TYPE = "STELLA-Appetizer"
# copyright NASA under MIT open source software license
# author Paul Mirel

## link to STELLA project webpage:
## https://science.gsfc.nasa.gov/stella/

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
import random

# set the constant values for the locations of the buttons on the gamepad
BUTTON_X = const(6)
BUTTON_Y = const(2)
BUTTON_A = const(5)
BUTTON_B = const(1)
BUTTON_SELECT = const(0)
BUTTON_START = const(16)

# Define the main function of the software
def main():
    run_test_patterns = False

    # Set up the software resources:

    # 1. Start the Integrated circuit to Integrated circuit Communications system, the IIC bus, to allow the three devices
    # (the QTpy microcontroller, the gamepad buttons, and the LED stick) to talk to each other over the four-wire cables.
    # IIC is also called I squared C because I * I is I squared, and because "eye-squared-see" is easier to say than "eye-eye-see".
    # We write it as I2C because writing "squared" in symbols confuses the CircuitPython interpreter.
    # (i**2 gives the value of i squared, and i^2 gives the "bitwise exlusive or" of the value of i and the value 2.)
    # Learn more about the i2c bus and how it works, here: https://www.ti.com/lit/an/sbaa565/sbaa565.pdf

    i2c_bus = board.STEMMA_I2C()

    # 2. Tell the software that the LED stick is likely to be connected, and complain if the software doesn't find it on the bus.
    try:
        led_stick = qwiic_led_stick.QwiicLEDStick()
        led_stick.begin()
        print( "led_stick found and started up" )
    except Exception as error:
        led_stick = False
        print( "Can't find the led_stick, because: {}".format( error ))


    # 3. If the led_stick is on the bus, do some actions:
    if led_stick:
        # make a note for us of how many lamp positions there are on the stick
        number_of_lamps = 10
        # set the brightness to half of maximum, because it's super bright, and because if you set all the leds to maximum brightness,
        # the led_stick trys to draw more current than the bus can supply, causing the bus voltage to drop, resulting in poor or
        # non-functional communications between the microcontroller and the led_stick
        led_stick.set_all_LED_brightness(15) # minimum brightness of 0 (off), maximum of 31 (draws too much current).

        # Turn all the lamps off, if they were somehow left on by the last run of some software.
        led_stick.LED_off()
        # wait a tenth of a second for the led_stick to consider the command to turn all the lamps off
        time.sleep(0.1)
        # then send "all-lamps-off" command a second time, because when the led_stick first starts up, it can sometimes be a bit confused.
        led_stick.LED_off()

        wait_seconds = 0.25

        if run_test_patterns:
            # Flash all the lamps to clear the led_stick internal communications from its chip to the lamp units.
            for count in range (0, 3):
                print( "flash count {}".format(count))
                led_stick.set_all_LED_color(10, 10, 10)
                time.sleep(1)
                led_stick.LED_off()
                time.sleep(1)
            print()

            # Run a basic test pattern on the LED stick to demonstrate that the three LEDs in each lamp unit are working.

            # test the red led in each lamp
            for lamp_index in range (0, number_of_lamps):
                print( "testing red for lamp number: {}".format( lamp_index ))
                # set the color of a single lamp unit. The format for this command is ( lamp_number, red_value, green_value, blue_value )
                # the value minimum is 0, off, and the value maximum is 255 (much too bright, even at a half_brightness setting overall
                led_stick.set_single_LED_color( lamp_index, 25, 0, 0 )
                time.sleep( wait_seconds )
            # turn them all off, one at a time
            for lamp_index in range (0, number_of_lamps):
                led_stick.set_single_LED_color( lamp_index, 0, 0, 0 )
                time.sleep( wait_seconds )
            print()

            # test the green led in each lamp
            for lamp_index in range (0, number_of_lamps):
                print( "testing green for lamp number: {}".format( lamp_index ))
                led_stick.set_single_LED_color( lamp_index, 0, 25, 0 )
                time.sleep( wait_seconds )
            # turn them all off, one at a time, in reverse order
            for lamp_index in range (0, number_of_lamps):
                temporary_index = number_of_lamps - lamp_index - 1
                led_stick.set_single_LED_color( temporary_index, 0, 0, 0 )
                time.sleep( wait_seconds )
            print()

            # test the blue led in each lamp
            for lamp_index in range (0, number_of_lamps):
                print( "testing blue for lamp number: {}".format( lamp_index ))
                led_stick.set_single_LED_color( lamp_index, 0, 0, 25 )
                time.sleep( wait_seconds )
            # turn them all off, one at a time, starting with the middle lamp
            for lamp_index in range (0, number_of_lamps):
                temporary_index = ( 5 + lamp_index ) % number_of_lamps  # the % symbol acts as the modulo operator. Learn more here:
                                                                        # https://www.geeksforgeeks.org/python/what-is-a-modulo-operator-in-python/
                led_stick.set_single_LED_color( temporary_index, 0, 0, 0 )
                time.sleep( wait_seconds )
            print()

            # Run a custom test pattern in which you can set the colors and timing and number of repetitions
            for repetition in range ( 0, 40 ):
                print( "repetition number {}".format( repetition ))
                temporary_index = random.randint(0,10)
                temporary_red = random.randint(0,20)
                temporary_green = random.randint(0,20)
                temporary_blue = random.randint(0,20)
                led_stick.set_single_LED_color( temporary_index, temporary_red, temporary_green, temporary_blue )
                time.sleep(wait_seconds)
                # based on the examples of random and systematic color selections here and in the basic test pattern,
                # you can make your own test pattern here.
            led_stick.LED_off()
            print()

    # Set up the gamepad buttons
    gamepad = Seesaw( i2c_bus, addr=0x50 )
    set_pin_mode( gamepad )

    # Start a program loop
    buttons_last_pressed = [ False, False, False, False, False, False ]
    operational = True
    while operational:
        # Check for button presses
        buttons_pressed = check_buttons( gamepad )
        if buttons_pressed[0] and not buttons_last_pressed[ 0 ]:
            button_x_event = True
            print( "button x event" )
        if buttons_pressed[1] and not buttons_last_pressed[ 1 ]:
            button_y_event = True
            print( "button y event" )
        if buttons_pressed[2] and not buttons_last_pressed[ 2 ]:
            button_a_event = True
            print( "button a event" )
        if buttons_pressed[3] and not buttons_last_pressed[ 3 ]:
            button_b_event = True
            print( "button b event" )
        if buttons_pressed[4] and not buttons_last_pressed[ 4 ]:
            button_select_event = True
            print( "button select event" )
        if buttons_pressed[5] and not buttons_last_pressed[ 5 ]:
            button_start_event = True
            print( "button start event" )

        buttons_last_pressed = buttons_pressed

        # Check for joystick movements

        # Decide what to do given the button presses and joystick movements

        # Make changes to the color and brightness of the LEDs according to the decisions

        # Wait for a short amount of time so that the program can be stopped by a ctrl-c in the REPL dialogue. (Read, Evaluate, Print Loop)
        time.sleep(0.1)

# Below here, define all the other functions we need to make the main function simpler and easier to read and understand
def set_pin_mode( gamepad ):
    button_mask = const(
        (1 << BUTTON_X)
        | (1 << BUTTON_Y)
        | (1 << BUTTON_A)
        | (1 << BUTTON_B)
        | (1 << BUTTON_SELECT)
        | (1 << BUTTON_START)
    )
    gamepad.pin_mode_bulk(button_mask, gamepad.INPUT_PULLUP)
    print( "gamepad pin mode set" )

def check_buttons( gamepad ):
    buttons = gamepad.digital_read_bulk(button_mask)
    buttons_pressed = [ False, False, False, False, False, False ]
    if not buttons & (1 << BUTTON_X):
        buttons_pressed[ 0 ] = True
        #print("Button x pressed")

    if not buttons & (1 << BUTTON_Y):
        buttons_pressed[ 1 ] = True
        #print("Button Y pressed")

    if not buttons & (1 << BUTTON_A):
        buttons_pressed[ 2 ] = True
        #print("Button A pressed")

    if not buttons & (1 << BUTTON_B):
        buttons_pressed[ 3 ] = True
        #print("Button B pressed")

    if not buttons & (1 << BUTTON_SELECT):
        #print("Button Select pressed")
        buttons_pressed[ 4 ] = True

    if not buttons & (1 << BUTTON_START):
        #print("Button Start pressed")
        buttons_pressed[ 5 ] = True

    return buttons_pressed


# After all the function definitions, we can run the main function
main()



'''

        x = 1023 - gamepad.analog_read(14)
        y = 1023 - gamepad.analog_read(15)

        if (abs(x - last_x) > 3) or (abs(y - last_y) > 3):
            print(x, y)
            last_x = x
            last_y = y

'''
