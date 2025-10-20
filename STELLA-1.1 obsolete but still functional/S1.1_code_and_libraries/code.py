SOFTWARE_VERSION_NUMBER = "11.1.2"
DEVICE_TYPE = "STELLA-1.1"
# STELLA-1.1 instrument code
# Science and Technology Education for Land/ Life Assessment
# Paul Mirel 2023
# NASA Open Source Software License

print( "SOFTWARE_VERSION_NUMBER = {}".format( SOFTWARE_VERSION_NUMBER ))
print( "DEVICE_TYPE = {}".format( DEVICE_TYPE ))

# import system libraries
import gc #garbage collection, RAM management
gc.collect()
start_memory_free = gc.mem_free()/1000
print("start memory free {} kB".format( start_memory_free ))
last_alloc = gc.mem_alloc()

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
import asyncio
import adafruit_ticks
import keypad

# import DISPlay libraries
import displayio
import vectorio # for shapes
import adafruit_ili9341 # TFT (thin film transistor) DISPlay
from adafruit_display_text.bitmap_label import Label
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.circle import Circle
#from adafruit_display_shapes.triangle import Triangle
#from adafruit_display_shapes.line import Line
import adafruit_focaltouch # touch screen controller

# import device specific libraries
import adafruit_mlx90614    # thermal infrared
import adafruit_mcp9808     # air temperature
import adafruit_as726x      # visible spectrum
import adafruit_pcf8523     # real time hardware_clock
from adafruit_bme280 import basic as adafruit_bme280 # weather
import adafruit_vl53l4cd    # LiDAR range 0 to 6000mm
import adafruit_gps         # GPS
import ulab                 # math functions, needed for calculating standard deviation

# instrument modes:
BLUE =   0   # toggle between record (increment batch) and pause
YELLOW = 1   # take a single datapoint (increment batch) and hold data
GREEN =  2   # sample and average (increment batch)
ORANGE = 3   # FUTURE measurement dialogue
AUX =    4   # FUTURE utiilty mode

# display modes:
display_drone =        0
display_welcome =      1
display_table =        2
display_averaging =    3
display_mmt_guide =    4   # FUTURE interactive measurement dialogue screen
display_reference =    5   # FUTURE auxiliary data
display_clock =        6   # clock set
SCREENSIZE_X =      320 # pixels
SCREENSIZE_Y =      240 # pixels
DISPLAY_ROTATION =  180 # degrees
SCREEN_RESET_PIN =  board.D4

# data modes:
RECORD =    0 # recording continuously
PAUSE =     1 # live data on screen, not recording


ON =    0 # sample_indicator is active low.
OFF =   1 # sample_indicator is active low.
CREATE = 0
UPDATE = 1

DAYS = { 0:"Sunday", 1:"Monday", 2:"Tuesday", 3:"Wednesday", 4:"Thursday", 5:"Friday", 6:"Saturday" }

DATA_FILE = "/sd/data.csv"

VIS_BANDS = ( 450, 500, 550, 570, 600, 650 ) # from amd as7262 datasheet
VIS_BAND_PREFIXES = ( "V", "B",  "G", "Y", "O", "R" )
NIR_BANDS = ( 610, 680, 730, 760, 810, 860 ) # from amd as7263 datasheet
MAX_VALUE = 99999
HUGE_VALUE = False #999999 #False #999999 #huge value for stress testing memory allocations

UID = int.from_bytes(microcontroller.cpu.uid, "big") % 10000
print("unique identifier (UID) == {0}".format( UID ))

LOW_BATTERY_VOLTAGE = 3.1

async def main():
    Mode.number_of_instrument_modes = 3
    Mode.number_of_display_modes = 6
    Mode.number_of_data_modes = 2

    PUSHBUTTON_PIN = board.D12
    SAMPLE_INDICATOR_LED_PIN = board.A0
    MAIN_BATTERY_MONITOR_PIN = board.A1

    # initialize busses
    i2c_bus = initialize_i2c_bus( board.SCL, board.SDA )
    spi_bus = initialize_spi_bus()
    uart_nir = initialize_uart_bus( board.D24, board.D25, 115200, 1 ) #pins, baudrate, timeout
    uart_gps = initialize_uart_bus( board.TX, board.RX, 9600, 0.5 ) #pins, baudrate, timeout

    if i2c_bus and spi_bus:
        operational = True
    else:
        operational = False

    sdcard = initialize_sdcard( spi_bus )   # it is important that the SD card be initialized
                                        # before accessing any other peripheral on the bus.
                                        # Failure to do so can prevent the SD card from being
                                        # recognized until it is powered off or re-inserted.

    main_battery_monitor = initialize_main_battery_monitor( MAIN_BATTERY_MONITOR_PIN )
    if main_battery_monitor:
        main_battery_voltage = check_battery_voltage( main_battery_monitor )
        print( "main_battery_voltage == {}".format( main_battery_voltage ))

    touch_controller, cap_touch_present = initialize_touch_screen( spi_bus, i2c_bus )
    if touch_controller or screen_present( SCREEN_RESET_PIN ):
        print( "Display detected." )
        display = initialize_display( spi_bus )
        drone_mode = False
        display_group_table = initialize_display_group( display )
        text_group = create_table_screen( display, display_group_table )
        #text_group[6].text = "GPS:"
        gc.collect()
        welcome_group = create_welcome_screen( display )
        display.show( welcome_group )
    else:
        display = False
        print( "Display not detected. Operating without display." )
        drone_mode = True

    if not drone_mode:
        with digitalio.DigitalInOut( board.D12 ) as pushbutton:
            pushbutton.direction = digitalio.Direction.INPUT
            pushbutton.pull = digitalio.Pull.UP
            time.sleep( 0.1 )
            if not pushbutton.value:
                Mode.instrument = AUX
                Mode.display = display_clock
                Mode.data = PAUSE
                print( "set clock mode" )
                set_clock(pushbutton, i2c_bus, spi_bus, touch_controller, cap_touch_present, display)
            else:
                pass
                # boot into the following modes
    Mode.instrument = BLUE
    Mode.data = RECORD
    Mode.display = display_table

    # initialize devices
    sample_indicator_LED = initialize_discrete_LED( SAMPLE_INDICATOR_LED_PIN )
    if sample_indicator_LED:
        sample_indicator_LED.value = ON
        time.sleep( 0.1 )
        sample_indicator_LED.value = OFF

    keys = initialize_button( PUSHBUTTON_PIN )

    gc.collect()
    ### initialize real time hardware clock, and
    ### use it as the source for the microcontroller real time clock
    hardware_clock, hardware_clock_battery_OK = initialize_real_time_clock( i2c_bus )
    if hardware_clock:
        system_clock = rtc.RTC()
        system_clock.datetime = hardware_clock.datetime
    print( "Today is {}". format( DAYS[hardware_clock.datetime.tm_wday] ))
    # check config file
    desired_sample_interval_s = 1
    if sdcard:
        ( desired_sample_interval_s,
            averaging_number_of_samples,
            averaging_count_down,
            count_down_step_s ) = check_STELLA_config()
        write_header = initialize_data_file()
        #print( "write header == {}".format( write_header ))
    if i2c_bus:
        ST_sensor =     ST_sensor_c ( i2c_bus )
        AT_sensor =     AT_sensor_c ( i2c_bus )
        WX_sensor =     WX_sensor_c ( i2c_bus )
        Li_sensor =     Li_sensor_c ( i2c_bus )
        VIS_sensor =    VIS_sensor_c( i2c_bus )
    else:
        ST_sensor = False
        AT_sensor = False
        WX_sensor = False
        Li_sensor = False
        VIS_sensor = False
    try:
        print( Li_sensor.module_type )
        Li_sensor_present = True
        text_group[6].text = "Range:"
        text_group[6].x = text_group[6].x - 10
    except AttributeError:
        print( "no LI sensor")
        Li_sensor_present = False
    print( "Li_sensor_present == {}".format( Li_sensor_present ))
    #stall()
    if uart_nir:
        NIR_sensor =    NIR_sensor_c( uart_nir )
    else:
        NIR_sensor = False
    if uart_gps:
        GPS_sensor =    GPS_sensor_c( uart_gps )
        #print( "GPS_sensor.gps_present {}".format( GPS_sensor.gps_present ))
    else:
        GPS_sensor = False
    #print( "ST {}, AT {}, WX {}, Li {}, VIS {}, NIR {}, GPS {}" .format( ST_sensor, AT_sensor, WX_sensor, Li_sensor, VIS_sensor, NIR_sensor, GPS_sensor ))
    sensor_dictionary = { 'ST':ST_sensor, 'AT':AT_sensor,
                        'WX':WX_sensor, 'Li':Li_sensor,
                        'VIS':VIS_sensor, 'NIR':NIR_sensor,
                        'GPS':GPS_sensor, 'HC':hardware_clock,
                        'MB':main_battery_monitor
                        }
    print( "drone mode == {}".format( drone_mode ))
    gc.collect()

    if drone_mode:
        utilities_list = { 'SI':sample_indicator_LED, 'DM':drone_mode, 'DSI':desired_sample_interval_s, 'LiP':Li_sensor_present }
        instrument_task = asyncio.create_task( instrument( sensor_dictionary, utilities_list ))
        await asyncio.gather( instrument_task )
    else: # if not drone mode...
        utilities_list = { 'SI':sample_indicator_LED, 'DGT':display_group_table,'DISP':display,'TG':text_group, 'DM':drone_mode, 'DSI':desired_sample_interval_s, 'LiP':Li_sensor_present }
        display.show( display_group_table )
        create_telltale( display_group_table )
        create_or_update = CREATE
        show_record_pause_icon( display_group_table, Mode.instrument, create_or_update )
        create_or_update = UPDATE
        welcome_group_length = len(welcome_group)
        #print( "length of welcome group is {}".format( welcome_group_length ))
        for i in range (0, welcome_group_length):
            welcome_group.pop()
            #print( "pop" )
        del welcome_group
        show_mode_task = asyncio.create_task( show_mode( display_group_table, create_or_update ))
        touch_task = asyncio.create_task( check_touch( touch_controller, cap_touch_present ))
        button_task = asyncio.create_task( check_button( keys ))
        instrument_task = asyncio.create_task( instrument( sensor_dictionary, utilities_list ))
        await asyncio.gather( button_task, touch_task, instrument_task, show_mode_task )


