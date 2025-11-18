SOFTWARE_VERSION_NUMBER = "0.6.0.1"
DEVICE_TYPE = "STELLA-1.2"
# STELLA-1.2 multifunction instrument
# NASA open source software license
# Paul Mirel 2025

# set the data_source period = reciprocal of the data_source cadence
#               seconds + ( minutes ) + ( hours )   + ( days )
preset_sample_interval_s = 10.0 + ( 0 * 60 ) + ( 0 * 3600 ) + ( 0 * 3600 * 24 )
preset_burst_count = 1
usb_serial_out_enabled = False
record_on_startup = True #False #

## imports
import gc
gc.collect()
start_mem_free_kB = gc.mem_free()/1000
print("start memory free {0:.2f} kB".format( start_mem_free_kB ))
# core functionality libraries
import time
startup_start_time = time.monotonic()
import os
import microcontroller
import board
import digitalio
import storage
import sdcardio
import busio
import rotaryio
from fourwire import FourWire
import displayio
import terminalio
from adafruit_display_text import label
import vectorio
import rtc
import neopixel
from analogio import AnalogIn
# function support libraries
import math
# main unit devices libraries
import adafruit_ili9341
import adafruit_focaltouch
import adafruit_max1704x
from adafruit_pcf8523 import pcf8523
import adafruit_gps

## check i2c devices present
i2c_bus = board.I2C()
i2c_bus.try_lock()
devices_present = i2c_bus.scan()
devices_present_hex = []
for device_address in devices_present:
    devices_present_hex.append(hex(device_address))
#print( devices_present_hex )

spectral_sensors_detected = False
## conditional imports
if ('0x12') in devices_present_hex:
    from adafruit_pm25.i2c import PM25_I2C
if ('0x18') in devices_present_hex:
    from adafruit_ds248x import Adafruit_DS248x
if ('0x19') in devices_present_hex:
    import adafruit_lsm303_accel
if ('0x1c') in devices_present_hex:
    from adafruit_lsm6ds.lsm6ds3 import LSM6DS3 as LSM6DS
if ('0x1e') in devices_present_hex:
    import adafruit_lis2mdl
if ('0x1f') in devices_present_hex:
    import adafruit_mcp9808 ### close a0, a1, a2 address jumpers on board
if ('0x28') in devices_present_hex:
    print( "TBD need library for SparkFun conductive soil moisture sensor" )
if ('0x29') in devices_present_hex:
    import adafruit_vl53l1x
if ('0x33') in devices_present_hex:
    import adafruit_mlx90640
if ('0x34') in devices_present_hex:
    import qwiic_buzzer
# ('0x36') reserved for on board battery monitor (MAX17048)
if ('0x37') in devices_present_hex:
    from adafruit_seesaw.seesaw import Seesaw
# ('0x38') reserved for capacitive touch screen (FocalTouch)
if ('0x39') in devices_present_hex:
    from adafruit_as7341 import AS7341
    from adafruit_as7341 import Gain as AS7341_Gain
    spectral_sensors_detected = True
if ('0x44') in devices_present_hex:
    import adafruit_hdc302x
if ('0x48') in devices_present_hex:
    import adafruit_ads1x15.ads1015 as ADS1015
    from adafruit_ads1x15.analog_in import AnalogIn as ADS1x15_AnalogIn
if ('0x49') in devices_present_hex:
    import AS7265X_sparkfun
    from AS7265X_sparkfun import AS7265X
    spectral_sensors_detected = True
if ('0x4a') in devices_present_hex:
    import adafruit_ads1x15.ads1115 as ADS1115 ### connect ADDR to SDA to set address
    from adafruit_ads1x15.analog_in import AnalogIn as ADS1x15_AnalogIn
if ('0x4f') in devices_present_hex:
    import adafruit_pcf8591.pcf8591 as PCF8591  ### close a0, a1, a2 address jumpers on board
    from adafruit_pcf8591.analog_in import AnalogIn as PCF8591_AnalogIn
    from adafruit_pcf8591.analog_out import AnalogOut as PCF8591_AnalogOut
if ('0x53') in devices_present_hex:
    import adafruit_ltr390
if True: #('0x5a') in devices_present_hex:
    import adafruit_mlx90614 # This device doesn't answer the scan. Import the library unconditionally.
if ('0x61') in devices_present_hex:
    import adafruit_scd30
if ('0x62') in devices_present_hex:
    import adafruit_scd4x
if ('0x6a') in devices_present_hex:
    from adafruit_lis3mdl import LIS3MDL
if ('0x74') in devices_present_hex:
    import iorodeo_as7331 as as7331
    spectral_sensors_detected = True
if ('0x77') in devices_present_hex:
    from adafruit_bme280 import basic as adafruit_bme280
i2c_bus.unlock()
mem_free_after_imports = gc.mem_free()
#print( "mem free after imports = {} kB, {} %".format(int(gc.mem_free()/1000), int(100*(gc.mem_free()/1000)/start_mem_free_kB )) )

def main():
    BLUE = ( 0, 0, 255 )
    GREEN = ( 255, 0, 0 )
    YELLOW = ( 127, 255, 0 )
    RED = ( 0, 255, 0 )
    OFF = ( 0, 0, 0 )

    gc.collect()
    displayio.release_displays()
    UID = get_uid()
    spi_bus = board.SPI()
    vfs = initialize_sd_card( spi_bus, board.A5 )
    i2c_bus = initialize_i2c_bus()
    gps_uart_bus = initialize_uart( board.TX, board.RX )
    onboard_neopixel = initialize_neopixel( board.NEOPIXEL )
    if vfs:
        onboard_neopixel.fill(YELLOW)
    else:
        onboard_neopixel.fill(RED)
    buzzer = initialize_qwiic_buzzer( i2c_bus )
    buzzer.mute = False
    buzzer.set(932, 130) # frequency in Hz, time in ms. 932 Hz is B flat in octave 5. Fairly pleasant through this piezo driver, though maybe a bit medical in tone.
    buzzer.beep()
    battery_indicator = initialize_led( board.LED )

    instrument = create_instrument( i2c_bus, spi_bus, gps_uart_bus, UID, buzzer )
    instrument.welcome_page.show()
    spectral_register = create_spectral_register( instrument )

    # supported sensors
    ads1015_12_bit_adc = initialize_ads1015_12_bit_adc( instrument )
    ads1115_16_bit_adc = initialize_ads1115_16_bit_adc( instrument )
    as7265x_spectrometer = initialize_as7265x_spectrometer( instrument )
    as7331_spectrometer = initialize_as7331_spectrometer( instrument )
    as7341_spectrometer = initialize_as7341_spectrometer( instrument )
    bme280_air_sensor = initialize_bme280_air_sensor( instrument )
    capacitive_soil_moisture_sensor = initialize_capacitive_soil_moisture_sensor( instrument )
    ds2484_1_wire_thermometer = initialize_ds2484_1_wire_thermometer( instrument )
    hdc3022_air_sensor = initialize_hdc3022_air_sensor( instrument )
    lis2mdl_magnetic_field_sensor = initialize_lis2mdl_magnetic_field_sensor( instrument )
    lis3mdl_magnetic_field_sensor = initialize_lis3mdl_magnetic_field_sensor( instrument )
    lsm303_acceleration_sensor = initialize_lsm303_acceleration_sensor( instrument )
    lsm6ds_accel_gyro_sensor = initialize_lsm6ds_accel_gyro_sensor( instrument )
    ltr390_uva_sensor = initialize_ltr390_uva_sensor( instrument )
    mcp9808_air_thermometer = initialize_mcp9808_air_thermometer( instrument )
    mlx90614_surface_thermometer = initialize_mlx90614_surface_thermometer( instrument )
    mlx90640_thermal_camera = initialize_mlx90640_thermal_camera( instrument )
    pcf8591_8_bit_adc_dac = initialize_pcf8591_8_bit_adc_dac( instrument )
    pmsa0031_particulates_sensor = initialize_pmsa0031_particulates_sensor( instrument )
    scd30_CO2_sensor = initialize_scd30_CO2_sensor( instrument )
    scd4x_co2_sensor = initialize_scd4x_co2_sensor( instrument )
    vl53l1x_4m_range_sensor = initialize_vl53l1x_4m_range_sensor( instrument )
    instrument.welcome_page.announce( "Found {} external sensors".format( len(instrument.sensors_present) + len(instrument.spectral_sensors_present)))
    sense_5V = AnalogIn(board.A1)
    analog_in_0 = AnalogIn(board.A0)
    if mlx90614_surface_thermometer.pn and as7265x_spectrometer.pn:
        lv_ez_mb1013_rangefinder = initialize_lv_ez_mb1013_rangefinder( instrument, analog_in_0, sense_5V )
    else:
        lv_ez_mb1013_rangefinder = False
    battery_monitor = initialize_battery_monitor( instrument )
    gps = initialize_gps( instrument )


    #plus_5v_supply = False #TBD make a device object with digital out and analog in, check it for rising and falling
    enable_5V = digitalio.DigitalInOut( board.D10 )
    enable_5V.direction = digitalio.Direction.OUTPUT
    enable_5V.value = True
    # plus_5v_supply.enable(), .read(), .log(), .disable()

    gc.collect()
    mem_free_after_devices = gc.mem_free()
    print( "memory free after device object creations = {} kB, {} %".format(int(gc.mem_free()/1000),
                                                    int(100*(gc.mem_free()/1000)/start_mem_free_kB )))
    print( "memory usage by device objects = {} kB = {} %".format(( mem_free_after_imports - mem_free_after_devices)/1000,
                                round(100 * ( mem_free_after_imports - mem_free_after_devices)/1000/start_mem_free_kB, 1)))

    controls_page = make_controls_page( instrument, gps, battery_monitor ) #1
    main_menu_page = make_main_menu_page( instrument ) #2
    status_page = make_status_page( instrument ) #3
    settings_page = make_settings_page( instrument ) #4
    sensor_list_page = make_sensor_list_page( instrument ) #5
    generic_sensor_page = make_generic_sensor_page( instrument ) #6
    time_place_page = make_time_place_page( instrument ) #7
    air_analyzer_page = make_air_analyzer_page( instrument ) #8
    if spectral_sensors_detected:
        remote_sensing_page = make_remote_sensing_page( instrument, spectral_register, hdc3022_air_sensor, mlx90614_surface_thermometer, lv_ez_mb1013_rangefinder ) #9
        instrument.active_page_number = 9
        spectral_graph_page = make_spectral_graph_page( instrument, spectral_register ) #10 takes a lot of time
        instrument.add_spectral_graph_page( spectral_graph_page )
        remote_sensing_page.add_spectral_graph_page( spectral_graph_page )
    else:
        remote_sensing_missing_page = make_remote_sensing_missing_page( instrument ) #9 alt



    gc.collect()
    mem_free_after_pages = gc.mem_free()
    print( "memory free after page creations = {} kB, {} %".format(int(gc.mem_free()/1000), int(100*(gc.mem_free()/1000)/start_mem_free_kB )))
    print( "memory usage by pages = {} kB = {} %".format(
                                            ( mem_free_after_devices - mem_free_after_pages)/1000,
                                            int( 100 * ( mem_free_after_devices - mem_free_after_pages)/1000/start_mem_free_kB)))


    instrument.make_band_list()
    instrument.make_header()


    try:
        if vfs:
            onboard_neopixel.fill(GREEN)
        for sensor in instrument.sensors_present:
            sensor.read()
        gps.read()
        controls_page.update_values( instrument )
        operational = True
        loop_times = []
        last_sample_time = time.monotonic() - instrument.sample_interval_s
        first_sample_time = time.monotonic()
        while operational:
            loop_start = time.monotonic()
            instrument.show_active_page()
            instrument.update_active_page()
            controls_page.update_values( instrument )
            instrument.check_inputs()
            if False:
                for index in range (0,len(main_menu_page.selection_rectangles)):
                    main_menu_page.selection_rectangles[index].hidden = False
                    if index > 0:
                        main_menu_page.selection_rectangles[index-1].hidden = True
                    time.sleep(2)
                main_menu_page.selection_rectangles[-1].hidden = True


            if not instrument.input_flag:
                if ((time.monotonic() > last_sample_time + instrument.sample_interval_s) and instrument.record) or instrument.take_burst:
                    last_sample_time = time.monotonic()
                    #print( "sample interval satified at {} s".format(time.monotonic()-first_sample_time ))
                    for instrument.burst_counter in range( 0, instrument.burst_count):
                        controls_page.update_burst_countdown( instrument.burst_count - instrument.burst_counter )
                        system_log = instrument.get_system_log()
                        if not instrument.input_flag:
                            for sensor in instrument.sensors_present:
                                sensor.read()
                            instrument.check_inputs()
                        if not instrument.input_flag:
                            for spectral_sensor in instrument.spectral_sensors_present:
                                spectral_sensor.read()
                                spectral_sensor.check_gain_ratio()
                            instrument.check_inputs()
                        #instrument.update_active_page()
                        if not instrument.input_flag:
                            if vfs:
                                if instrument.take_burst:
                                    onboard_neopixel.fill(BLUE)
                                else:
                                    onboard_neopixel.fill(GREEN)
                                try:
                                    with open( "/sd/{}".format( instrument.filename ), "a" ) as f:
                                        f.write( system_log )
                                        if instrument.spectrometry:
                                            for index in range (0, instrument.spectral_header_count):
                                                f.write( ", - " ) # spectral column placeholders
                                        for sensor in instrument.sensors_present:
                                            f.write(", ")
                                            f.write( sensor.log() )
                                        f.write("\n")
                                        for band in instrument.wavelength_bands_list_sorted:
                                            f.write( system_log )
                                            for spectral_sensor in instrument.spectral_sensors_present:
                                                logline = spectral_sensor.log(band)
                                                if logline is not None:
                                                    f.write( ", " )
                                                    f.write( spectral_sensor.log(band) )
                                            f.write("\n")
                                        f.close()
                                except Exception as err:
                                    print( "write to file failed: {}".format( err ))
                                    vfs = False
                                onboard_neopixel.fill(OFF)
                                instrument.check_inputs()
                        if not instrument.input_flag:
                            if instrument.usb_serial_out_enabled:
                                onboard_neopixel.fill(WHITE)
                                #write to serial out
                                time.sleep(0.2)
                                onboard_neopixel.fill(OFF)
                                instrument.check_inputs()
                        instrument.measurement_counter += 1
                    instrument.take_burst = False
                    controls_page.burst_color.color_index = 16
            if instrument.input_flag:
                #print( "process inputs, change control values")
                if time.monotonic() > instrument.input_interval_start + instrument.input_interval:
                    instrument.input_flag = False

            if not vfs:
                onboard_neopixel.fill(RED)
            if False: #battery percentage < 20:
                flash_indicator( battery_indicator )
            #TBD command 5V supply
            #TBD command servo motors
            #TBD command source lamps
            #TBD command DAC output
            instrument.check_calendar_day()

            loop_stop = time.monotonic()
            loop_time = loop_stop - loop_start
            #print("loop time {} s".format( loop_time ))
            loop_times.append(loop_time)
            if len(loop_times) > 40:
                loop_times.pop(0)
            #print( "max loop time = {}, min loop time = {}".format( max(loop_times), min(loop_times)))


        #TBD announce exit message and clean up

    finally:
        displayio.release_displays()
        print( "displayio displays released" )
        i2c_bus.deinit()
        print( "i2c_bus deinitialized" )


##############
# begin register class definitions
##############


class Instrument:
    def __init__( self, i2c_bus, spi_bus, uart_bus, UID, buzzer):
        self.i2c_bus = i2c_bus
        self.uart_bus = uart_bus
        self.device_type = DEVICE_TYPE
        self.uid = UID
        self.buzzer = buzzer
        self.usb_serial_out_enabled = usb_serial_out_enabled
        self.sample_interval_s = preset_sample_interval_s
        self.burst_count = preset_burst_count
        self.usb_serial_out_enabled = usb_serial_out_enabled
        self.pages_list = []
        self.palette = make_palette()
        self.main_display_group = initialize_display( spi_bus )
        self.welcome_page = make_welcome_page( self )
        self.hardware_clock = initialize_hardware_clock( i2c_bus )
        #self.hardware_clock.report()
        self.hardware_clock.sync_system_clock()
        self.clock_battery_ok_text =  "clock battery OK: {}".format( self.hardware_clock.battery_ok() )
        self.welcome_page.announce( self.clock_battery_ok_text )
        self.datestamp = self.hardware_clock.get_datestamp_now()
        self.last_datestamp = self.datestamp
        self.iso_time = self.hardware_clock.get_iso_time_now()
        self.batch_number = update_batch(self.datestamp)
        print( "batch number = {}".format( self.batch_number ))
        self.filename = None
        self.sensors_present = []
        self.spectral_sensors_present = []
        self.spectrometry = spectral_sensors_detected
        self.record = record_on_startup
        self.session_tag = "{}-{}-session-".format(self.uid, self.iso_time)
        self.measurement_counter = 0
        self.rotary_encoder = initialize_rotary_encoder( pin_a = board.A3, pin_b = board.A4, pin_button = board.A2 )
        self.encoder_increment = 0
        self.button_pressed = False
        self.touch_screen = initialize_touch_screen( self.i2c_bus )
        self.input_flag = False
        self.input_interval_start = 0
        self.input_interval = 1
        self.active_page_number = 2
        self.last_active_page_number = 0
        self.take_burst = False
        self.main_menu_select = 6  # default to first main menu item selected
        self.main_menu_select_count = 17
        self.remote_sensing_select = 2  # default to record/pause
        self.remote_sensing_select_count = 17
    def update_batch(self):
        self.batch_number = update_batch(self.datestamp)
    def update_time(self):
        self.datestamp = self.hardware_clock.get_datestamp_now()
        self.iso_time = self.hardware_clock.get_iso_time_now()
        self.decimal_time = self.hardware_clock.get_decimal_hour_now()
    def update_filename(self):
        update_filename( self )
        print( "filename_in_use:", self.filename )
    def check_calendar_day( self ):
        self.datestamp = self.hardware_clock.get_datestamp_now()
        if self.datestamp != self.last_datestamp:
            self.last_datestamp = self.datestamp
            print( "new calendar day, updating system values" )
            self.update_batch()
            self.update_filename()
            self.session_tag = "{}-{}-session-".format(self.uid, self.iso_time)
            self.measurement_counter = 0
    def make_band_list( self ):
        self.wavelength_bands_list = []
        for sensor in self.spectral_sensors_present:
            for band in sensor.bands:
                self.wavelength_bands_list.append(band)
        self.wavelength_bands_list_sorted = sorted( self.wavelength_bands_list )
        #print( "line 411 -- wavelength_bands_list_sorted: ")
        #print( self.wavelength_bands_list_sorted  )
        self.number_of_plot_points = len( self.wavelength_bands_list_sorted )
        #print( "number of bands: ", end = "")
        #print( self.number_of_plot_points )
    def make_header( self ):
        self.header = "unique_identifier"
        self.header += ", unique_measurement_number"
        self.header += ", timestamp-!-iso8601utc"
        self.header += ", batch_number"
        self.header += ", burst_counter"
        self.header += ", decimal_time-!-hour"
        self.system_header = self.header
        spectral_header_list = []
        spectral_header_list.append( "spectral_sensor_part_number" )
        spectral_header_list.append( "spectral_wavelength-!-nm" )
        spectral_header_list.append( "spectral_bandwidth-!-nm" )
        spectral_header_list.append( "spectral_photodetector_digital_number-!-counts" )
        spectral_header_list.append( "spectral_irradiance-!-uW_per_cm_sq" )
        spectral_header_list.append( "spectral_uncertainty_in_irradiance-!-uW_per_cm_sq" )
        spectral_header_list.append( "spectral_gain-!-" )
        spectral_header_list.append( "spectral_integration_time-!-ms" )
        spectral_header_list.append( "spectral_detector_chip_number" )
        spectral_header_list.append( "spectral_detector_chip_temperature-!-C" )
        self.spectral_header_count = len( spectral_header_list )
        if self.spectrometry:
            for item in spectral_header_list:
                self.header += ", {}".format( item )
        for sensor in self.sensors_present:
            self.header += ", "
            self.header += sensor.header()
        self.header += ("\n")
        #print( self.header )
        #print( "spectral_header_count: ", self.spectral_header_count )
        self.update_filename()
    def hide_all_pages( self ):
        for item in self.pages_list:
            item.hide()
    def build_unique_measurement_number( self ):
        self.unique_measurement_number = "{}{}".format(self.session_tag, self.measurement_counter)
        return self.unique_measurement_number
    def get_system_log( self ):
        self.update_time()
        self.build_unique_measurement_number()
        system_log = "{}".format( self.uid )
        system_log += ", {}".format( self.unique_measurement_number )
        system_log += ", {}".format( self.iso_time )
        system_log += ", {}".format( self.batch_number )
        system_log += ", {}".format( self.burst_counter )
        system_log += ", {}".format( self.decimal_time )
        return system_log
    def check_inputs( self ):
        self.touch_screen.read()
        if not self.touch_screen.flag and self.touch_screen.is_touched:
            self.touch_tx = self.touch_screen.tx
            self.touch_ty = self.touch_screen.ty
            self.input_flag = True
            self.input_interval_start = time.monotonic()
        self.rotary_encoder.read_button()
        if self.rotary_encoder.button_flag:
            self.buzzer.beep()
            self.button_pressed = True
            self.rotary_encoder.button_flag = False
            self.input_flag = True
            self.input_interval_start = time.monotonic()
        self.rotary_encoder.read_encoder()
        if self.rotary_encoder.encoder_flag:
            self.encoder_increment = self.rotary_encoder.last_value
            self.rotary_encoder.encoder_flag = False
            self.input_flag = True
            self.input_interval_start = time.monotonic()
    def add_spectral_graph_page( self, spectral_graph_page ):
        self.spectral_graph_page = spectral_graph_page
    def show_active_page( self ):
        if self.active_page_number != self.last_active_page_number:
            self.last_active_page_number = self.active_page_number
            hide_all_pages( self.pages_list )
            self.pages_list[ self.active_page_number ].show()
            if self.active_page_number == 2 or self.active_page_number == 9: # main menu, remote sensing
                self.pages_list[ 1 ].show()  # controls
            if self.active_page_number == 9:
                if spectral_sensors_detected:
                    self.pages_list[ 10 ].show() # spectral graph
    def update_active_page( self ):
        self.pages_list[ self.active_page_number ].update_values( self )
        if self.active_page_number == 9:
            if spectral_sensors_detected:
                self.spectral_graph_page.update_plot_data()
        if self.encoder_increment != 0:
            if self.active_page_number == 2:
                self.main_menu_select = (self.main_menu_select + self.encoder_increment) % self.main_menu_select_count
            if self.active_page_number == 9:
                self.remote_sensing_select = (self.remote_sensing_select + self.encoder_increment) % self.remote_sensing_select_count
            self.encoder_increment = 0

def create_instrument( i2c_bus, spi_bus, uart_bus, UID, buzzer ):
    instrument = Instrument( i2c_bus, spi_bus, uart_bus, UID, buzzer )
    return instrument


