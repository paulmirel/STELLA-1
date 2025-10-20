# STELLA-1.1 set date and time utility
SOFTWARE_VERSION_NUMBER = "CLK 2.0"

# import system libraries
import gc #garbage collection, RAM management
gc.collect()
print("start memory free {} B".format( gc.mem_free() ))
import os
import sys
import board
import microcontroller
import time
import rtc
import busio
import digitalio
import terminalio
import storage
import sdcardio
from analogio import AnalogIn

# import display libraries
import displayio
import vectorio # for shapes
import adafruit_ili9341 # TFT (thin film transistor) display
from adafruit_display_text.bitmap_label import Label
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.circle import Circle
#from adafruit_display_shapes.triangle import Triangle
#from adafruit_display_shapes.line import Line
import adafruit_focaltouch # touch screen controller

SCREENSIZE_X = 320
SCREENSIZE_Y = 240

DAYS = { 0:"Sunday", 1:"Monday", 2:"Tuesday", 3:"Wednesday", 4:"Thursday", 5:"Friday", 6:"Saturday" }


# import device specific libraries
import adafruit_pcf8523     # real time hardware_clock

gc.collect()

def main():
    set_clock = True
    # set  constants
    PUSHBUTTON_IO_PIN = board.D12
    alternate_screen_reset_pin = board.D4

    # initialize bus
    i2c_bus = initialize_i2c_bus( board.SCL, board.SDA )
    spi_bus = initialize_spi_bus()

    if i2c_bus and spi_bus:
        operational = True
    else:
        operational = False
    pushbutton = initialize_pushbutton( PUSHBUTTON_IO_PIN )
    display = initialize_display( spi_bus )
    touch_controller, cap_touch_present = initialize_touch_screen( spi_bus, i2c_bus )
    if touch_controller:
        print( "Display detected." )
        drone_mode = False
        display_group_table = initialize_display_group( display )
        welcome_group = create_welcome_screen( display )
        display.show( welcome_group )
        time.sleep(1)
    else:
        print( "Display not detected. Operating without display." )
        drone_mode = True
    gc.collect()
    # initialize real time hardware clock, and use it as the source for the microcontroller real time clock
    hardware_clock, hardware_clock_battery_OK = initialize_real_time_clock( i2c_bus )
    system_clock = rtc.RTC()
    system_clock.datetime = hardware_clock.datetime
    days = ( "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday" )
    # wday =    0         1         2           3            4          5          6
    # initialize sd card file storage
    if set_clock:
        timestamp = hardware_clock.datetime
        weekday = DAYS[timestamp.tm_wday]
        print( "create set clock display screen" )
        set_clock_group = create_set_clock_screen( display )

        year_minimum = 2023
        year_group = displayio.Group( scale=2, x=20, y=30 )
        year_setting = timestamp.tm_year
        if year_setting < year_minimum:
            year_setting = year_minimum
        year_text = str(year_setting)
        year_text_area = label.Label( terminalio.FONT, text=year_text, color=0x0 )
        year_group.append( year_text_area )
        set_clock_group.append( year_group )

        month_group = displayio.Group( scale=2, x=100, y=30 )
        month_setting = timestamp.tm_mon
        month_text = str("{:02d}".format(month_setting))
        month_text_area = label.Label( terminalio.FONT, text=month_text, color=0x0 )
        month_group.append( month_text_area )
        set_clock_group.append( month_group )

        day_group = displayio.Group( scale=2, x=160, y=30 )
        day_max = 31
        day_setting = timestamp.tm_mday
        day_text = str("{:02d}".format(day_setting))
        day_text_area = label.Label( terminalio.FONT, text=day_text, color=0x0 )
        day_group.append( day_text_area )
        set_clock_group.append( day_group )

        weekday_group = displayio.Group( scale=2, x=200, y=30 )
        weekday_setting = timestamp.tm_wday
        weekday_text = wday_to_weekday( weekday_setting )
        weekday_text_area = label.Label( terminalio.FONT, text=weekday_text, color=0x0 )
        weekday_group.append( weekday_text_area )
        set_clock_group.append( weekday_group )

        hour_group = displayio.Group( scale=2, x=30, y=120 )
        hour_setting = timestamp.tm_hour
        hour_text = str("{:02d}".format( hour_setting ))
        hour_text_area = label.Label( terminalio.FONT, text=hour_text, color=0x0 )
        hour_group.append( hour_text_area )
        set_clock_group.append( hour_group )

        colon_group = displayio.Group( scale=2, x=30, y=120 )
        colon_text = "   :   :"
        colon_text_area = label.Label( terminalio.FONT, text=colon_text, color=0x0 )
        colon_group.append( colon_text_area )
        set_clock_group.append( colon_group )

        utc_group = displayio.Group( scale=2, x=170, y=120 )
        utc_text = "UTC"
        utc_text_area = label.Label( terminalio.FONT, text=utc_text, color=0x0 )
        utc_group.append( utc_text_area )
        set_clock_group.append( utc_group )

        minute_group = displayio.Group( scale=2, x=85, y=120 )
        min_setting = timestamp.tm_min
        minute_text = str("{:02d}".format( min_setting ))
        minute_text_area = label.Label( terminalio.FONT, text=minute_text, color=0x0 )
        minute_group.append( minute_text_area )
        set_clock_group.append( minute_group )

        second_group = displayio.Group( scale=2, x=135, y=120 )
        sec_setting = timestamp.tm_sec
        second_text = str("{:02d}".format( sec_setting ))
        second_text_area = label.Label( terminalio.FONT, text=second_text, color=0x0 )
        second_group.append( second_text_area )
        set_clock_group.append( second_group )

        set_y = 150
        set_banish_y = 400
        set_marker_group = displayio.Group( scale=3, x=235, y=set_y )
        set_marker_text = "SET"
        set_marker_text_area = label.Label( terminalio.FONT, text=set_marker_text, color=0x0 )
        set_marker_group.append( set_marker_text_area )
        set_clock_group.append( set_marker_group )
        set_marker_time = time.monotonic()
        set_marker_dwell = 2

        cbat_ok_group = displayio.Group( scale=2, x=190, y=200 )
        if hardware_clock_battery_OK:
            cbat_ok_text = "OK"
        else:
            cbat_ok_text = "LOW"
        cbat_ok_text_area = label.Label( terminalio.FONT, text=cbat_ok_text, color=0x0 )
        cbat_ok_group.append( cbat_ok_text_area )
        set_clock_group.append( cbat_ok_group )

        palette = displayio.Palette(1)
        palette[0] = 0x0
        marker_bar = vectorio.Rectangle(pixel_shader=palette, width=60, height=10, x = 115, y=400)
        set_clock_group.append(marker_bar)
        #mode = (x, y)
        sc_year     = (15, 45)
        sc_month    = (80, 45)
        sc_day      = (145, 45)
        sc_weekday  = (200, 45)
        sc_hour     = (15, 136)
        sc_min      = (65, 136)
        sc_sec      = (115, 136)
        sc_banish   = (300, 400)

        display.show( set_clock_group )
        set_clock_mode = sc_banish
        last_set_clock_mode = sc_banish

        last_touch_up = False
        last_touch_down = False
        while set_clock:
            touch_x = 0
            touch_y = 0
            touch_up = False
            touch_down = False
            if time.monotonic() > set_marker_time + set_marker_dwell:
                #print( "banish the SET marker" )
                set_marker_group.y = set_banish_y
            timestamp = hardware_clock.datetime
            weekday = DAYS[timestamp.tm_wday]


            if touch_controller and cap_touch_present:
                if touch_controller.touched:
                    touch_values = touch_controller.touches
                    if touch_values[0]:
                        touch_x = int(touch_values[0]['y']) #transpose
                        touch_y = int(touch_values[0]['x'])
                        print( touch_x, touch_y )
                        if touch_y > 175:
                            #print( "working in the date row")
                            if touch_x in range( 13, 80 ):
                                set_clock_mode = sc_year
                            elif touch_x in range( 85, 145 ):
                                set_clock_mode = sc_month
                            elif touch_x in range( 150, 190 ):
                                set_clock_mode = sc_day
                            elif touch_x in range( 200, 300 ):
                                set_clock_mode = sc_weekday
                        if touch_x in range( 400, 2300 ): # working in the time columns
                            if touch_y in range (1300, 2400): # working in the time row
                                if touch_x < 1200:
                                    set_clock_mode = sc_hour
                                elif touch_x in range( 1200, 1600):
                                    set_clock_mode = sc_min
                                elif touch_x in range( 1700, 2300 ):
                                    set_clock_mode = sc_sec
                        elif touch_x > 2600: # working in buttons column
                            if touch_y in range( 1700, 2700 ):
                                touch_up = True
                            elif touch_y < 1670:
                                touch_down = True

                else:
                    #print( "not being touched" )
                    touch_up = False
                    touch_down = False

            if touch_up:
                if not last_touch_up:
                    increment = True
                    #print( "increment == {}".format( increment) )
                    last_touch_up = True
                else:
                    increment = False
            else:
                increment = False
                #print( "increment == {}".format( increment) )
                last_touch_up = False
            if touch_down:
                if not last_touch_down:
                    decrement = True
                    #print( "decrement == {}".format( decrement) )
                    last_touch_down = True
                else:
                    decrement = False
            else:
                decrement = False
                #print( "decrement == {}".format( decrement) )
                last_touch_down = False

            marker_bar.x, marker_bar.y = set_clock_mode

            if set_clock_mode == sc_year:
                if False: #last_set_clock_mode != sc_year:
                    year_setting = timestamp.tm_year
                if increment:
                    year_setting += 1
                if decrement:
                    year_setting -= 1
                    if year_setting < year_minimum:
                        year_setting = year_minimum
                last_set_clock_mode = sc_year
            year_text_area.text = str(year_setting)

            if set_clock_mode == sc_month:
                if False: #last_set_clock_mode != sc_month:
                    month_setting = timestamp.tm_mon
                if increment:
                    month_setting += 1
                    if month_setting > 12:
                        month_setting = 1
                if decrement:
                    month_setting -= 1
                    if month_setting < 1:
                        month_setting = 12
                last_set_clock_mode = sc_month
            month_text_area.text = str("{:02d}".format( month_setting ))

            if set_clock_mode == sc_day:
                if False: #last_set_clock_mode != sc_day:
                    pass
                    #day_setting = timestamp.tm_mday
                day_max = 31
                if month_setting == 2:
                    day_max = 29
                elif month_setting == 4 or month_setting == 6 or month_setting == 9 or month_setting == 11:
                    day_max = 30
                if increment:
                    day_setting += 1
                    if day_setting > day_max:
                        day_setting = 1
                if decrement:
                    day_setting -= 1
                    if day_setting < 1:
                        day_setting = day_max
                last_set_clock_mode = sc_day
            day_text_area.text = str("{:02d}".format( day_setting ))

            if set_clock_mode == sc_weekday:
                if last_set_clock_mode != sc_weekday:
                    pass
                if increment:
                    weekday_setting += 1
                    if weekday_setting > 6:
                        weekday_setting = 0
                if decrement:
                    weekday_setting -= 1
                    if weekday_setting < 1:
                        day_setting = 6
                last_set_clock_mode = sc_weekday
            weekday_text_area.text = wday_to_weekday( weekday_setting )

            if set_clock_mode == sc_hour:
                if False: #last_set_clock_mode != sc_hour:
                    hour_setting = timestamp.tm_hour
                if increment:
                    hour_setting += 1
                    if hour_setting > 23:
                        hour_setting = 0
                if decrement:
                    hour_setting -= 1
                    if hour_setting < 0:
                        hour_setting = 23
                last_set_clock_mode = sc_hour
            hour_text_area.text = str("{:02d}".format( hour_setting ))

            if set_clock_mode == sc_min:
                if last_set_clock_mode != sc_min:
                    min_setting = timestamp.tm_min
                if increment:
                    min_setting += 10
                    if min_setting > 59:
                        min_setting = 0
                if decrement:
                    min_setting -= 1
                    if min_setting < 0:
                        min_setting = 59
                last_set_clock_mode = sc_min
            minute_text_area.text = str("{:02d}".format( min_setting ))

            if set_clock_mode == sc_sec:
                if last_set_clock_mode != sc_sec:
                    sec_setting = timestamp.tm_sec
                if increment:
                    sec_setting += 10
                    if sec_setting > 59:
                        sec_setting = 0
                if decrement:
                    sec_setting -= 1
                    if sec_setting < 0:
                        sec_setting = 50
                last_set_clock_mode = sc_sec
            else:
                sec_setting = timestamp.tm_sec
            second_text_area.text = str("{:02d}".format( sec_setting ))

            if pushbutton_pressed( pushbutton ):
                count = 0
                while pushbutton_pressed( pushbutton ) and count < 15:
                    count += 1
                    time.sleep( 0.1 )
                if count > 2:
                    print( "set the clock" )
                    set_clock_mode = sc_banish
                    t = time.struct_time(( year_setting, month_setting, day_setting, hour_setting, min_setting, sec_setting, weekday_setting, -1,  -1 ))
                    hardware_clock.datetime = t
                    print( "move SET message to buttons" )
                    set_marker_group.y = set_y
                    set_marker_time = time.monotonic()
                if count > 10:
                    print( "set the clock and exit" )
                    set_clock = False
            time.sleep( 0.2 )
        print( "delete set_clock display variables" )
        mem_free_begin_removal = gc.mem_free()/1000
        for i in range (0, len(set_clock_group)):
            set_clock_group.pop()
            print( "pop" )
        gc.collect()
        mem_free_end_removal = gc.mem_free()/1000
        print( "mem saved by removing clock set group = {} kB".format( mem_free_end_removal - mem_free_begin_removal ))