### define async instrument loop ###
async def instrument( sensor_dictionary, utilities_list ):
    text_group = (utilities_list['TG'])
    drone_mode = (utilities_list['DM'])
    operational = True
    startup = True
    write_data = True
    loop_count = 0
    desired_sample_interval = 1
    create_or_update = UPDATE
    timestamp = sensor_dictionary['HC'].datetime
    batch_number = update_batch( timestamp )

    Mode.data = RECORD
    last_data_mode = Mode.data

    while operational:
        sample_indicator_LED = utilities_list['SI']

        ## always update time and GPS
        last_sample_time_s = time.monotonic()
        gc.collect()
        current_memory_free = gc.mem_free()/1000
        print("\nmemory free {:.2f} kB, {:.2f} %\n".format( current_memory_free, 100*current_memory_free/start_memory_free ))
        timestamp = sensor_dictionary['HC'].datetime
        iso8601_utc = "{:04}{:02}{:02}T{:02}{:02}{:02}Z".format(
            timestamp.tm_year, timestamp.tm_mon, timestamp.tm_mday,
            timestamp.tm_hour, timestamp.tm_min, timestamp.tm_sec )
        decimal_hour = timestamp_to_decimal_hour( timestamp )
        weekday = DAYS[ timestamp.tm_wday ]
        sensor_dictionary['GPS'].update()
        print( "instrument running, loop {}".format( loop_count ))#, timestamp {}".format( loop_count, iso8601_utc ))

        ## always read sensors
        air_temperature_C       = sensor_dictionary['AT'].read()
        await asyncio.sleep(0)
        surface_temperature_C   = sensor_dictionary['ST'].read()
        await asyncio.sleep(0)
        ST_sensor_temperature_C = sensor_dictionary['ST'].read_sensor_temperature()
        await asyncio.sleep(0)
        relative_humidity_percent, barometric_pressure_hPa, altitude_m = sensor_dictionary['WX'].read()
        await asyncio.sleep(0)
        range_m                 = sensor_dictionary['Li'].read()
        await asyncio.sleep(0)
        visible_irradiance_uW_per_cm_squared    = sensor_dictionary['VIS'].read()
        await asyncio.sleep(0)
        nir_irradiance_uW_per_cm_squared        = sensor_dictionary['NIR'].read()
        await asyncio.sleep(0)
        gps_data                                = sensor_dictionary['GPS'].read()
        await asyncio.sleep(0)
        main_battery_voltage                    = check_battery_voltage( sensor_dictionary['MB'] )
        await asyncio.sleep(0)

        ## always mirror data over usb
        mirror_data_over_usb( DEVICE_TYPE, SOFTWARE_VERSION_NUMBER,
            UID, timestamp, decimal_hour, batch_number,
            visible_irradiance_uW_per_cm_squared, nir_irradiance_uW_per_cm_squared,
            surface_temperature_C, air_temperature_C, relative_humidity_percent,
            barometric_pressure_hPa, range_m, gps_data, main_battery_voltage
            )

        if Mode.instrument == YELLOW or Mode.instrument == GREEN:
            if Mode.data == RECORD:
                batch_number = update_batch( timestamp )
        if Mode.data == RECORD and Mode.instrument == BLUE:
            if last_data_mode != RECORD:
                batch_number = update_batch( timestamp )
            last_data_mode = Mode.data

        ## if in record mode, write data to file
        if Mode.data == RECORD:
            write_line_success = write_data_to_file( DEVICE_TYPE, SOFTWARE_VERSION_NUMBER, UID, timestamp, decimal_hour, batch_number,
                visible_irradiance_uW_per_cm_squared, nir_irradiance_uW_per_cm_squared, range_m,
                surface_temperature_C, air_temperature_C, relative_humidity_percent,
                barometric_pressure_hPa, altitude_m, gps_data,
                main_battery_voltage, sample_indicator_LED )

        ## if not drone mode, display data and battery message in display table
        if not drone_mode:
            ## populate display table
            populate_table_values( utilities_list['TG'], UID, timestamp, decimal_hour, batch_number,
                visible_irradiance_uW_per_cm_squared, nir_irradiance_uW_per_cm_squared,
                surface_temperature_C, air_temperature_C, range_m, utilities_list['LiP'] )
            if main_battery_voltage < LOW_BATTERY_VOLTAGE:
                low_battery_voltage_notification( text_group )

        if Mode.instrument == GREEN and Mode.data == RECORD:
                ## sample and average sequence
                ( desired_sample_interval_s,
                    averaging_number_of_samples,
                    averaging_count_down,
                    count_down_step_s ) = check_STELLA_config()
                print( "sample and average here" )
                sampling_index = 0
                gc.collect()
                print( "take samples and average them, write to special file" )
                count_down_index = averaging_count_down
                VIS_sensor_temperature, NIR_sensor_temperature = 0, 0 # = get_spectral_sensor_temperatures( VIS_sensor, NIR_sensor )
                header_values = ( UID, batch_number, iso8601_utc, surface_temperature_C, air_temperature_C, relative_humidity_percent, VIS_sensor_temperature, NIR_sensor_temperature )
                sampling_filename = create_sampling_file( DEVICE_TYPE, SOFTWARE_VERSION_NUMBER, UID, batch_number, timestamp, decimal_hour, header_values )
                if not drone_mode:
                    display = utilities_list['DISP']
                    sampling_group = create_sampling_overlay( display )
                    sampling_text_area = create_sampling_text( count_down_index, count_down_step_s, display )
                sampling_index = averaging_number_of_samples
                sampling_text = ("SAMPLE\n   {}".format( sampling_index ))
                gc.collect()
                print( "Memory free right before create sampling text area == {} kB".format(gc.mem_free()/1000))
                sample_average = [ 0,0,0,0,0,0,0,0,0,0,0,0 ]
                gc.collect()
                while sampling_index > 0:
                    if not drone_mode:
                        if sampling_index > 9:
                            sampling_text_area.text = ("SAMPLE\n  {}".format( sampling_index ))
                        else:
                            sampling_text_area.text = ("SAMPLE\n   {}".format( sampling_index ))
                    visible_irradiance_uW_per_cm_squared = sensor_dictionary['VIS'].read()
                    nir_irradiance_uW_per_cm_squared = sensor_dictionary['NIR'].read()
                    write_sampling_line_to_file( DEVICE_TYPE, SOFTWARE_VERSION_NUMBER, UID, batch_number, iso8601_utc,
                        utilities_list['SI'], sampling_filename, sampling_index,
                        visible_irradiance_uW_per_cm_squared, nir_irradiance_uW_per_cm_squared )
                    spectral_samples = [0,0,0,0,0,0,0,0,0,0,0,0]
                    for i, v in enumerate( visible_irradiance_uW_per_cm_squared ):
                        spectral_samples[ i ] = visible_irradiance_uW_per_cm_squared[ i ]
                    for i, v in enumerate( nir_irradiance_uW_per_cm_squared ):
                        spectral_samples[ i + 6] = nir_irradiance_uW_per_cm_squared[ i ]
                    print( spectral_samples )
                    for i,v in enumerate( spectral_samples ):
                        sample_average[ i ] = sample_average[ i ] + v
                    sampling_index = sampling_index - 1
                for i,v in enumerate( sample_average ):
                    sample_average[ i ] = int( round( sample_average[ i ]/ averaging_number_of_samples, 1 ))
                write_tail_of_sampling_file( DEVICE_TYPE, SOFTWARE_VERSION_NUMBER, UID, batch_number, iso8601_utc,
                    utilities_list['SI'], sampling_filename, averaging_number_of_samples,
                    sample_average, VIS_sensor_temperature, NIR_sensor_temperature, surface_temperature_C,
                    air_temperature_C, relative_humidity_percent, range_m
                    )
                gc.collect()
                del sampling_group
                del header_values
                del sample_average
                time_begin_sdev = time.monotonic()
                sampling_text_area.text = ( "ST DEV\n CALC" )
                gc.collect()
                print( "make function call to calculate standard deviations, with {} kB free of {} kB total".format( gc.mem_free()/1000, (gc.mem_alloc()+gc.mem_free())/1000 ))
                success = calculate_and_write_standard_deviations( UID, batch_number, sampling_filename )
                if success:
                    sampling_text_area.text = ( "SUCCESS\n      " )
                else:
                    sampling_text_area.text = ( "No SDV\n      " )
                time.sleep(0.5)
                time_stop_sdev = time.monotonic()
                print( "elapsed time to process standard deviation == {} s".format( time_stop_sdev - time_begin_sdev))
                display.show( utilities_list['DGT'] )
                ## end sample and average sequence

        if False:
            if gps_data is None:
                gps_msg = "none"
            else:
                if gps_data[0]:
                    gps_msg = "<FIX> "
                else:
                    gps_msg = "nofix  "

        if Mode.instrument == YELLOW or Mode.instrument == GREEN:
            Mode.data = PAUSE
        if Mode.data == PAUSE:
            last_data_mode = Mode.data


        ## end loop with wait
        remaining_wait_time = utilities_list['DSI'] - (time.monotonic() - last_sample_time_s)
        while remaining_wait_time > 0:
            remaining_wait_time = utilities_list['DSI'] - (time.monotonic() - last_sample_time_s)
            #print( "remaining_wait_time == {:}".format(remaining_wait_time))
            await asyncio.sleep( 0.01 )
        loop_count += 1

### define async event loops ###

async def show_mode( display_group_table, create_or_update ):
    while True:
        await asyncio.sleep( 0 )
        show_telltale( display_group_table, Mode.instrument )
        await asyncio.sleep( 0 )
        show_record_pause_icon( display_group_table, Mode.data, create_or_update )
        await asyncio.sleep( 0 )

async def check_button( keys ):
    while True:
        event = keys.events.get()
        if event:
            if event.pressed and event.key_number == 0:
                if Mode.instrument == BLUE:
                    Mode.data = (Mode.data + 1) % 2 #Mode.number_of_data_modes
                elif Mode.instrument == YELLOW:
                    Mode.data = RECORD #record once and stop
                elif Mode.instrument == GREEN:
                    Mode.data = RECORD #sample and average and stop
                #Mode.data = (Mode.data + 1) % Mode.number_of_data_modes
                print("data_mode == ", Mode.data )
        await asyncio.sleep( 0 )

