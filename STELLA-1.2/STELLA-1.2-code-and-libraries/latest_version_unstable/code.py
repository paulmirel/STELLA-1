SOFTWARE_VERSION_NUMBER = "0.7.1"
DEVICE_TYPE = "STELLA-1.2"
# STELLA-1.2 multifunction instrument
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

# gather startup statistics
import time
startup_start_time = time.monotonic()
import gc
gc.collect()
start_mem_free_kB = gc.mem_free()/1000
print("start memory free {0:.2f} kB".format( start_mem_free_kB ))

# configuration imports
from configuration_files import user_settings

# operational imports
import os
import microcontroller
import board
import digitalio
import busio
import displayio
import rotaryio
#import terminalio
#from adafruit_display_text import label
#import vectorio
import rtc
from analogio import AnalogIn

# functional imports
import math

# main unit device imports

#import adafruit_focaltouch
#import adafruit_max1704x
#from adafruit_pcf8523 import pcf8523
#import adafruit_gps

# scan the i2c_bus for devices present
i2c_bus = board.I2C()
i2c_bus.try_lock()
devices_present = i2c_bus.scan()
devices_present_hex = []
for device_address in devices_present:
    devices_present_hex.append(hex(device_address))
i2c_bus.unlock()
#print( devices_present_hex )

# supported devices by i2c_address:
# 0x12 pmsa0031 particulates sensor
# 0x18 DS248x   1 wire thermometer reader
# 0x19 lsm303   accelerometer
# 0x1c lsm6ds   TBD
# 0x1e lis2mdl  TBD
# 0x1f mcp9808  Thermometer ### close a0, a1, a2 address jumpers on board to set address
# 0x28 soil_con Soil conductance sensor
# 0x29 vl53l1x  Lidar range finder
# 0x33 mlx90640 Thermal camera
# 0x34 buzzer   Qwiic buzzer
# 0x36 max1704x Battery monitor
# 0x37 seesaw   TBD
# 0x38 focaltouch   Capacitive touch screen sensor
# 0x39 as7341   Visible spectral sensor
# 0x44 hdc302x  Precision temperature and humidity sensor
# 0x49 as7265x  Visible and Near Infrared spectral sensor
# 0x4a ads1115  Analog to digital converter, 16 bits, 4 channels ### connect ADDR to SDA to set address
# 0x4f pcf8591  Analog to digital converter, 8 bits, 4 channels, and digital to analog converter, 1 channel ### close a0, a1, a2 address jumpers on board to set address
# 0x53 ltr390   UV and total illumination sensor
# 0x5a mlx90614 Thermal infrared remote surface thermometer
# 0x61 scd30    CO2 sensor, NDIR: nondispersive infrared absorption, with temperature and humidity sensors
# 0x62 scd4x    CO2 sensor, thermo-acoustic: pulsed infrared resonant heating and microphone, with temperature and humidity sensors
# 0x6a lis3mdl  Magnetic field sensor
# 0x74 as7331   Ultraviolet spectral sensor
# 0x77 bme280   Barometric pressure sensor, with temperature and humidity sensors

mem_free_after_imports = gc.mem_free()
print( "mem free after imports = {} kB, {} %".format(int(gc.mem_free()/1000), int(100*(gc.mem_free()/1000)/start_mem_free_kB )) )


from software_modules import functionm_file, functionm_palette, functionm_spectral_graph
from software_modules import devicem_pcf8523_rtc, devicem_neopixel
from software_modules import devicem_ili9341_display, devicem_gps
from software_modules import devicem_rotary_encoder, devicem_focaltouch
from software_modules import pagem_welcome, pagem_controls, pagem_main_menu, pagem_status
from software_modules import pagem_settings, pagem_sensor_list, pagem_generic_sensor
from software_modules import pagem_remote_sensing, pagem_air_analyzer, pagem_time_place