# function definitions below
def throwaway_for_reading_featherwing_touch_screen():
    pass
    '''
     if False: #touch_screen and not alt_touch: # FeatherWing Display touch coordinates.
                while not touch_screen.buffer_empty:
                    touch_y, touch_x, touch_pressure = touch_screen.read_data()
                    #print("x = {}, y = {}, pressure = {}".format(touch_x, touch_y, touch_pressure))
                if touch_pressure in range (5, 50):
                    #print( "being touched" )
                    if touch_y > 3000: # working in the date row
                        if touch_x > 3000:
                            set_clock_mode = sc_year
                        elif touch_x in range( 2200, 2700 ):
                            set_clock_mode = sc_month
                        elif touch_x in range( 1200, 2000 ):
                            set_clock_mode = sc_day
                        elif touch_x in range( 400, 1000 ):
                            set_clock_mode = sc_weekday
                    if touch_x in range( 1700, 4000 ): # working in the time columns
                        if touch_y in range (1200, 2000): # working in the time row
                            if touch_x > 3200:
                                set_clock_mode = sc_hour
                            elif touch_x in range( 2300, 3100 ):
                                set_clock_mode = sc_min
                            elif touch_x in range( 1700, 2200 ):
                                set_clock_mode = sc_sec
                    elif touch_x < 1000: # working in buttons column
                        if touch_y in range( 1900, 2500 ):
                            touch_up = True
                        elif touch_y < 1500:
                            touch_down = True
                else:
                    #print( "not being touched" )
                    touch_up = False
                    touch_down = False
    '''