class Spectral_Register:
    def __init__( self, instrument ):
        self.instrument = instrument
        self.scale_linear = True
        self.y_axis_irradiance = True
        self.scope = 0
        self.number_of_scope_choices = 6
        self.autoexposure = False
        self.lamps_on = False
        self.five_x_values = [[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0]]
        self.data_source = 0
        self.number_of_data_source_choices = 3
        self.x_axis_units = 0
        self.number_of_x_axis_units_choices = 4
        self.live = True
        self.number_of_plot_points = 0
        self.show_table = False
        self.wavelength_range = (410, 1000)
        self.wavelengths_to_plot = []
    def calculate_five_x_values( self ):
        c_m_per_s = 299792458
        nm_per_m = 10**9
        Hz_per_THz = 10**12
        h_e_V_per_Hz = 4.135667696/10**15
        self.five_x_values[0][2] = int( (self.five_x_values[0][0] + self.five_x_values[0][4])/2 )
        self.five_x_values[0][1] = int( (self.five_x_values[0][0] + self.five_x_values[0][2])/2 )
        self.five_x_values[0][3] = int( (self.five_x_values[0][2] + self.five_x_values[0][4])/2 )
        for index in range( 0, 5 ):
            self.five_x_values[1][index] = int((c_m_per_s / ((self.five_x_values[0][index])/nm_per_m))/Hz_per_THz) # frequency
            self.five_x_values[2][index] = round((self.five_x_values[1][index]* Hz_per_THz)*h_e_V_per_Hz,1)  # energy
            self.five_x_values[3][index] = int( 10000000/self.five_x_values[0][index] )  # wave number


def create_spectral_register( instrument ):
    spectral_register = Spectral_Register( instrument )
    return spectral_register


##############
# end register class definitions
##############

##############
# begin functions I'm working on
##############


##############
# end functions I'm working on
##############



##############
# begin pages definitions section
##############

class Page:
    def __init__( self ):
        pass
    def show(self):
        self.group.hidden = False
    def hide(self):
        self.group.hidden = True
    def update_values(self):
        pass

class Spectral_Graph_Page( Page ):
    def __init__( self, instrument, spectral_register ):
        super().__init__()
        self.instrument = instrument
        self.spectral_register = spectral_register
        self.palette = instrument.palette
        self.points = []
    def make_group( self ):
        self.group = displayio.Group()
        graph_x = 14 #4
        graph_width = 320-60-24
        graph_height = 240-124 #240-120
        message_height = int( graph_height/4 )
        message_offset = 10
        graph_y = 80
        self.graph_pix_y0 = graph_y + graph_height
        self.graph_pix_x0 = graph_x
        self.graph_pix_xn = self.graph_pix_x0 + graph_width
        self.graph_pix_yn = self.graph_pix_y0 - graph_height
        graph_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=graph_width, height=graph_height-4, x=graph_x, y=graph_y+4 )
        self.group.append( graph_background )
        ## make all the plot points, store them on the x-axis
        self.pixels_per_point = 2 #4
        self.point_height = 2
        self.number_of_points = int(graph_width / self.pixels_per_point)
        #print( "number_of_points", self.number_of_points )
        for index in range (0, self.number_of_points):
            #color_index = index % 10 or color_index = 0
            point = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0 , width=self.pixels_per_point, height=self.point_height,
                        x=self.graph_pix_x0 + index*self.pixels_per_point, y=self.graph_pix_y0 - self.point_height )
            self.points.append(point)
            self.group.append(point)

        self.message_bar = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9,
                        width=graph_width-2*message_offset, height=message_height,
                        x=self.graph_pix_x0+message_offset, y=self.graph_pix_y0 - message_offset - message_height )
        self.group.append( self.message_bar )
        self.message_bar.hidden = True
        message_group = displayio.Group(scale=2, x=self.graph_pix_x0+3*message_offset, y=self.graph_pix_y0 - message_height+4)
        message_text = "updating graph"
        self.message_text_area = label.Label(terminalio.FONT, text=message_text, color=self.palette[19])
        message_group.append(self.message_text_area)
        self.message_text_area.hidden = True
        self.group.append(message_group)

        # future function banner
        self.banner_group = displayio.Group()
        select_width = 2
        banner_width = 250
        banner_height = 60
        banner_x = 30
        banner_y = 110
        banner_color_x = banner_x + select_width
        banner_color_y = banner_y + select_width
        banner_border = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=banner_width, height=banner_height, x=banner_x, y=banner_y)
        self.banner_group.append( banner_border )
        banner_color_width = banner_width - 2 * select_width
        banner_color_height = banner_height - 2 * select_width
        banner_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=banner_color_width, height=banner_color_height, x=banner_color_x, y=banner_color_y)
        self.banner_group.append( banner_color )
        banner_text_x = banner_color_x + 3
        banner_text_y = banner_color_y + 12
        banner_text_group = displayio.Group(scale=2, x=banner_text_x, y=banner_text_y)
        banner_text = "*future function: "
        banner_text_area = label.Label(terminalio.FONT, text=banner_text, color=self.palette[0])
        banner_text_group.append(banner_text_area)
        self.banner_group.append(banner_text_group)
        self.banner_message_group = displayio.Group(scale=2, x=banner_text_x, y=banner_text_y+26)
        banner_message = "message goes here"
        self.banner_message_area = label.Label(terminalio.FONT, text=banner_message, color=self.palette[0])
        self.banner_message_group.append( self.banner_message_area )
        self.banner_group.append(self.banner_message_group)
        self.group.append( self.banner_group )
        self.banner_group.hidden = True

        return self.group

    def update_plot_data( self ):
        if self.spectral_register.live:
            data_dict_to_plot = {}
            if self.spectral_register.y_axis_irradiance:
                for spectral_sensor in self.instrument.spectral_sensors_present:
                    if spectral_sensor.pn == "as7256x":
                        spectral_sensor.read_fcal()
                        data_dict_to_plot.update( spectral_sensor.dict_fcal )
                    if spectral_sensor.pn == "as7331":
                        spectral_sensor.read_fcal()
                        data_dict_to_plot.update( spectral_sensor.dict_fcal )
                    if spectral_sensor.pn == "as7341":
                        spectral_sensor.read()
                        data_dict_to_plot.update( as7341_spectrometer.dict_stenocal )
            else:
                for spectral_sensor in self.instrument.spectral_sensors_present:
                    if spectral_sensor.pn == "as7256x":
                        spectral_sensor.read_counts()
                        data_dict_to_plot.update( spectral_sensor.dict_counts )
                    if spectral_sensor.pn == "as7331":
                        spectral_sensor.read_counts()
                        data_dict_to_plot.update( spectral_sensor.dict_counts )
                    if spectral_sensor.pn == "as7341":
                        spectral_sensor.read()
                        data_dict_to_plot.update( as7341_spectrometer.dict_counts )
            if self.spectral_register.scope == 0: # vis +nir
                wavelength_range = (410, 1000)
            if self.spectral_register.scope == 1: # vis
                wavelength_range = (410, 700)
            if self.spectral_register.scope == 2: # nir
                wavelength_range = (700, 1000)
            if self.spectral_register.scope == 3: # uv + vis + nir
                wavelength_range = (200, 1000)
            if self.spectral_register.scope == 4: # uv + vis
                wavelength_range = (200, 700)
            if self.spectral_register.scope == 5: # uv
                wavelength_range = (200, 400)
            wavelengths_to_plot = []
            for item in self.instrument.wavelength_bands_list_sorted:
                if item in range (wavelength_range[0], wavelength_range[1]):
                    wavelengths_to_plot.append(item)
            if wavelengths_to_plot != []:
                self.spectral_register.five_x_values[0][0] = wavelengths_to_plot[0]
                self.spectral_register.five_x_values[0][4] = wavelengths_to_plot[-1]
                self.spectral_register.calculate_five_x_values()
            else:
                self.spectral_register.scope = (self.spectral_register.scope +1) % self.spectral_register.number_of_scope_choices
            spectral_graph_x_values_nm = []
            spectral_bandwidths_nm = []
            spectral_graph_y_values = []
            for item in self.instrument.wavelength_bands_list_sorted:
                if item in range ( wavelength_range[0], wavelength_range[1]):
                    if data_dict_to_plot.get(item) is not None:
                        spectral_graph_x_values_nm.append( item )
                        for spectral_sensor in self.instrument.spectral_sensors_present:
                            bw = spectral_sensor.get_bandwidth(item)
                            if bw is not None:
                                spectral_bandwidths_nm.append(bw)
                        if self.spectral_register.scale_linear:
                            spectral_graph_y_values.append( data_dict_to_plot.get(item) )
                        else:
                            if data_dict_to_plot.get(item) < 1:
                                spectral_graph_y_values.append( 0 )
                            else:
                                spectral_graph_y_values.append( math.log(data_dict_to_plot.get(item),10))
            #print(spectral_bandwidths_nm)

            # TBD look up the bandwidth for each
            # TBD plot all the points. set their color, width, height, offset. Interpolate the inactive points.
            if spectral_graph_y_values:
                #print( spectral_graph_x_values_nm[0], spectral_graph_x_values_nm[-1])
                wavelength_nm_per_point = (spectral_graph_x_values_nm[-1] - spectral_graph_x_values_nm[0])/(self.number_of_points - 1 )
                #print( wavelength_nm_per_point )

                inactive_point_color = 19
                indicies_of_active_points = []
                point_wavelengths_nm = []  # wavelength for each point
                point_active = []       # boolean list, true if there's real data for that point
                point_colors = []       # color index for each point
                point_bandwidths = []   # bandwidth for each point ( 0 for inactive points )
                point_y_values = []     # y value in counts or irradiance for each point
                point_y_location = []   # display position in y pixels for each point: plot this value

                for value in spectral_graph_x_values_nm:
                    indicies_of_active_points.append(int( round((value - spectral_graph_x_values_nm[0]) / wavelength_nm_per_point,0)))

                slopes_delta_y_per_point = []
                for index in range ( 0, len(indicies_of_active_points)-1):
                    slopes_delta_y_per_point.append( (spectral_graph_y_values[index+1]-spectral_graph_y_values[index])/(indicies_of_active_points[index+1]-indicies_of_active_points[index]) )

                y_value_index = -1
                last_index = 0
                for index in range (0, self.number_of_points):
                    point_wavelengths_nm.append( spectral_graph_x_values_nm[0] + index * wavelength_nm_per_point)
                    if index in indicies_of_active_points:
                        y_value_index += 1
                        point_active.append( True )
                        bandwidth = spectral_bandwidths_nm[y_value_index]
                        wavelength = spectral_graph_x_values_nm[y_value_index]
                        if wavelength in range(390,420):
                            self.points[index].color_index = 25
                        if wavelength in range(420,450):
                            self.points[index].color_index = 26
                        if wavelength in range(450,470):
                            self.points[index].color_index = 27
                        if wavelength in range(470,500):
                            self.points[index].color_index = 28
                        if wavelength in range(500,520):
                            self.points[index].color_index = 29
                        if wavelength in range(520,550):
                            self.points[index].color_index = 30
                        if wavelength in range(550,570):
                            self.points[index].color_index = 31
                        if wavelength in range(570,600):
                            self.points[index].color_index = 32
                        if wavelength in range(600,630):
                            self.points[index].color_index = 33
                        if wavelength in range(630,660):
                            self.points[index].color_index = 34
                        if wavelength in range(660,690):
                            self.points[index].color_index = 35
                        if wavelength in range(690,720):
                            self.points[index].color_index = 36
                        if wavelength in range(720,745):
                            self.points[index].color_index = 37
                        if wavelength in range(745,785):
                            self.points[index].color_index = 38
                        if wavelength > 785 or wavelength < 390:
                            self.points[index].color_index = 0
                        bw_in_points = int( bandwidth/wavelength_nm_per_point )*self.pixels_per_point
                        self.points[index].width = bw_in_points
                        self.points[index].x = self.graph_pix_x0 + index*self.pixels_per_point - int(bw_in_points/2)
                        self.points[index].height = self.point_height *3
                        point_y_values.append( spectral_graph_y_values[ y_value_index ] )
                        last_index = index
                    else:
                        point_active.append( False )
                        self.points[index].color_index = 19
                        self.points[index].width = self.pixels_per_point
                        self.points[index].height = self.point_height
                        self.points[index].x=self.graph_pix_x0 + index*self.pixels_per_point
                        point_y_values.append( (index-last_index)*slopes_delta_y_per_point[y_value_index] + spectral_graph_y_values[ y_value_index ] )

                y_pixel_span = self.graph_pix_y0 - self.graph_pix_yn
                y_value_span = max( point_y_values ) -  min( point_y_values )
                if y_value_span > 0:
                    y_pix_per_value = y_pixel_span / y_value_span
                else:
                    y_pix_per_value = 1

                y_pix_coords = []
                for item in point_y_values:
                    y_pix_coords.append( self.graph_pix_y0 - self.point_height - int( y_pix_per_value *(item - min(point_y_values))) )

                for index in range (0, self.number_of_points):
                    #print( index, y_pix_coords[index] )
                    self.points[index].y = y_pix_coords[index]


def make_spectral_graph_page( instrument, spectral_register ):
    instrument.welcome_page.announce( "make_spectral_graph_page" )
    page = Spectral_Graph_Page( instrument, spectral_register )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page