def main():
    gc.collect()
    displayio.release_displays()
    UID = get_uid()
    spi_bus = board.SPI()
    vfs = functionm_file.initialize_sd_card( spi_bus, board.A5 )
    i2c_bus = initialize_i2c_bus()
    gps_uart_bus = initialize_uart( board.TX, board.RX )
    onboard_neopixel = devicem_neopixel.initialize_neopixel( board.NEOPIXEL )
    if vfs:
        onboard_neopixel.fill(devicem_neopixel.YELLOW)
    else:
        onboard_neopixel.fill(devicem_neopixel.RED)
    if ('0x34') in devices_present_hex:
        from software_modules import devicem_qwiic_buzzer
        buzzer = devicem_qwiic_buzzer.initialize_qwiic_buzzer( i2c_bus )
        buzzer.mute = False
        buzzer.set(932, 130) # frequency in Hz, time in ms. 932 Hz is B flat in octave 5. Fairly pleasant through this piezo driver, though maybe a bit medical in tone.
        buzzer.beep()
    battery_indicator = initialize_led( board.LED )

    instrument = create_instrument( i2c_bus, spi_bus, gps_uart_bus, UID, buzzer )
    instrument.welcome_page.show()
    spectral_register = functionm_spectral_graph.create_spectral_register( instrument )

    # initialize spectral sensors
    spectral_sensors_detected = False
    if ('0x49') in devices_present_hex:
        spectral_sensors_detected = True
        from software_modules import spectralm_as7265x
        as7265x_spectrometer = spectralm_as7265x.initialize_as7265x_spectrometer( instrument )
    if ('0x74') in devices_present_hex:
        spectral_sensors_detected = True
        from software_modules import spectralm_as7331
        as7331_spectrometer = spectralm_as7331.initialize_as7331_spectrometer( instrument )
    if ('0x39') in devices_present_hex:
        spectral_sensors_detected = True
        from software_modules import spectralm_as7341
        as7341_spectrometer = spectralm_as7341.initialize_as7341_spectrometer( instrument )
    if spectral_sensors_detected:
        from software_modules import functionm_exposure_control
        #from software_modules import spectral_graph
        #from software_modules import remote_sensing_page

    # initialize sensors
    if ('0x48') in devices_present_hex:
        from software_modules import devicem_ads1015
        ads1015_12_bit_adc = devicem_ads1015.initialize_ads1015_12_bit_adc( instrument )
    if ('0x4a') in devices_present_hex:
        from software_modules import devicem_ads1115
        ads1115_16_bit_adc = devicem_ads1115.initialize_ads1115_16_bit_adc( instrument ) ### connect ADDR to SDA to set address
    if ('0x36') in devices_present_hex:
        from software_modules import devicem_max1704x
        battery_monitor = devicem_max1704x.initialize_battery_monitor( instrument )
    if ('0x77') in devices_present_hex:
        from software_modules import devicem_bme280
        bme280_air_sensor = devicem_bme280.initialize_bme280_air_sensor( instrument )
    if ('0x18') in devices_present_hex:
        from software_modules import devicem_ds2484
        ds2484_1_wire_thermometer = devicem_ds2484.initialize_ds2484_1_wire_thermometer( instrument )
    if ('0x44') in devices_present_hex:
        #import adafruit_hdc302x
        from software_modules import devicem_hdc3022
        hdc3022_air_sensor = initialize_hdc3022_air_sensor( instrument )
    if ('0x1e') in devices_present_hex:
        #import adafruit_lis2mdl
        from software_modules import devicem_lis2mdl
        lis2mdl_magnetic_field_sensor = initialize_lis2mdl_magnetic_field_sensor( instrument )
    if ('0x6a') in devices_present_hex:
        #from adafruit_lis3mdl import LIS3MDL
        from software_modules import devicem_lis3mdl
        lis3mdl_magnetic_field_sensor = initialize_lis3mdl_magnetic_field_sensor( instrument )
    if ('0x19') in devices_present_hex:
        #import adafruit_lsm303_accel
        from software_modules import devicem_lsm303
        lsm303_acceleration_sensor = initialize_lsm303_acceleration_sensor( instrument )
    if ('0x1c') in devices_present_hex:
        #from adafruit_lsm6ds.lsm6ds3 import LSM6DS3 as LSM6DS
        from software_modules import devicem_lsm6ds
        lsm6ds_accel_gyro_sensor = initialize_lsm6ds_accel_gyro_sensor( instrument )
    if ('0x53') in devices_present_hex:
        #import adafruit_ltr390
        from software_modules import devicem_ltr390
        ltr390_uva_sensor = initialize_ltr390_uva_sensor( instrument )
    if ('0x1f') in devices_present_hex:
        #import adafruit_mcp9808 ### close a0, a1, a2 address jumpers on board
        from software_modules import devicem_mcp9808
        mcp9808_air_thermometer = initialize_mcp9808_air_thermometer( instrument )
    if True: # This device doesn't answer the scan.
        from software_modules import devicem_mlx90614
        mlx90614_surface_thermometer = devicem_mlx90614.initialize_mlx90614_surface_thermometer( instrument )
    if ('0x33') in devices_present_hex:
        #import adafruit_mlx90640
        from software_modules import devicem_mlx90640
        mlx90640_thermal_camera = initialize_mlx90640_thermal_camera( instrument )
    if ('0x4f') in devices_present_hex:
        #import adafruit_pcf8591.pcf8591 as PCF8591  ### close a0, a1, a2 address jumpers on board
        #from adafruit_pcf8591.analog_in import AnalogIn as PCF8591_AnalogIn
        #from adafruit_pcf8591.analog_out import AnalogOut as PCF8591_AnalogOut
        from software_modules import devicem_pcf8591
        pcf8591_8_bit_adc_dac = initialize_pcf8591_8_bit_adc_dac( instrument )
    if ('0x12') in devices_present_hex:
        from software_modules import devicem_pmsa0031
        pmsa0031_particulates_sensor = initialize_pmsa0031_particulates_sensor( instrument )
    if ('0x61') in devices_present_hex:
        #import adafruit_scd30
        from software_modules import devicem_scd30
        scd30_CO2_sensor = initialize_scd30_CO2_sensor( instrument )
    if ('0x62') in devices_present_hex:
        #import adafruit_scd4x
        from software_modules import devicem_scd4x
        scd4x_co2_sensor = initialize_scd4x_co2_sensor( instrument )
    if ('0x37') in devices_present_hex:
        pass
        #from adafruit_seesaw.seesaw import Seesaw
        #from software_modules import devicem_soil_cap
        soil_capacitance_sensor_sensor = initialize_soil_capacitance_sensor( instrument )
    if ('0x28') in devices_present_hex:
        pass #need library
        #from software_modules import devicem_soil_con
        #soil_conductance_sensor = initialize_soil_conductance_sensor( instrument )
    if ('0x29') in devices_present_hex:
        #import adafruit_vl53l1x
        from software_modules import devicem_vl53l1x
        vl53l1x_4m_range_sensor = initialize_vl53l1x_4m_range_sensor( instrument )

    instrument.welcome_page.announce( "Found {} external sensors".format( len(instrument.sensors_present) + len(instrument.spectral_sensors_present)))


    '''
    sense_5V = AnalogIn(board.A1)
    analog_in_0 = AnalogIn(board.A0)
    if mlx90614_surface_thermometer.pn and as7265x_spectrometer.pn:
        lv_ez_mb1013_rangefinder = initialize_lv_ez_mb1013_rangefinder( instrument, analog_in_0, sense_5V )
    else:
        lv_ez_mb1013_rangefinder = False
    '''

    #gps = devicem_gps.initialize_gps( instrument )

    '''
    #plus_5v_supply = False #TBD make a device object with digital out and analog in, check it for rising and falling
    enable_5V = digitalio.DigitalInOut( board.D10 )
    enable_5V.direction = digitalio.Direction.OUTPUT
    enable_5V.value = True
    # plus_5v_supply.enable(), .read(), .log(), .disable()
    '''
    gc.collect()
    mem_free_after_devices = gc.mem_free()
    print( "memory free after device object creations = {} kB, {} %".format(int(gc.mem_free()/1000),
                                                    int(100*(gc.mem_free()/1000)/start_mem_free_kB )))
    print( "memory usage by device objects = {} kB = {} %".format(( mem_free_after_imports - mem_free_after_devices)/1000,
                                round(100 * ( mem_free_after_imports - mem_free_after_devices)/1000/start_mem_free_kB, 1)))

    if False:
        controls_page = pagem_controls.make_controls_page( instrument, gps, battery_monitor ) #1
        main_menu_page = pagem_main_menu.make_main_menu_page( instrument ) #2
        status_page = pagem_status.make_status_page( instrument ) #3
        settings_page = pagem_settings.make_settings_page( instrument ) #4
        sensor_list_page = pagem_sensor_list.make_sensor_list_page( instrument ) #5
        generic_sensor_page = pagem_generic_sensor.make_generic_sensor_page( instrument ) #6
        time_place_page = pagem_time_place.make_time_place_page( instrument ) #7
        air_analyzer_page = pagem_air_analyzer.make_air_analyzer_page( instrument ) #8
        if False: #spectral_sensors_detected:
            remote_sensing_page = pagem_remote_sensing.make_remote_sensing_page( instrument, spectral_register, hdc3022_air_sensor, mlx90614_surface_thermometer, lv_ez_mb1013_rangefinder ) #9
            instrument.active_page_number = 9
            spectral_graph_page = functionm_spectral_graph.make_spectral_graph_page( instrument, spectral_register ) #10 takes a lot of time
            instrument.add_spectral_graph_page( spectral_graph_page )
            remote_sensing_page.add_spectral_graph_page( spectral_graph_page )
        else:
            remote_sensing_missing_page = pagem_remote_sensing.make_remote_sensing_missing_page( instrument ) #9 alt



    gc.collect()
    mem_free_after_pages = gc.mem_free()
    print( "memory free after page creations = {} kB, {} %".format(int(gc.mem_free()/1000), int(100*(gc.mem_free()/1000)/start_mem_free_kB )))
    print( "memory usage by pages = {} kB = {} %".format(
                                            ( mem_free_after_devices - mem_free_after_pages)/1000,
                                            int( 100 * ( mem_free_after_devices - mem_free_after_pages)/1000/start_mem_free_kB)))


    instrument.make_band_list()
    #instrument.make_header()

    operational = True
    first_sample_time = time.monotonic()
    last_sample_time = time.monotonic() - instrument.sample_interval_s
    instrument.take_burst = False
    instrument.sample_interval_s = 2
    try:
        if vfs:
            onboard_neopixel.fill(devicem_neopixel.GREEN)
        while operational:
            loop_start = time.monotonic()
            for sensor in instrument.sensors_present:
                sensor.read()
            for sensor in instrument.sensors_present:
                print( sensor.pn, end= ": ")
                sensor.printlog()
            print()
            while time.monotonic() < last_sample_time + instrument.sample_interval_s:#) and instrument.record) or instrument.take_burst:
                pass
            last_sample_time = time.monotonic()
            #print( "sample interval satified at {} s".format(time.monotonic()-first_sample_time ))
        '''
        for sensor in instrument.sensors_present:
            sensor.read()
        gps.read()
        controls_page.update_values( instrument )

        loop_times = []




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
        '''
    finally:
        displayio.release_displays()
        print( "displayio displays released" )
        i2c_bus.deinit()
        print( "i2c_bus deinitialized" )