def create_set_clock_screen( display ):
    set_clock_screen_start_memory = gc.mem_free()
    set_clock_group = initialize_display_group( display )
    border_color = 0xFF6C00 #0xFF00FE #0x14C30E
    front_color = 0xFFFFFF
    if (display == False) or ( set_clock_group == False):
        print("No display")
        return
    border = displayio.Palette(1)
    border[0] = border_color
    front = displayio.Palette(1)
    front[0] = front_color
    outer_rectangle = vectorio.Rectangle(pixel_shader=border, width=320, height=240, x=0, y=0)
    set_clock_group.append( outer_rectangle )
    border_width = 7
    x = border_width
    y = border_width
    width = 320-2*border_width
    height = 240-2*border_width
    front_rectangle = vectorio.Rectangle(pixel_shader=front, width=width, height=height, x=x, y=y)
    set_clock_group.append( front_rectangle )

    date_group = displayio.Group( scale=2, x=20, y=65 )
    date_text = "Year Month Day Weekday"
    date_text_area = label.Label( terminalio.FONT, text=date_text, color=0x0 )
    date_group.append( date_text_area ) # Subgroup for text scaling
    set_clock_group.append( date_group )

    time_group = displayio.Group( scale=2, x=20, y=160 )
    time_text = "Hour:Min:Sec"
    time_text_area = label.Label( terminalio.FONT, text=time_text, color=0x0 )
    time_group.append( time_text_area ) # Subgroup for text scaling
    set_clock_group.append( time_group )

    cbat_group = displayio.Group( scale=2, x=20, y=200 )
    cbat_text = "Clock Battery: "
    cbat_text_area = label.Label( terminalio.FONT, text=cbat_text, color=0x0 )
    cbat_group.append( cbat_text_area ) # Subgroup for text scaling
    set_clock_group.append( cbat_group )

    palette = displayio.Palette(1)
    palette[0] = 0x45FF00
    points2 = [ (40, 50), (80, 100), (00, 100)]
    polygon = vectorio.Polygon(pixel_shader=palette, points=points2, x=220, y=35)
    set_clock_group.append(polygon)

    palette = displayio.Palette(1)
    palette[0] = 0x0028FF
    points2 = [ (40, 150), (80, 100), (00, 100)]
    polygon = vectorio.Polygon(pixel_shader=palette, points=points2, x=220, y=65)
    set_clock_group.append(polygon)

    return set_clock_group