async def check_touch( touch_controller, cap_touch_present ):
    while True:
        if touch_controller and cap_touch_present:
            try:
                if touch_controller.touched:
                    touch_values = touch_controller.touches
                    #print( touch_values )
                    if touch_values[0]:
                        touch_x = int(touch_values[0]['y']) #transpose
                        touch_y = int(touch_values[0]['x'])
                        print( touch_x, touch_y )
                        #print("do mode changes here")
                        if touch_y in range ( 110, 250 ):
                            print( "upper" )
                            last_mode = Mode.instrument
                            if touch_x in range ( 0, 119 ):
                                #print( "yellow" )
                                Mode.instrument = YELLOW
                                Mode.data = PAUSE
                                last_mode = YELLOW
                            if touch_x in range ( 120, 204 ):
                                #print( "blue" )
                                Mode.instrument = BLUE
                                if last_mode != BLUE:
                                    Mode.data = RECORD
                                else:
                                    Mode.data = (Mode.data + 1) % 2 #Mode.number_of_data_modes
                                last_mode = BLUE
                            if touch_x in range ( 205, 330 ):
                                #print( "green" )
                                Mode.instrument = GREEN
                                Mode.data = PAUSE
                                last_mode = GREEN
                        print( "Instrument mode == {}".format (Mode.instrument))
                timeout_ms = 0
                while touch_controller.touched and timeout_ms < 200:
                    timeout_ms += 1
                    await asyncio.sleep( 0.001 )
            except (OSError, IndexError):
                pass
            await asyncio.sleep( 0 )


### define sensor classes ###
class GPS_sensor_c:
    def __init__(self, uart_gps):
        if uart_gps:
            try:
                self.gps_sensor = adafruit_gps.GPS(uart_gps, debug=False)
                self.gps_sensor.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
                self.gps_sensor.send_command(b"PMTK220,1000")
                self.gps_sensor.send_command(b"PMTK605")  # request firmware version
                data = self.gps_sensor.read(32)  # read up to 32 bytes
                # print(data)  # this is a bytearray type
                if data is not None:
                    # convert bytearray to string
                    data_string = "".join([chr(b) for b in data])
                    print( "GPS present: {}...".format(data_string[0:4]))
                    if data_string[0] == '$':
                        self.gps_present = True
                        print( "self.gps_present = True" )
                    else:
                        self.gps_present = False
                        print( "self.gps_present = False" )
                else:
                    #print( "no data on firmware" )
                    self.gps_sensor = False

            except ValueError:
                self.gps_sensor = False
        else:
            self.gps_sensor = False

    def update(self):
        self.gps_sensor.update()
        #print( "gps update()1" )

    def read(self):
        fix = False
        lat = 0
        long = 0
        self.gps_sensor.update()
        #print( "gps update()2" )
        #print("self.gps_sensor.has_fix {}".format(self.gps_sensor.has_fix))
        if self.gps_sensor.has_fix:
            self.satellites = self.gps_sensor.satellites
            print("# satellites: {}".format(self.gps_sensor.satellites))
            print("Latitude: {0:.6f} degrees".format(self.gps_sensor.latitude))
            print("Longitude: {0:.6f} degrees".format(self.gps_sensor.longitude))
            fix = True
            lat = self.gps_sensor.latitude
            lon = self.gps_sensor.longitude
            print(
                "Precise Latitude: {:2.}{:2.4f} degrees".format(
                self.gps_sensor.latitude_degrees, self.gps_sensor.latitude_minutes )
                )
            print(
                "Precise Longitude: {:2.}{:2.4f} degrees".format(
                    self.gps_sensor.longitude_degrees, self.gps_sensor.longitude_minutes )
                )

            print(
                "Fix timestamp: {}/{}/{} {:02}:{:02}:{:02}".format(
                    self.gps_sensor.timestamp_utc.tm_mon,  # Grab parts of the time from the
                    self.gps_sensor.timestamp_utc.tm_mday,  # struct_time object that holds
                    self.gps_sensor.timestamp_utc.tm_year,  # the fix time.  Note you might
                    self.gps_sensor.timestamp_utc.tm_hour,  # not get all data like year, day,
                    self.gps_sensor.timestamp_utc.tm_min,  # month!
                    self.gps_sensor.timestamp_utc.tm_sec,
                    )
                )
        else:
            fix = False
            lat = False
            long = False

        return( fix, lat, long )

class NIR_sensor_c:
    def __init__(self, uart_nir):
        if not uart_nir:
            self.as_sensor = False
        else:
            self.as_sensor = uart_nir           # as7263 NIR spectrum sensor on uart
            self.as_sensor.write(b"AT\n")
            data = self.as_sensor.readline() #typical first response from the device is b'ERROR\n', which indicates it is present.
            if data is None:
                print ( "Error: near infrared spectrum sensor fail" )
                return False
            else:
                #print( "\nSet near infrared spectral sensor to 16x gain and 166 ms integration time, because those are the values used at the factory during the sensor calibration." )
                # initialized near infrared spectrum sensor
                # check gain setting
                b = b"ATGAIN\n"
                self.as_sensor.write(b)
                data = str( self.as_sensor.readline() )[2]
                #print( "default gain setting = {}, where 0 is 1x gain, 1 is 3.7x gain, 2 is 16x gain, and 3 is 64x gain".format( data ))

                b = b"ATGAIN=2\n"
                self.as_sensor.write(b)
                data = str( self.as_sensor.readline() )[2:4]
                #print( "gain setting successful == {}".format( data ))

                b = b"ATGAIN\n"
                self.as_sensor.write(b)
                gain_set = int(str( self.as_sensor.readline() )[2])
                gain = 0
                if gain_set == 0:
                    gain = 1
                elif gain_set == 1:
                    gain = 3.7
                elif gain_set == 2:
                    gain = 16
                elif gain_set == 3:
                    gain = 64
                #print( "updated gain setting = {}, where 0 is 1x gain, 1 is 3.7x gain, 2 is 16x gain, and 3 is 64x gain".format( gain ))

                #check integration time setting
                b = b"ATINTTIME=166\n"
                self.as_sensor.write(b)
                data = self.as_sensor.readline()

                b = b"ATINTTIME\n"
                self.as_sensor.write(b)
                int_time = str( self.as_sensor.readline() )[2:6]
                #print( "updated integration time setting = {}ms".format( int_time ))
                print( "NIR sensor gain = {}x, integration time = {}ms".format( gain, int_time ))
                # print( "# NIR spectrum default INTTIME (59 * 2.8ms = 165ms): {:}".format(data))

    def read( self ):
        # returns: R_610nm, S_680nm, T_730nm, U_760nm, V_810nm, W_860nm
        if not self.as_sensor:
            datalist_nir = [0 for x in NIR_BANDS]
        else:
            decimal_places = 1
            b = b"ATCDATA\n"
            self.as_sensor.write(b)
            data = self.as_sensor.readline()
            if data is None:                    #if returned data is of type NoneType
                print( "Alert: Sensor miswired at main instrument board, or not properly modified for uart usage" )
                print( "Enable serial communication via uart by removing solder from the jumpers labeled JP1," )
                print( "and add solder to the jumper labeled JP2 (on the back of the board)" )
                return [0 for x in NIR_BANDS]
            else:
                #print(gc.mem_free())
                datastr = data.decode("utf-8")
                #datastr = "".join([chr(b) for b in data]) # convert bytearray to string
                datastr = datastr.rstrip(" OK\n")
                if datastr == "ERROR":
                    print("Error: NIR read")
                    return [0 for x in NIR_BANDS]
                # convert to float, and round, in place
                datalist_nir = datastr.split( ", " )
                for n, value in enumerate(datalist_nir): # should be same number as items in NIR_BANDS
                    try:
                        as_float = float( value )
                        value = int( round( as_float, decimal_places ))
                        if value > MAX_VALUE:
                            value = MAX_VALUE
                    except ValueError:
                        print("Failed to convert '{:}' to a float") # only during verbose/development
                        value = 0
                    # After converting to float, element {:} of the list is: {:0.1f} and is type".format( n, datalist_nir[n] ) )
                    datalist_nir[n] = value
            # R_610nm, S_680nm, T_730nm, U_760nm, V_810nm, W_860nm
            if HUGE_VALUE:
                datalist_nir = [HUGE_VALUE for x in NIR_BANDS]
        return datalist_nir