class Instrument:
    def __init__( self, i2c_bus, spi_bus, uart_bus, UID, buzzer):
        self.i2c_bus = i2c_bus
        self.uart_bus = uart_bus
        self.device_type = DEVICE_TYPE
        self.uid = UID
        self.buzzer = buzzer
        #self.usb_serial_out_enabled = usb_serial_out_enabled
        self.sample_interval_s = user_settings.sample_interval_s
        self.burst_count = user_settings.burst_count
        self.pages_list = []
        self.palette = functionm_palette.make_palette()
        self.main_display_group = devicem_ili9341_display.initialize_display( spi_bus )
        self.welcome_page = pagem_welcome.make_welcome_page( self, SOFTWARE_VERSION_NUMBER )
        self.hardware_clock = devicem_pcf8523_rtc.initialize_hardware_clock( i2c_bus )
        #self.hardware_clock.report()
        self.hardware_clock.sync_system_clock()
        self.clock_battery_ok_text =  "clock battery OK: {}".format( self.hardware_clock.battery_ok() )
        self.welcome_page.announce( self.clock_battery_ok_text )
        self.datestamp = self.hardware_clock.get_datestamp_now()
        self.last_datestamp = self.datestamp
        self.iso_time = self.hardware_clock.get_iso_time_now()
        self.batch_number = functionm_file.update_batch(self.datestamp)
        print( "batch number = {}".format( self.batch_number ))
        self.filename = None
        self.sensors_present = []
        self.spectral_sensors_present = []
        self.record = user_settings.record_on_startup
        self.session_tag = "{}-{}-session-".format(self.uid, self.iso_time)
        self.measurement_counter = 0
        self.rotary_encoder = devicem_rotary_encoder.initialize_rotary_encoder( pin_a = board.A3, pin_b = board.A4, pin_button = board.A2 )
        self.encoder_increment = 0
        self.button_pressed = False
        self.touch_screen = devicem_focaltouch.initialize_touch_screen( self.i2c_bus )
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
            for band in sensor.wavelength_bands_nm:
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


class Page:
    def __init__( self ):
        pass
    def show(self):
        self.group.hidden = False
    def hide(self):
        self.group.hidden = True
    def update_values(self):
        pass

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

def initialize_i2c_bus():
    try:
        i2c_bus = board.I2C() #TBD might need to limit speed to 100kHz for the mlx90614
        print( "i2c bus initialized" )
    except:
        print( "i2c bus failed to initialize" )
        i2c_bus = False
    return i2c_bus

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