def alternate_screen_present( IO_pin ):
    display_check = digitalio.DigitalInOut( IO_pin )
    display_check.direction = digitalio.Direction.INPUT
    display_check.pull = digitalio.Pull.DOWN
    if display_check.value:
        return True
    else:
        return False


def screen_pressed( touch_screen, alt_touch ):
    if touch_screen and not alt_touch:
        top_center_pressed = False  #blue screen button
        top_left_pressed = False    #yellow screen button
        top_right_pressed = False   #green screen button
        while not touch_screen.buffer_empty:
            touch_y, touch_x, touch_pressure = touch_screen.read_data()
            #print( "touch_x, touch_y, touch_pressure" )
            #print( touch_x, touch_y, touch_pressure )
            if touch_y > 2300:
                if touch_x in range( 2350, 3750 ):
                    top_left_pressed = True
                elif touch_x in range( 1220, 2300 ):
                    top_center_pressed = True
                elif touch_x in range( 180, 1150 ):
                    top_right_pressed = True

        #print( "top_left_pressed, top_center_pressed, top_right_pressed" )
        #print( top_left_pressed, top_center_pressed, top_right_pressed )
        return top_left_pressed, top_center_pressed, top_right_pressed
    elif touch_screen and alt_touch:
        top_center_pressed = False  #blue screen button
        top_left_pressed = False    #yellow screen button
        top_right_pressed = False   #green screen button
        if touch_screen.touched:
            point = touch_screen.touch
            touch_y = point["x"] #coordinate transform x to y to better match previous
            touch_x = point["y"]
            touch_pressure= point["pressure"]
            #print( "touch_x, touch_y, touch_pressure" )
            #print( touch_x, touch_y, touch_pressure )
            if touch_pressure > 10:
                #print( "touch_x, touch_y, touch_pressure" )
                #print( touch_x, touch_y, touch_pressure )
                if touch_y > 2300:
                    if touch_x in range( 350, 1600 ):
                        top_left_pressed = True #yellow
                    elif touch_x in range( 1650, 2700 ):
                        top_center_pressed = True #blue
                    elif touch_x in range( 2750, 3500 ):
                        top_right_pressed = True #green
        #print( "top_left_pressed, top_center_pressed, top_right_pressed" )
        #print( top_left_pressed, top_center_pressed, top_right_pressed )
        return top_left_pressed, top_center_pressed, top_right_pressed
    else:
        return False, False, False