class VIS_sensor_c:
    def __init__(self, i2c_bus):
        if not i2c_bus:
            self.as_sensor = False
        else:
            try:
                self.as_sensor = adafruit_as726x.AS726x_I2C( i2c_bus )
                #print( "\nSet visible spectral sensor to 16x gain and 166 ms integration time, because those are the values used at the factory during the sensor calibration." )
                self.as_sensor.conversion_mode = self.as_sensor.MODE_2
                #print( "Default Gain = {}".format( self.as_sensor.gain ))
                self.as_sensor.gain = 16
                #print( "Gain Now = {}".format( self.as_sensor.gain ))
                #print( "Default Integration Time = {} ms".format( self.as_sensor.integration_time ))
                self.as_sensor.integration_time = 166 # from 1 to 714 = 255 * 2.8ms ms
                #print( "Integration Time Now = {} ms".format( self.as_sensor.integration_time ))
                print( "VIS sensor gain = {}x, integration time = {} ms".format( self.as_sensor.gain, self.as_sensor.integration_time ))
            except ValueError as err:
                #print( "Error: visible spectrum sensor fail: {:}".format(err) )
                self.as_sensor = False

    def read( self ):
        decimal_places = 1
        # returns readings in a tuple, six channels of data
        # Calibration information from AS7262 datasheet:
        # Each channel is tested with GAIN = 16x, Integration Time (INT_T) = 166ms and VDD = VDD1 = VDD2 = 3.3V, TAMB=25°C.
        # The accuracy of the channel counts/μW/cm2 is ±12%.
        # Sensor Mode 2 is a continuous conversion of light into data on all 6 channels
        # 450nm, 500nm, 550nm, 570nm, 600nm and 650nm
        # sensor.violet returns the calibrated floating point value in the violet channel.
        # sensor.raw_violet returns the uncalibrated decimal count value in the violet channel.
        # that syntax is the same for each of the 6 channels

        # NOTE: the library was written for the visible sensor, as7262.
        # The library works exactly the same for the near infrared sensor, as7263,
        # but the band names are called as if the sensor were the visible one.
        if self.as_sensor:
            try:
                while not self.as_sensor.data_ready:
                    time.sleep(0.01)
                initial_read_time_s = time.monotonic()
                violet_calibrated = int( round( self.as_sensor.violet, decimal_places ))
                if violet_calibrated > MAX_VALUE:
                    violet_calibrated = MAX_VALUE
                blue_calibrated = int( round( self.as_sensor.blue, decimal_places ))
                if blue_calibrated > MAX_VALUE:
                    blue_calibrated = MAX_VALUE
                green_calibrated = int( round( self.as_sensor.green, decimal_places ))
                if green_calibrated > MAX_VALUE:
                    green_calibrated = MAX_VALUE
                yellow_calibrated = int( round( self.as_sensor.yellow, decimal_places ))
                if yellow_calibrated > MAX_VALUE:
                    yellow_calibrated = MAX_VALUE
                orange_calibrated = int( round( self.as_sensor.orange, decimal_places ))
                if orange_calibrated > MAX_VALUE:
                    orange_calibrated = MAX_VALUE
                red_calibrated = int( round( self.as_sensor.red, decimal_places ))
                if red_calibrated > MAX_VALUE:
                    red_calibrated = MAX_VALUE
                final_read_time_s = time.monotonic()
                read_time_s = final_read_time_s - initial_read_time_s
                #print( "Sensor read time s = {}".format( read_time_s ))
                spectral_tuple = ( violet_calibrated, blue_calibrated, green_calibrated, yellow_calibrated, orange_calibrated, red_calibrated )
                if HUGE_VALUE:
                    spectral_tuple = [ HUGE_VALUE for x in VIS_BANDS]
            except ValueError as err:
                print( "Error: spectral sensor fail: {:}".format(err) )
                spectral_tuple = [0 for x in VIS_BANDS]
        else:
            spectral_tuple = [0 for x in VIS_BANDS]
        return spectral_tuple

class Li_sensor_c:
    def __init__(self, i2c_bus):
        if i2c_bus:
            try:
                self.vl53_sensor = adafruit_vl53l4cd.VL53L4CD( i2c_bus )
                self.model_id, self.module_type = self.vl53_sensor.model_info
                self.vl53_sensor.start_ranging()
                print( "LiDAR present: model ID = {}, module type: {}".format( self.model_id, self.module_type ))
                if self.module_type != 170:
                    self.vl53_sensor = False
            except (ValueError, OSError):
                self.vl53_sensor = False
        else:
            self.vl53_sensor = False

    def present( self ):
        return Li_sensor_present

    def read( self ):
        try:
            offset_m = 0.005
            while not self.vl53_sensor.data_ready:
                #await asyncio.sleep( 0.001 )
                pass
            self.vl53_sensor.clear_interrupt()
            distance_m = self.vl53_sensor.distance * 10 / 1000
            distance_m = distance_m + offset_m
            if distance_m > offset_m:
                pass
            else:
                distance_m = 0
        except AttributeError:
            distance_m = 0
        return distance_m

class WX_sensor_c:
    def __init__(self, i2c_bus):
        if not i2c_bus:
            self.bme_sensor = False
        else:
            try:
                self.bme_sensor = adafruit_bme280.Adafruit_BME280_I2C( i2c_bus )
                # initialized weather sensor
            except ( ValueError, RuntimeError ) as err:
                #print( "Error: weather sensor fail {:}".format(err) )
                self.bme_sensor = False

    def read( self ):
        decimal_places = 1
        if self.bme_sensor:
            try:
                relative_humidity_percent = int(round( self.bme_sensor.humidity, decimal_places ))
                barometric_pressure_hPa = int(round( self.bme_sensor.pressure, decimal_places ))
                altitude_m = round( self.bme_sensor.altitude, decimal_places )
            except ValueError:
                print( "Error: WX sensor failed to read:  {:}".format(err) )
        else:
            relative_humidity_percent = 0
            barometric_pressure_hPa = 1
            altitude_m = -500
        return relative_humidity_percent, barometric_pressure_hPa, altitude_m

class ST_sensor_c:
    def __init__(self, i2c_bus):
        if not i2c_bus:
            self.mlx_sensor = False
        else:
            try:
                self.mlx_sensor = adafruit_mlx90614.MLX90614( i2c_bus )
                # initialized thermal infrared sensor
            except ValueError as err:
                #print( "Error: thermal infrared sensor fail: {:}".format(err) )
                self.mlx_sensor = False

    def read( self ):
        if self.mlx_sensor:
            decimal_places = 1
            try:
                surface_temperature_C = self.mlx_sensor.object_temperature
                surface_temperature_C = round( surface_temperature_C, decimal_places )
                return surface_temperature_C
            except ValueError as err:
                print( "Error: thermal infrared sensor fail: {:}".format(err) )
                return -273
        else:
            return -273

    def read_sensor_temperature( self ):
        if self.mlx_sensor:
            decimal_places = 1
            try:
                ambient_temperature_C = self.mlx_sensor.ambient_temperature
                ambient_temperature_C = round( ambient_temperature_C, decimal_places )
                return ambient_temperature_C
            except ValueError as err:
                print( "Error: thermal infrared sensor fail: {:}".format(err) )
                return -273
        else:
            return -273

    def margin():
        return 1.0

    def units():
        return "C"

    def readScientific():
        value = self.read()
        #return ScientificValue(value, self.margin(), self.units())
        return (value, self.margin(), self.units())

class AT_sensor_c:
    def __init__(self, i2c_bus):
        if not i2c_bus:
            self.mcp_sensor = False
        else:
            try:
                self.mcp_sensor = adafruit_mcp9808.MCP9808( i2c_bus )
                # initialized air temperature sensor
            except ValueError as err:
                self.mcp_sensor = False

    def read(self):
        if self.mcp_sensor:
            # mcp9808 datasheet: accuracy +/- 0.25 C
            decimal_places = 1
            try:
                air_temperature_C = round( self.mcp_sensor.temperature, decimal_places )
                return air_temperature_C
            except ValueError as err:
                print( "Error: air temperature sensor fail: {:}".format(err) )
                return -273
        else:
            return -273

    def margin():
        return 0.25

    def units():
        return "C"

    def readScientific():
        value = self.read()
        #return ScientificValue(value, self.margin(), self.units())
        return (value, self.margin(), self.units())

class ScientificValue:
    def __init__ (self):
        pass
    def value():
        return self.value
    def units():
        return self.units
    def variation():
        return self.variation
    def margin():
        return self.margin


### define background functions ###
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

def pushbutton_pressed( pushbutton ):
    pushbutton_press_state = not pushbutton.value   #active low, so True is notpushed and False is pushed
    return pushbutton_press_state                   #pushbutton_press_state is True if button is being pushed

def set_clock(pushbutton, i2c_bus, spi_bus, touch_controller, cap_touch_present, display):
    set_clock = True
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
    if set_clock:
        timestamp = hardware_clock.datetime
        weekday = DAYS[timestamp.tm_wday]
        print( "create set clock display screen" )
        set_clock_group = create_set_clock_screen( display )

        year_minimum = 2023
        year_maximum = 2030
        year_group = displayio.Group( scale=2, x=20, y=30 )
        year_setting = timestamp.tm_year
        if year_setting < year_minimum:
            year_setting = year_minimum
        if year_setting > year_maximum:
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
        weekday_text = DAYS[ weekday_setting ]
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
            cbat_ok_text = "<LOW>"
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
                    if True: #touch_values[0]:
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
                        if touch_x in range( 10, 170 ): # working in the time columns
                            if touch_y in range (55, 130): # working in the time row
                                if touch_x < 70:
                                    set_clock_mode = sc_hour
                                elif touch_x in range( 71, 120):
                                    set_clock_mode = sc_min
                                elif touch_x in range( 130, 160 ):
                                    set_clock_mode = sc_sec
                        elif touch_x > 200: # working in buttons column
                            if touch_y in range( 89, 155 ):
                                touch_up = True
                            elif touch_y < 89:
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
            weekday_text_area.text = DAYS[ weekday_setting ]

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
        '''
        displayio.release_displays()
        i2c_bus.unlock()
        spi_bus.unlock()
        return board.SCL
        return board.SDA
        '''

def calculate_and_write_standard_deviations( UID, batch_number, filename ):
    try:
        with open( filename, "r") as sf:
            sf.readline() #throw away the header line
            line = sf.readline().split(',')
            number_of_samples = int( line[ 2 ] )
            #print( "number of samples == {}".format( number_of_samples ))
            number_of_channels = 12
            sf.close()
            stdev_list = []
            stdev_list=[str(UID), str(batch_number),"standard_deviation"]
            for n in range( 0, number_of_channels ):
                #print( "n == {}".format( n ))
                with open( filename, "r") as sf:
                    dataline=[]
                    sf.readline() #throw away the header line
                    for i in range( 0, number_of_samples ):
                        #print( "i == {}".format( i ))
                        dataline.append( int((sf.readline().split(','))[ n + 3 ]))
                        #print( dataline )
                    #print( dataline )
                    stdev_list.append( "{}".format( ulab.numpy.std( dataline )))
                sf.close()
            print( stdev_list )
            print( "STANDARD DEVIATION SUCCESS!" )

        with open( filename, "a") as sf:
            #sf.write("\n")
            for i,value in enumerate( stdev_list ):
                sf.write( "{},".format( value ))
            sf.close()
        return True
    except (MemoryError, IndexError) as err:
        print( "{}: could not complete standard deviation operation".format(err) )
        time.sleep(2)
        return False

def alternate_screen_present( IO_pin ):
    display_check = digitalio.DigitalInOut( IO_pin )
    display_check.direction = digitalio.Direction.INPUT
    display_check.pull = digitalio.Pull.DOWN
    if display_check.value:
        return True
    else:
        return False

def create_sampling_overlay( display ):
    sampling_group = initialize_display_group( display )
    border_color = 0xFF0022 # red
    block_color = 0x0000FF # blue
    if (display == False) or ( sampling_group == False):
        print("No display")
        return
    block = displayio.Palette(1)
    block[0] = block_color
    rectangle = vectorio.Rectangle(pixel_shader=block, width=320, height=180, x=0, y=30)
    sampling_group.append( rectangle )
    return sampling_group

