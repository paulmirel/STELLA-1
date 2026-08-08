SOFTWARE_VERSION_NUMBER = "1.3.1x"
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
import sys

# functional imports
import math

# scan the i2c_bus for devices present
i2c_bus = board.I2C()
i2c_bus.try_lock()
devices_present = i2c_bus.scan()
devices_present_hex = []
for device_address in devices_present:
    devices_present_hex.append(hex(device_address))
i2c_bus.unlock()
print( devices_present_hex )

# supported devices by i2c_address:
# 0x12 pmsa0031 particulates sensor
# 0x18 DS248x   1 wire thermometer reader
# 0x19 lsm303   accelerometer
# 0x1c lsm6ds   Accelerometer and gyroscope
# 0x1e lis2mdl  Magnetic field sensor
# 0x1f mcp9808  Thermometer ### close a0, a1, a2 address jumpers on board to set address
# TBD 0x28 soil_con Soil conductance sensor
# 0x29 vl53l1x  Lidar range finder
# TBD 0x33 mlx90640 Thermal camera
# 0x34 buzzer   Qwiic buzzer
# 0x36 max1704x Battery monitor
# TBD 0x37 seesaw soil_cap Soil capacitance sensor
# 0x38 focaltouch   Capacitive touch screen sensor
# 0x39 as7341   Visible spectral sensor
# 0x39 as7343   VNIR spectral sensor (address collision)
# 0x44 hdc302x  Precision temperature and humidity sensor
# 0x48 ads1015  Analog to digital converter, 12 bits, 4 channels
# 0x49 as7265x  Visible and Near Infrared spectral sensor
# 0x4a ads1115  Analog to digital converter, 16 bits, 4 channels ### connect ADDR to SDA to set address
# 0x4f pcf8591  Analog to digital converter, 8 bits, 4 channels, and digital to analog converter, 1 channel ### close a0, a1, a2 address jumpers on board to set address
# 0x53 ltr390   UV and total illumination sensor
# 0x5a mlx90614 Thermal infrared remote surface thermometer
# 0x60 mcp4728  Quad DAC
# 0x61 scd30    CO2 sensor, NDIR: nondispersive infrared absorption, with temperature and humidity sensors
# 0x62 scd4x    CO2 sensor, thermo-acoustic: pulsed infrared resonant heating and microphone, with temperature and humidity sensors
# 0x68 pcf8523  Real time clock
# 0x6a lis3mdl  Magnetic field sensor
# 0x74 as7331   Ultraviolet spectral sensor
# 0x77 bme280   Barometric pressure sensor, with temperature and humidity sensors

mem_free_after_imports = gc.mem_free()
print( "mem free after imports = {} kB, {} %".format(int(gc.mem_free()/1000), int(100*(gc.mem_free()/1000)/start_mem_free_kB )) )

from software_modules import classm_device
from software_modules import functionm_file, functionm_palette
from software_modules import devicem_pcf8523_rtc, devicem_neopixel
from software_modules import devicem_ili9341_display, devicem_gps
from software_modules import devicem_rotary_encoder, devicem_focaltouch
from software_modules import pagem_welcome, pagem_controls, pagem_main_menu, pagem_status
from software_modules import pagem_settings, pagem_sensors, pagem_lab_spec
from software_modules import pagem_light, pagem_exposure, pagem_heat, pagem_air, pagem_time_place
from software_modules import devicem_supply_5V

try:
    # wifi is optional
    from software_modules import wifi as wifi_module
except ImportError as e:
    if 'software_modules.wifi' in str(e):
        print(f"wifi module")
        class wifi_module:
            # the only api from code.py
            def initialize(instrument):
                return None
    else:
        raise e
try:
    # ntp is optional
    from software_modules import ntp
except ImportError as e:
    if 'software_modules.ntp' in str(e):
        print(f"ntp module: no internet time")
        class NTPTime:
            def update(self):
                pass
        class ntp:
            # the only api from code.py
            def initialize():
                return NTPTime()
    else:
        raise e
