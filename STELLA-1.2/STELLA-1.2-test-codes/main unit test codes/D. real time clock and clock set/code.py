# interactive console set date and time
# Paul Mirel 2024
# NASA open source software license

## look up UTC time here: https://time.is/UTC

import busio
from adafruit_pcf8523 import pcf8523
import time
#import rtc    # import the microcontroller system real time clock functionality
import board
import displayio
import terminalio

try:
    i2c_bus = board.I2C()
    print( "i2c bus initialized" )
except:
    print( "i2c bus failed to initialize" )
    i2c_bus = False


try:
    real_time_clock = pcf8523.PCF8523(i2c_bus)
    print( "real time clock initialized" )
except:
    print( "real time clock failed to initialize" )
    real_time_clock = False

days = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
# wday =    0         1         2           3            4          5          6
if False: #True:    # if False, do not change the time setting on the real time clock module.
                    # if True, write the new time setting from below onto the real time clock module.

    #                   (( year, mon, date, hour, min, sec, wday, yday, isdst ))
    t = time.struct_time(( 2022,  12,   30,   22,  21,  15,   5,   -1,    -1 ))
    # you must set year, mon, date, hour, min, sec and weekday
    # yday = day of the year is not supported by this clock,
    # isdst = 'is daylight savings time' can be set but we don't do anything with it at this time

    print("Setting time to:", t)     # uncomment for debugging
    real_time_clock.datetime = t
    print()
if real_time_clock:
    battery_low = real_time_clock.battery_low
else:
    battery_low = False

if battery_low:
    print( "Clock battery is low. Replace the clock battery." )
else:
    print( "Clock battery voltage is OK." )

try:
    while True:
        timenow = real_time_clock.datetime
        #print(timenow)  # hardware clock time
        #feather_local_time = time.localtime()
        #print(feather_local_time)       # microcontroller local time
        print()
        weekday = timenow.tm_wday
        year = timenow.tm_year
        month = timenow.tm_mon
        day = timenow.tm_mday
        hour = timenow.tm_hour
        minute = timenow.tm_min
        second = timenow.tm_sec
        previous_weekday = weekday
        previous_year = year
        previous_month = month
        previous_day = day

        previous_hour = hour
        previous_minute = minute
        previous_second = second

        try:
            print( "The date is %s %d-%d-%d" % ( days[ weekday ], year, month, day ))
            print( "The time is %d:%02d:%02d" % ( hour, minute, second ))
        except IndexError as err:
            print( "The clock has not been set, and the values are out of range." )

        print()
        print( "Current year is {}. Enter a new year and press return, or press return to skip.".format(timenow.tm_year))
        print(">", end = ' ')
        input_string = False
        while input_string == False:
            input_string = input().strip()
        try:
            input_integer = int( input_string )
        except ValueError:
            input_integer = 2000
        if input_integer in range (2010, 2100):
            year = input_integer
            t = time.struct_time(( year,  month,   day,   hour,  minute,  second,   weekday,   -1,    -1 ))
            real_time_clock.datetime = t

        print()
        print( "Current month is {}. Enter a new month and press return, or press return to skip.".format(timenow.tm_mon))
        print(">", end = ' ')
        input_string = False
        while input_string == False:
            input_string = input().strip()
        try:
            input_integer = int( input_string )
        except ValueError:
            pass
        if input_integer in range (1, 12):
            month = input_integer
            t = time.struct_time(( year,  month,   day,   hour,  minute,  second,   weekday,   -1,    -1 ))
            real_time_clock.datetime = t

        print()
        print( "Current day is {}. Enter a new day and press return, or press return to skip.".format(timenow.tm_mday))
        print(">", end = ' ')
        input_string = False
        while input_string == False:
            input_string = input().strip()
        try:
            input_integer = int( input_string )
        except ValueError:
            pass
        if input_integer in range (1, 32):
            day = input_integer
            t = time.struct_time(( year,  month,   day,   hour,  minute,  second,   weekday,   -1,    -1 ))
            real_time_clock.datetime = t

        print()
        print( "Current hour is {} UTC. Enter a new hour and press return, or press return to skip.".format(timenow.tm_hour))
        print(">", end = ' ')
        input_string = False
        while input_string == False:
            input_string = input().strip()
        try:
            input_integer = int( input_string )
        except ValueError:
            pass
        if input_integer in range (0, 23):
            hour = input_integer
            t = time.struct_time(( year,  month,   day,   hour,  minute,  second,   weekday,   -1,    -1 ))
            real_time_clock.datetime = t

        print()
        print( "Current minute is {}. Enter a new minute and press return, or press return to skip.".format(timenow.tm_min))
        print(">", end = ' ')
        input_string = False
        while input_string == False:
            input_string = input().strip()
        try:
            input_integer = int( input_string )
        except ValueError:
            pass
        if input_integer in range (0, 59):
            minute = input_integer
            t = time.struct_time(( year,  month,   day,   hour,  minute,  second,   weekday,   -1,    -1 ))
            real_time_clock.datetime = t

        print()
        print( "Current second is {}. Enter a new second and press return, or press return to skip.".format(timenow.tm_sec))
        print(">", end = ' ')
        input_string = False
        while input_string == False:
            input_string = input().strip()
        try:
            input_integer = int( input_string )
        except ValueError:
            pass
        if input_integer in range (0, 59):
            second = input_integer
            t = time.struct_time(( year,  month,   day,   hour,  minute,  second,   weekday,   -1,    -1 ))
            real_time_clock.datetime = t

        print()
        print( "Current weekday is {}. Enter a new weekday and press return, or press return to skip.".format(days[timenow.tm_wday]))
        print( "Enter: sun, mon, tue, wed, thu, fri, sat" )
        print(">", end = ' ')
        input_string = False

        input_string = input().strip()
        print(input_string)
        if input_string == "mon":
            weekday = 1
        elif input_string == "tue":
            weekday = 2
        elif input_string == "wed":
            weekday = 3
        elif input_string == "thu":
            weekday = 4
        elif input_string == "fri":
            weekday = 5
        elif input_string == "sat":
            weekday = 6
        elif input_string == "sun":
            weekday = 0
        else:
            pass
        print("weekday = {}".format(weekday))
        t = time.struct_time(( year,  month,   day,   hour,  minute,  second,   weekday,   -1,    -1 ))
        real_time_clock.datetime = t

        time.sleep( 0.1 )
finally:
        i2c_bus.deinit()
        print( "i2c_bus deinitialized" )
        print( " ---- end --- " )