def create_sampling_text(wait_count, count_down_step_s, display):
    count = wait_count
    text_group = displayio.Group( scale=6, x=40, y=60 )
    text = "WAIT"
    text_area = label.Label( terminalio.FONT, text=text, color=0xFFFFFF )
    text_group.append( text_area ) # Subgroup for text scaling
    display.show(text_group)
    while count > 0:
        time.sleep( count_down_step_s)
        count -= 1
        print(count)
        text_area.text = ("WAIT {}".format(count))
    #text_group.scale = 4
    return text_area

def write_tail_of_sampling_file( DEVICE_TYPE, SOFTWARE_VERSION_NUMBER, UID, batch_number, iso8601_utc,
    sample_indicator, sampling_filename, averaging_number_of_samples,
    sample_average, VIS_sensor_temperature, NIR_sensor_temperature, surface_temperature_C,
    air_temperature_C, relative_humidity_percent, range_m
    ):
    gc.collect()
    if sample_indicator:
        sample_indicator.value = ON
    try:
        with open( sampling_filename, "a" ) as sf:
            sf.write( str( UID ))
            sf.write(",")
            sf.write( str( batch_number ))
            sf.write( ", average, " )
            for i,v in enumerate( sample_average ):
                sf.write( str(v) )
                #if i < len(sample_average)-1: # no trailing ','
                sf.write(",")
            #sf.write( "\n" )
            sf.write( " {}, {}, {}, {}, {}, {}, {}, {}, {}\n".format(
                VIS_sensor_temperature, NIR_sensor_temperature, surface_temperature_C,
                air_temperature_C, relative_humidity_percent, range_m, iso8601_utc, DEVICE_TYPE, SOFTWARE_VERSION_NUMBER
                ))
        if sample_indicator:
            sample_indicator.value = OFF
        return True
    except OSError:
        return False

def write_sampling_line_to_file( DEVICE_TYPE, SOFTWARE_VERSION_NUMBER, UID, batch_number, iso8601_utc, sample_indicator, sampling_filename, sampling_index, visible_spectrum_uW_per_cm_squared, nir_spectrum_uW_per_cm_squared ):
    gc.collect()
    with open( sampling_filename, "r" ) as sf:
        sf.flush()
        sf.close()

    if sample_indicator:
        sample_indicator.value = ON
    try:
        with open( sampling_filename, "a" ) as sf:
            sf.write( str( UID ))
            sf.write(",")
            sf.write( str( batch_number ))
            sf.write( ", " )
            sf.write( str( sampling_index ))
            sf.write( ", " )
            for i,v in enumerate(visible_spectrum_uW_per_cm_squared):
                sf.write( str(v) )
                sf.write(",")
            for i,v in enumerate(nir_spectrum_uW_per_cm_squared):
                sf.write( str(v) )
                #if i < len(nir_spectrum_uW_per_cm_squared)-1: # no trailing ','
                sf.write(",")
            sf.write( "0, 0, 0, 0, 0, 0, ")
            sf.write( str( iso8601_utc ))
            sf.write( "\n" )
            sf.flush()
            sf.close()
        if sample_indicator:
            sample_indicator.value = OFF
        return True
    except OSError:
        return False

def create_sampling_file( DEVICE_TYPE, SOFTWARE_VERSION_NUMBER, UID, batch_number, timestamp, decimal_hour, values ): # 16 B
    gc.collect()
    sampling_filename = "/sd/{}_{:04}{:02}{:02}_{}.csv".format( UID, timestamp.tm_year, timestamp.tm_mon, timestamp.tm_mday, batch_number)
    try:
        with open( sampling_filename, "w" ) as sf:
            sf.write( "UID, batch_number, sample_number, irradiance_450nm_blue_irradiance_uW_per_cm_squared, irradiance_500nm_cyan_irradiance_uW_per_cm_squared, "
                "irradiance_550nm_green_irradiance_uW_per_cm_squared, irradiance_570nm_yellow_irradiance_uW_per_cm_squared, irradiance_600nm_orange_irradiance_uW_per_cm_squared, "
                "irradiance_650nm_red_irradiance_uW_per_cm_squared, irradiance_610nm_orange_irradiance_uW_per_cm_squared, irradiance_680nm_near_infrared_irradiance_uW_per_cm_squared, "
                "irradiance_730nm_near_infrared_irradiance_uW_per_cm_squared, irradiance_760nm_near_infrared_irradiance_uW_per_cm_squared, "
                "irradiance_810nm_near_infrared_irradiance_uW_per_cm_squared, irradiance_860nm_near_infrared_irradiance_uW_per_cm_squared,  VIS_sensor_temperature_C,  NIR_sensor_temperature_C, "
                "surface_temperature_C, air_temperature_C, relative_humidity_percent, range_m, timestamp_iso8601, "
                "device_type, software_version\n" )
            sf.close()
        return sampling_filename
    except OSError:
        return False


def write_data_to_file( DEVICE_TYPE, SOFTWARE_VERSION_NUMBER, UID, timestamp, decimal_hour, batch_number,
                visible_irradiance_uW_per_cm_squared, nir_irradiance_uW_per_cm_squared, range_m,
                surface_temperature_C, air_temperature_C, humidity_relative_percent,
                barometric_pressure_hPa, altitude_uncalibrated_m, gps_data,
                main_battery_voltage, sample_indicator ):
    # we let operations fail if the sdcard didn't initialize
    need_header = False
    try:
        os.stat( DATA_FILE ) # fail if data.cav file is not already there
        #raise OSError # uncomment to force header everytime
    except OSError:
        if sample_indicator:
            sample_indicator.value = ON
    try:
        # with sys.stdout as f: # uncomment to write to console (comment "with open")
        with open( DATA_FILE, "a" ) as f: # open seems about 0.016 secs.
            if sample_indicator:
                sample_indicator.value = ON
            iso8601_utc = "{:04}{:02}{:02}T{:02}{:02}{:02}Z".format( timestamp.tm_year,
            timestamp.tm_mon, timestamp.tm_mday, timestamp.tm_hour, timestamp.tm_min,
            timestamp.tm_sec
            )
            weekday = DAYS[timestamp.tm_wday]
            decimal_hour = timestamp_to_decimal_hour( timestamp )
            f.write( "{}, {}, {}, {}, {}, {}, {}, ".format( DEVICE_TYPE, SOFTWARE_VERSION_NUMBER, UID, batch_number, weekday, iso8601_utc, decimal_hour ))
            f.write( "{}, 1.0, ".format( surface_temperature_C ))
            f.write( "{}, 0.3, ".format( air_temperature_C ))
            f.write( "{}, 1.8, ".format( humidity_relative_percent ))
            f.write( "{}, 1, ".format( barometric_pressure_hPa ))
            f.write( "{}, 100, ".format( altitude_uncalibrated_m ))
            for i,band in enumerate( VIS_BANDS ):
                f.write( str(VIS_BANDS[ i ]) )
                f.write( ", ")
                f.write( "5, " )
                f.write( str(visible_irradiance_uW_per_cm_squared[ i ] ))
                f.write( ", ")
                f.write( str(visible_irradiance_uW_per_cm_squared[ i ] * 12/100) )
                f.write( ", ")
            for i,band in enumerate( NIR_BANDS ):
                f.write( str(NIR_BANDS[ i ] ))
                f.write( ", ")
                f.write( "5, " )
                f.write( str(nir_irradiance_uW_per_cm_squared[ i ] ))
                f.write( ", ")
                f.write( str( nir_irradiance_uW_per_cm_squared[ i ] * 12/100 ))
                f.write( ", ")
            f.write( "{}, 0.001, ".format( range_m ))
            f.write( "{}".format( main_battery_voltage ))
            f.write("\n")
        if sample_indicator:
            sample_indicator.value = OFF
        return True
    except OSError as err:
        # TBD: maybe show something on the display like sd_full? this will "Error" every sample pass
        # "[Errno 30] Read-only filesystem" probably means no sd_card
        print( "Error: sd card fail: {:} ".format(err) )
        if sample_indicator != False:
            sample_indicator.value = ON #  ant ON to show error, likely no SD card present, or SD card full.
        return False

def mirror_data_over_usb( DEVICE_TYPE, SOFTWARE_VERSION_NUMBER,
    UID, timestamp, decimal_hour, batch_number,
    visible_irradiance_uW_per_cm_squared, nir_irradiance_uW_per_cm_squared,
    surface_temperature_C, air_temperature_C, relative_humidity_percent,
    barometric_pressure_hPa, range_m, gps_data, main_battery_voltage
    ):
    if True: #False:
        gc.collect()
        #print( "memory free immediately before mirror data == {} kB.".format( gc.mem_free()/1000))
        print( "mirror_data", end=", " )
        print( "device_type, {}".format( DEVICE_TYPE ), end=", ")
        print( "software_version, {}".format( SOFTWARE_VERSION_NUMBER ), end=", ")
        print( "UID, {}".format( UID ), end=", ")
        print( "batch, {}".format( batch_number ), end=", ")
        print( "year, {}".format( timestamp.tm_year ), end=", ")
        print( "month, {}".format( timestamp.tm_mon ), end=", ")
        print( "day, {}".format( timestamp.tm_mday ), end=", ")
        print( "hour, {}".format( timestamp.tm_hour ), end=", ")
        print( "min, {}".format( timestamp.tm_min ), end=", ")
        print( "sec, {}".format( timestamp.tm_sec ), end=", ")
        print( "dec_hour, {}".format( decimal_hour ), end=", ")
        print( "v450, {}".format( visible_irradiance_uW_per_cm_squared[ 0 ]), end=", ")
        print( "b500, {}".format( visible_irradiance_uW_per_cm_squared[ 1 ]), end=", ")
        print( "g550, {}".format( visible_irradiance_uW_per_cm_squared[ 2 ]), end=", ")
        print( "y570, {}".format( visible_irradiance_uW_per_cm_squared[ 3 ]), end=", ")
        print( "o600, {}".format( visible_irradiance_uW_per_cm_squared[ 4 ]), end=", ")
        print( "r650, {}".format( visible_irradiance_uW_per_cm_squared[ 5 ]), end=", ")
        print( "610, {}".format( nir_irradiance_uW_per_cm_squared[ 0 ]), end=", ")
        print( "680, {}".format( nir_irradiance_uW_per_cm_squared[ 1 ]), end=", ")
        print( "730, {}".format( nir_irradiance_uW_per_cm_squared[ 2 ]), end=", ")
        print( "760, {}".format( nir_irradiance_uW_per_cm_squared[ 3 ]), end=", ")
        print( "810, {}".format( nir_irradiance_uW_per_cm_squared[ 4 ]), end=", ")
        print( "860, {}".format( nir_irradiance_uW_per_cm_squared[ 5 ]), end=", ")
        print( "surface_temp, {}".format( surface_temperature_C ), end=", ")
        print( "air_temp, {}".format( air_temperature_C ), end=", ")
        print( "rel_humidity, {}".format( relative_humidity_percent ), end=", ")
        print( "range, {:.2f}".format( range_m ), end=", ")
        print( "gps data, {}".format( gps_data ), end=", ")
        print( "main_battery_voltage, {}".format( main_battery_voltage ))
    return True