class Remote_Sensing_Page( Page ):
    def __init__( self, instrument, spectral_register, hdc3022_air_sensor, mlx90614_surface_thermometer, lv_ez_mb1013_rangefinder ):
        self.instrument = instrument
        self.palette = instrument.palette
        self.spectral_register = spectral_register
        self.hdc3022_air_sensor = hdc3022_air_sensor
        self.mlx90614_surface_thermometer = mlx90614_surface_thermometer
        self.lv_ez_mb1013_rangefinder = lv_ez_mb1013_rangefinder
        super().__init__()
    def make_group( self ):
        extra_space = 8
        self.group = displayio.Group()
        separator_bar_height = 2
        rs_background_y = 54 + separator_bar_height
        rs_background_height = 240 - rs_background_y
        upper_text_y = rs_background_y + 14
        select_width = 4
        offset = 4
        upper_select_y = offset + rs_background_y
        upper_control_height = 14
        upper_select_height = upper_control_height + 2*select_width
        upper_control_y = upper_select_y + select_width
        rs_background = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=320, height=rs_background_height, x=0, y=rs_background_y)
        self.group.append( rs_background )
        # scale
        scale_select_x = offset
        scale_color_x = scale_select_x + select_width
        scale_select_width = 49
        self.scale_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=scale_select_width, height=upper_select_height, x=scale_select_x, y=upper_select_y)
        self.group.append( self.scale_select )
        self.scale_select.hidden = True
        scale_control_width = scale_select_width - 2 * select_width
        self.scale_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=scale_control_width, height=upper_control_height, x=scale_color_x, y=upper_control_y)
        self.group.append( self.scale_color )
        scale_text_x = scale_color_x + 3
        scale_group = displayio.Group(scale=1, x=scale_text_x, y=upper_text_y)
        scale_text = "linear"
        self.scale_text_area = label.Label(terminalio.FONT, text=scale_text, color=self.palette[0])
        scale_group.append(self.scale_text_area)
        self.group.append(scale_group)
        # units
        units_y_select_x = offset + scale_select_width - select_width
        units_y_color_x = units_y_select_x + select_width
        units_y_select_width = 73
        self.units_y_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=units_y_select_width, height=upper_select_height, x=units_y_select_x, y=upper_select_y)
        self.group.append( self.units_y_select )
        self.units_y_select.hidden = True
        units_y_control_width = units_y_select_width - 2 * select_width
        self.units_y_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=units_y_control_width, height=upper_control_height, x=units_y_color_x, y=upper_control_y)
        self.group.append( self.units_y_color )
        units_y_text_x = units_y_color_x + 3
        units_y_group = displayio.Group(scale=1, x=units_y_text_x, y=upper_text_y)
        units_y_text = "irradiance"
        self.units_y_text_area = label.Label(terminalio.FONT, text=units_y_text, color=self.palette[0])
        units_y_group.append(self.units_y_text_area)
        self.group.append(units_y_group)
        # spectrum
        spectrum_select_x = offset + scale_select_width + units_y_select_width - 2* select_width
        spectrum_color_x = spectrum_select_x + select_width
        spectrum_select_width = 96
        self.spectrum_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=spectrum_select_width, height=upper_select_height, x=spectrum_select_x, y=upper_select_y)
        self.group.append( self.spectrum_select )
        self.spectrum_select.hidden = True
        spectrum_control_width = spectrum_select_width - 2 * select_width
        self.spectrum_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=spectrum_control_width, height=upper_control_height, x=spectrum_color_x, y=upper_control_y)
        self.group.append( self.spectrum_color )
        spectrum_text_x = spectrum_color_x + 3
        spectrum_group = displayio.Group(scale=1, x=spectrum_text_x, y=upper_text_y)
        spectrum_text = "uv + vis + nir"
        #spectrum_text = "near infrared"
        #spectrum_text = "ultraviolet"
        #spectrum_text = "visible"
        #spectrum_text = "uv + visible"
        self.spectrum_text_area = label.Label(terminalio.FONT, text=spectrum_text, color=self.palette[0])
        spectrum_group.append(self.spectrum_text_area)
        self.group.append(spectrum_group)


        # exposure
        exposure_select_x = offset + scale_select_width + units_y_select_width + spectrum_select_width - 3*select_width
        exposure_color_x = exposure_select_x + select_width
        exposure_select_width = 49
        self.exposure_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=exposure_select_width, height=upper_select_height, x=exposure_select_x, y=upper_select_y)
        self.group.append( self.exposure_select )
        self.exposure_select.hidden = True
        exposure_control_width = exposure_select_width - 2 * select_width
        self.exposure_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=exposure_control_width, height=upper_control_height, x=exposure_color_x, y=upper_control_y)
        self.group.append( self.exposure_color )
        exposure_text_x = exposure_color_x + 3
        exposure_group = displayio.Group(scale=1, x=exposure_text_x, y=upper_text_y)
        exposure_text = "autoEx"
        self.exposure_text_area = label.Label(terminalio.FONT, text=exposure_text, color=self.palette[0])
        exposure_group.append(self.exposure_text_area)
        self.group.append(exposure_group)

        # lamps
        lamps_select_x = offset + scale_select_width + units_y_select_width + spectrum_select_width + exposure_select_width - 4* select_width
        lamps_color_x = lamps_select_x + select_width
        lamps_select_width = 66
        self.lamps_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=lamps_select_width, height=upper_select_height, x=lamps_select_x, y=upper_select_y)
        self.group.append( self.lamps_select )
        self.lamps_select.hidden = True
        lamps_control_width = lamps_select_width - 2 * select_width
        self.lamps_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=lamps_control_width, height=upper_control_height, x=lamps_color_x, y=upper_control_y)
        self.group.append( self.lamps_color )
        lamps_text_x = lamps_color_x + 3
        lamps_group = displayio.Group(scale=1, x=lamps_text_x, y=upper_text_y)
        lamps_text = "lamps off"
        self.lamps_text_area = label.Label(terminalio.FONT, text=lamps_text, color=self.palette[0])
        lamps_group.append(self.lamps_text_area)
        self.group.append(lamps_group)
        # lower controls
        lower_control_height = 14
        lower_select_y = 240 - offset - separator_bar_height - lower_control_height - select_width
        lower_select_height = lower_control_height + 2*select_width
        lower_control_y = lower_select_y + select_width
        lower_text_y = lower_control_y + 6
        # data_source
        data_source_select_x = offset
        data_source_color_x = data_source_select_x + select_width
        data_source_select_width = 50
        self.data_source_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=data_source_select_width, height=lower_select_height, x=data_source_select_x, y=lower_select_y)
        self.group.append( self.data_source_select )
        self.data_source_select.hidden = True
        data_source_control_width = data_source_select_width - 2 * select_width
        self.data_source_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=data_source_control_width, height=lower_control_height, x=data_source_color_x, y=lower_control_y)
        self.group.append( self.data_source_color )
        data_source_text_x = data_source_color_x + 3
        data_source_group = displayio.Group(scale=1, x=data_source_text_x, y=lower_text_y)
        data_source_text = "s/ref"
        self.data_source_text_area = label.Label(terminalio.FONT, text=data_source_text, color=self.palette[0])
        data_source_group.append(self.data_source_text_area)
        self.group.append(data_source_group)

        #graph_settings
        graph_settings_select_x = offset + data_source_select_width
        graph_settings_color_x = graph_settings_select_x + select_width
        graph_settings_select_width = 36
        self.graph_settings_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=graph_settings_select_width, height=lower_select_height, x=graph_settings_select_x, y=lower_select_y)
        self.group.append( self.graph_settings_select )
        self.graph_settings_select.hidden = True
        graph_settings_control_width = graph_settings_select_width - 2 * select_width
        self.graph_settings_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=graph_settings_control_width, height=lower_control_height, x=graph_settings_color_x, y=lower_control_y)
        self.group.append( self.graph_settings_color )
        graph_settings_text_x = graph_settings_color_x + 3
        graph_settings_group = displayio.Group(scale=1, x=graph_settings_text_x, y=lower_text_y)
        graph_settings_text = "set"
        self.graph_settings_text_area = label.Label(terminalio.FONT, text=graph_settings_text, color=self.palette[0])
        graph_settings_group.append(self.graph_settings_text_area)
        self.group.append(graph_settings_group)
        # units_x
        units_x_select_x = offset + data_source_control_width +graph_settings_select_width+ extra_space - 4
        units_x_color_x = units_x_select_x + select_width
        units_x_select_width = 96
        self.units_x_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=units_x_select_width, height=lower_select_height, x=units_x_select_x, y=lower_select_y)
        self.group.append( self.units_x_select )
        self.units_x_select.hidden = True
        units_x_control_width = units_x_select_width - 2 * select_width
        self.units_x_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=units_x_control_width, height=lower_control_height, x=units_x_color_x, y=lower_control_y)
        self.group.append( self.units_x_color )
        units_x_text_x = units_x_color_x + 4
        units_x_group = displayio.Group(scale=1, x=units_x_text_x, y=lower_text_y)
        units_x_text = "wavelength nm"
        self.units_x_text_area = label.Label(terminalio.FONT, text=units_x_text, color=self.palette[0])
        units_x_group.append(self.units_x_text_area)
        self.group.append(units_x_group)

        # table / graph
        table_graph_select_width = 46
        table_graph_select_x = offset + data_source_control_width + graph_settings_control_width + units_x_control_width + 2*extra_space
        table_graph_color_x = table_graph_select_x + select_width
        self.table_graph_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=table_graph_select_width, height=lower_select_height, x=table_graph_select_x, y=lower_select_y)
        self.group.append( self.table_graph_select )
        self.table_graph_select.hidden = True
        table_graph_control_width = table_graph_select_width - 2 * select_width
        self.table_graph_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=table_graph_control_width, height=lower_control_height, x=table_graph_color_x, y=lower_control_y)
        self.group.append( self.table_graph_color )
        table_graph_text_x = table_graph_color_x + 3
        table_graph_group = displayio.Group(scale=1, x=table_graph_text_x, y=lower_text_y)
        table_graph_text = "table"
        self.table_graph_text_area = label.Label(terminalio.FONT, text=table_graph_text, color=self.palette[0])
        table_graph_group.append(self.table_graph_text_area)
        self.group.append(table_graph_group)

        # live
        live_select_width = 36
        live_select_x = offset + data_source_control_width + graph_settings_control_width + units_x_control_width + table_graph_select_width +2*extra_space
        live_color_x = live_select_x + select_width
        self.live_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=live_select_width, height=lower_select_height, x=live_select_x, y=lower_select_y)
        self.group.append( self.live_select )
        self.live_select.hidden = True
        live_control_width = live_select_width - 2 * select_width
        self.live_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=live_control_width, height=lower_control_height, x=live_color_x, y=lower_control_y)
        self.group.append( self.live_color )
        live_text_x = live_color_x + 3
        live_group = displayio.Group(scale=1, x=live_text_x, y=lower_text_y)
        live_text = "LIVE"
        self.live_text_area = label.Label(terminalio.FONT, text=live_text, color=self.palette[0])
        live_group.append(self.live_text_area)
        self.group.append(live_group)

        # RETURN

        return_select_width = 50
        return_select_x = 320 - offset - return_select_width
        return_color_x = return_select_x + select_width
        self.return_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=return_select_width, height=lower_select_height, x=return_select_x, y=lower_select_y)
        self.group.append( self.return_select )
        self.return_select.hidden = True
        return_control_width = return_select_width - 2 * select_width
        self.return_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=return_control_width, height=lower_control_height, x=return_color_x, y=lower_control_y)
        self.group.append( self.return_color )
        return_text_x = return_color_x + 3
        return_group = displayio.Group(scale=1, x=return_text_x, y=lower_text_y)
        return_text = "RETURN"
        self.return_text_area = label.Label(terminalio.FONT, text=return_text, color=self.palette[0])
        return_group.append(self.return_text_area)
        self.group.append(return_group)
        right_sidebar_width = 50
        right_sidebar_x = 320 - right_sidebar_width#tbd remove
        range_text_y = upper_control_y + 25
        range_group = displayio.Group(scale=1, x=right_sidebar_x, y=range_text_y)
        range_text = "range m"
        range_text_area = label.Label(terminalio.FONT, text=range_text, color=self.palette[0])
        range_group.append(range_text_area)
        self.group.append(range_group)
        range_value_group = displayio.Group(scale=2, x=right_sidebar_x, y=range_text_y+20)
        range_value_text = "0.0m"
        self.range_value_text_area = label.Label(terminalio.FONT, text=range_value_text, color=self.palette[0])
        range_value_group.append(self.range_value_text_area)
        self.group.append(range_value_group)
        right_sidebar_spacing_y = 44
        temperature_text_y = range_text_y + right_sidebar_spacing_y
        temperature_group = displayio.Group(scale=1, x=right_sidebar_x, y=temperature_text_y)
        temperature_text = "T sf-air"
        temperature_text_area = label.Label(terminalio.FONT, text=temperature_text, color=self.palette[0])
        temperature_group.append(temperature_text_area)
        self.group.append(temperature_group)
        temperature_value_group = displayio.Group(scale=2, x=right_sidebar_x, y=temperature_text_y+20)
        temperature_value_text = "0.0C"
        self.temperature_value_text_area = label.Label(terminalio.FONT, text=temperature_value_text, color=self.palette[0])
        temperature_value_group.append(self.temperature_value_text_area)
        self.group.append(temperature_value_group)
        humidity_text_y = temperature_text_y + right_sidebar_spacing_y
        humidity_group = displayio.Group(scale=1, x=right_sidebar_x, y=humidity_text_y)
        humidity_text = "humidity"
        humidity_text_area = label.Label(terminalio.FONT, text=humidity_text, color=self.palette[0])
        humidity_group.append(humidity_text_area)
        self.group.append(humidity_group)
        humidity_value_group = displayio.Group(scale=2, x=right_sidebar_x, y=humidity_text_y+20)
        humidity_value_text = "00%"
        self.humidity_value_text_area = label.Label(terminalio.FONT, text=humidity_value_text, color=self.palette[0])
        humidity_value_group.append(self.humidity_value_text_area)
        self.group.append(humidity_value_group)
        # values bar
        values_bar_height = 14
        values_bar_y = 240 - offset - values_bar_height - lower_control_height
        values_bar_text_y = values_bar_y + 6
        values_width = 26
        left_value_x = 2* offset
        values_spacing = int((320 - left_value_x - values_width - right_sidebar_width) / 4)
        # left_value
        left_value_group = displayio.Group(scale=1, x=left_value_x, y=values_bar_y)
        left_value_text = "000"
        self.left_value_text_area = label.Label(terminalio.FONT, text=left_value_text, color=self.palette[0])
        left_value_group.append(self.left_value_text_area)
        self.group.append(left_value_group)
        # left_mid_value
        left_mid_value_x = offset + values_spacing
        left_mid_value_group = displayio.Group(scale=1, x=left_mid_value_x, y=values_bar_y)
        left_mid_value_text = "000"
        self.left_mid_value_text_area = label.Label(terminalio.FONT, text=left_mid_value_text, color=self.palette[0])
        left_mid_value_group.append(self.left_mid_value_text_area)
        self.group.append(left_mid_value_group)
        # mid_value
        mid_value_x = offset + 2* values_spacing
        mid_value_group = displayio.Group(scale=1, x=mid_value_x, y=values_bar_y)
        mid_value_text = "000"
        self.mid_value_text_area = label.Label(terminalio.FONT, text=mid_value_text, color=self.palette[0])
        mid_value_group.append(self.mid_value_text_area)
        self.group.append(mid_value_group)
        # right_mid_value
        right_mid_value_x = offset + 3*values_spacing
        right_mid_value_group = displayio.Group(scale=1, x=right_mid_value_x, y=values_bar_y)
        right_mid_value_text = "000"
        self.right_mid_value_text_area = label.Label(terminalio.FONT, text=right_mid_value_text, color=self.palette[0])
        right_mid_value_group.append(self.right_mid_value_text_area)
        self.group.append(right_mid_value_group)
        # right_value
        right_value_x = offset + 4*values_spacing
        right_value_group = displayio.Group(scale=1, x=right_value_x, y=values_bar_y)
        right_value_text = "000"
        self.right_value_text_area = label.Label(terminalio.FONT, text=right_value_text, color=self.palette[0])
        right_value_group.append(self.right_value_text_area)
        self.group.append(right_value_group)

        return self.group
    def add_spectral_graph_page(self, spectral_graph_page):
        self.spectral_graph_page = spectral_graph_page

    def update_values( self, instrument ):
        banner_duration = 3
        self.left_value_text_area.text = "{}".format(self.spectral_register.five_x_values[self.spectral_register.x_axis_units][0])
        self.left_mid_value_text_area.text = "{}".format(self.spectral_register.five_x_values[self.spectral_register.x_axis_units][1])
        self.mid_value_text_area.text = "{}".format(self.spectral_register.five_x_values[self.spectral_register.x_axis_units][2])
        self.right_mid_value_text_area.text = "{}".format(self.spectral_register.five_x_values[self.spectral_register.x_axis_units][3])
        self.right_value_text_area.text = "{}".format(self.spectral_register.five_x_values[self.spectral_register.x_axis_units][4])
        if self.spectral_register.scale_linear:
            self.scale_text_area.text = "linear"
        else:
            self.scale_text_area.text = "log"
        if self.spectral_register.y_axis_irradiance:
            self.units_y_text_area.text = "irradiance"
        else:
            self.units_y_text_area.text = "raw counts"
        if self.spectral_register.scope == 0:
            self.spectrum_text_area.text = "visible + nir"
        if self.spectral_register.scope == 1:
            self.spectrum_text_area.text = "visible"
        if self.spectral_register.scope == 2:
            self.spectrum_text_area.text = "near infrared"
        if self.spectral_register.scope == 3:
            self.spectrum_text_area.text = "uv + vis + nir"
        if self.spectral_register.scope == 4:
            self.spectrum_text_area.text = "uv + visible"
        if self.spectral_register.scope == 5:
            self.spectrum_text_area.text = "ultraviolet"
        if self.spectral_register.autoexposure:
            self.exposure_text_area.text = "autoEx"
        else:
            self.exposure_text_area.text = "holdEx"
        if self.spectral_register.lamps_on:
            self.lamps_text_area.text = "lamps on"
        else:
            self.lamps_text_area.text = "lamps off"
        if self.spectral_register.data_source == 0:
            self.data_source_text_area.text = "sample"
        if self.spectral_register.data_source == 1:
            self.data_source_text_area.text = "s/ref"
        if self.spectral_register.data_source == 2:
            self.data_source_text_area.text = "ref"
        if self.spectral_register.x_axis_units == 0:
            self.units_x_text_area.text = "wavelength nm"
        if self.spectral_register.x_axis_units == 1:
            self.units_x_text_area.text = "frequency THz"
        if self.spectral_register.x_axis_units == 2:
            self.units_x_text_area.text = "energy eV"
        if self.spectral_register.x_axis_units == 3:
            self.units_x_text_area.text = "wavenumber/cm"
        if self.spectral_register.live:
            self.live_text_area.text = "LIVE"
        else:
            self.live_text_area.text = "HOLD"
        if self.spectral_register.show_table:
            self.table_graph_text_area.text = "graph"
        else:
            self.table_graph_text_area.text = "table"

        if instrument.remote_sensing_select == 6:
            self.scale_select.hidden = False
            if instrument.button_pressed:
                self.spectral_register.scale_linear = not self.spectral_register.scale_linear
                instrument.button_pressed = False
        else:
            self.scale_select.hidden = True
        if instrument.remote_sensing_select == 7:
            self.units_y_select.hidden = False
            if instrument.button_pressed:
                self.spectral_register.y_axis_irradiance = not self.spectral_register.y_axis_irradiance
                instrument.button_pressed = False
        else:
            self.units_y_select.hidden = True
        if instrument.remote_sensing_select == 8:
            self.spectrum_select.hidden = False
            if instrument.button_pressed:
                self.spectral_register.scope = (self.spectral_register.scope + 1) % self.spectral_register.number_of_scope_choices
                instrument.button_pressed = False
        else:
            self.spectrum_select.hidden = True
        if instrument.remote_sensing_select == 9:
            self.exposure_select.hidden = False
            if instrument.button_pressed:
                self.spectral_graph_page.banner_group.hidden = False
                self.spectral_graph_page.banner_message_area.text = "autoexposure"
                #self.spectral_register.autoexposure = not self.spectral_register.autoexposure
                instrument.button_pressed = False
                time.sleep(banner_duration)
        else:
            self.spectral_graph_page.banner_group.hidden = True
            self.exposure_select.hidden = True
        if instrument.remote_sensing_select == 10:
            self.lamps_select.hidden = False
            if instrument.button_pressed:
                self.spectral_register.lamps_on = not self.spectral_register.lamps_on
                for spectral_sensor in self.instrument.spectral_sensors_present:
                    if self.spectral_register.lamps_on:
                        spectral_sensor.lamps_on()
                    else:
                        spectral_sensor.lamps_off()
                instrument.button_pressed = False
        else:
            self.lamps_select.hidden = True
        if instrument.remote_sensing_select == 11:
            self.data_source_select.hidden = False
            if instrument.button_pressed:
                self.spectral_graph_page.banner_message_area.text = "sample, ref, s/ref"
                self.spectral_graph_page.banner_group.hidden = False
                #self.spectral_register.data_source = (self.spectral_register.data_source + 1) % self.spectral_register.number_of_data_source_choices
                instrument.button_pressed = False
                time.sleep(banner_duration)
        else:
            self.spectral_graph_page.banner_group.hidden = True
            self.data_source_select.hidden = True
        if instrument.remote_sensing_select == 12:
            self.graph_settings_select.hidden = False
            if instrument.button_pressed:
                self.spectral_graph_page.banner_message_area.text = "sensor + ref set"
                self.spectral_graph_page.banner_group.hidden = False
                instrument.button_pressed = False
                time.sleep(banner_duration)
        else:
            self.graph_settings_select.hidden = True
            self.spectral_graph_page.banner_group.hidden = True
        if instrument.remote_sensing_select == 13:
            self.units_x_select.hidden = False
            if instrument.button_pressed:
                self.spectral_register.x_axis_units = (self.spectral_register.x_axis_units + 1) % self.spectral_register.number_of_x_axis_units_choices
                instrument.button_pressed = False
        else:
            self.units_x_select.hidden = True
        if instrument.remote_sensing_select == 14:
            self.table_graph_select.hidden = False
            if instrument.button_pressed:
                self.spectral_graph_page.banner_message_area.text = "table or graph"
                self.spectral_graph_page.banner_group.hidden = False
                #self.spectral_register.show_table = not self.spectral_register.show_table
                instrument.button_pressed = False
                time.sleep(banner_duration)
        else:
            self.table_graph_select.hidden = True
            self.spectral_graph_page.banner_group.hidden = True
        if instrument.remote_sensing_select == 15:
            self.live_select.hidden = False
            if instrument.button_pressed:
                self.spectral_register.live = not self.spectral_register.live
                instrument.button_pressed = False
        else:
            self.live_select.hidden = True
        if instrument.remote_sensing_select == 16:
            self.return_select.hidden = False
            if instrument.button_pressed:
                instrument.active_page_number = 2
                instrument.button_pressed = False
        else:
            self.return_select.hidden = True

        if self.spectral_register.live:
            if self.mlx90614_surface_thermometer.pn and self.hdc3022_air_sensor.pn:
                self.lv_ez_mb1013_rangefinder.read()
                if self.lv_ez_mb1013_rangefinder.range_m < 0.3:
                    self.range_value_text_area.text = "<0.3"
                elif self.lv_ez_mb1013_rangefinder.range_m > 2.5:
                    self.range_value_text_area.text = ">2.5"
                else:
                    self.range_value_text_area.text = "{}".format(round(self.lv_ez_mb1013_rangefinder.range_m,2))
                self.mlx90614_surface_thermometer.read()
                self.hdc3022_air_sensor.read()
                t_surface_minus_air_C = int(self.mlx90614_surface_thermometer.surface_temperature_C - self.hdc3022_air_sensor.temperature_C)
                if t_surface_minus_air_C < 0:
                    self.temperature_value_text_area.text = "{}C".format(t_surface_minus_air_C)
                elif t_surface_minus_air_C < 10:
                    self.temperature_value_text_area.text = " {}C".format(t_surface_minus_air_C)
                else:
                    self.temperature_value_text_area.text = "{}C".format(t_surface_minus_air_C)

                self.humidity_value_text_area.text = "{}%".format(int(self.hdc3022_air_sensor.humidity_percent))
            else:
                self.range_value_text_area.text = " --"
                self.humidity_value_text_area.text = " --"
                self.temperature_value_text_area.text = " --"

def make_remote_sensing_page( instrument, spectral_register, hdc3022_air_sensor, mlx90614_surface_thermometer, lv_ez_mb1013_rangefinder ):
    instrument.welcome_page.announce( "make_remote_sensing_page" )
    page = Remote_Sensing_Page( instrument, spectral_register, hdc3022_air_sensor, mlx90614_surface_thermometer, lv_ez_mb1013_rangefinder )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page

class Main_Menu_Page( Page ):
    def __init__( self, palette):
        super().__init__()
        self.palette = palette
    def make_group( self ):
        menu_list = "Remote Sense", "Air Analyzer", "Sensors", "Time / Place", "*future use", "*future use", "*future use", "*future use"#, "* Air Analyz", "* Heat", "* Plants"
        menu_color_list = 20, 12, 21, 14, 19, 19, 19, 19
        self.group = displayio.Group()
        start_y = 54
        status_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240-start_y, x=0, y=start_y )
        self.group.append( status_background )
        title_bar = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=320-2*5, height=24, x=0+5, y=start_y)
        self.group.append( title_bar )
        title_group = displayio.Group(scale=2, x=100, y=12+start_y)
        title_text = "Main Menu"
        title_text_area = label.Label(terminalio.FONT, text=title_text, color=self.palette[0])
        title_group.append(title_text_area)
        self.group.append(title_group)
        #selection rectangles
        selection_start_x = 2
        selection_start_y = 78
        selection_offset_x = 158
        selection_offset_y = 31
        self.selection_rectangles = []
        #TBD be more clever about this section
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=158, height=36, x=selection_start_x, y=selection_start_y))
        self.group.append( self.selection_rectangles[0] )
        self.selection_rectangles[0].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=158, height=36, x=selection_start_x+selection_offset_x, y=selection_start_y))
        self.group.append( self.selection_rectangles[1] )
        self.selection_rectangles[1].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=158, height=36, x=selection_start_x, y=selection_start_y+selection_offset_y))
        self.group.append( self.selection_rectangles[2] )
        self.selection_rectangles[2].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=158, height=36, x=selection_start_x+selection_offset_x, y=selection_start_y+selection_offset_y))
        self.group.append( self.selection_rectangles[3] )
        self.selection_rectangles[3].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=158, height=36, x=selection_start_x, y=selection_start_y+selection_offset_y*2))
        self.group.append( self.selection_rectangles[4] )
        self.selection_rectangles[4].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=158, height=36, x=selection_start_x+selection_offset_x, y=selection_start_y+selection_offset_y*2))
        self.group.append( self.selection_rectangles[5] )
        self.selection_rectangles[5].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=158, height=36, x=selection_start_x, y=selection_start_y+selection_offset_y*3))
        self.group.append( self.selection_rectangles[6] )
        self.selection_rectangles[6].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=158, height=36, x=selection_start_x+selection_offset_x, y=selection_start_y+selection_offset_y*3))
        self.group.append( self.selection_rectangles[7] )
        self.selection_rectangles[7].hidden = True
        #choice color rectangles
        selection_border = 5
        choice_rectangles = []
        #TBD be more clever about this section
        choice_width = 158-2*selection_border
        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[0],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border, y=selection_start_y+selection_border))
        self.group.append( choice_rectangles[0] )
        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[1],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border+selection_offset_x, y=selection_start_y+selection_border))
        self.group.append( choice_rectangles[1] )
        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[2],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border, y=selection_start_y+selection_border+selection_offset_y))
        self.group.append( choice_rectangles[2] )
        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[3],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border+selection_offset_x, y=selection_start_y+selection_border+selection_offset_y))
        self.group.append( choice_rectangles[3] )
        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[4],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border, y=selection_start_y+selection_border+selection_offset_y*2))
        self.group.append( choice_rectangles[4] )
        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[5],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border+selection_offset_x, y=selection_start_y+selection_border+selection_offset_y*2))
        self.group.append( choice_rectangles[5] )
        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[6],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border, y=selection_start_y+selection_border+selection_offset_y*3))
        self.group.append( choice_rectangles[6] )
        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[7],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border+selection_offset_x, y=selection_start_y+selection_border+selection_offset_y*3))
        self.group.append( choice_rectangles[7] )



        #choice text
        menu_spacing_y = selection_offset_y
        menu_start_y = 12+start_y+30
        menu_spacing_x = 158
        menu_start_x = 10
        for index in range ( 0, len(menu_list), 2):
            item_group = displayio.Group(scale=2, x=menu_start_x, y=menu_start_y+menu_spacing_y*int(index/2))
            item_text = menu_list[ index ]
            item_text_area = label.Label(terminalio.FONT, text=item_text, color=self.palette[0])
            item_group.append(item_text_area)
            self.group.append(item_group)
            if index + 1 < len(menu_list):
                item_group = displayio.Group(scale=2, x=menu_start_x+menu_spacing_x, y=menu_start_y+menu_spacing_y*int(index/2))
                item_text = menu_list[ index+1 ]
                item_text_area = label.Label(terminalio.FONT, text=item_text, color=self.palette[0])
                item_group.append(item_text_area)
                self.group.append(item_group)

        footer_start_y = 204
        footer_offset_x = 106
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=104, height=36, x=selection_start_x, y=footer_start_y))
        self.group.append( self.selection_rectangles[8] )
        self.selection_rectangles[8].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=104, height=36, x=selection_start_x+footer_offset_x, y=footer_start_y))
        self.group.append( self.selection_rectangles[9] )
        self.selection_rectangles[9].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=104, height=36, x=selection_start_x+2*footer_offset_x, y=footer_start_y))
        self.group.append( self.selection_rectangles[10] )
        self.selection_rectangles[10].hidden = True
        status_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=16, width=96, height=28, x=selection_start_x+4, y=208)
        self.group.append( status_color )
        self.more_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=96, height=28, x=selection_start_x+4+footer_offset_x, y=208)
        self.group.append( self.more_color )
        self.return_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=22, width=96, height=28, x=selection_start_x+4+2*footer_offset_x, y=208)
        self.group.append( self.return_color )

        footer_text_start_x = 14
        footer_text_y = 222
        status_text = "Status"
        status_group = displayio.Group(scale=2, x=footer_text_start_x, y=footer_text_y)
        status_text_area = label.Label(terminalio.FONT, text=status_text, color=self.palette[0])
        status_group.append(status_text_area)
        self.group.append(status_group)
        more_text =   "*More.."
        more_group = displayio.Group(scale=2, x=footer_text_start_x+footer_offset_x, y=footer_text_y)
        more_text_area = label.Label(terminalio.FONT, text=more_text, color=self.palette[0])
        more_group.append(more_text_area)
        self.group.append(more_group)
        return_text = "RETURN"
        return_group = displayio.Group(scale=2, x=footer_text_start_x+2*footer_offset_x, y=footer_text_y)
        return_text_area = label.Label(terminalio.FONT, text=return_text, color=self.palette[0])
        return_group.append(return_text_area)
        self.group.append(return_group)
        return self.group

    def update_values( self, instrument ):
        if instrument.main_menu_select in range( 10, 13 ): ### skip future use choices
            instrument.main_menu_select = 14
        if instrument.main_menu_select == 15:  ### skip future use *more option
            instrument.main_menu_select = 16
        if instrument.main_menu_select == 6:
            self.selection_rectangles[0].hidden = False
            if instrument.button_pressed:
                instrument.active_page_number = 9
                instrument.button_pressed = False
        else:
            self.selection_rectangles[0].hidden = True
        if instrument.main_menu_select == 7:
            self.selection_rectangles[1].hidden = False
            if instrument.button_pressed:
                instrument.active_page_number = 8
                instrument.button_pressed = False
        else:
            self.selection_rectangles[1].hidden = True
        if instrument.main_menu_select == 8:
            self.selection_rectangles[2].hidden = False
            if instrument.button_pressed:
                instrument.active_page_number = 5
                instrument.button_pressed = False
        else:
            self.selection_rectangles[2].hidden = True
        if instrument.main_menu_select == 9:
            if instrument.button_pressed:
                instrument.active_page_number = 7
                instrument.button_pressed = False
            self.selection_rectangles[3].hidden = False
        else:
            self.selection_rectangles[3].hidden = True
        if instrument.main_menu_select == 10:
            self.selection_rectangles[4].hidden = False
        else:
            self.selection_rectangles[4].hidden = True
        if instrument.main_menu_select == 11:
            self.selection_rectangles[5].hidden = False
        else:
            self.selection_rectangles[5].hidden = True
        if instrument.main_menu_select == 12:
            self.selection_rectangles[6].hidden = False
        else:
            self.selection_rectangles[6].hidden = True
        if instrument.main_menu_select == 13:
            self.selection_rectangles[7].hidden = False
        else:
            self.selection_rectangles[7].hidden = True
        if instrument.main_menu_select == 14:
            self.selection_rectangles[8].hidden = False
            if instrument.button_pressed:
                instrument.active_page_number = 3
                instrument.button_pressed = False
        else:
            self.selection_rectangles[8].hidden = True
        if instrument.main_menu_select == 15:
            self.selection_rectangles[9].hidden = False
        else:
            self.selection_rectangles[9].hidden = True
        if instrument.main_menu_select == 16:
            self.selection_rectangles[10].hidden = False
            if instrument.button_pressed:
                print("TBD go back to previous page" )
                instrument.button_pressed = False
        else:
            self.selection_rectangles[10].hidden = True


def make_main_menu_page( instrument ):
    instrument.welcome_page.announce( "make_main_menu_page" )
    page = Main_Menu_Page(instrument.palette)
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page