def pushbutton_pressed( pushbutton ):
    pushbutton_press_state = not pushbutton.value   #active low, so True is notpushed and False is pushed
    return pushbutton_press_state                   #pushbutton_press_state is True if button is being pushed

def check_inputs( pushbutton, touch_screen, pushbutton_last_press_state, screen_record_pause_last_press_state, source_lamps_last_press_state ):
    pushbutton_press_state = pushbutton_pressed( pushbutton )
    press = screen_pressed( touch_screen )
    if pushbutton_last_press_state == pushbutton_press_state and screen_record_pause_last_press_state == press[0] and source_lamps_last_press_state == press[1]:
        no_change = True
    else:
        no_change = False
    return no_change, pushbutton_press_state, press[0], press[1]

def initialize_pushbutton( IO_pin ):
    pushbutton = digitalio.DigitalInOut( IO_pin )
    pushbutton.direction = digitalio.Direction.INPUT
    pushbutton.pull = digitalio.Pull.UP
    return pushbutton

def wday_to_weekday( wday ):
    try:
        clock_days = ( "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday" )
        weekday = clock_days[ wday ]
        return weekday
    except ValueError as err:
        print( "Error: weekday index out of range" )

def timestamp_to_weekday( timestamp ):
    try:
        clock_days = ( "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday" )
        weekday = clock_days[ timestamp.tm_wday ]
        return weekday
    except ValueError as err:
        print( "Error: real time hardware_clock fail: {:}".format(err) )
        return "Error"