def update_batch( timestamp ):
    gc.collect()
    datestamp = "{:04}{:02}{:02}".format( timestamp.tm_year, timestamp.tm_mon, timestamp.tm_mday)
    try:
        with open( "/sd/batch.txt", "r" ) as b:
            try:
                previous_batchfile_string = b.readline()
                previous_datestamp = previous_batchfile_string[ 0:8 ]
                previous_batch_number = int( previous_batchfile_string[ 8: ])
            # TBD: catch error when /sd doesn't exist
            except ValueError:
                previous_batch_number = 0
                # corrupted data in batch number file, setting batch to 0
            if datestamp == previous_datestamp:
                # this is the same day, so increment the batch number
                batch_number = previous_batch_number + 1
            else:
                # this is a different day, so start the batch number at 0
                batch_number = 0
    except OSError:
            print( "batch.txt file not found" )
            batch_number = 0
    batch_string = ( "{:03}".format( batch_number ))
    batch_file_string = datestamp + batch_string
    try:
        with open( "/sd/batch.txt", "w" ) as b:
            b.write( batch_file_string )
        # TBD: catch error when /sd doesn't exist
    except OSError as err:
        print("Error: writing batch.txt {:}".format(err) )
        pass
    batch_string = ( "{:}".format( batch_number ))
    return batch_string

def initialize_data_file():
    need_header = False
    try:
        os.stat( DATA_FILE ) # fail if data.csv file is not already there
        #raise OSError # uncomment to force header everytime
        return False
    except OSError:
        # setup the header for first time
        need_header = True
        #print( "need header = True")
        if need_header:
            preheader_mem_free = gc.mem_free()
            #print( "preheader mem free = {}".format(preheader_mem_free))
            gc.collect()
            try:
                with open( DATA_FILE, "w" ) as f:
                    header = (
                    "device_type, software_version, UID, batch_number, weekday, timestamp_iso8601, decimal_hour, "
                    "surface_temperature_C, surface_temperature_uncertainty_C, "
                    "air_temperature_C, air_temperature_uncertainty_C, "
                    "relative_humidity_percent, relative_humidity_uncertainty_percent, "
                    "barometric_pressure_hPa, barometric_pressure_uncertainty_hPa, "
                    "altitude_uncalibrated_m, altitude_uncertainty_m, "
                    "irradiance_450nm_blue_wavelength_nm, irradiance_450nm_blue_wavelength_uncertainty_nm, irradiance_450nm_blue_irradiance_uW_per_cm_squared, irradiance_450nm_blue_irradiance_uncertainty_uW_per_cm_squared, "
                    "irradiance_500nm_cyan_wavelength_nm, irradiance_500nm_cyan_wavelength_uncertainty_nm, irradiance_500nm_cyan_irradiance_uW_per_cm_squared, irradiance_500nm_cyan_irradiance_uncertainty_uW_per_cm_squared, "
                    "irradiance_550nm_green_wavelength_nm, irradiance_550nm_green_wavelength_uncertainty_nm, irradiance_550nm_green_irradiance_uW_per_cm_squared, irradiance_550nm_green_irradiance_uncertainty_uW_per_cm_squared, "
                    "irradiance_570nm_yellow_wavelength_nm, irradiance_570nm_yellow_wavelength_uncertainty_nm, irradiance_570nm_yellow_irradiance_uW_per_cm_squared, irradiance_570nm_yellow_irradiance_uncertainty_uW_per_cm_squared, "
                    "irradiance_600nm_orange_wavelength_nm, irradiance_600nm_orange_wavelength_uncertainty_nm, irradiance_600nm_orange_irradiance_uW_per_cm_squared, irradiance_600nm_orange_irradiance_uncertainty_uW_per_cm_squared, "
                    "irradiance_650nm_red_wavelength_nm, irradiance_650nm_red_wavelength_uncertainty_nm, irradiance_650nm_red_irradiance_uW_per_cm_squared, irradiance_650nm_red_irradiance_uncertainty_uW_per_cm_squared, "
                    "irradiance_610nm_orange_wavelength_nm, irradiance_610nm_orange_wavelength_uncertainty_nm, irradiance_610nm_orange_irradiance_uW_per_cm_squared, irradiance_610nm_orange_irradiance_uncertainty_uW_per_cm_squared, "
                    "irradiance_680nm_near_infrared_wavelength_nm, irradiance_680nm_near_infrared_wavelength_uncertainty_nm, irradiance_680nm_near_infrared_irradiance_uW_per_cm_squared, irradiance_680nm_near_infrared_irradiance_uncertainty_uW_per_cm_squared, "
                    "irradiance_730nm_near_infrared_wavelength_nm, irradiance_730nm_near_infrared_wavelength_uncertainty_nm, irradiance_730nm_near_infrared_irradiance_uW_per_cm_squared, irradiance_730nm_near_infrared_irradiance_uncertainty_uW_per_cm_squared, "
                    "irradiance_760nm_near_infrared_wavelength_nm, irradiance_760nm_near_infrared_wavelength_uncertainty_nm, irradiance_760nm_near_infrared_irradiance_uW_per_cm_squared, irradiance_760nm_near_infrared_irradiance_uncertainty_uW_per_cm_squared, "
                    "irradiance_810nm_near_infrared_wavelength_nm, irradiance_810nm_near_infrared_wavelength_uncertainty_nm, irradiance_810nm_near_infrared_irradiance_uW_per_cm_squared, irradiance_810nm_near_infrared_irradiance_uncertainty_uW_per_cm_squared, "
                    "irradiance_860nm_near_infrared_wavelength_nm, irradiance_860nm_near_infrared_wavelength_uncertainty_nm, "
                    "irradiance_860nm_near_infrared_irradiance_uW_per_cm_squared, irradiance_860nm_near_infrared_irradiance_uncertainty_uW_per_cm_squared, "
                    "range_m, range_uncertainty_m,"
                    "battery_voltage"
                    "\n"
                        )

                    f.write( header )
            except OSError:
                pass
            postheader_mem_free = gc.mem_free()
            #print( "header mem usage = {}".format(postheader_mem_free - preheader_mem_free))
        return True

def check_STELLA_config():
    try:
        with open( "/sd/STELLA_config.txt", "r" ) as s:
            try:
                header = s.readline()
                #print( sampling_header )
                values = s.readline()
                #print(sampling_values)
                values= values.rstrip('\n')
                values = values.split(',')
                #print(line)
                desired_sample_interval_s = float( values[ 0 ])
                averaging_number_of_samples = int( values[ 1 ])
                averaging_count_down = int( values[ 2 ])
                count_down_step_s = float( values[ 3 ])

            # TBD: catch error when /sd doesn't exist
            except ValueError:
                pass
    except OSError:
            #print( "sampling_config.txt file not found" )
            try:
                with open( "/sd/STELLA_config.txt", "w" ) as s:
                    s.write( "desired_sample_interval_s, averaging_number_of_samples, averaging_count_down, count_down_step_s\n" )
                    s.write( "0.75, 20, 3, 0.75\n" )
                print("created new STELLA_config.txt file")
            except OSError:
                pass
            desired_sample_interval_s, averaging_number_of_samples, averaging_count_down, count_down_step_s = 0.75, 20, 3, 0.75
    return desired_sample_interval_s, averaging_number_of_samples, averaging_count_down, count_down_step_s

def check_battery_voltage( battery_monitor ):
    if battery_monitor:
        battery_voltage = round(( battery_monitor.value * 3.3) / 65536 * 2, 2 )
        return battery_voltage
    else:
        return 0

class Mode:
    def __init__(self, initial_instrument_mode):
        self.instrument = initial_instrument_mode
    def __init__(self, initial_number_of_instrument_modes):
        self.number_of_instrument_modes = initial_number_of_instrument_modes
    def __init__(self, initial_display_mode):
        self.display = initial_display_mode
    def __init__(self, initial_number_of_display_modes):
        self.number_of_display_modes = initial_number_of_display_modes
    def __init__(self, initial_data_mode):
        self.data = initial_data_mode
    def __init__(self, initial_number_of_data_modes):
        self.number_of_data_modes = initial_number_of_data_modes
    def __init__( self ):
        self.trigger = False

### create display modes and display modifiers ###

def show_telltale( display_group, instrument_mode ):
    BANISH = 250
    if display_group:
        len_group = ( len ( display_group ))
        if instrument_mode == BLUE:
            display_group[ len_group - 5 ].y = BANISH  #green tab
            display_group[ len_group - 6 ].y = 158  #blue tab
            display_group[ len_group - 7 ].y = BANISH  #yellow tab

        if instrument_mode == GREEN:
            display_group[ len_group - 5 ].y = 193  #green tab
            display_group[ len_group - 6 ].y = BANISH  # blue tab
            display_group[ len_group - 7 ].y = BANISH  #yellow tab

        if instrument_mode == YELLOW:
            display_group[ len_group - 5 ].y = BANISH  #green tab
            display_group[ len_group - 6 ].y = BANISH  #blue tab
            display_group[ len_group - 7 ].y = 121  #yellow tab
    else:
        print("No display")
        return