class Controls_Page( Page ):
    def __init__( self, palette, gps, battery_monitor ):
        super().__init__()
        self.palette = palette
        self.gps = gps
        self.battery_monitor = battery_monitor
        self.select_value = 2
        self.number_of_select_values = 7
    def make_group( self ):
        self.group = displayio.Group()
        control_bar_height = 54
        text_y1 = 16
        text_y2 = text_y1 + 14 + 3
        select_width = 4
        offset = 4
        select_height = control_bar_height - 2 * offset
        select_y = offset
        control_y = select_y + select_width
        control_height = select_height - 2 * select_width
        controls_background = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=320, height=control_bar_height, x=0, y=0)
        self.group.append( controls_background )
        # gps
        gps_select_x = offset - 1
        gps_color_x = gps_select_x + select_width
        gps_select_width = 44
        self.gps_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=gps_select_width, height=select_height, x=gps_select_x, y=select_y)
        self.group.append( self.gps_select )
        self.gps_select.hidden = True
        gps_control_width = gps_select_width - 2 * select_width
        self.gps_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=8, width=gps_control_width, height=control_height, x=gps_color_x, y=control_y)
        self.group.append( self.gps_color )
        gps_text_x = gps_color_x + 3
        gps_group = displayio.Group(scale=1, x=gps_text_x, y=text_y1+2)
        gps_text = " GPS"
        gps_text_area = label.Label(terminalio.FONT, text=gps_text, color=self.palette[9])
        gps_group.append(gps_text_area)
        self.group.append(gps_group)
        gps_value_group = displayio.Group(scale=1, x=gps_text_x, y=text_y2)
        gps_value_text = "nofix"
        self.gps_value_text_area = label.Label(terminalio.FONT, text=gps_value_text, color=self.palette[9])
        gps_value_group.append(self.gps_value_text_area)
        self.group.append(gps_value_group)
        # batch
        batch_select_x = 2*offset+gps_select_width-3
        batch_color_x = batch_select_x + select_width
        batch_select_width = 52
        self.batch_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=batch_select_width, height=select_height, x=batch_select_x, y=select_y)
        self.group.append( self.batch_select )
        self.batch_select.hidden = True
        batch_control_width = batch_select_width - 2 * select_width
        batch_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=6, width=batch_control_width, height=control_height, x=batch_color_x, y=control_y)
        self.group.append( batch_color )
        self.batch_text_x = batch_color_x + 5
        batch_group = displayio.Group(scale=1, x=self.batch_text_x+1, y=text_y1)
        batch_text = "batch"
        batch_text_area = label.Label(terminalio.FONT, text=batch_text, color=self.palette[9])
        batch_group.append(batch_text_area)
        self.group.append(batch_group)
        self.batch_value_group = displayio.Group(scale=2, x=self.batch_text_x, y=text_y2)
        batch_value_text = "000"
        self.batch_value_text_area = label.Label(terminalio.FONT, text=batch_value_text, color=self.palette[9])
        self.batch_value_group.append(self.batch_value_text_area)
        self.group.append(self.batch_value_group)
        # pause and record
        pause_record_select_x = 2*offset+gps_select_width+batch_select_width+2
        pause_record_x = pause_record_select_x + select_width
        pause_record_select_width = select_height
        self.pause_record_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=pause_record_select_width, height=select_height, x=pause_record_select_x, y=select_y)
        self.group.append( self.pause_record_select )
        pause_record_control_width = pause_record_select_width - 2 * select_width
        pause_record_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=pause_record_control_width, height=control_height, x=pause_record_x, y=control_y)
        self.group.append( pause_record_color )
        pause_record_offset_x = 6
        pause_record_y = 14
        pause_base = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=26, height=26, x=pause_record_x+pause_record_offset_x, y=pause_record_y)
        self.group.append( pause_base )
        pause_split = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=8, height=26, x=pause_record_x+9+pause_record_offset_x, y=pause_record_y)
        self.group.append( pause_split )
        self.record_circle = vectorio.Circle( pixel_shader=self.palette, color_index=2, radius=18, x=pause_record_x+12+pause_record_offset_x, y=pause_record_y+13 )
        self.group.append( self.record_circle )
        #self.record_circle.hidden = True
        self.pause_record_select.hidden = True
        # burst
        burst_select_x = pause_record_select_width + pause_record_x # - offset
        burst_color_x = burst_select_x + select_width
        burst_select_width = 44
        self.burst_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=burst_select_width, height=select_height, x=burst_select_x, y=select_y)
        self.group.append( self.burst_select )
        self.burst_select.hidden = True
        burst_control_width = burst_select_width - 2 * select_width
        self.burst_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=16, width=burst_control_width, height=control_height, x=burst_color_x, y=control_y)
        self.group.append( self.burst_color )
        burst_text_x = burst_color_x + 6
        burst_group = displayio.Group(scale=1, x=burst_text_x-2, y=text_y1)
        burst_text = "burst"
        burst_text_area = label.Label(terminalio.FONT, text=burst_text, color=self.palette[9])
        burst_group.append(burst_text_area)
        self.group.append(burst_group)
        burst_value_group = displayio.Group(scale=2, x=burst_text_x+1, y=text_y2)
        burst_value_text = "00"
        self.burst_value_text_area = label.Label(terminalio.FONT, text=burst_value_text, color=self.palette[9])
        burst_value_group.append(self.burst_value_text_area)
        self.group.append(burst_value_group)
        # interval
        interval_select_x = burst_select_width + burst_color_x - 2
        interval_color_x = interval_select_x + select_width
        interval_select_width = 58
        self.interval_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=interval_select_width, height=select_height, x=interval_select_x, y=select_y)
        self.group.append( self.interval_select )
        self.interval_select.hidden = True
        interval_control_width = interval_select_width - 2 * select_width
        interval_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=7, width=interval_control_width, height=control_height, x=interval_color_x, y=control_y)
        self.group.append( interval_color )
        interval_text_x = interval_color_x + 5
        interval_group = displayio.Group(scale=1, x=interval_text_x-3, y=text_y1)
        interval_text = "settings"
        interval_text_area = label.Label(terminalio.FONT, text=interval_text, color=self.palette[9])
        interval_group.append(interval_text_area)
        self.group.append(interval_group)
        interval_value_group = displayio.Group(scale=2, x=interval_text_x+3, y=text_y2)
        interval_value_text = " >>"
        self.interval_value_text_area = label.Label(terminalio.FONT, text=interval_value_text, color=self.palette[9])
        interval_value_group.append(self.interval_value_text_area)
        self.group.append(interval_value_group)
        # battery
        battery_select_x = interval_select_width + interval_color_x - 2
        battery_color_x = battery_select_x + select_width
        battery_select_width = 56
        self.battery_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=battery_select_width, height=select_height, x=battery_select_x, y=select_y)
        self.group.append( self.battery_select )
        self.battery_select.hidden = True
        battery_control_width = battery_select_width - 2 * select_width
        battery_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=15, width=battery_control_width, height=control_height, x=battery_color_x, y=control_y)
        self.group.append( battery_color )
        battery_text_x = battery_color_x + 6
        battery_group = displayio.Group(scale=1, x=battery_text_x-2, y=text_y1)
        battery_text = "battery"
        battery_text_area = label.Label(terminalio.FONT, text=battery_text, color=self.palette[9])
        battery_group.append(battery_text_area)
        self.group.append(battery_group)
        battery_value_group = displayio.Group(scale=2, x=battery_text_x+1, y=text_y2)
        battery_value_text = "00%"
        self.battery_value_text_area = label.Label(terminalio.FONT, text=battery_value_text, color=self.palette[9])
        battery_value_group.append(self.battery_value_text_area)
        self.group.append(battery_value_group)
        return self.group
    def update_burst_countdown( self, value ):
        if value < 10:
            self.burst_value_text_area.text = " {}".format(value)
        else:
            self.burst_value_text_area.text = "{}".format(value)
    def update_values( self, instrument ):
        if self.gps.fix():
            self.gps_value_text_area.text = " FIX"
            self.gps_color.color_index = 18
        else:
            self.gps_value_text_area.text = "nofix"
            self.gps_color.color_index = 8
        self.battery_value_text_area.text = "{}%".format( int(self.battery_monitor.percentage))
        if instrument.burst_count < 10:
            self.burst_value_text_area.text = " {}".format(instrument.burst_count)
        else:
            self.burst_value_text_area.text = "{}".format(instrument.burst_count)
        if instrument.record:
            self.record_circle.hidden = False
        else:
            self.record_circle.hidden = True
        self.batch_value_text_area.text = "{}".format(instrument.batch_number)
        if instrument.batch_number < 10:
            self.batch_value_group.x = self.batch_text_x+7
        elif instrument.batch_number < 100:
            self.batch_value_group.x = self.batch_text_x+5
        else:
            self.batch_value_group.x = self.batch_text_x-3

        ## processing inputs


        if instrument.active_page_number == 2: # main menu
            if instrument.main_menu_select == 0:
                self.gps_select.hidden = False
                if instrument.button_pressed:
                    instrument.active_page_number = 7
                    instrument.button_pressed = False
            else:
                self.gps_select.hidden = True
            if instrument.main_menu_select == 1:
                self.batch_select.hidden = False
                if instrument.button_pressed:
                    instrument.update_batch()
                    instrument.button_pressed = False
            else:
                self.batch_select.hidden = True
            if instrument.main_menu_select == 2:
                self.pause_record_select.hidden = False
                if instrument.button_pressed:
                    instrument.record = not instrument.record
                    instrument.button_pressed = False
            else:
                self.pause_record_select.hidden = True
            if instrument.main_menu_select == 3:
                self.burst_select.hidden = False
                if instrument.button_pressed:
                    instrument.take_burst = True
                    instrument.record = False
                    self.burst_color.color_index = 6
                    instrument.button_pressed = False
            else:
                self.burst_select.hidden = True
            if instrument.main_menu_select == 4:
                self.interval_select.hidden = False
                if instrument.button_pressed:
                    instrument.active_page_number = 4
                    instrument.button_pressed = False
            else:
                self.interval_select.hidden = True
            if instrument.main_menu_select == 5:
                self.battery_select.hidden = False
                if instrument.button_pressed:
                    instrument.active_page_number = 3
                    instrument.button_pressed = False
            else:
                self.battery_select.hidden = True

        if instrument.active_page_number == 9: # remote sensing
            if instrument.remote_sensing_select == 0:
                self.gps_select.hidden = False
                if instrument.button_pressed:
                    instrument.active_page_number = 7
                    instrument.button_pressed = False
            else:
                self.gps_select.hidden = True
            if instrument.remote_sensing_select == 1:
                self.batch_select.hidden = False
                if instrument.button_pressed:
                    instrument.update_batch()
                    instrument.button_pressed = False
            else:
                self.batch_select.hidden = True
            if instrument.remote_sensing_select == 2:
                self.pause_record_select.hidden = False
                if instrument.button_pressed:
                    instrument.record = not instrument.record
                    instrument.button_pressed = False
            else:
                self.pause_record_select.hidden = True
            if instrument.remote_sensing_select == 3:
                self.burst_select.hidden = False
                if instrument.button_pressed:
                    instrument.take_burst = True
                    instrument.record = False
                    self.burst_color.color_index = 6
                    instrument.button_pressed = False
            else:
                self.burst_select.hidden = True
            if instrument.remote_sensing_select == 4:
                self.interval_select.hidden = False
                if instrument.button_pressed:
                    instrument.active_page_number = 4
                    instrument.button_pressed = False
            else:
                self.interval_select.hidden = True
            if instrument.remote_sensing_select == 5:
                self.battery_select.hidden = False
                if instrument.button_pressed:
                    instrument.active_page_number = 3
                    instrument.button_pressed = False
            else:
                self.battery_select.hidden = True


def make_controls_page( instrument, gps, battery_monitor ):
    instrument.welcome_page.announce( "make_controls_page" )
    page = Controls_Page( instrument.palette, gps, battery_monitor )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page



class Settings_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.palette = instrument.palette
    def make_group( self ):
        self.group = displayio.Group()
        status_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240, x=0, y=0 )
        self.group.append( status_background )
        title_group = displayio.Group(scale=2, x=10, y=18)
        title_text = "Settings"
        title_text_area = label.Label(terminalio.FONT, text=title_text, color=self.palette[0])
        title_group.append(title_text_area)
        self.group.append(title_group)
        spacing_y = 25

        value_x = 220
        select_x = 212
        select_height = 30
        select_width = 100
        select_start_y = spacing_y + 4
        border_width = 2

        interval_group = displayio.Group(scale=2, x=10, y= 18 + spacing_y)
        interval_text = "Sample Interval:"
        interval_text_area = label.Label(terminalio.FONT, text=interval_text, color=self.palette[0])
        interval_group.append(interval_text_area)
        self.group.append(interval_group)

        self.interval_value_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=select_width,
                                                            height=select_height, x=select_x, y=select_start_y )
        self.group.append( self.interval_value_select )
        self.interval_value_highlight = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9,
                                                            width=select_width - 2* border_width, height=select_height-2*border_width,
                                                            x=select_x+border_width, y=select_start_y+border_width )
        self.group.append( self.interval_value_highlight )
        self.interval_value_select.hidden = True

        interval_value_group = displayio.Group(scale=2, x=value_x, y= 18 + spacing_y)
        interval_value_text = "000s"
        self.interval_value_text_area = label.Label(terminalio.FONT, text=interval_value_text, color=self.palette[0])
        interval_value_group.append(self.interval_value_text_area)
        self.group.append(interval_value_group)

        burst_group = displayio.Group(scale=2, x=10, y= 18 +2* spacing_y)
        burst_text = "Burst Count:"
        burst_text_area = label.Label(terminalio.FONT, text=burst_text, color=self.palette[0])
        burst_group.append(burst_text_area)
        self.group.append(burst_group)

        self.burst_value_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=select_width,
                                                        height=select_height, x=select_x, y=select_start_y + spacing_y)
        self.group.append( self.burst_value_select )
        self.burst_value_highlight = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9,
                                                        width=select_width - 2* border_width, height=select_height-2*border_width,
                                                        x=select_x+border_width, y=select_start_y+border_width + spacing_y)
        self.group.append( self.burst_value_highlight )
        self.burst_value_select.hidden = True

        burst_value_group = displayio.Group(scale=2, x=value_x, y= 18 + 2*spacing_y)
        burst_value_text = "000"
        self.burst_value_text_area = label.Label(terminalio.FONT, text=burst_value_text, color=self.palette[0])
        burst_value_group.append(self.burst_value_text_area)
        self.group.append(burst_value_group)

        serial_out_group = displayio.Group(scale=2, x=10, y= 18 +3* spacing_y)
        serial_out_text = "USB serial data output:"
        serial_out_text_area = label.Label(terminalio.FONT, text=serial_out_text, color=self.palette[0])
        serial_out_group.append(serial_out_text_area)
        self.group.append(serial_out_group)

        serial_out_x_adjust = 72
        self.serial_out_value_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=select_width - serial_out_x_adjust,
                                                        height=select_height, x=select_x+serial_out_x_adjust, y=select_start_y + 2* spacing_y)
        self.group.append( self.serial_out_value_select )
        self.serial_out_value_highlight = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9,
                                                        width=select_width - 2* border_width-serial_out_x_adjust, height=select_height-2*border_width,
                                                        x=select_x+border_width+serial_out_x_adjust, y=select_start_y+border_width + 2* spacing_y)
        self.group.append( self.serial_out_value_highlight )
        self.serial_out_value_select.hidden = True

        serial_out_value_group = displayio.Group(scale=2, x=value_x+70, y= 18 + 3*spacing_y)
        serial_out_value_text = "N"
        self.serial_out_value_text_area = label.Label(terminalio.FONT, text=serial_out_value_text, color=self.palette[0])
        serial_out_value_group.append(self.serial_out_value_text_area)
        self.group.append(serial_out_value_group)

        text_group = displayio.Group(scale=2, x=10, y= 18 +4* spacing_y)
        text = "TBD allow user to set vals"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        if False:
            spectral_sensor_group = displayio.Group(scale=2, x=10, y=int(18+4.5*spacing_y))
            spectral_sensor_text = "Spectral Sensor:"
            spectral_sensor_text_area = label.Label(terminalio.FONT, text=spectral_sensor_text, color=self.palette[0])
            spectral_sensor_group.append(spectral_sensor_text_area)
            self.group.append(spectral_sensor_group)

            self.sensor_value_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=select_width,
                                                            height=select_height, x=select_x, y=int( select_start_y + 3.5* spacing_y) )
            self.group.append( self.sensor_value_select )
            self.sensor_value_highlight = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9,
                                                            width=select_width - 2* border_width, height=select_height-2*border_width,
                                                            x=select_x+border_width, y=int( select_start_y+border_width + 3.5* spacing_y) )
            self.group.append( self.sensor_value_highlight )
            self.sensor_value_select.hidden = True

            spectral_sensor_value_group = displayio.Group(scale=2, x=value_x, y=int(18+4.5*spacing_y))
            spectral_sensor_value_text = "as7265x"
            self.spectral_sensor_value_text_area = label.Label(terminalio.FONT, text=spectral_sensor_value_text, color=self.palette[0])
            spectral_sensor_value_group.append(self.spectral_sensor_value_text_area)
            self.group.append(spectral_sensor_value_group)

            gain_group = displayio.Group(scale=2, x=10, y=int(18 + 5.5* spacing_y))
            gain_text = "Gain:"
            gain_text_area = label.Label(terminalio.FONT, text=gain_text, color=self.palette[0])
            gain_group.append(gain_text_area)
            self.group.append(gain_group)

            self.gain_value_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=select_width,
                                                            height=select_height, x=select_x, y=int( select_start_y + 4.5* spacing_y) )
            self.group.append( self.gain_value_select )
            self.gain_value_highlight = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9,
                                                            width=select_width - 2* border_width, height=select_height-2*border_width,
                                                            x=select_x+border_width, y=int( select_start_y+border_width + 4.5* spacing_y) )
            self.group.append( self.gain_value_highlight )
            self.gain_value_select.hidden = True

            gain_value_group = displayio.Group(scale=2, x=value_x, y=int(18 + 5.5* spacing_y))
            gain_value_text = "1X"
            self.gain_value_text_area = label.Label(terminalio.FONT, text=gain_value_text, color=self.palette[0])
            gain_value_group.append(self.gain_value_text_area)
            self.group.append(gain_value_group)

            integration_time_group = displayio.Group(scale=2, x=10, y=int(18+6.5*spacing_y))
            integration_time_text = "Integration Time:"
            integration_time_text_area = label.Label(terminalio.FONT, text=integration_time_text, color=self.palette[0])
            integration_time_group.append(integration_time_text_area)
            self.group.append(integration_time_group)

            self.integration_time_value_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=select_width,
                                                            height=select_height, x=select_x, y=int( select_start_y + 5.5* spacing_y) )
            self.group.append( self.integration_time_value_select )
            self.integration_time_value_highlight = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9,
                                                            width=select_width - 2* border_width, height=select_height-2*border_width,
                                                            x=select_x+border_width, y=int( select_start_y+border_width + 5.5* spacing_y) )
            self.group.append( self.integration_time_value_highlight )
            self.integration_time_value_select.hidden = True

            integration_time_value_group = displayio.Group(scale=2, x=value_x, y=int(18+6.5*spacing_y))
            integration_time_value_text = "166ms"
            self.integration_time_value_text_area = label.Label(terminalio.FONT, text=integration_time_value_text, color=self.palette[0])
            integration_time_value_group.append(self.integration_time_value_text_area)
            self.group.append(integration_time_value_group)

        # RETURN
        select_width = 4
        return_height = 28
        return_select_y = 240 - 4 - 2 - return_height - select_width
        return_select_height = return_height + 2*select_width
        return_y = return_select_y + select_width
        return_text_y = return_y + 14
        return_select_width = 100
        return_select_x = 320 - 4 - return_select_width
        return_x = return_select_x + select_width
        self.return_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=return_select_width, height=return_select_height, x=return_select_x, y=return_select_y)
        self.group.append( self.return_select )
        #self.return_select.hidden = True
        return_control_width = return_select_width - 2 * select_width
        self.return_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=return_control_width, height=return_height, x=return_x, y=return_y)
        self.group.append( self.return_color )
        return_text_x = return_x + 10
        return_group = displayio.Group(scale=2, x=return_text_x, y=return_text_y)
        return_text = "RETURN"
        self.return_text_area = label.Label(terminalio.FONT, text=return_text, color=self.palette[0])
        return_group.append(self.return_text_area)
        self.group.append(return_group)

        return self.group
    def update_values( self, instrument ):
        if instrument.button_pressed:
            instrument.active_page_number = 2
            instrument.button_pressed = False
        intervals = instrument.sample_interval_s
        #print( intervals )
        intervalm = intervals / 60
        intervalh = intervalm / 60
        intervald = intervalh / 24
        #print( intervals, intervalm, intervalh, intervald )
        if intervals < 10:
            interval_text = " {}s".format(int(intervals))
        elif intervals < 60:
            interval_text = "{}s".format(int(intervals))
        elif intervalm < 10:
            interval_text = " {}m".format(int(intervalm))
        elif intervals < 60:
            interval_text = "{}m".format(int(intervalm))
        elif intervalh < 10:
            interval_text = " {}h".format(int(intervalh))
        elif intervalh < 60:
            interval_text = "{}h".format(int(intervalh))
        elif intervald < 10:
            interval_text = " {}d".format(int(intervald))
        else:
            interval_text = "{}d".format(int(intervald))
        self.interval_value_text_area.text = interval_text
        if instrument.burst_count < 10:
            burst_text = " {}".format(instrument.burst_count)
        else:
            burst_text = "{}".format(instrument.burst_count)
        #if instrument.usb_serial_out:
        #    self.serial_out_value_text_area.text = "Y"
        #else:
        #    self.serial_out_value_text_area.text = "N"


        self.burst_value_text_area.text = burst_text

def make_settings_page( instrument ):
    instrument.welcome_page.announce( "make_settings_page" )
    page = Settings_Page( instrument )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page

class Status_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.palette = instrument.palette
    def make_group( self ):
        self.group = displayio.Group()
        status_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240, x=0, y=0 )
        self.group.append( status_background )
        text_spacing_y = 28
        status_title_group = displayio.Group(scale=2, x=10, y=18)
        status_title_text = "Instrument Status: TBD"
        status_title_text_area = label.Label(terminalio.FONT, text=status_title_text, color=self.palette[0])
        status_title_group.append(status_title_text_area)
        self.group.append(status_title_group)

        text_group = displayio.Group(scale=2, x=10, y=18+text_spacing_y)
        text = "main battery status"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        text_group = displayio.Group(scale=2, x=10, y=18+2*text_spacing_y)
        text = "clock battery status"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        text_group = displayio.Group(scale=2, x=10, y=18+3*text_spacing_y)
        text = "sd card storage remaining"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        # RETURN
        select_width = 4
        return_height = 28
        return_select_y = 240 - 4 - 2 - return_height - select_width
        return_select_height = return_height + 2*select_width
        return_y = return_select_y + select_width
        return_text_y = return_y + 12
        return_select_width = 100
        return_select_x = 320 - 4 - return_select_width
        return_x = return_select_x + select_width
        self.return_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=return_select_width, height=return_select_height, x=return_select_x, y=return_select_y)
        self.group.append( self.return_select )
        #self.return_select.hidden = True
        return_control_width = return_select_width - 2 * select_width
        self.return_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=return_control_width, height=return_height, x=return_x, y=return_y)
        self.group.append( self.return_color )
        return_text_x = return_x + 10
        return_group = displayio.Group(scale=2, x=return_text_x, y=return_text_y)
        return_text = "RETURN"
        self.return_text_area = label.Label(terminalio.FONT, text=return_text, color=self.palette[0])
        return_group.append(self.return_text_area)
        self.group.append(return_group)

        return self.group
    def update_values( self, instrument ):
        #if instrument.active_page_number == 3:
        if instrument.button_pressed:
            instrument.active_page_number = 2
            instrument.button_pressed = False


def make_status_page( instrument ):
    instrument.welcome_page.announce( "make_status_page" )
    page = Status_Page( instrument )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page