def timestamp_to_decimal_hour( timestamp ):
    try:
        decimal_hour = timestamp.tm_hour + timestamp.tm_min/60.0 + timestamp.tm_sec/3600.0
        return decimal_hour
    except ValueError as err:
        print( "Error: invalid timestamp: {:}".format(err) )
        return False

def initialize_real_time_clock( i2c_bus ):
    try:
        hardware_clock = adafruit_pcf8523.PCF8523( i2c_bus )
        clock_battery_OK = not hardware_clock.battery_low
        if clock_battery_OK:
            print( "clock battery is OK." )
        else:
            print( "clock battery is low. Replace the clock battery." )
    except NameError:
        print( "real time clock failed to initialize" )
        hardware_clock = False
    return ( hardware_clock, clock_battery_OK )

def create_welcome_screen( display ):
    welcome_start_memory = gc.mem_free()
    try:
        bitmap = displayio.OnDiskBitmap("/lib/stella_logo.bmp")
        print( "Bitmap image file found" )
        # Create a TileGrid to hold the bitmap
        tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
        # Create a Group to hold the TileGrid
        welcome_group = displayio.Group()
        # Add the TileGrid to the Group
        welcome_group.append(tile_grid)

        version_group = displayio.Group( scale=2, x=25, y=210 )
        text = ( "software version {}".format( SOFTWARE_VERSION_NUMBER ))
        version_area = label.Label( terminalio.FONT, text=text, color=0x000000 )
        version_group.append( version_area ) # Subgroup for text scaling
        welcome_group.append( version_group )
        # Add the Group to the Display
        #display.show(group)
    except (MemoryError, OSError):
        print( "bitmap image file not found or memory not available" )
        welcome_group = initialize_display_group( display )
        border_color = 0xFF0022 # red
        front_color = 0x0000FF # blue
        if (display == False) or ( welcome_group == False):
            print("No display")
            return
        border = displayio.Palette(1)
        border[0] = border_color
        front = displayio.Palette(1)
        front[0] = front_color
        outer_rectangle = vectorio.Rectangle(pixel_shader=border, width=320, height=240, x=0, y=0)
        welcome_group.append( outer_rectangle )
        front_rectangle = vectorio.Rectangle(pixel_shader=front, width=280, height=200, x=20, y=20)
        welcome_group.append( front_rectangle )
        text_group = displayio.Group( scale=6, x=50, y=110 )
        text = "STELLA"
        text_area = label.Label( terminalio.FONT, text=text, color=0xFFFFFF )
        text_group.append( text_area ) # Subgroup for text scaling
        welcome_group.append( text_group )

        version_group = displayio.Group( scale=2, x=27, y=200 )
        text =( "software version {}".format( SOFTWARE_VERSION_NUMBER ))
        version_area = label.Label( terminalio.FONT, text=text, color=0xFFFFFF )
        version_group.append( version_area ) # Subgroup for text scaling
        welcome_group.append( version_group )
    welcome_stop_memory = gc.mem_free()
    print( "welcome routine uses {} kB".format( -1 *(welcome_stop_memory - welcome_start_memory)/1000))
        #uses 2.4kB"
    return welcome_group