def create_telltale( display_group ):
    telltale_color_x = 161
    telltale_color_width = 16 - 4
    telltale_color_height = 34
    BLUE = 0x00BFFF
    YELLOW = 0xF8FF33
    GREEN = 0x34FF1A
    if display_group:
        yellow_tab = Rect( telltale_color_x, 121, telltale_color_width, telltale_color_height-0, fill = YELLOW)
        display_group.append( yellow_tab )
        blue_tab = Rect( telltale_color_x, 121+34+2+1, telltale_color_width, telltale_color_height-1, fill = BLUE)
        display_group.append( blue_tab )
        green_tab = Rect( telltale_color_x, 125+34*2, telltale_color_width, telltale_color_height, fill = GREEN)
        display_group.append( green_tab )
    else:
        print("No display")
        return

def show_record_pause_icon( display_group, data_mode, create_or_update ):
    if not display_group:
        print("No display")
        return
    #print ( len ( display_group ))
    #WHITE = 0xFFFFFF
    BACKGROUND = 0x99E6FF
    RED = 0xFF0022
    BLACK = 0x000000
    x_center = 170
    y_center = 70
    radius = 8
    x_corner = x_center - radius
    y_corner = y_center - radius
    off_screen_y = 300
    width = 18
    split_width = int( width/3 )
    height = 18
    if create_or_update == CREATE:
        blank_icon = Rect( x_corner, y_corner, width, height, fill = BACKGROUND )#WHITE)
        recording_icon = Circle( x_center, y_center, radius, fill = RED)
        pause_square_icon = Rect( x_corner, y_corner, width, height, fill = BLACK)
        pause_split_icon = Rect( x_corner + split_width, y_corner, split_width, height, fill = BACKGROUND) #WHITE)
        display_group.append( blank_icon )
        display_group.append( recording_icon )
        display_group.append( pause_square_icon )
        display_group.append( pause_split_icon )
    else:
        len_group = ( len ( display_group ))
        if data_mode == RECORD:
            display_group[ len_group - 4 ].y = y_corner
            display_group[ len_group - 3 ].y = y_corner
            display_group[ len_group - 2 ].y = off_screen_y
            display_group[ len_group - 1 ].y = off_screen_y
        else: #elif data_mode == LIVE:
            display_group[ len_group - 4 ].y = off_screen_y
            display_group[ len_group - 3 ].y = off_screen_y
            display_group[ len_group - 2 ].y = y_corner
            display_group[ len_group - 1 ].y = y_corner

def remove_record_pause_icon ( display_group ):
    len_group = ( len ( display_group ))
    display_group[ len_group - 2 ].y = 250
    display_group[ len_group - 1 ].y = 250

def populate_table_values( text_group, UID, timestamp, decimal_hour, batch_number, visible_irradiance_uW_per_cm_squared,
        nir_irradiance_uW_per_cm_squared, surface_temperature_C, air_temperature_C, range_m, Li_present):
    day_date = "UID:{0} {1:04}-{2:02}-{3:02}".format( UID, timestamp.tm_year, timestamp.tm_mon, timestamp.tm_mday )
    # don't take time to update display if not changed:
    #if battery_voltage > LOW_BATTERY_VOLTAGE:
    if text_group[ GROUP.DAY_DATE ].text != day_date:
        text_group[ GROUP.DAY_DATE ].text = day_date
    if text_group[ GROUP.BATCH ].text != batch_number:
        text_group[ GROUP.BATCH ].text = batch_number
    time_text = "{0:02}:{1:02}:{2:02}Z".format(timestamp.tm_hour, timestamp.tm_min, timestamp.tm_sec)
    text_group[ GROUP.TIME ].text = time_text
    text_group[ GROUP.SURFACE_TEMP ].text = "{:4}C".format( surface_temperature_C )
    for i,band in enumerate( VIS_BANDS ):
        waveband_string = "{:5}".format( visible_irradiance_uW_per_cm_squared[ i ] )
        text_group[ GROUP.VIS_VALUES + i ].text = waveband_string
    for i,band in enumerate( NIR_BANDS ):
        waveband_string = "{:4}".format( nir_irradiance_uW_per_cm_squared[ i ] )
        text_group[ GROUP.NIR_VALUES + i ].text = waveband_string
    if Li_present:
        text_group[ GROUP.AIR_TEMPERATURE ].text = "{:.2f}m".format( range_m )
    else:
        text_group[ GROUP.AIR_TEMPERATURE ].text = "{:}C".format( air_temperature_C )
    gc.collect()

def create_welcome_screen( display ):
    welcome_start_memory = gc.mem_free()
    try:
        bitmap = displayio.OnDiskBitmap("/lib/stella_logo.bmp")
        #print( "Bitmap image file found" )
        # Create a TileGrid to hold the bitmap
        tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
        # Create a Group to hold the TileGrid
        welcome_group = displayio.Group()
        # Add the TileGrid to the Group
        welcome_group.append(tile_grid)

        version_group = displayio.Group( scale=2, x=25, y=210 )
        text = "software version {}".format( SOFTWARE_VERSION_NUMBER )
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
        text = "software version {}".format( SOFTWARE_VERSION_NUMBER )
        version_area = label.Label( terminalio.FONT, text=text, color=0xFFFFFF )
        version_group.append( version_area ) # Subgroup for text scaling
        welcome_group.append( version_group )
    welcome_stop_memory = gc.mem_free()
    #print( "welcome routine uses {} kB".format( -1 *(welcome_stop_memory - welcome_start_memory)/1000))
        #uses 2.4kB"
    return welcome_group

def full_spectrum_frame( table_group, border_color ):
    # begin full spectrum frame
    if table_group == False:
        return
        #Make the background
    palette = displayio.Palette(1)
    palette[0] = border_color
    background_rectangle = vectorio.Rectangle(pixel_shader=palette, width=SCREENSIZE_X, height=SCREENSIZE_Y, x=0, y=0)
    table_group.append( background_rectangle )
    palette = displayio.Palette(1)
    palette[0] = 0xFFFFFF
    border_width = 7 #0 #7

    #Make the foreground_rectangle
    foreground_rectangle = vectorio.Rectangle(pixel_shader=palette, width=SCREENSIZE_X - 2*border_width, height=SCREENSIZE_Y - 2*border_width, x=border_width, y=border_width)
    table_group.append( foreground_rectangle )

    #Draw the record_pause_state circle:
    palette = displayio.Palette(1)
    palette[0] = 0x99E6FF #0x00BFFF
    record_pause_circle = vectorio.Circle( pixel_shader=palette, radius=42, x=170, y=70 )
    table_group.append( record_pause_circle )

    #Draw the single_point circle:
    palette = displayio.Palette(1)
    palette[0] = 0xFCFF99 #0xF8FF33
    single_point_circle = vectorio.Circle( pixel_shader=palette, radius=42, x=65, y=70 )
    table_group.append( single_point_circle )

    #Draw the sample_and_average_circle:
    palette = displayio.Palette(1)
    palette[0] = 0x9CFF8F #0x34FF1A
    sample_and_average_circle = vectorio.Circle( pixel_shader=palette, radius=42, x=270, y=70 )
    table_group.append( sample_and_average_circle )

    #Make the frame
    batch_x = 258
    batch_border_offset = 0
    batch_height_y = 26
    palette = displayio.Palette(1)
    palette[0] = border_color
    batch_border = vectorio.Rectangle(pixel_shader=palette, width=SCREENSIZE_X - batch_x - border_width - batch_border_offset, height=batch_height_y, x=batch_x, y=border_width + batch_border_offset)
    table_group.append( batch_border )

    batch_area_border_width = 3
    palette = displayio.Palette(1)
    palette[0] = 0xFFFFFF
    batch_clear_area = vectorio.Rectangle(pixel_shader=palette, width=SCREENSIZE_X - batch_x - border_width - batch_area_border_width, height=batch_height_y - batch_area_border_width, x=batch_x + batch_area_border_width, y=border_width)
    table_group.append( batch_clear_area )

    #print( "draw a black narrow vertical rectangle" )
    palette = displayio.Palette(1)
    palette[0] = 0x000000
    telltale_background = vectorio.Rectangle( pixel_shader=palette, width=16, height=110, x=160, y=120 )
    table_group.append( telltale_background )

    #print( "draw a white narrower rectangle to make a black rectangular frame" )
    telltale_frame_width = 2
    palette = displayio.Palette(1)
    palette[0] = 0xFFFFFF
    telltale_background = vectorio.Rectangle( pixel_shader=palette, width=16 - 2 * telltale_frame_width , height=110 - 2 * telltale_frame_width, x=160 + telltale_frame_width, y=120+telltale_frame_width )
    table_group.append( telltale_background )

    #print( "draw a black narrow separators" )
    palette = displayio.Palette(1)
    palette[0] = 0x000000
    telltale_separator = vectorio.Rectangle( pixel_shader=palette, width=16, height=2, x=160, y=120+34+2+1 )
    table_group.append( telltale_separator )

    #print( "draw a black narrow separators" )
    palette = displayio.Palette(1)
    palette[0] = 0x000000
    telltale_separator2 = vectorio.Rectangle( pixel_shader=palette, width=16, height=2, x=160, y=120+2*34+2+1+1 )
    table_group.append( telltale_separator2 )

    #Draw screen switch button:
    palette = displayio.Palette(1)
    palette[0] = 0xC1C1C1
    screen_button_triangle_r = vectorio.Polygon( pixel_shader=palette, points = [(250, 120), (250, 220), (310, 170)], x=0, y=0)
    #table_group.append( screen_button_triangle_r )
    screen_button_triangle_l = vectorio.Polygon( pixel_shader=palette, points = [(320-250, 120), (320-250, 220), (320-310, 170)], x=0, y=0)
    #table_group.append( screen_button_triangle_l )


def create_table_screen( display, display_group ):
    RED = 0xFF0022
    full_spectrum_frame( display_group, RED )
    text_group = full_spectrum_text_groups( display_group )
    return text_group