class Sensor_List_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.palette = instrument.palette
    def make_group( self ):
        self.group = displayio.Group()
        status_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240, x=0, y=0 )
        self.group.append( status_background )
        text_spacing_y = 28
        status_title_group = displayio.Group(scale=2, x=10, y=18)
        status_title_text = "Sensor List: TBD"
        status_title_text_area = label.Label(terminalio.FONT, text=status_title_text, color=self.palette[0])
        status_title_group.append(status_title_text_area)
        self.group.append(status_title_group)

        text_group = displayio.Group(scale=2, x=10, y=18+text_spacing_y)
        text = "list active sensors"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        text_group = displayio.Group(scale=2, x=10, y=18+2*text_spacing_y)
        text = "list supported inactive"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        if False:
            text_group = displayio.Group(scale=2, x=10, y=18+3*text_spacing_y)
            text = "sd card storage remaining"
            text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
            text_group.append(text_area)
            self.group.append(text_group)

        # RETURN
        select_width = 4
        return_height = 28
        return_select_y = 240 - 4 - 2 - return_height - select_width
        return_select_height = return_height + 2*select_width
        return_y = return_select_y + select_width
        return_text_y = return_y + 12
        return_select_width = 100
        return_select_x = 320 - 4 - return_select_width
        return_x = return_select_x + select_width
        self.return_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=return_select_width, height=return_select_height, x=return_select_x, y=return_select_y)
        self.group.append( self.return_select )
        #self.return_select.hidden = True
        return_control_width = return_select_width - 2 * select_width
        self.return_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=return_control_width, height=return_height, x=return_x, y=return_y)
        self.group.append( self.return_color )
        return_text_x = return_x + 10
        return_group = displayio.Group(scale=2, x=return_text_x, y=return_text_y)
        return_text = "RETURN"
        self.return_text_area = label.Label(terminalio.FONT, text=return_text, color=self.palette[0])
        return_group.append(self.return_text_area)
        self.group.append(return_group)

        return self.group
    def update_values( self, instrument ):
        if instrument.button_pressed:
            instrument.active_page_number = 2
            instrument.button_pressed = False


def make_sensor_list_page( instrument ):
    instrument.welcome_page.announce( "make_sensor_list_page" )
    page = Sensor_List_Page( instrument )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page


class Generic_Sensor_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.palette = instrument.palette
    def make_group( self ):
        self.group = displayio.Group()
        status_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240, x=0, y=0 )
        self.group.append( status_background )
        text_spacing_y = 28
        status_title_group = displayio.Group(scale=2, x=10, y=18)
        status_title_text = "Sensor Data: TBD"
        status_title_text_area = label.Label(terminalio.FONT, text=status_title_text, color=self.palette[0])
        status_title_group.append(status_title_text_area)
        self.group.append(status_title_group)

        text_group = displayio.Group(scale=2, x=10, y=18+text_spacing_y)
        text = "sensor mfr, name, pn"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        text_group = displayio.Group(scale=2, x=10, y=18+2*text_spacing_y)
        text = "live sensor data"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        if False:
            text_group = displayio.Group(scale=2, x=10, y=18+3*text_spacing_y)
            text = "sd card storage remaining"
            text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
            text_group.append(text_area)
            self.group.append(text_group)

        # RETURN
        select_width = 4
        return_height = 28
        return_select_y = 240 - 4 - 2 - return_height - select_width
        return_select_height = return_height + 2*select_width
        return_y = return_select_y + select_width
        return_text_y = return_y + 12
        return_select_width = 100
        return_select_x = 320 - 4 - return_select_width
        return_x = return_select_x + select_width
        self.return_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=return_select_width, height=return_select_height, x=return_select_x, y=return_select_y)
        self.group.append( self.return_select )
        #self.return_select.hidden = True
        return_control_width = return_select_width - 2 * select_width
        self.return_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=return_control_width, height=return_height, x=return_x, y=return_y)
        self.group.append( self.return_color )
        return_text_x = return_x + 10
        return_group = displayio.Group(scale=2, x=return_text_x, y=return_text_y)
        return_text = "RETURN"
        self.return_text_area = label.Label(terminalio.FONT, text=return_text, color=self.palette[0])
        return_group.append(self.return_text_area)
        self.group.append(return_group)

        return self.group
    def update_values( self, instrument ):
        if instrument.button_pressed:
            instrument.active_page_number = 2
            instrument.button_pressed = False


def make_generic_sensor_page( instrument ):
    instrument.welcome_page.announce( "make_generic_sensor_page" )
    page = Generic_Sensor_Page( instrument )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page

class Time_Place_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.palette = instrument.palette
    def make_group( self ):
        self.group = displayio.Group()
        status_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240, x=0, y=0 )
        self.group.append( status_background )
        text_spacing_y = 28
        status_title_group = displayio.Group(scale=2, x=10, y=18)
        status_title_text = "Time / Place: TBD"
        status_title_text_area = label.Label(terminalio.FONT, text=status_title_text, color=self.palette[0])
        status_title_group.append(status_title_text_area)
        self.group.append(status_title_group)

        text_group = displayio.Group(scale=2, x=10, y=18+text_spacing_y)
        text = "clock time, settable"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        text_group = displayio.Group(scale=2, x=10, y=18+2*text_spacing_y)
        text = "gps time if available"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        text_group = displayio.Group(scale=2, x=10, y=18+3*text_spacing_y)
        text = "> sync clock to gps"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        text_group = displayio.Group(scale=2, x=10, y=18+4*text_spacing_y)
        text = "gps position, alt"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        text_group = displayio.Group(scale=2, x=10, y=18+5*text_spacing_y)
        text = "gps satellites visible"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)


        # RETURN
        select_width = 4
        return_height = 28
        return_select_y = 240 - 4 - 2 - return_height - select_width
        return_select_height = return_height + 2*select_width
        return_y = return_select_y + select_width
        return_text_y = return_y + 12
        return_select_width = 100
        return_select_x = 320 - 4 - return_select_width
        return_x = return_select_x + select_width
        self.return_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=return_select_width, height=return_select_height, x=return_select_x, y=return_select_y)
        self.group.append( self.return_select )
        #self.return_select.hidden = True
        return_control_width = return_select_width - 2 * select_width
        self.return_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=return_control_width, height=return_height, x=return_x, y=return_y)
        self.group.append( self.return_color )
        return_text_x = return_x + 10
        return_group = displayio.Group(scale=2, x=return_text_x, y=return_text_y)
        return_text = "RETURN"
        self.return_text_area = label.Label(terminalio.FONT, text=return_text, color=self.palette[0])
        return_group.append(self.return_text_area)
        self.group.append(return_group)

        return self.group
    def update_values( self, instrument ):
        if instrument.button_pressed:
            instrument.active_page_number = 2
            instrument.button_pressed = False


def make_time_place_page( instrument ):
    instrument.welcome_page.announce( "make_time_place_page" )
    page = Time_Place_Page( instrument )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page

class Air_Analyzer_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.palette = instrument.palette
    def make_group( self ):
        self.group = displayio.Group()
        status_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240, x=0, y=0 )
        self.group.append( status_background )
        text_spacing_y = 28
        status_title_group = displayio.Group(scale=2, x=10, y=18)
        status_title_text = "Air Analyzer: TBD"
        status_title_text_area = label.Label(terminalio.FONT, text=status_title_text, color=self.palette[0])
        status_title_group.append(status_title_text_area)
        self.group.append(status_title_group)

        text_group = displayio.Group(scale=2, x=10, y=18+text_spacing_y)
        text = "co2, ch4"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        text_group = displayio.Group(scale=2, x=10, y=18+2*text_spacing_y)
        text = "pressure, temp, humid"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        text_group = displayio.Group(scale=2, x=10, y=18+3*text_spacing_y)
        text = "particulates"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)
        if False:
            text_group = displayio.Group(scale=2, x=10, y=18+4*text_spacing_y)
            text = " "
            text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
            text_group.append(text_area)
            self.group.append(text_group)

            text_group = displayio.Group(scale=2, x=10, y=18+5*text_spacing_y)
            text = " "
            text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
            text_group.append(text_area)
            self.group.append(text_group)


        # RETURN
        select_width = 4
        return_height = 28
        return_select_y = 240 - 4 - 2 - return_height - select_width
        return_select_height = return_height + 2*select_width
        return_y = return_select_y + select_width
        return_text_y = return_y + 12
        return_select_width = 100
        return_select_x = 320 - 4 - return_select_width
        return_x = return_select_x + select_width
        self.return_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=return_select_width, height=return_select_height, x=return_select_x, y=return_select_y)
        self.group.append( self.return_select )
        #self.return_select.hidden = True
        return_control_width = return_select_width - 2 * select_width
        self.return_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=return_control_width, height=return_height, x=return_x, y=return_y)
        self.group.append( self.return_color )
        return_text_x = return_x + 10
        return_group = displayio.Group(scale=2, x=return_text_x, y=return_text_y)
        return_text = "RETURN"
        self.return_text_area = label.Label(terminalio.FONT, text=return_text, color=self.palette[0])
        return_group.append(self.return_text_area)
        self.group.append(return_group)

        return self.group
    def update_values( self, instrument ):
        if instrument.button_pressed:
            instrument.active_page_number = 2
            instrument.button_pressed = False


def make_air_analyzer_page( instrument ):
    instrument.welcome_page.announce( "make_air_analyzer_page" )
    page = Air_Analyzer_Page( instrument )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page


class Remote_Sensing_Missing_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.palette = instrument.palette
    def make_group( self ):
        self.group = displayio.Group()
        status_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240, x=0, y=0 )
        self.group.append( status_background )
        text_spacing_y = 28
        status_title_group = displayio.Group(scale=2, x=10, y=18)
        status_title_text = "Remote Sensing Missing:"
        status_title_text_area = label.Label(terminalio.FONT, text=status_title_text, color=self.palette[0])
        status_title_group.append(status_title_text_area)
        self.group.append(status_title_group)

        text_group = displayio.Group(scale=2, x=10, y=18+text_spacing_y)
        text = "connect either "
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        text_group = displayio.Group(scale=2, x=10, y=18+2*text_spacing_y)
        text = "Remote Sensing plugin"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        text_group = displayio.Group(scale=2, x=10, y=18+3*text_spacing_y)
        text = "or as7265x_Spectrometer"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        text_group = displayio.Group(scale=2, x=10, y=18+4*text_spacing_y)
        text = "to view spectral graph"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)


        # RETURN
        select_width = 4
        return_height = 28
        return_select_y = 240 - 4 - 2 - return_height - select_width
        return_select_height = return_height + 2*select_width
        return_y = return_select_y + select_width
        return_text_y = return_y + 12
        return_select_width = 100
        return_select_x = 320 - 4 - return_select_width
        return_x = return_select_x + select_width
        self.return_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=return_select_width, height=return_select_height, x=return_select_x, y=return_select_y)
        self.group.append( self.return_select )
        #self.return_select.hidden = True
        return_control_width = return_select_width - 2 * select_width
        self.return_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=return_control_width, height=return_height, x=return_x, y=return_y)
        self.group.append( self.return_color )
        return_text_x = return_x + 10
        return_group = displayio.Group(scale=2, x=return_text_x, y=return_text_y)
        return_text = "RETURN"
        self.return_text_area = label.Label(terminalio.FONT, text=return_text, color=self.palette[0])
        return_group.append(self.return_text_area)
        self.group.append(return_group)

        return self.group
    def update_values( self, instrument ):
        if instrument.button_pressed:
            instrument.active_page_number = 2
            instrument.button_pressed = False

def make_remote_sensing_missing_page( instrument ):
    instrument.welcome_page.announce( "make_remote_sensing_missing_page" )
    page = Remote_Sensing_Missing_Page( instrument )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page

class GPS_Page( Page ):
    def __init__( self, palette):
        super().__init__()
        self.palette = palette
    def make_group( self ):
        self.group = displayio.Group()
        gps_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240, x=0, y=0 )
        self.group.append( gps_background )
        gps_group = displayio.Group(scale=2, x=10, y=18)
        gps_text = "GPS status: "
        gps_text_area = label.Label(terminalio.FONT, text=gps_text, color=self.palette[0])
        gps_group.append(gps_text_area)
        self.group.append(gps_group)
        gps_value_group = displayio.Group(scale=2, x=146, y=18)
        gps_value_text = "no fix"
        self.gps_value_text_area = label.Label(terminalio.FONT, text=gps_value_text, color=self.palette[0])
        gps_value_group.append(self.gps_value_text_area)
        self.group.append(gps_value_group)
        # RETURN
        select_width = 4
        return_height = 28
        return_select_y = 240 - 4 - 2 - return_height - select_width
        return_select_height = return_height + 2*select_width
        return_y = return_select_y + select_width
        return_text_y = return_y + 12
        return_select_width = 100
        return_select_x = 320 - 4 - return_select_width
        return_x = return_select_x + select_width
        self.return_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=return_select_width, height=return_select_height, x=return_select_x, y=return_select_y)
        self.group.append( self.return_select )
        #self.return_select.hidden = True
        return_control_width = return_select_width - 2 * select_width
        self.return_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=return_control_width, height=return_height, x=return_x, y=return_y)
        self.group.append( self.return_color )
        return_text_x = return_x + 10
        return_group = displayio.Group(scale=2, x=return_text_x, y=return_text_y)
        return_text = "RETURN"
        self.return_text_area = label.Label(terminalio.FONT, text=return_text, color=self.palette[0])
        return_group.append(self.return_text_area)
        self.group.append(return_group)

        return self.group
    def update_values( self, gps ):
        gps.read()
        if gps.fix():
            self.gps_value_text_area.text = "FIX"
        else:
            self.gps_value_text_area.text = "no fix"

def make_gps_page( main_display_group, palette):
    page = GPS_Page(palette)
    group = page.make_group()
    main_display_group.append( group )
    page.hide()
    return page

class Welcome_Page( Page ):
    def __init__( self ):
        super().__init__()
    def make_group( self ):
        self.group = displayio.Group()
        try:
            bitmap = displayio.OnDiskBitmap("/lib/stella_logo.bmp")
            #print( "Bitmap image file found" )
            # Create a TileGrid to hold the bitmap
            tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
            self.group.append(tile_grid)

            version_group = displayio.Group( scale=2, x=40, y=185 )
            text = "STELLA-1.2 ver {}".format( SOFTWARE_VERSION_NUMBER )
            version_area = label.Label( terminalio.FONT, text=text, color=0x000000 )
            version_group.append( version_area )
            self.group.append( version_group )

            message_group = displayio.Group( scale=2, x=4, y=220 )
            text = ""
            self.message_area = label.Label( terminalio.FONT, text=text, color=0x000000 )
            message_group.append( self.message_area )
            self.group.append( message_group )

            #battery_group = displayio.Group( scale=2, x=90, y=215 )
            #text = "battery {}%".format( battery_level )
            #battery_area = label.Label( terminalio.FONT, text=text, color=0x000000 )
            #battery_group.append( battery_area )
            #welcome_group.append( battery_group )
            #print( "showing welcome screen with logo")
        except (MemoryError, OSError):
            print( "bitmap image file not found or memory not available" )
            border_color = 0xFF0022 # red
            front_color = 0x0000FF # blue
            if (display == False):
                print("No display")
                return
            border = displayio.Palette(1)
            border[0] = border_color
            front = displayio.Palette(1)
            front[0] = front_color
            outer_rectangle = vectorio.Rectangle(pixel_shader=border, width=320, height=240, x=0, y=0)
            self.group.append( outer_rectangle )
            front_rectangle = vectorio.Rectangle(pixel_shader=front, width=280, height=200, x=20, y=20)
            self.group.append( front_rectangle )
            text_group = displayio.Group( scale=4, x=45, y=110 )
            text = "STELLA-1.2"
            text_area = label.Label( terminalio.FONT, text=text, color=0xFFFFFF )
            text_group.append( text_area )
            self.group.append( text_group )

            version_group = displayio.Group( scale=2, x=27, y=200 )
            text = "software version {}".format( SOFTWARE_VERSION_NUMBER )
            version_area = label.Label( terminalio.FONT, text=text, color=0xFFFFFF )
            version_group.append( version_area )
            self.group.append( version_group )

            message_group = displayio.Group( scale=2, x=4, y=220 )
            text = "message here"
            self.message_area = label.Label( terminalio.FONT, text=text, color=0xFFFFFF )
            message_group.append( self.message_area )
            self.group.append( message_group )

        return self.group
    def announce( self, text ):
        self.message_area.text = text
        print( text )
    def update_values( self ):
        pass

def make_welcome_page( instrument ):
    welcome_page = Welcome_Page()
    group = welcome_page.make_group()
    welcome_page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( welcome_page )
    return welcome_page

def hide_all_pages( pages_list ):
    for page in pages_list:
        page.hide()

def make_palette():
    # TBD make a color name dictionary
    palette = displayio.Palette(40)
    palette[0] = 0x000000 # black
    palette[1] = 0xA0522D # brown
    palette[2] = 0xFF0000 # red
    palette[3] = 0xFF8C00 # orange
    palette[4] = 0xFFFF00 # yellow
    palette[5] = 0x00FF00 # green
    palette[6] = 0x0000FF # blue
    palette[7] = 0x9400D3 # violet
    palette[8] = 0x808080 # grey
    palette[9] = 0xFFFFFF # white
    palette[10] = 0xFF99FF # light
    palette[11] = 0xFF751A # heat
    palette[12] = 0x66CCFF # light blue, air analyzer
    palette[13] = 0x6FDC6F # plants
    palette[14] = 0xCE954B # here
    palette[15] = 0x8C8C8C # dark grey
    palette[16] = 0x00998F # burst
    palette[17] = 0x0066FF # border
    palette[18] = 0x009900 # GPS flag
    palette[19] = 0xCCCCCC # light grey
    palette[20] = 0x00CC00 # remote sens green
    palette[21] = 0x00CCBE # sensors
    palette[22] = 0xA6A6A6 # medium grey, return
    palette[23] = 0xFF6666 # medium red, not used yet
    palette[24] = 0x000000 # placeholder
    palette[25] = 0x7E00DB # blueviolet, 410nm
    palette[26] = 0x2300FF # blue, 435nm
    palette[27] = 0x007BFF # royalblue, 460nm
    palette[28] = 0x00EAFF # darkturquoise,485nm
    palette[29] = 0x00FF00 # lime, 510nm
    palette[30] = 0x70FF00 # chartreuse, 535nm
    palette[31] = 0xC3FF00 # greenyellow, 560nm
    palette[32] = 0xFFEF00 # yellow, 585nm
    palette[33] = 0xFF9B00 # orange, 610nm
    palette[34] = 0xFE0000 # red1, 645nm
    palette[35] = 0xDF0000 # red2, 680nm
    palette[36] = 0xC90000 # red3, 705nm
    palette[37] = 0xB10000 # firebrick, 730nm
    palette[38] = 0x940000 # darkred, 760nm

    return palette
##############
# end pages definitions section
##############

##############
# begin sensor definitions section
##############

class Device: #parent class
    def __init__(self, name = None, pn = None, address = None, swob = None ):
        self.name = name
        self.swob = swob
        self.pn = pn
        self.address = address
    def report(self):
        found = False
        if self.swob is not None:
            print("report:", hex(self.address), self.pn, "\t", self.name, "found" )
            found = True
        return found
    def found(self):
        if self.swob is not None:
            return True
        else:
            return False