def initialize_touch_screen( spi_bus, i2c_bus ):
    try:
        print( "capacitive touch screen boot message", end = ": ")
        touch_screen = adafruit_focaltouch.Adafruit_FocalTouch( i2c_bus, debug=False )
        cap_touch_present = True
        return touch_screen, cap_touch_present
    except ( RuntimeError, ValueError, AttributeError) as err:
        print( "capacitive touch screen controller not found" )
        try:
            resistive_touch_screen_chip_select = digitalio.DigitalInOut(board.D6)
            touch_screen = Adafruit_STMPE610_SPI(spi_bus, resistive_touch_screen_chip_select)
            cap_touch_present = False
            return touch_screen, cap_touch_present
        except ( RuntimeError, ValueError) as err:
            print( "resistive touch screen controller not found" )
            return False, False

def initialize_display( spi_bus ):
    if spi_bus == False:
        return False
    try:
        # displayio/dafruit_ili9341 library owns the pins until display release
        displayio.release_displays()
        tft_display_cs = board.D9
        tft_display_dc = board.D10
        display_bus = displayio.FourWire( spi_bus, command=tft_display_dc, chip_select=tft_display_cs )
        display = adafruit_ili9341.ILI9341( display_bus, width=SCREENSIZE_X, height=SCREENSIZE_Y, rotation=180 )
        return display
    except ValueError as err:
        print("Error: display fail {:}".format(err))
        return False

def initialize_display_group( display ):
    if display == False:
        print("no display")
        return False
    display_group = displayio.Group()
    return display_group

def low_battery_voltage_notification( power_indicator, text_group ):
    for index in range( 5 ):
        power_indicator.value = False
        time.sleep( 0.05 )
        power_indicator.value = True
        time.sleep( 0.05 )
    text_group[ GROUP.DAY_DATE ].text = "Low battery: plug in"
    time.sleep(0.6)

def check_battery_voltage( battery_monitor ):
    if battery_monitor:
        battery_voltage = round(( battery_monitor.value * 3.3) / 65536 * 2, 2 )
        return battery_voltage
    else:
        return 10

def initialize_AnalogIn( pin_number ):
    try:
        analog_signal = AnalogIn( pin_number )
    except ValueError:
        print( "analog input initialization failed." )
        analog_signal = False
    return analog_signal

def stall():
    print("intentionally stalled, press return to continue")
    input_string = False
    while input_string == False:
        input_string = input().strip()

def initialize_discrete_LED( pin_number ):
    try:
        discrete_LED = digitalio.DigitalInOut( pin_number )
        discrete_LED.direction = digitalio.Direction.OUTPUT
    except ValueError:
        print( "discrete LED initialization failed." )
        discrete_LED = False
    return discrete_LED

def initialize_spi_bus():
    try:
        spi_bus = board.SPI()
        return spi_bus
    except ValueError as err:
        print( "Error: spi bus fail: {:}".format(err) )
        return False

def initialize_i2c_bus( SCL_pin, SDA_pin ):
    try:
        i2c_bus = busio.I2C( SCL_pin, SDA_pin )
    except ValueError as err:
        print( "i2c bus failed to initialize '{}'".format( err ))
        i2c_bus = False
    return i2c_bus

gc.collect()
print( "memory free after load function definitions == {} kB".format( gc.mem_free()/1000))

main()

