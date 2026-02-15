SOFTWARE_VERSION_NUMBER = "0.0.1"
DEVICE_TYPE = "STELLA_Lab_Spec_Q"
# laboratory fluorescence spectrometer
# Copyright NASA 2026 under MIT open source license
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
import terminalio
from adafruit_display_text import label
import vectorio
import rtc
import sys
import adafruit_sdcard

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
# 0x0B bat mon
# 0x10 mini_gps
# 0x34 buzzer   Qwiic buzzer
# 0x36 seesaw rotary encoder
# 0x39 as7341   Visible spectral sensor
# 0x3D display
# 0x48 ads1015  Analog to digital converter, 12 bits, 4 channels
# 0x58 led driver
# 0x68 clock

mem_free_after_imports = gc.mem_free()
print( "mem free after imports = {} kB, {} %".format(int(gc.mem_free()/1000), int(100*(gc.mem_free()/1000)/start_mem_free_kB )) )

from software_modules import classm_device
from software_modules import functionm_file, functionm_palette
from software_modules import devicem_pcf8523_rtc, devicem_neopixel
from software_modules import devicem_gps, pagem_welcome_LSQ

def main():
    gc.collect()
    displayio.release_displays()
    UID = get_uid()
    vfs = False
    spi_bus = busio.SPI(board.SD_CLK, board.SD_MOSI, board.SD_MISO)
    vfs = functionm_file.initialize_sd_card( spi_bus, board.SD_CS )
    i2c_bus = initialize_i2c_bus()
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
    instrument = create_instrument( i2c_bus, UID, buzzer )
    instrument.vfs = vfs
    instrument.welcome_page.show()

    instrument.spectral_sensors_detected = False
    # initialize spectral sensors
    if True:
        if ('0x39') in devices_present_hex:
            print("as7341 found")
            from software_modules import spectralm_as7341 #VIS
            as7341_spectrometer = spectralm_as7341.initialize_as7341_spectrometer( instrument )
        if len( instrument.spectral_sensors_present ) > 0:
            instrument.spectral_sensors_detected = True

    # initialize sensors
    #gps = devicem_gps.initialize_gps( instrument )
    if ('0x48') in devices_present_hex:
        from software_modules import devicem_ads1015
        ads1015_12_bit_adc = devicem_ads1015.initialize_ads1015_12_bit_adc( instrument )
        lab_spec_present[1] = True
    if ('0x36') in devices_present_hex:
        pass
        #from software_modules import devicem_tbd
        # tbd rotary_encoder = devicem_tbd.initialize_tbd( instrument )

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

    stall()

    controls_page = pagem_controls.make_controls_page( instrument, gps, battery_monitor )
    main_menu_page = pagem_main_menu.make_main_menu_page( instrument )
    status_page = pagem_status.make_status_page( instrument, battery_monitor )
    settings_page = pagem_settings.make_settings_page( instrument )
    sensors_page = pagem_sensors.make_sensors_page( instrument )
    time_place_page = pagem_time_place.make_time_place_page( instrument )
    #air_page = pagem_air.make_air_page( instrument )
    heat_page = pagem_heat.make_heat_page( instrument )
    lab_spec_page = pagem_lab_spec.make_lab_spec_page( instrument, onboard_neopixel )
    start = time.monotonic()

    if instrument.spectral_sensors_detected and not lab_spec_present:
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

    if True: #False: #non-menu startup page
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
                if instrument.serial_out:
                    sensor.printlog()
                    instrument.handle_inputs()
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
                    if instrument.serial_out:
                        for sensor in instrument.sensors_present:
                            sensor.printlog()
                            instrument.handle_inputs()
                        print()
                        last_serial_time = time.monotonic()

                if battery_monitor.percentage < 20:
                    flash_indicator( battery_indicator )
                if time.monotonic() > system_update_period_start + system_update_period_s:
                    instrument.check_calendar_day()
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
    def __init__( self, i2c_bus, UID, buzzer):
        self.i2c_bus = i2c_bus
        self.device_type = DEVICE_TYPE
        self.uid = UID
        self.buzzer = buzzer
        self.palette = functionm_palette.make_palette()
        self.main_display_group = False #tbd
        self.pages_list = []
        self.welcome_page = pagem_welcome_LSQ.make_welcome_page( self, SOFTWARE_VERSION_NUMBER )
        self.hardware_clock = devicem_pcf8523_rtc.initialize_hardware_clock( i2c_bus )
        #self.hardware_clock.report()
        self.hardware_clock.sync_system_clock()
        self.clock_battery_ok_text =  "clock battery OK: {}".format( self.hardware_clock.battery_ok() )
        self.datestamp = self.hardware_clock.get_datestamp_now()
        self.last_datestamp = self.datestamp
        self.iso_time = self.hardware_clock.get_iso_time_now()
        self.batch_number = functionm_file.update_batch(self.datestamp)
        print( "batch number = {}".format( self.batch_number ))
        self.filename = None
        self.sensors_present = []
        self.spectral_sensors_present = []
        self.measurement_counter = 0
        #self.rotary_encoder = devicem_rotary_encoder.initialize_rotary_encoder( pin_a = board.A3, pin_b = board.A4, pin_button = board.A2 )
        self.encoder_increment = 0
        self.button_pressed = False
        self.input_flag = False
        self.input_interval_start = 0
        self.input_interval = 1
        self.active_page_number = 2
        self.last_active_page_number = 0
        self.previous_page_number = 1
        self.vfs = False
        self.make_header()
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
            self.rotary_encoder.encoder_flag = False
            self.input_flag = True
        self.rotary_encoder.read_button()
        if self.rotary_encoder.button_flag:
            self.buzzer.beep()
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




def create_instrument( i2c_bus, UID, buzzer ):
    instrument = Instrument( i2c_bus, UID, buzzer )
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