def initialize_ads1015_12_bit_adc( instrument ):
    ads1015_12_bit_adc = Null_ads1015_12_Bit_ADC()
    try:
        ads1015_12_bit_adc = ads1015_12_Bit_ADC( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_ads1015_12_bit_adc" )
        instrument.sensors_present.append( ads1015_12_bit_adc )
    except Exception as err:
        #print( err )
        pass
    return ads1015_12_bit_adc

class ads1015_12_Bit_ADC( Device ):
    #https://learn.adafruit.com/adafruit-4-channel-adc-breakouts/python-circuitpython
    def __init__( self, com_bus ):
        super().__init__(name = "ads1015_12_bit_adc", pn = "ads1015", address = 0x48, swob = ADS1015.ADS1015( com_bus ))
        self.channel_0 = ADS1x15_AnalogIn(self.swob, ADS1015.P0)
        self.channel_1 = ADS1x15_AnalogIn(self.swob, ADS1015.P1)
        self.channel_2 = ADS1x15_AnalogIn(self.swob, ADS1015.P2)
        self.channel_3 = ADS1x15_AnalogIn(self.swob, ADS1015.P3)
        # set up a differential channel like this self.channel_0-1 = ADS1x15_AnalogIn(swob, ADS1015.P0, ADS1015.P1)
        # self.swob.instrument_mode = self.Mode.SINGLE # this is the default instrument_mode. I don't know where to find Mode. Waits for completed conversion to read the value TBD implement this.
        # Mode.CONTINUOUS # read the latest value that's been converted. TBD look into this and explain
        self.swob.gain = 1
        # gain:
        # setting, full scale voltage
        # 2/3 (how do we enter a fraction?), +/- 6.144V
        # 1, +/- 4.096V
        # 2, +/- 2.048V
        # 4, +/- 1.024V
        # 8, +/- 0.512V
        # 16, +/- 0.256V
    def found(self):
        print("found", self.pn, self.swob)
    def read(self):
        # reports 16 bit values even though the conversion is only 12 bits. Least significant four bits (LSBs) should all be 0
        self.raw = (self.channel_0.value, self.channel_1.value, self.channel_2.value, self.channel_3.value)
        #print( self.raw )
        self.voltage = (self.channel_0.voltage, self.channel_1.voltage, self.channel_2.voltage, self.channel_3.voltage)
        #print( self.voltage )
    def header(self):
        headers = "ads1015_channel_0_voltage-!-V, ads1015_channel_1_voltage-!-V, ads1015_channel_2_voltage-!-V, ads1015_channel_3_voltage-!-V"
        headers += ", ads1015_channel_0_digital_number-!-counts, ads1015_channel_1_digital_number-!-counts, ads1015_channel_2_digital_number-!-counts, ads1015_channel_3_digital_number-!-counts"
        headers += ", ads1015_gain-!-"
        return headers
    def log(self):
        log_values = "{}, {}, {}, {}".format( *self.voltage )
        log_values += ", {}, {}, {}, {}".format( *self.raw)
        log_values += ", {}".format(self.swob.gain)
        return log_values

    def printlog(self):
        print( self.log())

class Null_ads1015_12_Bit_ADC(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

def initialize_ads1115_16_bit_adc( instrument ):
    ads1115_16_bit_adc = Null_ads1115_16_Bit_ADC()
    try:
        ads1115_16_bit_adc = ads1115_16_Bit_ADC( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_ads1115_16_bit_adc" )
        instrument.sensors_present.append( ads1115_16_bit_adc )
    except Exception as err:
        #print( err )
        pass
    return ads1115_16_bit_adc

class ads1115_16_Bit_ADC( Device ):
    # to prevent address collision, connect SDA to ADDR to set the address to 0x4a
    # https://learn.adafruit.com/adafruit-4-channel-adc-breakouts/python-circuitpython
    def __init__( self, com_bus ):
        super().__init__(name = "ads1115_16_bit_adc", pn = "ads1115", address = 0x4a, swob = ADS1115.ADS1115( com_bus, address = 0x4a ))
        self.channel_0 = ADS1x15_AnalogIn(self.swob, ADS1115.P0)
        self.channel_1 = ADS1x15_AnalogIn(self.swob, ADS1115.P1)
        self.channel_2 = ADS1x15_AnalogIn(self.swob, ADS1115.P2)
        self.channel_3 = ADS1x15_AnalogIn(self.swob, ADS1115.P3)
        # set up a differential channel like this self.channel_0-1 = ADS1x15_AnalogIn(swob, ADS1115.P0, ADS1115.P1)
        # self.swob.instrument_mode = self.Mode.SINGLE # this is the default instrument_mode. I don't know where to find Mode. Waits for completed conversion to read the value TBD implement this.
        # Mode.CONTINUOUS # read the latest value that's been converted. TBD look into this and explain
        self.swob.gain = 1
        # gain:
        # setting, full scale voltage
        # 2/3 (how do we enter a fraction?), +/- 6.144V
        # 1, +/- 4.096V
        # 2, +/- 2.048V
        # 4, +/- 1.024V
        # 8, +/- 0.512V
        # 16, +/- 0.256V
    def found(self):
        print("found", self.pn, self.swob)
    def read(self):
        self.raw = (self.channel_0.value, self.channel_1.value, self.channel_2.value, self.channel_3.value)
        #print( self.raw )
        self.voltage = (self.channel_0.voltage, self.channel_1.voltage, self.channel_2.voltage, self.channel_3.voltage)
        #print( self.voltage )
    def header(self):
        headers = "ads1115_channel_0_voltage-!-V, ads1115_channel_1_voltage-!-V, ads1115_channel_2_voltage-!-V, ads1115_channel_3_voltage-!-V"
        headers += ", ads1115_channel_0_digital_number-!-counts, ads1115_channel_1_digital_number-!-counts, ads1115_channel_2_digital_number-!-counts, ads1115_channel_3_digital_number-!-counts"
        headers += ", ads1115_gain-!-"
        return headers
    def log(self):
        log_values = "{}, {}, {}, {}".format( *self.voltage)
        log_values += ", {}, {}, {}, {}".format( *self.raw)
        log_values += ", {}".format(self.swob.gain)
        return log_values
    def printlog(self):
        print( self.log())

class Null_ads1115_16_Bit_ADC(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

def initialize_as7265x_spectrometer( instrument ):
    as7265x_spectrometer = Null_as7265x_Spectrometer()
    try:
        as7265x_spectrometer = as7265x_Spectrometer( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_as7265x_spectrometer" )
        instrument.spectral_sensors_present.append( as7265x_spectrometer )
        as7265x_spectrometer.lamps_on()
        time.sleep(0.1)
        as7265x_spectrometer.lamps_off()
    except Exception as err:
        #print( "as7265x spectrometer failed: {}".format( err ))
        pass
    return as7265x_spectrometer

class as7265x_Spectrometer( Device ):
    # custom library
    # cycle time is a little less than 1 whole second
    def __init__( self, com_bus ):
        super().__init__(name = "as7265x_spectrometer", pn = "as7256x", address = 0x49, swob = AS7265X( com_bus ))
        if self.swob:
            self.swob.disable_indicator()
            self.swob.set_measurement_mode(AS7265X_sparkfun.MEASUREMENT_MODE_6CHAN_CONTINUOUS)
            #MEASUREMENT_MODE_6CHAN_ONE_SHOT
            self.bands = 610, 680, 730, 760, 810, 860, 560, 585, 645, 705, 900, 940, 410, 435, 460, 485, 510, 535
            self.bandwidth = 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20
            self.chip_n = 1,   1,   1,   1,   1,   1,   2,   2,   2,   2,   2,   2,   3,   3,   3,   3,   3,   3
            self.dict_chip_n = {key:value for key, value in zip(self.bands, self.chip_n )}
            self.dict_bandwidths = {key:value for key, value in zip(self.bands, self.bandwidth )}
            self.bands_sorted = sorted( self.bands )
            self.uncertainty_percent = 12
            self.gain_ratio = 16 #default, calibrated at
            self.intg_time_ms = 166 #default, calibrated at
            self.afov_deg = (20.5 * 2) #datasheet reports half angle.
    def check_gain_ratio(self):
        gain_number = self.swob._gain
        if gain_number < 1:
            self.gain_ratio = 1
        elif gain_number == 1:
            self.gain_ratio = 3.7
        elif gain_number == 2:
            self.gain_ratio = 16
        elif gain_number == 3:
            self.gain_ratio = 64
        return self.gain_ratio
    def set_gain_number(self, gain_number):
        if gain_number in range (0,4):
            self.swob.set_gain( gain_number )
        else:
            print( "out of range: set gain number to 0-3 to get gain_ratios of 1, 3.7, 16, 64" )
    def set_integration_cycles( self, cycles ):
        if cycles in range (0, 256):
            self.swob.set_integration_cycles(cycles)
            self.intg_time_ms = int(round((2.8*(cycles+1)),0))
        else:
            print( "out of range: set integration cycles to 0-255 for 0-717ms integration time." )
        return self.intg_time_ms
    def read(self):
        self.chip_temp_c = {1:self.swob.get_temperature(1), 2:self.swob.get_temperature(2), 3:self.swob.get_temperature(3)}
        self.data_counts = self.swob.get_value(0) # 0th position raw counts, bands unsorted order
        # dictionary where key = WL and value = raw counts
        self.dict_counts = {key:value for key, value in zip(self.bands, self.data_counts)}
        self.data_fcal = self.swob.get_value(1) # 1th position factory calibrated irrad value, bands unsorted order
        # dictionary where key = WL and value = factory cal irradiance
        self.dict_fcal = {key:value for key, value in zip(self.bands, self.data_fcal)}
        # OMIT as it's always 12% # self.dict_uncty_fcal = {key:value for key, value in zip(self.bands, (self.data_fcal*self.uncert_percent/100))}
        # TBD self.dict_scal = {key:value for key, value in zip(self.bands, 0)}
        # TBD self.dict_uncty_scal = {key:value for key, value in zip(self.bands, (0))}
        # print( self.data_counts )
    def read_counts(self):
        self.data_counts = self.swob.get_value(0) # 0th position raw counts, bands unsorted order
        self.dict_counts = {key:value for key, value in zip(self.bands, self.data_counts)}
    def read_fcal(self):
        self.data_fcal = self.swob.get_value(1) # 1th position factory calibrated irrad value, bands unsorted order
        self.dict_fcal = {key:value for key, value in zip(self.bands, self.data_fcal)}
        #print( self.data_fcal )
    def read_temperatures(self):
        self.chip_temp_c = {1:self.swob.get_temperature(1), 2:self.swob.get_temperature(2), 3:self.swob.get_temperature(3)}
    def list_channels():
        return self.bands_sorted
    def header( self ):
        return "WL.nm, irrad.uW/(cm^2), irrad.uncty.uW/(cm^2), counts, chip_num, chip_temp_C"
    def get_bandwidth(self, wavelength):
        return self.dict_bandwidths[wavelength]
    def log( self, wavelength):
        if wavelength in self.bands:
            logline = "{}".format( self.pn )
            logline += ", {}".format( wavelength )
            logline += ", {}".format( self.dict_bandwidths[wavelength] )
            logline += ", {}".format( self.dict_counts[wavelength] )
            logline += ", {}".format( self.dict_fcal[wavelength] )
            logline += ", {}".format( self.dict_fcal[wavelength]*self.uncertainty_percent/100 )
            logline += ", {}".format( self.gain_ratio )#gain
            logline += ", {}".format( self.intg_time_ms )#integration time
            logline += ", {}".format( self.dict_chip_n[wavelength] )#chip number
            logline += ", {}".format( self.chip_temp_c[self.dict_chip_n[wavelength]] )#chip temperature
            return logline
    def serial_log(self, wavelength):
        if wavelength in self.bands:
            loglist = "pn: {}".format( self.pn )
            loglist += ", WL-!-nm: {}".format( wavelength )
            loglist += ", BW-!-nm: {}".format( self.dict_bandwidths[wavelength] )
            loglist += ", raw-!-counts: {}".format( self.dict_counts[wavelength] )
            loglist += ", irrad-!-uW_per_cm_sq: {}".format( self.dict_fcal[wavelength] )
            loglist += ", gain-!-: {}".format( self.gain_ratio )
            loglist += ", intg-!-ms: {}".format( self.intg_time_ms )
            return loglist

    def printlog(self,ch):
        print( self.log(ch) )
    def lamps_on(self):
        #print( "turn on the lamps")
        self.swob.enable_bulb(0)   # white
        self.swob.enable_bulb(1)   # NIR
        self.swob.enable_bulb(2)   # UV
    def lamps_off(self):
        #print( "turn off the lamps")
        self.swob.disable_bulb(0)   # white
        self.swob.disable_bulb(1)   # NIR
        self.swob.disable_bulb(2)   # UV

class Null_as7265x_Spectrometer(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.swob = None
        self.bands = None
        self.bands_sorted = [0,0]   # empty list
        self.dict_chip_n = [0,0]
        self.chip_temps = [0,0]
        self.dict_fcal = {0:0}      # empty dictionary
        self.dict_counts = {0:0}
        self.uncert_percent = 10
    def check_gain_ratio(self):
        pass
    def set_gain_number(self, gain_number):
        pass
    def read(self):
        pass
    def read_counts(self):
        pass
    def read_fcal(self):
        pass
    def read_temperatures(self):
        pass
    def log(self, value):
        pass
    def get_bandwidth(self, wavelength):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def blink(self, duration):
        pass
    def header(self):
        pass
    def lamps_on(self):
        pass
    def lamps_off(self):
        pass
    def set_integration_cycles(self):
        pass
    def serial_log(self, wavelength):
        pass

def initialize_as7331_spectrometer( instrument ):
    as7331_spectrometer = Null_as7331_Spectrometer()
    try:
        as7331_spectrometer = as7331_Spectrometer( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_as7331_spectrometer" )
        instrument.spectral_sensors_present.append( as7331_spectrometer )
    except ValueError as err:
        #print( "uv spectrometer failed to initialize: {}".format(err))
        pass
    except Exception as err:
        pass
    return as7331_spectrometer

class as7331_Spectrometer( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "as7331_spectrometer", pn = "as7331", address = 0x74, swob = as7331.AS7331( com_bus ))
        self.bands = 360, 300, 260
        self.bandwidth = 80, 40, 40
        self.chip_n = 1, 1, 1
        self.dict_chip_n = {key:value for key, value in zip(self.bands, self.chip_n )}
        self.dict_bandwidths = {key:value for key, value in zip(self.bands, self.bandwidth )}
        #https://look.ams-osram.com/m/1856fd2c69c35605/original/AS7331-Spectral-UVA-B-C-Sensor.pdf
        self.afov_deg = (10 * 2)
        self.fcal_unct_percent = 0 # no reported value
        self.gain_ratio = 0 #TBD what are the defaults?
        self.intg_time_ms = 0 #TBD what are the defaults?
    def check_gain_ratio(self):
        gain_callout = self.swob.gain
        if gain_callout == 11:
            self.gain_ratio = 1
        elif gain_callout == 10:
            self.gain_ratio = 2
        elif gain_callout == 9:
            self.gain_ratio = 4
        elif gain_callout == 8:
            self.gain_ratio = 8
        elif gain_callout == 7:
            self.gain_ratio = 16
        elif gain_callout == 6:
            self.gain_ratio = 32
        elif gain_callout == 5:
            self.gain_ratio = 64
        elif gain_callout == 4:
            self.gain_ratio = 128
        elif gain_callout == 3:
            self.gain_ratio = 256
        elif gain_callout == 2:
            self.gain_ratio = 512
        elif gain_callout == 1:
            self.gain_ratio = 1024
        elif gain_callout == 0:
            self.gain_ratio = 2048
        return self.gain_ratio

    def set_gain_number(self, gain_number):
        if gain_number in range (0,12):
            if gain_number == 11:
                gain_constant = as7331.GAIN_2048X
            if gain_number == 10:
                gain_constant = as7331.GAIN_1024X
            if gain_number == 9:
                gain_constant = as7331.GAIN_512X
            if gain_number == 8:
                gain_constant = as7331.GAIN_256X
            if gain_number == 7:
                gain_constant = as7331.GAIN_128X
            if gain_number == 6:
                gain_constant = as7331.GAIN_64X
            if gain_number == 5:
                gain_constant = as7331.GAIN_32X
            if gain_number == 4:
                gain_constant = as7331.GAIN_16X
            if gain_number == 3:
                gain_constant = as7331.GAIN_8X
            if gain_number == 2:
                gain_constant = as7331.GAIN_4X
            if gain_number == 1:
                gain_constant = as7331.GAIN_2X
            if gain_number == 0:
                gain_constant = as7331.GAIN_1X
            self.swob.gain = gain_constant
        else:
            print( "out of range: set gain number to 0-11 to get gain_ratios from 1 to 2048" )

    def set_integration_time( self, intg_number ):
        if intg_number == 0:
            self.integration_time = as7331.INTEGRATION_TIME_1MS
            self.intg_time_ms = 1
        if intg_number == 1:
            self.integration_time = as7331.INTEGRATION_TIME_2MS
            self.intg_time_ms = 2
        if intg_number == 2:
            self.integration_time = as7331.INTEGRATION_TIME_4MS
            self.intg_time_ms = 4
        if intg_number == 3:
            self.integration_time = as7331.INTEGRATION_TIME_8MS
            self.intg_time_ms = 8
        if intg_number == 4:
            self.integration_time = as7331.INTEGRATION_TIME_16MS
            self.intg_time_ms = 16
        if intg_number == 5:
            self.integration_time = as7331.INTEGRATION_TIME_32MS
            self.intg_time_ms = 32
        if intg_number == 6:
            self.integration_time = as7331.INTEGRATION_TIME_64MS
            self.intg_time_ms = 64
        if intg_number == 7:
            self.integration_time = as7331.INTEGRATION_TIME_128MS
            self.intg_time_ms = 128
        if intg_number == 8:
            self.integration_time = as7331.INTEGRATION_TIME_256MS
            self.intg_time_ms = 256
        if intg_number == 9:
            self.integration_time = as7331.INTEGRATION_TIME_512MS
            self.intg_time_ms = 512
        if intg_number == 10:
            self.integration_time = as7331.INTEGRATION_TIME_1024MS
            self.intg_time_ms = 1024
        if intg_number == 11:
            self.integration_time = as7331.INTEGRATION_TIME_2048MS
            self.intg_time_ms = 2048
        if intg_number == 12:
            self.integration_time = as7331.INTEGRATION_TIME_4096MS
            self.intg_time_ms = 4096
        if intg_number == 13:
            self.integration_time = as7331.INTEGRATION_TIME_8192MS
            self.intg_time_ms = 8192
        if intg_number == 14:
            self.integration_time = as7331.INTEGRATION_TIME_16384MS
            self.intg_time_ms = 16384
        return self.intg_time_ms
    def lamps_on(self):
        pass
    def lamps_off(self):
        pass
    def read(self):
        self.UVA_counts, self.UVB_counts, self.UVC_counts, self.chip_temp_c_counts = self.swob.raw_values
        self.dict_counts = {360:self.UVA_counts, 300:self.UVB_counts, 260:self.UVC_counts}
        self.UVA, self.UVB, self.UVC, self.chip_temp_c = self.swob.values
        self.dict_fcal = {360:self.UVA, 300:self.UVB, 260:self.UVC}
    def read_counts(self):
        self.UVA_counts, self.UVB_counts, self.UVC_counts, self.chip_temp_c_counts = self.swob.raw_values
        self.dict_counts = {360:self.UVA_counts, 300:self.UVB_counts, 260:self.UVC_counts}
    def read_fcal(self):
        self.UVA, self.UVB, self.UVC, self.chip_temp_c = self.swob.values
        self.dict_fcal = {360:self.UVA, 300:self.UVB, 260:self.UVC}
    def read_temperatures(self):
        pass
    def header(self):
        return "sensorPN, Wl.nm, raw_counts, irrad.stella.cal, irrad.stella.uncty, irrad_factory.cal, irrad_factory.uncty, gain, integration_time_ms, chip_temp_C"
        #return "UVC.WL.nm, UVC_uncal, UVB.WL.nm, UVB_uncal, UVA.WL.nm, UVA_uncal, UVS.temp.C"
    def log( self, wavelength):
        if wavelength in self.bands:
            logline = "{}".format( self.pn )
            logline += ", {}".format( wavelength )
            logline += ", {}".format( self.dict_bandwidths[wavelength] )
            logline += ", {}".format( self.dict_counts[wavelength] )
            logline += ", {}".format( self.dict_fcal[wavelength] )
            logline += ", {}".format( " - " )
            logline += ", {}".format( self.gain_ratio )#gain
            logline += ", {}".format( self.intg_time_ms )#integration time
            logline += ", {}".format( self.dict_chip_n[wavelength] )#chip number
            logline += ", {}".format( " - " )#self.chip_temp_c[self.dict_chip_n[wavelength]] )#chip temperature
            return logline
    def serial_log(self, wavelength):
        if wavelength in self.bands:
            loglist = "pn: {}".format( self.pn )
            loglist += ", WL-!-nm: {}".format( wavelength )
            loglist += ", BW-!-nm: {}".format( self.dict_bandwidths[wavelength] )
            loglist += ", raw-!-counts: {}".format( self.dict_counts[wavelength] )
            loglist += ", irrad-!-uW_per_cm_sq: {}".format( self.dict_fcal[wavelength] )
            loglist += ", gain-!-: {}".format( self.gain_ratio )
            loglist += ", intg-!-ms: {}".format( self.intg_time_ms )
            return loglist
    def get_bandwidth(self, wavelength):
        return self.dict_bandwidths[wavelength]
    def printlog(self):
        print( self.log())

class Null_as7331_Spectrometer(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def read_counts(self):
        pass
    def read_fcal(self):
        pass
    def read_temperatures(self):
        pass
    def lamps_on(self):
        pass
    def lamps_off(self):
        pass
    def log(self, value):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def get_bandwidth(self, wavelength):
        pass
    def header(self):
        pass
    def check_gain_ratio(self):
        pass
    def serial_log(self, wavelength):
        pass

def initialize_as7341_spectrometer( instrument ):
    as7341_spectrometer = Null_as7341_Spectrometer()
    try:
        as7341_spectrometer = as7341_Spectrometer( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_as7341_spectrometer" )
        instrument.spectral_sensors_present.append( as7341_spectrometer )
    except:
        pass
    return as7341_spectrometer

class as7341_Spectrometer( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "as7341_spectrometer", pn = "as7341", address = 0x39, swob = AS7341( com_bus ))
        self.bands = 415, 445, 480, 515, 555, 590, 630, 682
        self.bandwidth = 26, 30, 36, 39, 39, 40, 50, 52
        self.chip_n = 1, 1, 1, 1, 1, 1, 1, 1
        self.dict_chip_n = {key:value for key, value in zip(self.bands, self.chip_n )}
        self.dict_bandwidths = {key:value for key, value in zip(self.bands, self.bandwidth )}
        self.colors = ["violet", "indigo", "blue", "cyan", "green", "yellow", "orange", "red"]
        #self.tsis_cal_counts_per_irradiance = 1405.9, 2079.6, 2631.6, 3556.8, 4246.0, 5060.6, 6888.9, 9130.9
        # first principles calibration by Sten Odenwald of NASA Heliophysics
        self.steno_cal_counts_per_irradiance = 4398.0, 6104.0, 7583.0, 9972.0, 11536.0, 13374.0, 17115.0, 20916.0
        self.calibration_error = 0.6
        self.irradiance = [0,0,0,0,0,0,0,0]
        self.dict_stenocal = {}
        self.swob.led_current = 50
    def check_gain_ratio(self):
        pass
    def lamps_on(self):
        self.swob.led = True
    def lamps_off(self):
        self.swob.led = False
    def blink( self, duration ):
        self.swob.led_current = 50
        self.swob.led = True
        time.sleep( duration )
        self.swob.led = False
    def read(self):
        self.raw = self.swob.all_channels
        self.dict_counts = {key:value for key, value in zip(self.bands, self.raw )}
        for ch in range (0,8):
            self.irradiance[ch] = self.raw[ch]/self.steno_cal_counts_per_irradiance[ch]
        self.dict_stenocal = {key:value for key, value in zip(self.bands, self.irradiance )}
    def list_channels():
        return self.center_wavelengths
    def header(self, ch):
        return " {}.WL.nm, {}.counts, {}.W/(m^2*nm), {}.uncty.W/(m^2*nm)".format( self.colors[ch], self.colors[ch], self.colors[ch], self.colors[ch] )
    def log( self, wavelength):
        if wavelength in self.bands:
            logline = "{}".format( self.pn )
            logline += ", {}".format( wavelength )
            logline += ", {}".format( self.dict_bandwidths[wavelength] )
            logline += ", {}".format( self.dict_counts[wavelength] )
            logline += ", {}".format( self.dict_stenocal[wavelength] )
            logline += ", {}".format( " - " )
            logline += ", {}".format( " - " )#gain
            logline += ", {}".format( " - " )#integration time
            logline += ", {}".format( " - " )#chip number
            logline += ", {}".format( " - " )#chip temperature
            return logline
    def serial_log(self, wavelength):
        if wavelength in self.bands:
            loglist = "pn: {}".format( self.pn )
            loglist += ", WL-!-nm: {}".format( wavelength )
            loglist += ", BW-!-nm: {}".format( self.dict_bandwidths[wavelength] )
            loglist += ", raw-!-counts: {}".format( self.dict_counts[wavelength] )
            loglist += ", irrad-!-uW_per_cm_sq: {}".format( self.dict_stenocal[wavelength] )
            loglist += ", gain-!-: {}".format( '-' ) #self.gain_ratio )
            loglist += ", intg-!-ms: {}".format( '-' )#self.intg_time_ms )
            return loglist
    def get_bandwidth(self, wavelength):
        return self.dict_bandwidths[wavelength]
    def printlog(self,ch):
        print( self.log(ch))

class Null_as7341_Spectrometer(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def log(self, value):
        pass
    def serial_log(self, wavelength):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def lamps_on(self):
        pass
    def lamps_off(self):
        pass
    def blink(self, duration):
        pass
    def get_bandwidth(self, wavelength):
        pass
    def header(self):
        pass
    def check_gain_ratio(self):
        pass

def initialize_bme280_air_sensor( instrument ):
    bme280_air_sensor = Null_bme280_Air_Sensor()
    try:
        bme280_air_sensor = bme280_Air_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_bme280_air_sensor" )
        instrument.sensors_present.append( bme280_air_sensor )
    except Exception as err:
        pass
        #print("bme280 failed: {}".format(err))
    return bme280_air_sensor

class bme280_Air_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "bme280_air_sensor", pn = "bme280", address = 0x77, swob = adafruit_bme280.Adafruit_BME280_I2C( com_bus ))
        self.temperature_C = None
        self.pressure = None
        self.altitude = None
        self.humidity = None
    def read(self):
        self.temperature_C = self.swob.temperature
        self.pressure = self.swob.pressure
        self.humidity = self.swob.relative_humidity
        self.altitude = self.swob.altitude
        #print( self.altitude )
        # TBD calculate dewpoint, but do that in an auxilliary function, because I'll have many sources of T and RH
        # TD: =243.04*(LN(RH/100)+((17.625*T)/(243.04+T)))/(17.625-LN(RH/100)-((17.625*T)/(243.04+T)))
        # from https://bmcnoldy.earth.miami.edu/Humidity.html
        #self.dewpoint = 0 #self.temperature -((100-self.humidity)/5) #update this to the formula above.
        #self.dp_uncty = 3.2
    def log(self):
        # name, units, value, +/-, uncertainty ## per datasheet
        return "{}, {}, {}, {}".format( self.pressure, round(self.altitude, 3), round(self.humidity, 1), round(self.temperature_C, 3) )
    def printlog(self):
        print( self.log())
    def header(self):
        return( "bme280_barometric_pressure-!-hPa, bme280_altitude_relative-!-m, bme280_humidity_relative-!-percent, bme280_temperature_ambient-!-C" )

class Null_bme280_Air_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.swob = None
        self.temperature_C = None
        self.pressure = None
        self.altitude = None
        self.humidity = None
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

def initialize_capacitive_soil_moisture_sensor( instrument ):
    capacitive_soil_moisture_sensor = Null_Capacitive_Soil_Moisture_Sensor()
    try:
        capacitive_soil_moisture_sensor = Capacitive_Soil_Moisture_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_capacitive_soil_moisture_sensor" )
        instrument.sensors_present.append( capacitive_soil_moisture_sensor )
    except:
        pass
    return capacitive_soil_moisture_sensor

class Capacitive_Soil_Moisture_Sensor( Device ):
    # https://learn.adafruit.com/adafruit-stemma-soil-sensor-i2c-capacitive-moisture-sensor/python-circuitpython-test
    def __init__( self, com_bus ):
        super().__init__(name = "capacitive_soil_moisture_sensor", pn = "cap_sm", address = 0x37, swob = Seesaw(com_bus, addr=0x37))
    def read(self):
        self.soil_capacitance = self.swob.moisture_read()
        #print( self.soil_capacitance )
    def header(self):
        return "capacitive_soil_moisture_signal-!-"
    def log(self):
        return "{}".format( self.soil_capacitance )
    def printlog(self):
        print( self.log())

class Null_Capacitive_Soil_Moisture_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

##TBD add conductive soil moisture sensor

def initialize_ds2484_1_wire_thermometer( instrument ):
    ds2484_1_wire_thermometer = Null_ds2484_1_Wire_Thermometer_Reader()
    try:
        ds2484_1_wire_thermometer = ds2484_1_Wire_Thermometer_Reader( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_ds2484_1_wire_thermometer" )
        instrument.sensors_present.append( ds2484_1_wire_thermometer )
    except:
        pass
    return ds2484_1_wire_thermometer

class ds2484_1_Wire_Thermometer_Reader( Device ):
    #https://learn.adafruit.com/adafruit-ds2484-i2c-to-1-wire-bus-adapter-breakout/circuitpython-and-python
    def __init__( self, com_bus ):
        super().__init__(name = "ds2484_1_wire_thermometer", pn = "ds2484", address = 0x18, swob = Adafruit_DS248x( com_bus ))
        self.rom = bytearray(8)
        if not self.swob.onewire_search(self.rom):
            pass
            #print( "no 1-wire thermometers found" )
    def read(self):
        self.temperature_C = self.swob.ds18b20_temperature(self.rom)
        #print( self.temperature_C )
    def header(self):
        return "ds2484_temperature_material-!-C"
    def log(self):
        return "{}".format( round(self.temperature_C,1))
    def printlog(self):
        print( self.log())

class Null_ds2484_1_Wire_Thermometer_Reader(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

def initialize_gps( instrument ):
    gps = Null_GPS()
    try:
        gps = pa1616d_GPS( instrument.uart_bus )
        instrument.welcome_page.announce( "initialize_gps" )
        instrument.sensors_present.append( gps )
        time.sleep(0.1)
        gps.request_firmware_report()
        gps.send_start_commands()
    except Exception as err:
        print("gps failed init: {}".format(err))
        pass
    return gps

class pa1616d_GPS( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "gps", pn = "pa1616d", address = 0x00, swob = adafruit_gps.GPS( com_bus, debug=False))
        self.last_read = 0
    def send_start_commands(self):
        self.swob.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0") #set data output configuration
        self.swob.send_command(b"PMTK220,1000") #set update interval to 1000 ms

    def request_firmware_report( self ):
        self.swob.send_command(b"PMTK605")  # request firmware version
        data = self.swob.read(32)  # read up to 32 bytes
            # print(data)  # this is a bytearray type
        if data is not None:
            # convert bytearray to string
            data_string = "".join([chr(b) for b in data])
            print( "gps firmware report = ", end='')
            report = data_string[:4]
            print( report )
        else:
            report = ["False"]
            print( "no data on firmware" )
        if report[0] == '$':
            print("good gps firmware report")
        else:
            print("gps status not determined")
        return report
    # TBD can we get warm start battery health information?
    def fix(self):
        return self.swob.has_fix
    def read(self):
        self.swob.update()
        self.latitude = self.swob.latitude
        self.longitude = self.swob.longitude
        self.altitude = self.swob.altitude_m
        self.timestruct = self.swob.timestamp_utc
    def header(self):
        return( "gps_fix-!-boolean, gps_latitude-!-degrees, gps_longitude-!-degrees, gps_altitude-!-m, gps_timestamp-!-iso8601utc" )
    def log(self):
        if self.timestruct is not None:
            self.gps_timestamp = "{}{:02}{:02}T{:02}{:02}{:02}Z".format(
                        self.timestruct.tm_year,# Note you might not get all data like year month day
                        self.timestruct.tm_mon,
                        self.timestruct.tm_mday,
                        self.timestruct.tm_hour,
                        self.timestruct.tm_min,
                        self.timestruct.tm_sec
                        )
        else: self.gps_timestamp = None #"20000101T000000Z"
        return "{}, {}, {}, {}, {}".format( self.swob.has_fix, self.latitude, self.longitude, self.altitude, self.gps_timestamp )
    def printlog(self):
        print( self.log())

class Null_GPS(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def log(self):
        pass
    def fix(self):
        return False
    def report(self):
        pass
    def send_start_commands(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

def initialize_hdc3022_air_sensor( instrument ):
    hdc3022_air_sensor = Null_hdc3022_Air_Sensor()
    try:
        hdc3022_air_sensor = hdc3022_Air_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_hdc3022_air_sensor" )
        instrument.sensors_present.append( hdc3022_air_sensor )
    except Exception as err:
        pass
        #print("hdc3022 failed: {}".format(err))
    return hdc3022_air_sensor

class hdc3022_Air_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "hdc3022_air_sensor", pn = "hdc3022", address = 0x44, swob = adafruit_hdc302x.HDC302x( com_bus ))
        self.temperature_C = 0
        self.humidity_percent = 0
    def read(self):
        self.temperature_C = self.swob.temperature
        self.humidity_percent = self.swob.relative_humidity
        #print( self.temperature_C )
    def log(self):
        # name, units, value, +/-, uncertainty ## per datasheet
        return "{}, {}".format( round(self.temperature_C, 2), round(self.humidity_percent, 1) )
    def printlog(self):
        print( self.log())
    def header(self):
        return( "hdc3022_temperature_ambient-!-C, hdc3022_humidity_relative-!-percent" )

class Null_hdc3022_Air_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.temperature_C = 0
        self.humidity_percent = 0
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

def initialize_lv_ez_mb1013_rangefinder( instrument, analog_in_0, sense_5V ):
    lv_ez_mb1013_rangefinder = Null_Lv_ez_mb1013_Rangefinder()
    try:
        lv_ez_mb1013_rangefinder = Lv_ez_mb1013_Rangefinder( analog_in_0, sense_5V )
        instrument.sensors_present.append( lv_ez_mb1013_rangefinder )
    except Exception as err:
        pass
        #print( "error:", err )
    return lv_ez_mb1013_rangefinder

class Lv_ez_mb1013_Rangefinder( Device ):
    def __init__( self, analog_in_0, sense_5V):
        super().__init__(name = "lv_ez_mb1013_rangefinder", pn = "lv_ez_mb1013", address = 0x00, swob = True)
        self.range_m = None
        self.analog_in_0 = analog_in_0
        self.sense_5V = sense_5V
    def read(self):
        supply_v = 2 * (self.sense_5V.value * 3.3) / 65536
        range_m =self.analog_in_0.value * 8.312 / 100000 - 0.05 # offset
        self.range_m = round(range_m, 3)
    def log(self):
        return "{}, {}".format( self.analog_in_0.value, self.range_m )
    def header(self):
        return "analog_input_0_digital_number-!-counts, hrlv-ez-mb1013_range-!-m"

class Null_Lv_ez_mb1013_Rangefinder(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.range_m = None
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

def initialize_lis2mdl_magnetic_field_sensor( instrument ):
    lis2mdl_magnetic_field_sensor = Null_lis2mdl_Magnetic_Field_Sensor()
    try:
        lis2mdl_magnetic_field_sensor = lis2mdl_Magnetic_Field_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_lis2mdl_magnetic_field_sensor" )
        instrument.sensors_present.append( lis2mdl_magnetic_field_sensor )
    except NameError as err:
        pass
        #print( "library missing:", err )
    except Exception:
        pass
    return lis2mdl_magnetic_field_sensor

class lis2mdl_Magnetic_Field_Sensor( Device ):
    #https://www.st.com/en/mems-and-sensors/lis2mdl.html#documentation
    def __init__( self, com_bus ):
        super().__init__(name = "lis2mdl_magnetic_field_sensor", pn = "lis2mdl", address = 0x1E, swob = adafruit_lis2mdl.LIS2MDL(com_bus ))
        self.Bx_uT = None
        self.By_uT = None
        self.Bz_uT = None
        self.B_uncertainty_uT = 0.3 #TBD how close is this uncertainty to actual performance
    def read(self):
        self.Bx_uT, self.By_uT, self.Bz_uT = self.swob.magnetic
        #print( self.Bx_uT, self.By_uT, self.Bz_uT )
    def log(self):
        return "{}, {}, {}".format(
            round(self.Bx_uT, 3),
            round(self.By_uT, 3),
            round(self.Bz_uT, 3))
    def printlog(self):
        print( self.log())
    def header(self):
        return( "lis2mdl_magnetic_field_x-!-uT, lis2mdl_magnetic_field_y-!-uT, lis2mdl_magnetic_field_z-!-uT" )

class Null_lis2mdl_Magnetic_Field_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.Bx = None
        self.By = None
        self.Bz = None
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

def initialize_lis3mdl_magnetic_field_sensor( instrument ):
    lis3mdl_magnetic_field_sensor = Null_lis3mdl_Magnetic_Field_Sensor()
    try:
        lis3mdl_magnetic_field_sensor = lis3mdl_Magnetic_Field_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_lis3mdl_magnetic_field_sensor" )
        instrument.sensors_present.append( lis3mdl_magnetic_field_sensor )
    except NameError as err:
        pass
        #print( "library missing:", err )
    except Exception:
        #print( "Exception:", err )
        pass
    return lis3mdl_magnetic_field_sensor

class lis3mdl_Magnetic_Field_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "lis3mdl_magnetic_field_sensor", pn = "lis3mdl", address = 0x6a, swob = LIS3MDL(com_bus ))
        self.Bx_uT = None
        self.By_uT = None
        self.Bz_uT = None
        self.B_uncertainty_uT = 0.3 #TBD how close is this uncertainty to actual performance
    def read(self):
        self.Bx_uT, self.By_uT, self.Bz_uT = self.swob.magnetic
        #print( self.Bx_uT, self.By_uT, self.Bz_uT )
    def log(self):
        return "{}, {}, {}".format(
            round(self.Bx_uT, 3),
            round(self.By_uT, 3),
            round(self.Bz_uT, 3))
    def printlog(self):
        print( self.log())
    def header(self):
        return( "lis3mdl_magnetic_field_x-!-uT, lis3mdl_magnetic_field_y-!-uT, lis3mdl_magnetic_field_z-!-uT" )

class Null_lis3mdl_Magnetic_Field_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.Bx = None
        self.By = None
        self.Bz = None
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass


def initialize_lsm303_acceleration_sensor( instrument ):
    lsm303_acceleration_sensor = Null_lsm303_Acceleration_Sensor()
    try:
        lsm303_acceleration_sensor = lsm303_Acceleration_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_lsm303_acceleration_sensor" )
        instrument.sensors_present.append( lsm303_acceleration_sensor )
    except NameError as err:
        pass
        #print( "library missing:", err )
    except Exception:
        pass
    return lsm303_acceleration_sensor

class lsm303_Acceleration_Sensor( Device ):
    #https://www.st.com/resource/en/datasheet/lsm303agr.pdf
    def __init__( self, com_bus ):
        super().__init__(name = "lsm303_acceleration_sensor", pn = "lms303", address = 0x19, swob = adafruit_lsm303_accel.LSM303_Accel( com_bus ))
        self.Ax_m_per_s2 = None
        self.Ay_m_per_s2 = None
        self.Az_m_per_s2 = None
        self.A_uncertainty_m_per_s2= 0.4
    def read(self):
        self.Ax_m_per_s2, self.Ay_m_per_s2, self.Az_m_per_s2 = self.swob.acceleration
        #print( self.Ax_m_per_s2, self.Ay_m_per_s2, self.Az_m_per_s2 )
    def log(self):
        return "{}, {}, {}".format(
            round(self.Ax_m_per_s2, 3),
            round(self.Ay_m_per_s2, 3),
            round(self.Az_m_per_s2, 3))
    def printlog(self):
        print( self.log())
    def header(self):
        return( "lsm303_acceleration_x-!-m_per_s_sq, lsm303_acceleration_y-!-m_per_s_sq, lsm303_acceleration_z-!-m_per_s_sq" )

class Null_lsm303_Acceleration_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.Ax_m_per_s2 = None
        self.Ay_m_per_s2 = None
        self.Az_m_per_s2 = None
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

def initialize_lsm6ds_accel_gyro_sensor( instrument ):
    lsm6ds_accel_gyro_sensor = Null_lsm6ds_Accel_Gyro_Sensor()
    try:
        lsm6ds_accel_gyro_sensor = lsm6ds_Accel_Gyro_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_lsm6ds_accel_gyro_sensor" )
        instrument.sensors_present.append( lsm6ds_accel_gyro_sensor )
    except NameError as err:
        pass
        #print( "library missing:", err )
    except Exception:
        pass
    return lsm6ds_accel_gyro_sensor

class lsm6ds_Accel_Gyro_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "lsm6ds_accel_gyro_sensor", pn = "lms6ds", address = 0x1c, swob = LSM6DS( com_bus ))
        self.Ax_m_per_s2 = 0
        self.Ay_m_per_s2 = 0
        self.Az_m_per_s2 = 0
        self.wx_deg_per_s = 0
        self.wy_deg_per_s = 0
        self.wz_deg_per_s = 0
        self.A_uncertainty_m_per_s2= 0.4
    def read(self):
        self.Ax_m_per_s2, self.Ay_m_per_s2, self.Az_m_per_s2 = self.swob.acceleration
        self.wx_deg_per_s, self.wy_deg_per_s, self.wz_deg_per_s = self.swob.gyro
        #print( self.wx_rad_per_s, self.wy_rad_per_s, self.wz_rad_per_s  )
    def log(self):
        return "{}, {}, {}, {}, {}, {}".format(
            round(self.Ax_m_per_s2, 3),
            round(self.Ay_m_per_s2, 3),
            round(self.Az_m_per_s2, 3),
            round(self.wx_deg_per_s, 3),
            round(self.wy_deg_per_s, 3),
            round(self.wz_deg_per_s, 3)
            )
    def printlog(self):
        print( self.log())
    def header(self):
        headers = "lsm6ds_acceleration_x-!-m_per_s_sq, lsm6ds_acceleration_y-!-m_per_s_sq, lsm6ds_acceleration_z-!-m_per_s_sq"
        headers += "lsm6ds_rotation_x-!-degrees_per_s, lsm6ds_rotation_x-!-degrees_per_s, lsm6ds_rotation_x-!-degrees_per_s"
        return headers

class Null_lsm6ds_Accel_Gyro_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.Ax_m_per_s2 = None
        self.Ay_m_per_s2 = None
        self.Az_m_per_s2 = None
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

def initialize_ltr390_uva_sensor( instrument ):
    ltr390_uva_sensor = Null_ltr390_UVA_Sensor()
    try:
        ltr390_uva_sensor = ltr390_UVA_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_ltr390_uva_sensor" )
        instrument.sensors_present.append( ltr390_uva_sensor )
    except:
        pass
    return ltr390_uva_sensor

class ltr390_UVA_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "ltr390_uva_sensor", pn = "ltr390", address = 0x53, swob = adafruit_ltr390.LTR390( com_bus ))
    def read(self):
        self.UVA = self.swob.uvs
        self.uv_index = self.swob.uvi
        self.light_raw = self.swob.light
        self.lux = self.swob.lux
        #print( self.lux )
    def header(self):
        return "ltr390_illumination-!-counts, ltr390_illumination-!-lux, ltr390_uva-!-counts, ltr390_uv_index-!-"
    def log(self):
        return "{}, {}, {}, {}".format( self.light_raw, self.lux, self.UVA, self.uv_index )
    def printlog(self):
        print( self.log())

class Null_ltr390_UVA_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

def initialize_battery_monitor( instrument ):
    battery_monitor = Null_Battery_Monitor()
    try:
        battery_monitor = max1704x_Battery_Monitor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_battery_monitor" )
        instrument.sensors_present.append( battery_monitor )
    except:
        pass
    return battery_monitor

class max1704x_Battery_Monitor( Device ): #child class ( parent class ):
    def __init__( self, com_bus ):
        super().__init__(name = "battery_monitor", pn = "max1704x", address = 0x36, swob = adafruit_max1704x.MAX17048( com_bus ))
        self.voltage = self.swob.cell_voltage
        self.percentage = round(self.swob.cell_percent, 1)
    def read(self):
        self.voltage = self.swob.cell_voltage
        self.percentage = round(self.swob.cell_percent, 1)
        #print( self.percentage )
    def header(self):
        return "max1704x_battery_voltage-!-V, max1704x_battery_energy-!-percent"
    def log(self):
        return "{}, {}".format( self.voltage, self.percentage )
    def printlog(self):
        print( self.log())

class Null_Battery_Monitor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        self.voltage = 0
        self.percentage = 0
    def log(self):
        return "{}, {}".format( self.voltage, self.percentage )
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

def initialize_mcp9808_air_thermometer( instrument ):
    mcp9808_air_thermometer = Null_mcp9808_Air_Thermometer()
    try:
        mcp9808_air_thermometer = mcp9808_Air_Thermometer( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_mcp9808_air_thermometer" )
        instrument.sensors_present.append( mcp9808_air_thermometer )
    except Exception as err:
        #print( "MCP9808 fail: {}".format(err))
        pass
    return mcp9808_air_thermometer

class mcp9808_Air_Thermometer( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "mcp9808_air_thermometer", pn = "mcp9808", address = 0x1f, swob = adafruit_mcp9808.MCP9808( com_bus, address = 0x1f ))
        self.temperature_C = None
    def read(self):
        self.temperature_C = self.swob.temperature
        #print( self.temperature_C )
    def header(self):
        return "mcp9808_temperature_ambient-!-C"
    def log(self):
        return "{}".format( round(self.temperature_C, 1 ))
    def printlog(self):
        print( self.log())

class Null_mcp9808_Air_Thermometer(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.temperature_C = None
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

def initialize_mlx90614_surface_thermometer( instrument ):
    mlx90614_surface_thermometer = Null_mlx90614_Surface_Thermometer()
    try:
        mlx90614_surface_thermometer = mlx90614_Surface_Thermometer( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_mlx90614_surface_thermometer" )
        instrument.sensors_present.append( mlx90614_surface_thermometer )
    except:
        pass
    return mlx90614_surface_thermometer

class mlx90614_Surface_Thermometer( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "mlx90614_surface_thermometer", pn = "mlx90614", address = 0x5A, swob = adafruit_mlx90614.MLX90614( com_bus ))
        self.surface_temperature_C = 0
        self.ambient_temperature_C = 0
    def read(self):
        self.surface_temperature_C = self.swob.object_temperature
        self.ambient_temperature_C = self.swob.ambient_temperature
    def header(self):
        return "mlx90614_temperature_surface-!-C, mlx90614_temperature_local-!-C"
    def log(self):
        return "{}, {}".format( round(self.surface_temperature_C,1), round(self.ambient_temperature_C,1) )
    def printlog(self):
        print( self.log())

class Null_mlx90614_Surface_Thermometer(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.surface_temperature_C = 0
        self.ambient_temperature_C = 0
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass


def initialize_mlx90640_thermal_camera( instrument ):
    mlx90640_thermal_camera = Null_mlx90640_Thermal_Camera()
    try:
        mlx90640_thermal_camera = mlx90640_Thermal_Camera( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_mlx90640_thermal_camera" )
        instrument.sensors_present.append( mlx90640_thermal_camera )
    except:
        pass
    return mlx90640_thermal_camera

class mlx90640_Thermal_Camera( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "mlx90640_thermal_camera", pn = "mlx90640", address = 0x33, swob = adafruit_mlx90640.MLX90640( com_bus ))
        # TBD self.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
        # TBD self.refresh_rate = self.swob.RefreshRate.REFRESH_4_HZ
    def read(self):
        pass
        #self.t_surface_C = self.swob.object_temperature
    def header(self):
        return ""
    def log(self):
        pass
        #return "{}".format( self.t_surface_C )
    def printlog(self):
        print( self.log())

class Null_mlx90640_Thermal_Camera(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass


def initialize_pcf8591_8_bit_adc_dac( instrument ):
    pcf8591_8_bit_adc_dac = Null_pcf8591_8_Bit_ADC_DAC()
    try:
        pcf8591_8_bit_adc_dac = pcf8591_8_Bit_ADC_DAC( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_pcf8591_8_bit_adc_dac" )
        instrument.sensors_present.append( pcf8591_8_bit_adc_dac )
    except Exception as err:
        pass
    return pcf8591_8_bit_adc_dac

class pcf8591_8_Bit_ADC_DAC( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "pcf8591_8_bit_adc_dac", pn = "pcf8591", address = 0x4f, swob = PCF8591.PCF8591( com_bus, address = 0x4f ))
        self.raw_0 = None
        self.raw_1 = None
        self.raw_2 = None
        self.raw_3 = None
        self.voltage_0 = None
        self.voltage_1 = None
        self.voltage_2 = None
        self.voltage_3 = None
    def read(self):
        self.raw_0 = PCF8591_AnalogIn(self.swob, PCF8591.A0).value
        self.raw_1 = PCF8591_AnalogIn(self.swob, PCF8591.A1).value
        self.raw_2 = PCF8591_AnalogIn(self.swob, PCF8591.A2).value
        self.raw_3 = PCF8591_AnalogIn(self.swob, PCF8591.A3).value
        self.voltage_0 = (self.raw_0/ 65535) * 3.3
        self.voltage_1 = (self.raw_1/ 65535) * 3.3
        self.voltage_2 = (self.raw_2/ 65535) * 3.3
        self.voltage_3 = (self.raw_3/ 65535) * 3.3
    def set(self, value):
        PCF8591_AnalogOut(self.swob, PCF8591.OUT).value = value #32767 max
    def header(self):
        headers = "pcf8591_channel_0_digital_number-!-counts, pcf8591_channel_1_digital_number-!-counts, pcf8591_channel_2_digital_number-!-counts, pcf8591_channel_3_digital_number-!-counts"
        headers += ", pcf8591_channel_0_voltage-!-V, pcf8591_channel_1_voltage-!-V, pcf8591_channel_2_voltage-!-V, pcf8591_channel_3_voltage-!-V"
        return headers
    def log(self):
        return "{}, {}, {}, {}, {}, {}, {}, {}".format( self.raw_0, self.raw_1, self.raw_2, self.raw_3, self.voltage_0, self.voltage_1, self.voltage_2, self.voltage_3 )
    def printlog(self):
        print( self.log())

class Null_pcf8591_8_Bit_ADC_DAC(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def read(self, value):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass


def initialize_pmsa0031_particulates_sensor( instrument ):
    pmsa0031_particulates_sensor = Null_pmsa0031_Particulates_Sensor()
    try:
        pmsa0031_particulates_sensor = pmsa0031_Particulates_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_pmsa0031_particulates_sensor" )
        instrument.sensors_present.append( pmsa0031_particulates_sensor )
    except Exception as err:
        pass
        #print( "pmsa0031 particulates sensor fail: {}".format(err))
    return pmsa0031_particulates_sensor

class pmsa0031_Particulates_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "pmsa0031_particulates_sensor", pn = "pmsa0031", address = 0x12, swob = PM25_I2C( com_bus, reset_pin = None ))
        self.aqip = None
        self.pm100 = None
        self.pm25 = None
        self.ratio = None
    def read(self):
        try:
            self.data = self.swob.read()
        except RuntimeError as err:
            self.data = None
            print( err )
        if self.data is not None:
            self.aqip = calculate_aqi_p( self.data["pm25 standard"], self.data["pm100 standard"] )
        self.pm25 = self.data["pm25 standard"]
        self.pm100 = self.data["pm100 standard"]
    def header(self):
        headers = "pmsa0031_air_quality_index_for_particulates-!-, pmsa0031_pm2.5_over_pm10_ratio-!-, pmsa0031_pm1-!-ug_per_m_cubed"
        headers += ", pmsa0031_pm2.5-!-ug_per_m_cubed, pmsa0031_pm10-!-ug_per_m_cubed, pmsa0031_particle_count_0.3m-!-count_per_100mL"
        headers += ", pmsa0031_particle_count_0.5m-!-count_per_100mL, pmsa0031_particle_count_1m-!-count_per_100mL, pmsa0031_particle_count_2.5m-!-count_per_100mL"
        headers += ", pmsa0031_particle_count_5m-!-count_per_100mL, pmsa0031_particle_count_10m-!-count_per_100mL"
        return headers
    def log(self):
        if self.data["pm100 standard"] > 0:
            ratio = round(self.data["pm25 standard"]/self.data["pm100 standard"], 2)
        else:
            ratio = 1
        self.datastring = "{}, {},{}, {}, {}, {}, {}, {}, {}, {}, {}".format(
                self.aqip,
                self.ratio,
                self.data["pm10 standard"],
                self.data["pm25 standard"],
                self.data["pm100 standard"],
                self.data["particles 03um"],
                self.data["particles 05um"],
                self.data["particles 10um"],
                self.data["particles 25um"],
                self.data["particles 50um"],
                self.data["particles 100um"])
        return self.datastring
    def printlog(self):
        print( self.log())

class Null_pmsa0031_Particulates_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.aqip = None
        self.pm100 = None
        self.pm25 = None
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

def initialize_qwiic_buzzer( i2c_bus ):
    buzzer = Null_Qwiic_Buzzer()
    try:
        buzzer = Qwiic_Buzzer( i2c_bus )
    except Exception as err:
        print( "buzzer failed to initialize: {}".format(err) )
        pass
    return buzzer

class Qwiic_Buzzer( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "qwiic_buzzer", pn = "BOB-24474", address = 0x34, swob = qwiic_buzzer.QwiicBuzzer(i2c_driver = com_bus))
        self.swob.configure( self.swob.VOLUME_MAX )
        self.mute = False
    def read(self):
        pass
    def beep(self):
        if self.mute:
            pass
        else:
            self.swob.on()
    def stop(self):
        self.swob.off()
    def set(self, frequency_hz, time_ms ):
        self.swob.configure( frequency_hz, time_ms )
    def header(self):
        return ""
    def log(self):
        return ""
    def printlog(self):
        print( self.log())

class Null_Qwiic_Buzzer(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def beep(self):
        pass
    def stop(self):
        pass
    def set(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

def initialize_scd30_CO2_sensor( instrument ):
    scd30_CO2_sensor = Null_scd30_CO2_Sensor()
    try:
        scd30_CO2_sensor = scd30_CO2_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_scd30_CO2_sensor" )
        instrument.sensors_present.append( scd30_CO2_sensor )
    except:
        pass
    return scd30_CO2_sensor

class scd30_CO2_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "scd30_CO2_sensor", pn = "scd30", address = 0x61, swob = adafruit_scd30.SCD30(com_bus))
        self.temperature_C = None
        self.humidity = None
        self.co2_ppm = None
        self.co2_ppm_uncertainty = None
    def read(self):
        if self.swob.data_available:
            self.temperature_C = self.swob.temperature
            self.humidity = self.swob.relative_humidity
            self.co2_ppm = self.swob.CO2
            self.co2_ppm_uncertainty = 30 + self.co2_ppm * 0.03
    def header(self):
        return "scd30_co2_ambient-!-ppm, scd30_co2_uncertainty-!-ppm, scd30_temperature_ambient-!-C, scd30_humidity_relative-!-percent"
    def log(self):
        return "{}, {}, {}, {}".format( round (self.co2_ppm, 1), round(self.co2_ppm_uncertainty, 1), round(self.temperature_C, 1) , int(round(self.humidity, 0)))
    def printlog(self):
        print( self.log())

class Null_scd30_CO2_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

def initialize_scd4x_co2_sensor( instrument ):
    scd4x_co2_sensor = Null_scd4x_CO2_Sensor()
    try:
        scd4x_co2_sensor = scd4x_CO2_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_scd4x_co2_sensor" )
        instrument.sensors_present.append( scd4x_co2_sensor )
    except:
        pass
    return scd4x_co2_sensor

class scd4x_CO2_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "scd4x_co2_sensor", pn = "scd4x", address = 0x62, swob = adafruit_scd4x.SCD4X( com_bus ))
        if self.swob:
            self.swob.start_periodic_measurement()
        self.temperature_C = None
        self.humidity = None
        self.co2_ppm = None
    def read(self):
        self.co2_ppm = self.swob.CO2
        self.co2_uncty_ppm = 50 + self.co2_ppm * 0.05
        self.temperature_C = self.swob.temperature
        self.humidity = self.swob.relative_humidity
    def header(self):
        return "scd4x_co2_ambient-!-ppm, scd30_co2_uncertainty-!-ppm, scd4x_temperature_ambient-!-C, scd4x_humidity_relative-!-percent"
    def log(self):
        return "{}, {}, {}, {}".format( round(self.co2_ppm,1), round(self.co2_uncty_ppm,1), round(self.temperature_C,1), int(round(self.humidity,0)) )
    def printlog(self):
        print( self.log())

class Null_scd4x_CO2_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.temperature_C = None
        self.humidity = None
        self.co2_ppm = None
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

def initialize_vl53l1x_4m_range_sensor( instrument ):
    vl53l1x_4m_range_sensor = Null_vl53l1x_4m_Range_Sensor()
    try:
        vl53l1x_4m_range_sensor = vl53l1x_4m_Range_Sensor( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_vl53l1x_4m_range_sensor" )
        instrument.sensors_present.append( vl53l1x_4m_range_sensor )
    except:
        pass
    return vl53l1x_4m_range_sensor

class vl53l1x_4m_Range_Sensor( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "vl53l1x_4m_range_sensor", pn = "vl53l1x", address = 0x29, swob = adafruit_vl53l1x.VL53L1X( com_bus ))
        #self.model_id, self.module_type, self.mask_rev = self.swob.instrument_model_info
        #print("Model ID: 0x{:0X}".format(self.instrument_model_id))
        #print("Module Type: 0x{:0X}".format(self.module_type))
        #print("Mask Revision: 0x{:0X}".format(self.mask_rev))
        self.swob.start_ranging()
        self.swob.clear_interrupt()
        self.swob.distance_instrument_mode = 2 # long distance instrument_mode
        self.swob.timing_budget = 100
        self.range_m = None
    def read(self):
        if self.swob.data_ready:
            self.range_m = self.swob.distance/100 #reports in cm for whatever reason
    def header(self):
        return "vl53l1x_distance-!-m"
    def log(self):
        return "{}".format( self.range_m )
    def printlog(self):
        print( self.log())

class Null_vl53l1x_4m_Range_Sensor(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass

##############
# end sensor definitions section
##############


def calculate_aqi_p( p25_reading, p100_reading ):
    gc.collect()
    p25_break_points = (0, 12, 12.1, 35.4, 35.5, 55.4, 55.5, 150.4, 150.5, 250.4, 250.5, 350.4, 350.5, 500.4)
    #print( p25_break_points )
    p100_break_points = (0, 54, 55, 154, 155, 254, 255, 354, 355, 424, 425, 504, 505, 604)
    #print( p100_break_points )
    AQI_levels = (0, 50, 51, 100, 101, 150, 151, 200, 201, 300, 301, 400, 401, 500)
    #print( AQI_levels )
    p25_index = 0
    p100_index = 0
    for i in range (len(AQI_levels)-1):
        if (p25_reading > p25_break_points[i] and p25_reading < p25_break_points[i+1]):
            p25_index = i
    #aqi = int((((ihi-ilo)/(bhi-blo))*(reading-blo))+ilo)
    aqi25 = int((((AQI_levels[p25_index+1] - AQI_levels[p25_index])/(p25_break_points[p25_index+1] - p25_break_points[p25_index]))*(p25_reading-p25_break_points[p25_index]))+AQI_levels[p25_index])
    #print(aqi25)
    for n in range (len(AQI_levels)-1):
        if (p100_reading > p100_break_points[i] and p100_reading < p100_break_points[i+1]):
            p100_index = i
    aqi100 = int((((AQI_levels[p100_index+1] - AQI_levels[p100_index])/(p100_break_points[p100_index+1] - p100_break_points[p100_index]))*(p100_reading-p25_break_points[p100_index]))+AQI_levels[p100_index])
    #print(aqi100)
    #print( p25_break_points[p25_index], p25_break_points[p25_index+1], AQI_levels[p25_index], AQI_levels[p25_index+1], p100_break_points[p100_index], p100_break_points[p100_index+1], AQI_levels[p100_index], AQI_levels[p100_index+1])
    if aqi100 > aqi25:
        return aqi100
    else:
        return aqi25

def update_batch( datestamp ):
    try:
        with open( "/sd/batch.txt", "r" ) as b:
            try:
                previous_batchfile_string = b.readline()
                previous_datestamp = previous_batchfile_string[ 0:8 ]
                previous_batch_number = int( previous_batchfile_string[ 8: ])
            except ValueError:
                previous_batch_number = 0
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
            b.write("\n")
    except OSError as err:
        print("Error: writing batch.txt {:}".format(err) )
    return batch_number

def update_filename( instrument ):
    # device_type, hardware_clock, new_header, batch_number
    timenow = instrument.hardware_clock.read()
    if timenow is not None:
        create_new_file = False
        filename_of_the_day = ("{}_data_{}{:02}{:02}-{}.csv".format(instrument.device_type, timenow.tm_year,timenow.tm_mon,timenow.tm_mday,instrument.batch_number))
        # create a dummy filename
        last_filename_in_use = ("{}_data_{}{:02}{:02}-{}.csv".format(instrument.device_type, 2000,01,01,0))
        # look up today's date
        current_datestamp = "{:04}{:02}{:02}".format( timenow.tm_year, timenow.tm_mon, timenow.tm_mday)
        previous_header = False
        # look up the last filename
        try:
            with open( "/sd/last_filename.txt", "r" ) as lfn:
                try:
                    last_filename_in_use = lfn.readline().rstrip()
                except ValueError as err:
                    print(err)
        except OSError:
            print( "last_filename.txt file not found, creating new last_filename.txt file" )
            try:
                with open ( "/sd/last_filename.txt", "w" ) as lfn:
                    lfn.write(filename_of_the_day)
            except:
                print( "unable to create last_filename.txt file")

        substrings = last_filename_in_use.split("_")
        date_batch = substrings[-1]
        substrings = date_batch.split("-")
        last_datestamp = substrings[0]
        if last_datestamp != current_datestamp:
            print( "new day, start a new file" )
            create_new_file = True
        else:
            try:
                with open( "/sd/{}".format(last_filename_in_use), "r" ) as lfn:
                    previous_header = lfn.readline().rstrip()
                    previous_header += "\n"
            except OSError as err:
                print( err )
            #print( "previous header", previous_header )
            #print( "current header", instrument.header )
            #print( "equal", instrument.header == previous_header )
            if instrument.header != previous_header:
                print( "configuration change, start a new file" )
                create_new_file = True
            else:
                filename_to_use = last_filename_in_use
        if create_new_file:
            filename_to_use = filename_of_the_day
            try:
                with open( "/sd/{}".format(filename_to_use), "w" ) as fn:
                    fn.write( instrument.header )
            except OSError as err:
                print( err )
            try:
                with open ( "/sd/last_filename.txt", "w" ) as lfn:
                    lfn.write(filename_to_use)
            except:
                print( "unable to write to last_filename.txt file")

    else:
        filename_to_use = "{}_data_no_timestamp.csv".format(DEVICE_TYPE)
        try:
            with open( "/sd/{}".format(filename_to_use), "w" ) as fn:
                fn.write( new_header )
        except OSError as err:
            print( err )

    instrument.filename = filename_to_use

def initialize_hardware_clock( i2c_bus ):
    hardware_clock = Null_Hardware_Clock()
    try:
        hardware_clock = pcf8523_Hardware_Clock( i2c_bus )
        print( "hardware clock initialized" )
    except NameError as err:
        print( "library missing:", err )
    except Exception:
        pass
    return hardware_clock

class pcf8523_Hardware_Clock( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "hardware_clock", pn = "pcf8523", address = 0x68, swob = pcf8523.PCF8523( com_bus ))
        self.null_time = time.struct_time(( 2020,  01,   01,   00,  00,  00,   0,   -1,    -1 ))
        self.timenow = self.null_time
        self.DAYS = { 0:"Sunday", 1:"Monday", 2:"Tuesday", 3:"Wednesday", 4:"Thursday", 5:"Friday", 6:"Saturday" }
    def battery_ok( self ):
        try:
            self.clock_battery_ok = not self.swob.battery_low
        except:
            self.clock_battery_ok = False
        return self.clock_battery_ok
    def read(self):
        try:
            self.timenow = self.swob.datetime
        except:
            self.timenow = self.null_time
        if self.timenow.tm_wday not in range ( 0, 7 ):
            self.datetime = null_time
        return self.timenow
    def get_iso_time_now( self ):
        self.read()
        iso8601_utc_timestamp = "{:04}{:02}{:02}T{:02}{:02}{:02}Z".format(
            self.timenow.tm_year, self.timenow.tm_mon, self.timenow.tm_mday,
            self.timenow.tm_hour, self.timenow.tm_min, self.timenow.tm_sec )
        return iso8601_utc_timestamp
    def get_decimal_hour_now( self ):
        self.read()
        decimal_hour = self.timenow.tm_hour + self.timenow.tm_min/60.0 + self.timenow.tm_sec/3600.0
        return decimal_hour
    def get_datestamp_now( self ):
        self.read()
        datestamp = "{:04}{:02}{:02}".format( self.timenow.tm_year, self.timenow.tm_mon, self.timenow.tm_mday )
        return datestamp
    def get_day_now( self ):
        return self.DAYS[self.timenow.tm_wday]
    def sync_system_clock(self):
        self.read()
        try:
            system_clock = rtc.RTC()
            system_clock.datetime = self.swob.datetime
            print( "system clock synchronized to hardware clock" )
        except:
            print( "failed to synchronize system clock to hardware clock" )
    def header(self):
        return "TBD"
    def log(self):
        return " "
    def printlog(self):
        print( self.log())
    def set_time(self):
        timenow = self.swob.datetime
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
            print( "The date is %s %d-%d-%d" % ( self.DAYS[ weekday ], year, month, day ))
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
            self.swob.datetime = t

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
            self.swob.datetime = t
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
            self.swob.datetime = t

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
            self.swob.datetime = t

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
            self.swob.datetime = t

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
            self.swob.datetime = t

        print()
        print( "Current weekday is {}. Enter a new weekday and press return, or press return to skip.".format(self.DAYS[timenow.tm_wday]))
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
        self.swob.datetime = t
        print( "returning to status page" )

class Null_Hardware_Clock():
    def __init__( self ):
        self.swob = None
        self.null_time = time.struct_time(( 2020,  01,   01,   00,  00,  00,   0,   -1,    -1 ))
        self.timenow = self.null_time
    def read(self):
        pass
    def battery_ok( self ):
        pass
    def get_day_now( self ):
        pass
    def get_time_now_iso_dec( self ):
        self.read()
        iso8601_utc_timestamp = "{:04}{:02}{:02}T{:02}{:02}{:02}Z".format(
            self.timenow.tm_year, self.timenow.tm_mon, self.timenow.tm_mday,
            self.timenow.tm_hour, self.timenow.tm_min, self.timenow.tm_sec )
        decimal_hour = time.monotonic()/ 3600
        return iso8601_utc_timestamp, decimal_hour
    def sync_system_clock(self):
        pass
    def set_time(self):
        pass

def increment_select( page ):
    select_value = (page.select_value + encoder_move) % page.number_of_select_positions

def initialize_rotary_encoder( pin_a, pin_b, pin_button ):
    encoder = Null_Rotary_Encoder()
    try:
        encoder = Rotary_Encoder( pin_a, pin_b, pin_button )
    except Exception as err:
        print( "encoder failed: {}".format(err))
    return encoder

class Rotary_Encoder( Device ):
    def __init__( self, pin_a, pin_b, pin_button ):
        super().__init__(name = "rotary_encoder", pn = "encoder", address = 00, swob = rotaryio.IncrementalEncoder( pin_b, pin_a ))
        self.button = digitalio.DigitalInOut( pin_button )
        self.button.direction = digitalio.Direction.INPUT
        self.button.pull = digitalio.Pull.UP
        self.button_pressed = False
        self.button_last_pressed = False
        self.encoder_flag = False
        self.button_flag = False
        self.last_position = None
        self.last_value = 0
        self.last_button_read = time.monotonic()
        self.button_cycle_time_s = 0
        self.slowest_button_cycle_time_s = 0
    def read_encoder(self):
        try:
            self.position = self.swob.position
            if not self.encoder_flag:
                if self.last_position is not None and self.position != self.last_position:
                    self.last_value = self.position - self.last_position
                    if self.last_value > 1:
                        self.last_value = 1
                    if self.last_value < -1:
                        self.last_value = -1
                    if self.last_value != 0:
                        self.encoder_flag = True
                self.last_position = self.position
        except Exception as err:
            print( err )
    def read_button(self):
        self.last_button_read = time.monotonic()
        try:
            self.button_pressed = not self.button.value
            if self.button_pressed:
                if self.button_last_pressed:
                    pass
                else:
                    self.button_flag = True
                self.button_last_pressed = True
            else:
                self.button_last_pressed = False
        except Exception as err:
            print( err )
    def log(self):
        pass
    def printlog(self):
        pass

class Null_Rotary_Encoder(Device):
    def __init__( self ):
        self.swob = None
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        print( "encoder failed to initialize" )
    def printlog(self):
        pass

def initialize_touch_screen( bus ):
    touch_screen = Null_Touch_Screen()
    try:
        touch_screen = Focal_Touch_Screen( bus )
    except Exception as err:
        print( "touch screen fail: {}".format(err))
    return touch_screen

class Focal_Touch_Screen( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "touch_screen", pn = "FocalTouch", address = 0x38, swob = adafruit_focaltouch.Adafruit_FocalTouch(com_bus, debug=False))
        self.flag = False
    def read(self):
        try:
            self.is_touched = self.swob.touched
            if self.is_touched:
                #print( "touched" )
                self.dict = self.swob.touches
                self.tx = 320 - self.dict[0]['y'] #transform
                self.ty = self.dict[0]['x'] #transform
        except Exception as err:
            print( err )
    def log(self):
        pass
    def printlog(self):
        print( self.log())

class Null_Touch_Screen(Device):
    def __init__( self ):
        self.swob = None
        self.is_touched = False
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass

def initialize_display( spi_bus ):
    try:
        # displayio/dafruit_ili9341 library owns the pins until display release
        displayio.release_displays()
        tft_dc = board.D11
        tft_cs = board.D12
        display_bus = FourWire(spi_bus, command=tft_dc, chip_select=tft_cs )
        display = adafruit_ili9341.ILI9341(display_bus, width=320, height=240, rotation=0)
        print( "display initialized")

    except ValueError as err:
        print("Error: display failed to initialize {:}".format(err))
        display = False
    if display:
        display_group = displayio.Group()
        display.root_group = display_group
    return display_group

def initialize_uart( txpin, rxpin ):
    try:
        uart = busio.UART(txpin, rxpin, baudrate=9600, timeout=10)
        print( "uart bus initialized" )
    except:
        uart = False
    return uart

def read_analog_in( pin ):
    ain_counts = pin.value

def read_5V_supply( pin ):
    voltage = 2 * (pin.value * 3.3) / 65536

def flash_indicator( lamp ):
    flash_count = 4
    flash_interval_s = 0.2
    for index in range (0, flash_count):
        lamp.value = True
        time.sleep( flash_interval_s )
        lamp.value = False
        time.sleep( flash_interval_s )

def initialize_led( pin ):
    LED = digitalio.DigitalInOut( pin )
    LED.direction = digitalio.Direction.OUTPUT
    count = 4
    interval = 0.1
    LED.value = True
    time.sleep(interval)
    LED.value = False
    return LED

def initialize_neopixel( pin ):
    try:
        num_pixels = 1
        ORDER = neopixel.RGB
        neopixel_instance = neopixel.NeoPixel( pin, num_pixels, brightness=0.3, auto_write=True, pixel_order=ORDER )
        print( "neopixel initialized" )
    except:
        neopixel_instance = False
        print( "neopixel failed to initialize" )
    return neopixel_instance

def initialize_i2c_bus():
    try:
        i2c_bus = board.I2C() #TBD might need to limit speed to 100kHz for the mlx90614
        print( "i2c bus initialized" )
    except:
        print( "i2c bus failed to initialize" )
        i2c_bus = False
    return i2c_bus

def evaluate_sdcard_storage( vfs, bytes_per_hour, verbose ):
    try:
        sdcard_status = os.statvfs("/sd")
        sdf_block_size = sdcard_status[0]
        sdf_blocks_avail = sdcard_status[4]
        storage_free_percent = sdf_blocks_avail/sdf_block_size *100
        #print( sdcard_status )
        #print( "bytes per block = {}".format(sdf_block_size))
        #print( "free blocks = {}".format(sdf_blocks_avail))
        sd_bytes_avail_B = sdf_blocks_avail * sdf_block_size
        sd_bytes_avail_MB = sd_bytes_avail_B/ 1000000
        #print( "MB available = {}".format(sd_bytes_avail_MB))
        sdfssize = sdcard_status[2]
        sdbytessize_MB = int (round(( sdfssize * sdf_block_size/ 1000000 ), 0))
        #print( "MB drive size = {}".format(sdbytessize_MB))
        sdbytessize_GB = int( round( sdbytessize_MB /1000, 0 ))
        sdavail_percent = int( sd_bytes_avail_MB/ sdbytessize_MB * 100)
        if verbose:
            if sdbytessize_GB < 1:
                print( "SD card space available = {} % of {} MB".format(sdavail_percent, sdbytessize_MB))
            else:
                print( "SD card space available = {} % of {} GB".format(sdavail_percent, sdbytessize_GB))
        if False:
            line_bytes_size = 200 #bytes_per_line
            line_capacity_remaining = int(sd_bytes_avail_MB * 1000000/ line_bytes_size)
            data_source_interval_s = 1.0
            lines_per_s= 1/sample_interval_s
            time_remaining_h = int( line_capacity_remaining * lines_per_s /3600 )
        time_remaining_h = sd_bytes_avail_B/ bytes_per_hour
        time_remaining_days = round(time_remaining_h/24, 1)
        if verbose:
            print( "data collection time remaining until this SD card is full: {} h = {} days".format(time_remaining_h, time_remaining_days))
    except Exception as err:
        print( err )
        time_remaining_h = False
    return time_remaining_h

def initialize_sd_card( spi_bus, sd_cs_pin ):
    try:
        sdcard = sdcardio.SDCard( spi_bus, sd_cs_pin )
        vfs = storage.VfsFat(sdcard)
        storage.mount(vfs, "/sd")
        print( "SD card initialized" )
    except Exception as err:
        print("SD card fail: missing or full: {}".format(err))
        print( "*** The card may be missing, or you may need to create a folder named sd in the root directory of CIRCUITPY ***" )
        vfs = False
    return vfs

def get_uid():
    try:
        UID = int.from_bytes(microcontroller.cpu.uid, "big") % 100000
        print("unique identifier (UID) : {0}".format( UID ))
    except:
        UID = False
        print("unique identifier (UID) not available")
    return UID

def memory_check( message ):
    gc.collect()
    mem_free_kB = gc.mem_free()/1000
    print( "{} memory free: {} kB, {} %".format( message, int(mem_free_kB), int((100* (mem_free_kB)/start_mem_free_kB ))))

def stall():
    print("intentionally stalled, press return to continue")
    input_string = False
    while input_string == False:
        input_string = input().strip()

gc.collect()
#print( "memory free after function definitions = {} kB, {} %".format(int(gc.mem_free()/1000), int(100*(gc.mem_free()/1000)/start_mem_free_kB )) )

main()