def full_spectrum_text_groups( table_group ):
    if table_group == False:
        return False
    # Fixed width font
    fontPixelWidth, fontPixelHeight = terminalio.FONT.get_bounding_box()
    text_color = 0x000000 # black text for readability
    text_group = displayio.Group( scale = 2, x = 15, y = 20 ) #scale sets the text scale in pixels per pixel
    try:
        # Name each text_group with some: GROUP.X = len(text_grup), then use in text_group[ GROUP.X ]
        # Order doesn't matter for that (but is easier to figure out if in "display order")
        # LINE 1
        GROUP.DAY_DATE = len(text_group) # text_group[ i ] day date
        text_area = label.Label( terminalio.FONT, color = text_color ) #text color
        text_area.y = -1
        text_area.x = 0
        text_group.append( text_area )
        GROUP.BATCH = len(text_group) #text_group[ i ] batch_display_string
        text_area = label.Label( terminalio.FONT, color = text_color )
        text_area.y = -2
        text_area.x = 127
        text_group.append( text_area )
        # LINE 2
        GROUP.TIME = len(text_group) #text_group[ i ] time
        text_area = label.Label( terminalio.FONT, color = text_color )
        text_area.y = 12
        text_area.x = 0
        text_group.append( text_area )
        # surface temperature label, doesn't need a name
        text_area = label.Label( terminalio.FONT, text="Surface:", color = text_color )
        text_area.y = 12
        text_area.x = 70
        text_group.append( text_area )
        GROUP.SURFACE_TEMP = len(text_group) #text_group[ i ] surface temperature
        text_area = label.Label( terminalio.FONT, color = text_color )
        text_area.y = text_group[-1].y
        text_area.x = text_group[-1].x + len( text_group[-1].text ) * fontPixelWidth # use the previous text to get offset
        text_group.append( text_area )
        # LINE 3
        # units_string, doesn't need a name
        text_area = label.Label( terminalio.FONT, text="nm: uW/cm^2", color = text_color )
        text_area.y = 24
        text_area.x = 0
        text_group.append( text_area )

        # air temp label, doesn't need a name
        text_area = label.Label( terminalio.FONT, text="Air:", color = text_color )
        text_area.x = 94
        text_area.y = 24
        text_group.append( text_area )
        #print( "text group after Air: is length {}".format(len(text_group)))
        GROUP.AIR_TEMPERATURE = len(text_group) #text_group[ i ] air temperature
        text_area = label.Label( terminalio.FONT, color = text_color )
        text_area.y = text_group[-1].y
        text_area.x = text_group[-1].x + len(text_group[-1].text) * fontPixelWidth
        text_group.append( text_area )
        # LINE 5..10
        #text groups[ i..+5 ] VIS channels labels
        vis_start_x = 0
        for waveband_index,nm in enumerate(VIS_BANDS):
            vis_start_y = 36 + 12 * waveband_index
            # just labels
            label_string = "{:1}{:03}: ".format( VIS_BAND_PREFIXES[waveband_index], nm )
            text_area = label.Label( terminalio.FONT, text=label_string, color = text_color )
            text_area.x = vis_start_x
            text_area.y = vis_start_y
            text_group.append( text_area )
        GROUP.VIS_VALUES = len(text_group) #text groups[ i..+5 ] VIS channels. Just the first one, we `+ i` it
        # x is always the same: a column
        vis_start_x = vis_start_x + len( label_string ) * fontPixelWidth
        for waveband_index,nm in enumerate(VIS_BANDS):
            vis_start_y = 36 + 12 * waveband_index
            text_area = label.Label( terminalio.FONT, color = text_color )
            text_area.x = vis_start_x
            text_area.y = vis_start_y
            text_group.append( text_area )
        #text groups[ i..+5 ] NIR channels labels
        nir_start_x = 82
        for waveband_index,nm in enumerate(NIR_BANDS):
            nir_start_y = 36 + 12 * waveband_index
            # just labels
            label_string = "{:03}: ".format( nm )
            text_area = label.Label( terminalio.FONT, text=label_string, color = text_color )
            text_area.x = nir_start_x
            text_area.y = nir_start_y
            text_group.append( text_area )
        GROUP.NIR_VALUES = len(text_group) #text groups[ i..+5 ] NIR channels. Just the first one, we `+ i` it
        # x is always the same: a column
        nir_start_x = nir_start_x + len( label_string ) * fontPixelWidth
        for waveband_index,nm in enumerate(NIR_BANDS):
            nir_start_y = 36 + 12 * waveband_index
            text_area = label.Label( terminalio.FONT, color = text_color )
            text_area.x = nir_start_x
            text_area.y = nir_start_y
            text_group.append( text_area )
    except RuntimeError as err:
        if str(err) == "Group full":
            print("### Had this many groups when code failed: {:}".format(len(text_group)))
        raise
    table_group.append( text_group )
    #print("TG max_size {:}".format(len(text_group))) # to figure max_size of group
    return text_group

class GROUP:
    '''
    class GROUP:
      a group to gather the index names

      GROUP.X = 1
      magically creates the class variable X in GROUP,
      so we don't have to explicitly declare it

      = len(text_group)
      how many text_groups already made, == index of this text_group

      something = GROUP.X
      Then you just use it. But, this ensures that you assigned to GROUP.X before you read from it.
    '''
    pass

def initialize_display_group( display ):
    if display == False:
        print("no display")
        return False
    display_group = displayio.Group()
    return display_group

### initialize devices ###

def timestamp_to_decimal_hour( timestamp ):
    try:
        decimal_hour = timestamp.tm_hour + timestamp.tm_min/60.0 + timestamp.tm_sec/3600.0
        return decimal_hour
    except ValueError as err:
        print( "Error: invalid timestamp: {:}".format(err) )
        return False

def initialize_real_time_clock( i2c_bus ):
    clock_battery_OK = False
    try:
        hardware_clock = adafruit_pcf8523.PCF8523( i2c_bus )
        clock_battery_OK = not hardware_clock.battery_low
        if clock_battery_OK:
            print( "clock battery is OK." )
        else:
            print( "clock battery is low. Replace the clock battery." )
    except (AttributeError, NameError):
        print( "real time clock failed to initialize" )
        hardware_clock = False
    return ( hardware_clock, clock_battery_OK )

def initialize_display( spi_bus ):
    if not spi_bus:
        return False
    try:
        # displayio/dafruit_ili9341 library owns the pins until display release
        displayio.release_displays()
        tft_display_cs = board.D9
        tft_display_dc = board.D10
        display_bus = displayio.FourWire( spi_bus, command=tft_display_dc, chip_select=tft_display_cs )
        display = adafruit_ili9341.ILI9341( display_bus, width=SCREENSIZE_X, height=SCREENSIZE_Y, rotation=DISPLAY_ROTATION )
        return display
    except ValueError as err:
        print("Error: display fail {:}".format(err))
        return False

def initialize_touch_screen( spi_bus, i2c_bus ):
    try:
        print( "capacitive touch screen boot message", end = ": ")
        touch_screen = adafruit_focaltouch.Adafruit_FocalTouch( i2c_bus, debug=False )
        cap_touch_present = True
        return touch_screen, cap_touch_present
    except ( RuntimeError, ValueError, AttributeError) as err:
        print( "capacitive touch screen controller not found" )
        return False, False

def initialize_main_battery_monitor( pin ):
    try:
        main_battery_monitor = initialize_AnalogIn( pin )
    except AttributeError:
        main_battery_monitor = False
    return main_battery_monitor

def initialize_AnalogIn( pin_number ):
    try:
        analog_object = AnalogIn( pin_number )
    except ValueError:
        print( "analog input initialization failed." )
        analog_object = False
    return analog_object

def initialize_sdcard( spi_bus ):
    gc.collect()
    if not spi_bus:
        return False # will fail later if we try use the directory /sd
    # NOTE: pin D10 is in use by the display for SPI D/C, and so is not available
    # for the SD card chip select.
    # Modify the Adalogger Featherwing to use pin D11 for SD card chip select
    sd_cs = board.D11
    try:
        sdcard = sdcardio.SDCard( spi_bus, sd_cs )
        vfs = storage.VfsFat( sdcard )
        storage.mount( vfs, "/sd" )
        # initialized sd card
        return sdcard
    except ValueError as err: # known error behavior
        print( "Error: sd-card init fail: {:}".format(err) )
        return False
    except OSError as err:
        #TBD distinguish between '[Errno 17] File exists' (already mounted), no card and full card conditions.
        # "card not present or card full: [Errno 5] Input/output error" retry?
        print( "Error: sd card fail: card not present or card full: {:} ".format(err) )
        return False

def initialize_discrete_LED( pin_number ):
    try:
        discrete_LED = digitalio.DigitalInOut( pin_number )
        discrete_LED.direction = digitalio.Direction.OUTPUT
    except ValueError:
        print( "discrete LED initialization failed." )
        discrete_LED = False
    return discrete_LED

def initialize_button( pin ):
    try:
        keys = keypad.Keys((pin,), value_when_pressed=False, pull=True)
    except ValueError:
        keys = False
    return keys

### initialize busses ###

def initialize_uart_bus( TX_pin, RX_pin, baudrate, timeout ):
    try:
        uart_bus = busio.UART(
            TX_pin, RX_pin, baudrate=baudrate, bits=8, parity=1, stop=1, timeout=timeout
            )
        return uart_bus
    except ValueError as err: # known error behavior
        print( "Error: uart bus fail: {:}".format(err) )
        return False

def initialize_i2c_bus( SCL_pin, SDA_pin ):
    try:
        i2c_bus = busio.I2C( SCL_pin, SDA_pin )
    except (ValueError, RuntimeError) as err:
        print( "i2c bus failed to initialize '{}'".format( err ))
        i2c_bus = False
    return i2c_bus

def initialize_spi_bus():
    try:
        spi_bus = board.SPI()
        print( "initialized spi_bus" )
        return spi_bus
    except ValueError as err:
        print( "Error: spi bus fail: {:}".format(err) )
        return False

def low_battery_voltage_notification( text_group ):
    text_group[ GROUP.DAY_DATE ].text = "Low battery: plug in"
    time.sleep(0.5)

def screen_present( IO_pin ):
    display_check = digitalio.DigitalInOut( IO_pin )
    display_check.direction = digitalio.Direction.INPUT
    display_check.pull = digitalio.Pull.DOWN
    if display_check.value:
        return True
    else:
        return False

gc.collect()
#print( "memory free after load function definitions == {} kB".format( gc.mem_free()/1000))

def stall():
    print("intentionally stalled, press return to continue")
    input_string = False
    while input_string == False:
        input_string = input().strip()

asyncio.run( main() )