try:
    # httpd for sd card is optional
    from software_modules import sd_httpd
except ImportError as e:
    if 'software_modules.sd_httpd' in str(e):
        print(f"sd_httpd module: no web-page")
        class sd_httpd:
            # the only api from code.py
            def initialize(instrument):
                return None
            def update():
                pass
    else:
        raise e
try:
    # mdns is optional
    from software_modules import mdns
except ImportError as e:
    if 'software_modules.mdns' in str(e):
        print(f"mdns module: use ip address in url")
        class mdns:
            # the only api from code.py
            def initialize(instrument):
                return None
            def update():
                pass
    else:
        raise e

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
        buzzer.click_enabled = True
        buzzer.beep()
    else:
        buzzer = False

    battery_indicator = initialize_led( board.LED )

    instrument = create_instrument( i2c_bus, spi_bus, gps_uart_bus, UID, buzzer )
    instrument.vfs = vfs
    instrument.welcome_page.show()

    supply_5V = devicem_supply_5V.initialize_supply_5V(instrument)
    inet_lan = wifi_module.initialize( instrument )
    ntp_time = ntp.initialize()
    mdns.initialize(hostname=f"stella-{instrument.uid}" )
    sd_httpd.initialize()

    lab_spec_present = [False,False,False]
    instrument.spectral_sensors_detected = False
    # initialize spectral sensors
    if True:
        if ('0x74') in devices_present_hex:
            print("as7331 found")
            from software_modules import spectralm_as7331 #UV
            as7331_spectrometer = spectralm_as7331.initialize_as7331_spectrometer( instrument )
        if ('0x39') in devices_present_hex:
            from software_modules import spectralm_as7341 #VIS
            as7341_spectrometer = spectralm_as7341.initialize_as7341_spectrometer( instrument )
            if as7341_spectrometer:
                lab_spec_present[0] = True
                print("as7341 found")
            else:
                from software_modules import spectralm_as7343 #VNIR
                as7343_spectrometer = spectralm_as7343.initialize_as7343_spectrometer( instrument )
                if as7343_spectrometer:
                    print("as7343 found")
                    lab_spec_present[0] = True
        else:
            as7341_spectrometer = False
            as7343_spectrometer = False
        if ('0x49') in devices_present_hex:
            print("as7265x found ")
            from software_modules import spectralm_as7265x #VIS+NIR
            as7265x_spectrometer = spectralm_as7265x.initialize_as7265x_spectrometer( instrument )
        if len( instrument.spectral_sensors_present ) > 0:
            instrument.spectral_sensors_detected = True

    # initialize sensors

    gps = devicem_gps.initialize_gps( instrument )
    if ('0x48') in devices_present_hex:
        from software_modules import devicem_ads1015
        ads1015_12_bit_adc = devicem_ads1015.initialize_ads1015_12_bit_adc( instrument )
        lab_spec_present[1] = True
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
    # '0x38' focaltouch initializes within the instrument init function
    if ('0x44') in devices_present_hex:
        from software_modules import devicem_hdc3022
        hdc3022_air_sensor = devicem_hdc3022.initialize_hdc3022_air_sensor( instrument )
    if ('0x1e') in devices_present_hex:
        from software_modules import devicem_lis2mdl
        lis2mdl_magnetic_field_sensor = devicem_lis2mdl.initialize_lis2mdl_magnetic_field_sensor( instrument )
    if ('0x6a') in devices_present_hex:
        from software_modules import devicem_lis3mdl
        lis3mdl_magnetic_field_sensor = devicem_lis3mdl.initialize_lis3mdl_magnetic_field_sensor( instrument )
    if ('0x19') in devices_present_hex:
        from software_modules import devicem_lsm303
        lsm303_acceleration_sensor = devicem_lsm303.initialize_lsm303_acceleration_sensor( instrument )
    if ('0x1c') in devices_present_hex:
        from software_modules import devicem_lsm6ds
        lsm6ds_accel_gyro_sensor = devicem_lsm6ds.initialize_lsm6ds_accel_gyro_sensor( instrument )
    if ('0x53') in devices_present_hex:
        from software_modules import devicem_ltr390
        ltr390_uva_sensor = devicem_ltr390.initialize_ltr390_uva_sensor( instrument )
    if ('0x1f') in devices_present_hex:
        from software_modules import devicem_mcp9808  ### close a0, a1, a2 address jumpers on board
        mcp9808_air_thermometer = devicem_mcp9808.initialize_mcp9808_air_thermometer( instrument )
    if True: # This device doesn't answer the i2c_bus scan.
        from software_modules import devicem_mlx90614
        mlx90614_surface_thermometer = devicem_mlx90614.initialize_mlx90614_surface_thermometer( instrument )
    if ('0x33') in devices_present_hex:
        from software_modules import devicem_mlx90640 # data from this thermal camera is not yet supported
        mlx90640_thermal_camera = devicem_mlx90640.initialize_mlx90640_thermal_camera( instrument )
    if ('0x4f') in devices_present_hex:
        from software_modules import devicem_pcf8591 ### close a0, a1, a2 address jumpers on board
        pcf8591_8_bit_adc_dac = devicem_pcf8591.initialize_pcf8591_8_bit_adc_dac( instrument )
    if ('0x12') in devices_present_hex:
        from software_modules import devicem_pmsa0031
        pmsa0031_particulates_sensor = devicem_pmsa0031.initialize_pmsa0031_particulates_sensor( instrument )
    if ('0x61') in devices_present_hex:
        from software_modules import devicem_scd30
        scd30_CO2_sensor = devicem_scd30.initialize_scd30_CO2_sensor( instrument )
    if ('0x62') in devices_present_hex:
        from software_modules import devicem_scd4x
        scd4x_co2_sensor = devicem_scd4x.initialize_scd4x_co2_sensor( instrument )
    if ('0x64') in devices_present_hex or ('0x60') in devices_present_hex:
        from software_modules import devicem_mcp4728
        mcp4728_quad_dac = devicem_mcp4728.initialize_mcp4728_quad_dac( instrument )
        lab_spec_present[2] = True
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
        from software_modules import devicem_vl53l1x
        vl53l1x_4m_range_sensor = devicem_vl53l1x.initialize_vl53l1x_4m_range_sensor( instrument )

    analog_in_0 = AnalogIn(board.A0)
    if mlx90614_surface_thermometer.pn: ##TBD recognize RS and RS-B plugins## and as7265x_spectrometer.pn:
        from software_modules import devicem_lv_ez_rangefinder
        lv_ez_rangefinder = devicem_lv_ez_rangefinder.initialize( instrument, analog_in_0, supply_5V )
        supply_5V.enable()
    else:
        lv_ez_rangefinder = False

    instrument.welcome_page.announce( "Found {} sensors".format( len(instrument.sensors_present) + len(instrument.spectral_sensors_present)))

    for sensor in instrument.spectral_sensors_present:
        sensor.make_spectral_channels()
    instrument.make_wavelength_bands_list()



    gc.collect()
    mem_free_after_devices = gc.mem_free()
    print( "memory free after device object creations = {} kB, {} %".format(int(gc.mem_free()/1000),
                                                    int(100*(gc.mem_free()/1000)/start_mem_free_kB )))
    print( "memory usage by device objects = {} kB = {} %".format(( mem_free_after_imports - mem_free_after_devices)/1000,
                                round(100 * ( mem_free_after_imports - mem_free_after_devices)/1000/start_mem_free_kB, 1)))


    controls_page = pagem_controls.make_controls_page( instrument, gps, battery_monitor )
    main_menu_page = pagem_main_menu.make_main_menu_page( instrument )
    status_page = pagem_status.make_status_page( instrument, battery_monitor )
    settings_page = pagem_settings.make_settings_page( instrument )
    sensors_page = pagem_sensors.make_sensors_page( instrument )
    time_place_page = pagem_time_place.make_time_place_page( instrument )
    #air_page = pagem_air.make_air_page( instrument )
    heat_page = pagem_heat.make_heat_page( instrument )
    if all(lab_spec_present):
        lab_spec_page = pagem_lab_spec.make_lab_spec_page( instrument, onboard_neopixel )
    else:
        lab_spec_page = pagem_lab_spec.make_lab_spec_missing_page( instrument )
    start = time.monotonic()

    if False:#instrument.spectral_sensors_detected and not all(lab_spec_present):
        light_page = pagem_light.make_light_page( instrument )
        exposure_page = pagem_exposure.make_exposure_page( instrument )
    else:
        light_page = pagem_light.make_light_missing_page( instrument )

    if False:
        for page in instrument.pages_list:
            print( page.page_name )
    instrument.make_pages_dictionary()
    #print( instrument.pages_dict )



    gc.collect()
    mem_free_after_pages = gc.mem_free()
    print( "memory free after page creations = {} kB, {} %".format(int(gc.mem_free()/1000), int(100*(gc.mem_free()/1000)/start_mem_free_kB )))
    print( "memory usage by pages = {} kB = {} %".format(
                                            ( mem_free_after_devices - mem_free_after_pages)/1000,
                                            int( 100 * ( mem_free_after_devices - mem_free_after_pages)/1000/start_mem_free_kB)))



    system_update_period_s = 60
    system_update_period_start = time.monotonic() - system_update_period_s + 10
    operational = True
    first_sample_time = time.monotonic()
    last_sample_time = time.monotonic() - instrument.sample_interval_s
    last_serial_time = time.monotonic() - instrument.serial_interval_s
    startup_end_time = time.monotonic()
    startup_time_s = startup_end_time - startup_start_time
    print( "startup_time_s = ", startup_time_s )
    stop = time.monotonic()
    elapsed = stop - start
    print( "time to make light page is {}s".format( elapsed ))
    instrument.take_burst = False
    accumulator_cycles = 5
    loop_times = []

    if False:#True: #False: #non-menu startup page
        if instrument.spectral_sensors_detected:
            instrument.active_page_number = instrument.pages_dict["Light"]
        if all(lab_spec_present):
            instrument.active_page_number = instrument.pages_dict["Lab_Spec"]
        if False:
            instrument.active_page_number = instrument.pages_dict["Heat"]

    try:
        if buzzer: buzzer.beep()
        if instrument.vfs:
            onboard_neopixel.fill(devicem_neopixel.GREEN)
            functionm_file.update_filename( instrument )
        else:
            onboard_neopixel.fill(devicem_neopixel.RED)
        instrument.check_inputs()
        while operational:
            loop_start = time.monotonic()
            instrument.show_active_page()
            instrument.handle_inputs()
            controls_page.update_values()
            sample_start_time = time.monotonic()
            system_log = instrument.get_system_log()
            if instrument.active_page_number == instrument.pages_dict["Lab_Spec"]:
                instrument.handle_inputs()
                instrument.update_active_page()
                time.sleep(0.01)
            elif instrument.active_page_number == instrument.pages_dict["Sensors"]:
                sensor = instrument.sensors_present[sensors_page.sensor_choice]
                sensor.read()
                instrument.handle_inputs()
                instrument.update_active_page()
                if instrument.record:
                    functionm_file.write_line( instrument, system_log, sensor.log() )
                    instrument.handle_inputs()
                instrument.measurement_counter += 1
                sample_stop_time = time.monotonic()
                sample_time = sample_stop_time - sample_start_time
                #print( "sample_time, one sensor, s = ", round(sample_time,3))
            else:
                for sensor in instrument.sensors_present:
                    sensor.read()
                    instrument.handle_inputs()
                sample_stop_time = time.monotonic()
                sample_time = sample_stop_time - sample_start_time
                #print( "sample_time, all sensors, s = ", round(sample_time,3))
                #print("call to update active page from line 325, page number",instrument.active_page_number, instrument.combined)
                instrument.update_active_page()
                if instrument.active_page_number == instrument.pages_dict["Light"]:
                    light_page.update_plot()
                if instrument.vfs:
                        if instrument.take_burst:
                            if instrument.burst_counter < instrument.burst_count:
                                instrument.burst_counter += 1
                                instrument.record = False
                                onboard_neopixel.fill(devicem_neopixel.BLUE)
                                for sensor in instrument.sensors_present:
                                        functionm_file.write_line( instrument, system_log, sensor.log() )
                                        instrument.handle_inputs()
                            else:
                                controls_page.update_burst_countdown( instrument.burst_count )
                                instrument.take_burst = False
                        else:
                            instrument.burst_counter = 0
                        if (time.monotonic() > last_sample_time + instrument.sample_interval_s):
                            if instrument.record:
                                onboard_neopixel.fill(devicem_neopixel.GREEN)
                                for sensor in instrument.sensors_present:
                                    functionm_file.write_line( instrument, system_log, sensor.log() )
                                    instrument.handle_inputs()
                            last_sample_time = time.monotonic()
                        onboard_neopixel.fill(devicem_neopixel.OFF)
                        instrument.measurement_counter += 1
                else:
                    onboard_neopixel.fill(devicem_neopixel.RED)
                if (time.monotonic() > last_serial_time + instrument.serial_interval_s):
                    if instrument.serial_out_index == 0:
                        for sensor in instrument.sensors_present:
                            sensor.printlog()
                            instrument.handle_inputs()
                    if instrument.serial_out_index == 1:
                        if False:
                            for sensor in instrument.sensors_present:
                                sensor.emit_json_packet()
                                instrument.handle_inputs()
                        print("emit_json_packet TBD")
                    last_serial_time = time.monotonic()
            if inet_lan:
                inet_lan.update()
                ntp_time.update()
                sd_httpd.update()
                mdns.update()
            battery_monitor.read()
            if battery_monitor.percentage < 20:
                flash_indicator( battery_indicator )
            if time.monotonic() > system_update_period_start + system_update_period_s:
                instrument.check_calendar_day()
                if gps.timestruct:
                    instrument.sync_rtc_to_gps_time(gps.timestruct)
                system_update_period_start = time.monotonic()

            loop_stop = time.monotonic()
            loop_time = loop_stop - loop_start
            #print("loop time {} s".format( loop_time ))
            loop_times.append(loop_time)
            if len(loop_times) > accumulator_cycles:
                loop_times.pop(0)
            #print( "loop working time: min = {}, max = {},".format( min(loop_times), max(loop_times)))
            #print( "loop working time average = {}".format( round(sum(loop_times)/len(loop_times),3)))
            #print()



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
        self.serial_out_index = getattr(user_settings, "serial_out_index", 0)
        self.serial_output_choices = ["text", "json-TBD", "none"]
        self.sample_interval_s = getattr(user_settings, "sample_interval_s", 3)
        self.burst_count = getattr(user_settings, "burst_count", 2)
        self.serial_interval_s = getattr(user_settings, "serial_interval_s", 10)
        self.wifi_enabled = getattr(user_settings, "wifi_enabled", False)
        self.take_burst = False
        self.burst_counter = 0
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
        self.record = getattr(user_settings, "record_on_startup", False)
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
        self.previous_page_number = 1
        self.combined_page_selection = 0
        self.combined_page_last_selection = 0
        self.vfs = False
        self.make_header()
        self.combined = False
        self.rtc_syncd_to_gps = False

    def show_active_page( self ):
        if self.active_page_number != self.last_active_page_number:
            if self.last_active_page_number == 0:
                self.previous_page_number = self.pages_dict["Main"]
            else:
                self.previous_page_number = self.last_active_page_number
            self.pages_list[ self.last_active_page_number ].hide()
            self.pages_list[ self.pages_dict["Controls"] ].hide()
            active_page_name = self.pages_list[self.active_page_number].page_name
            if active_page_name == "Main" or active_page_name == "Light" or active_page_name == "Heat":
                self.pages_list[ self.pages_dict["Controls"] ].show()
                self.pages_list[ self.active_page_number ].show()
                if self.combined_page_selection < self.pages_list[ self.pages_dict["Controls"] ].selection_count:
                    self.pages_list[ self.active_page_number ].hide_all_selections()
                    self.pages_list[ self.pages_dict["Controls"] ].update_selection()
                else:
                    self.pages_list[ self.active_page_number ].update_selection()
                    self.pages_list[ self.pages_dict["Controls"] ].hide_all_selections()
            elif active_page_name == "Lab_Spec":
                self.pages_list[ self.pages_dict["Controls"] ].hide()
                self.pages_list[ self.pages_dict["Lab_Spec"] ].show()
                #self.pages_list[ self.pages_dict["Light"] ].show()
            else:
                self.pages_list[ self.active_page_number ].show()
            self.last_active_page_number = self.active_page_number


    def handle_inputs( self ):
        self.check_inputs()
        self.combined = False
        if self.input_flag:
            active_page = self.pages_list[ self.last_active_page_number ]
            controls_page = self.pages_list[ self.pages_dict["Controls"] ]
            if active_page.field_selected:
                active_page.action()

            else:
                if active_page.page_name == "Main" or active_page.page_name == "Light" or active_page.page_name == "Heat":
                    self.combined = True
                if self.encoder_increment != 0:
                    #TBD lab_spec_page selection combined with light_page
                    #print( "track the selection and hand off between both controls and the active page" )
                    self.combined_page_last_selection = self.combined_page_selection
                    if self.combined:
                        combined_selection_count = active_page.selection_count + controls_page.selection_count
                        self.combined_page_selection = (self.combined_page_selection + self.encoder_increment) % combined_selection_count
                        if self.combined_page_selection < controls_page.selection_count:
                            controls_page.last_selection = controls_page.selection
                            controls_page.selection = self.combined_page_selection
                            active_page.hide_all_selections()
                            controls_page.update_selection()
                        else:
                            controls_page.hide_all_selections()
                            active_page.last_selection = active_page.selection
                            active_page.selection = self.combined_page_selection - controls_page.selection_count
                            active_page.update_selection()
                    else:
                        active_page.last_selection = active_page.selection
                        active_page.selection = ( active_page.selection + self.encoder_increment ) % active_page.selection_count
                        active_page.update_selection()
                    self.update_active_page()
                    self.encoder_increment = 0
                if self.button_pressed:
                    if self.combined:
                        if self.combined_page_selection < controls_page.selection_count:
                            #print( "act on controls page on selection {}".format( controls_page.selection ) )
                            controls_page.action()
                        else:
                            #print( "act on active page of combination on selection {}".format(active_page.selection ))
                            active_page.action()
                    else:
                        active_page.action()
                        #print( active_page.selection  )
                    #print( "button pressed, do something with that")
                    self.button_pressed = False
            #controls_page.update_values()
            #self.update_active_page()
            self.input_flag = False

    def check_inputs( self ):
        self.rotary_encoder.read_encoder()
        if self.rotary_encoder.encoder_flag:
            self.encoder_increment = self.rotary_encoder.last_value
            if self.buzzer: self.buzzer.click()
            self.rotary_encoder.encoder_flag = False
            self.input_flag = True
        self.rotary_encoder.read_button()
        if self.rotary_encoder.button_flag:
            if self.buzzer: self.buzzer.beep()
            self.button_pressed = True
            self.rotary_encoder.button_flag = False
            self.input_flag = True
        if False:
            self.touch_screen.read()
            if not self.touch_screen.flag and self.touch_screen.is_touched:
                self.touch_tx = self.touch_screen.tx
                self.touch_ty = self.touch_screen.ty
                self.input_flag = True

    def update_active_page( self ):
        active_page = self.pages_list[ self.last_active_page_number ]
        if self.combined:
            controls_page = self.pages_list[ self.pages_dict["Controls"] ]
            if self.combined_page_selection < controls_page.selection_count:
                active_page.hide_all_selections()
                controls_page.update_selection()
            else:
                controls_page.hide_all_selections()
                active_page.update_selection()
        else:
            try:
                self.pages_list[ self.active_page_number ].update_values()
                #print("update active page")
            except Exception as err:
                print("values update failed: ", err)


    def update_batch(self):
        self.batch_number = functionm_file.update_batch(self.datestamp)
    def update_time(self):
        self.datestamp = self.hardware_clock.get_datestamp_now()
        self.iso_time = self.hardware_clock.get_iso_time_now()
        self.decimal_time = self.hardware_clock.get_decimal_hour_now()
    def update_filename(self):
        functionm_file.update_filename( self )
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

    def sync_rtc_to_gps_time(self,timestruct):
        if timestruct is not None:
            self.rtc_syncd_to_gps = self.hardware_clock.sync_to_struct(timestruct)
        else:
            self.rtc_syncd_to_gps = False

    def make_pages_dictionary( self ):
        self.pages_dict = {}
        for index in range (0, len(self.pages_list) ):
            self.pages_dict[ self.pages_list[index].page_name ] = index
            #print(self.pages_list[index].page_name, index)

    def make_wavelength_bands_list( self ):
        self.wavelength_bands_list = []
        for sensor in self.spectral_sensors_present:
            for band in sensor.wavelength_bands_nm:
                self.wavelength_bands_list.append(band)
        self.wavelength_bands_list_sorted = sorted( self.wavelength_bands_list )
        self.number_of_plot_points = len( self.wavelength_bands_list_sorted )

    def make_header( self ):
        self.header = "instrument_id"
        self.header += ", measurement_number"
        self.header += ", timestamp"
        self.header += ", decimal_hour"
        self.header += ", batch_number"
        self.header += ", burst_counter"
        self.header += ", sensor_name"
        self.header += ", part_number"
        self.header += ", parameter_units"
        self.header += ", value"
        self.header += ", parameter_units"
        self.header += ", value"
        self.header += ", parameter_units"
        self.header += ", value"
        self.header += ", parameter_units"
        self.header += ", value"
        self.header += ", parameter_units"
        self.header += ", value"
        self.header += ", parameter_units"
        self.header += ", value"
        return self.header

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
        system_log += ", {}".format( self.decimal_time )
        system_log += ", {}".format( self.batch_number )
        system_log += ", {}".format( self.burst_counter )
        return system_log

    def add_spectral_graph_page( self, spectral_graph_page ):
        self.spectral_graph_page = spectral_graph_page




def create_instrument( i2c_bus, spi_bus, uart_bus, UID, buzzer ):
    instrument = Instrument( i2c_bus, spi_bus, uart_bus, UID, buzzer )
    return instrument

def initialize_uart( txpin, rxpin ):
    try:
        uart = busio.UART(txpin, rxpin, baudrate=9600, timeout=10)
        print( "uart bus initialized" )
    except:
        uart = False
    return uart

def read_analog_in( pin ):
    ain_counts = pin.value

def flash_indicator( lamp ):
    flash_count = 4
    flash_interval_s = 0.1
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
