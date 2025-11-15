SOFTWARE_VERSION_NUMBER = "0.0.4"
DEVICE_TYPE = "STELLA-1.2_Exposure_control"
# Paul Mirel 2025

import gc
import time
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
import math
import adafruit_ili9341
import adafruit_focaltouch
import qwiic_buzzer
import neopixel
from adafruit_seesaw.seesaw import Seesaw
from adafruit_as7341 import AS7341
from adafruit_as7341 import Gain as AS7341_Gain
import qwiic_i2c
import qwiic_as7265x
import iorodeo_as7331 as as7331
from software_modules import as7265x_spectral_sensor_module
from software_modules import as7331_spectral_sensor_module
from software_modules import as7341_spectral_sensor_module

## check i2c devices present
i2c_bus = board.I2C()
i2c_bus.try_lock()
devices_present = i2c_bus.scan()
devices_present_hex = []
for device_address in devices_present:
    devices_present_hex.append(hex(device_address))
print( devices_present_hex )
i2c_bus.unlock()

spectral_sensors_detected = True

#### begin main definition

def main():
    BLUE = ( 0, 0, 255 )
    GREEN = ( 255, 0, 0 )
    YELLOW = ( 127, 255, 0 )
    RED = ( 0, 255, 0 )
    OFF = ( 0, 0, 0 )


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

    as7265x_spectrometer = as7265x_spectral_sensor_module.initialize_as7265x_spectrometer( instrument )
    as7331_spectrometer = as7331_spectral_sensor_module.initialize_as7331_spectrometer( instrument )
    as7341_spectrometer = as7341_spectral_sensor_module.initialize_as7341_spectrometer( instrument )

    instrument.welcome_page.hide()
    exposure_control_page = make_exposure_control_page( instrument )
    exposure_control_page.show()


    # move most of the variables and functionality into the page class.
    # at the main level we only need to know about the instrument.spectral_sensors_present, instrument.input_flag, and instrument.encoder_increment
    # the sensors hold the settings, so we don't need to carry them around







    '''

    ### local local values
    scale_choice = 0
    scale_list = "log scale", "linear scale"
    setting_choice = 0
    slider_pixel_span = exposure_control_page.slider_pixel_span
    slider_min_y = exposure_control_page.slider_min_y
    local_gain_choice = 0
    local_gain = 0
    local_integration_time_choice = 0
    local_integration_time_ms = 0
    local_lamp_choice = 0
    local_lamp_current_mA = 0
    exposure_high = 0
    decimal_16_bits = 65535
    exposure_max_value = decimal_16_bits
    exposure_value_span = []
    exposure_value_span.append( math.log(decimal_16_bits, 10))
    exposure_value_span.append( decimal_16_bits )
    exposure_control_page.update_values()









    if False:
        last_sensor_integration_time_choices = []
        sensor_integration_time_choices = []
        for sensor_choice in range( 0, len(instrument.spectral_sensors_present)):
            last_sensor_integration_time_choices.append(instrument.spectral_sensors_present[sensor_choice].default_integration_time_index)
            sensor_integration_time_choices.append(instrument.spectral_sensors_present[sensor_choice].default_integration_time_index)
    sensor_choice = 0
    local_integration_time_choice = 0
        # TBD lamp selection, lamp current
    '''
    wait_time = 1
    exposure_control_page.update_values()
    try:
        operational = True
        while operational:
            instrument.check_inputs()
            exposure_control_page.update_values()
            if instrument.input_flag:
                pass
            else:
                pass
            '''
                exposure_control_page.slider_scale_text_area.text = scale_list[ scale_choice ]

                local_sensor = instrument.spectral_sensors_present[sensor_choice]
                exposure_control_page.sensor_choice_text_area.text = local_sensor.choice_label



                if False: #local_sensor == as7331_spectrometer:
                    print( local_integration_time_choice, local_sensor.integration_time_ms_list, local_sensor.integration_time_ms_list[local_integration_time_choice] )

                local_integration_time_ms_value = local_sensor.integration_time_ms_list[local_integration_time_choice]
                local_integration_time_ms = []
                local_integration_time_ms.append(math.log(local_integration_time_ms_value,10))
                local_integration_time_ms.append(local_integration_time_ms_value)
                local_integration_time_range_ms = max(local_sensor.integration_time_ms_list) - min(local_sensor.integration_time_ms_list)
                local_integration_time_ms_per_pixel = []
                local_integration_time_ms_per_pixel.append(math.log(local_integration_time_range_ms,10)/slider_pixel_span)
                local_integration_time_ms_per_pixel.append(local_integration_time_range_ms/slider_pixel_span)
                local_integration_time_pixel_offset = local_integration_time_ms[ scale_choice ] / local_integration_time_ms_per_pixel[ scale_choice ]
                if local_integration_time_ms_value == min(local_sensor.integration_time_ms_list):
                    local_integration_time_pixel_offset = 0
                exposure_control_page.integration_time_slider.y = slider_min_y - int( local_integration_time_pixel_offset )
                exposure_control_page.integration_time_shading.y = exposure_control_page.integration_time_slider.y
                exposure_control_page.integration_time_shading.height = slider_min_y + 6 - exposure_control_page.integration_time_shading.y
                exposure_control_page.integration_time_text_area.text = str(local_integration_time_ms_value)



            #as7265x_integration_time_ms = as7265x_spectrometer.swob.set_integration_cycles( integration_number )
            '''
            wait_start = time.monotonic()
            while (time.monotonic() - wait_start < wait_time) and not instrument.input_flag:
                #print( time.monotonic() - wait_start )
                instrument.check_inputs()
                time.sleep(0.1)
            '''
            if exposure_control_page.setting_modes_list[ exposure_control_page.setting_mode ] == "Auto":
                exposure_control_page.auto_engaged = True
                if exposure_high < exposure_target_fraction_low * exposure_max_value:
                    if sensor_gain_choices[ sensor_choice ] < len( instrument.spectral_sensors_present[sensor_choice].gain_list) - 1:
                        sensor_gain_choices[ sensor_choice ] = (sensor_gain_choices[ sensor_choice ] + 1)
                    if False: #sensor_integration_time_choices[ sensor_choice ] < len( instrument.spectral_sensors_present[sensor_choice].integration_time_list) - 1:
                        sensor_integration_time_choices[ sensor_choice ] = (sensor_integration_time_choices[ sensor_choice ] + 4)
            else:
                exposure_control_page.auto_engaged = False

            if exposure_control_page.setting_mode != 0:
                exposure_control_page.gain_area.color_index = 19
                exposure_control_page.integration_time_area.color_index = 19
            else:
                if not exposure_control_page.gain_field_selected:
                    exposure_control_page.gain_area.color_index = 9
                if not exposure_control_page.integration_time_field_selected:
                    exposure_control_page.integration_time_area.color_index = 9
            '''
            if instrument.input_flag:
                '''
                if exposure_control_page.sensor_choice_field_selected:
                    sensor_choice = (sensor_choice + 1) % len(instrument.spectral_sensors_present)
                elif exposure_control_page.setting_field_selected:
                    exposure_control_page.setting_mode = ( exposure_control_page.setting_mode + instrument.encoder_increment ) % exposure_control_page.number_of_setting_modes
                elif exposure_control_page.slider_scale_field_selected:
                    scale_choice = (scale_choice + 1) % len(scale_list)
                elif exposure_control_page.gain_field_selected:
                    sensor_gain_choices[ sensor_choice ] = (sensor_gain_choices[ sensor_choice ] + instrument.encoder_increment) % len( instrument.spectral_sensors_present[sensor_choice].gain_list)
                    if sensor_gain_choices[ sensor_choice ] != last_sensor_gain_choices[ sensor_choice ]:
                        instrument.spectral_sensors_present[sensor_choice].set_gain(sensor_gain_choices[ sensor_choice ])
                        last_sensor_gain_choices[ sensor_choice ] = sensor_gain_choices[ sensor_choice ]
                elif exposure_control_page.integration_time_field_selected:
                    local_integration_time_choice = (local_integration_time_choice + instrument.encoder_increment ) % (local_sensor.integration_time_choices_count+1)
                    local_integration_time_ms = local_sensor.integration_time_ms_list[local_integration_time_choice]
                    local_sensor.set_integration_time_ms( local_integration_time_ms )
                elif exposure_control_page.lamp_choice_field_selected:
                    print( "TBD increment lamp choice" )
                elif exposure_control_page.lamp_current_field_selected:
                    print( "TBD increment lamp current" )
                else:
                    new_choice = exposure_control_page.exposure_select_choice + instrument.encoder_increment
                    if exposure_control_page.setting_mode == 0:
                        pass
                    else:
                        if new_choice == 4 and exposure_control_page.exposure_select_choice == 3:
                            new_choice = 6
                        if new_choice == 5 and exposure_control_page.exposure_select_choice == 6:
                            new_choice = 3
                    exposure_control_page.exposure_select_choice = (new_choice) % exposure_control_page.exposure_select_range
                exposure_control_page.update_values()
                '''
                instrument.input_flag = False
    finally:
        displayio.release_displays()
        print( "displayio displays released" )
        i2c_bus.deinit()
        print( "i2c_bus deinitialized" )


#### begin parent class definitions ###

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

#### begin exposure control page class definition

class Exposure_Control_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.instrument = instrument
        self.palette = self.instrument.palette
        self.selection_color_index = 6
        self.field_selected_color_index = 5
        self.field_not_selected_color_index = 9
        self.field_selected = []

        self.slider_max_y = 54
        self.slider_min_y = 174
        self.slider_pixel_span = self.slider_min_y - self.slider_max_y
        self.setting_modes_list = [ "Manual", "Auto", "Sunny", "Cloudy", "Indoor", "Dark", "Save" ] #append to this list when configurations are saved
        self.number_of_setting_modes = len( self.setting_modes_list )
        self.default_setting_mode = 0
        self.auto_exposure_engaged = False
        self.scale_choices = "linear scale", "log scale"
        self.scale_choice = 1
        self.selection = 0
        self.spectral_sensors = self.instrument.spectral_sensors_present
        self.active_sensor_index = 0
        self.exposure_max_value = 65535
        self.exposure_target_fraction_high = 0.9
        self.exposure_target_fraction_low = 0.5
        self.number_of_sensors = len( self.spectral_sensors )
        self.gain_index = []
        sensor_index = 0 #for sensor_index in range (0, self.number_of_sensors):
        self.gain_index.append( self.spectral_sensors[sensor_index].gain_index )
    #def get_default_settings( self ):


    def update_values( self ):
        number_of_selections = len(self.selection_list)
        if any( self.field_selected ):
            pass
        else:
            if self.instrument.encoder_increment != 0:
                self.selection = ( self.selection + self.instrument.encoder_increment ) % number_of_selections
                self.instrument.encoder_increment = 0

        if self.selection == 3:
            self.slider_scale_area.hidden = False
        else:
            self.slider_scale_area.hidden = True


        for index in range( 0, number_of_selections):
            if index == self.selection:
                self.selection_list[ index ].hidden = False
                if self.instrument.button_pressed:
                    if index == 0:
                        print( "return whence" )
                    else:
                        self.field_selected[index] = not self.field_selected[index]
                    self.instrument.button_pressed = False
                if self.field_selected[index]:
                    self.field_list[index].color_index = self.field_selected_color_index
                    if self.instrument.encoder_increment != 0:
                        if index == 1:
                            self.active_sensor_index = ( self.active_sensor_index + self.instrument.encoder_increment ) % number_of_sensors
                        elif index == 2:
                            pass #setting_index
                        elif index == 3:
                            pass #scale choice
                        elif index == 4:
                            self.gain_index[self.active_sensor_index] = ( self.gain_index[self.active_sensor_index] + self.instrument.encoder_increment ) % len( self.spectral_sensors[self.active_sensor_index].gain_list )
                            self.spectral_sensors[self.active_sensor_index].set_gain( self.gain_index[self.active_sensor_index])
                        elif index == 5:
                            pass # active sensor integration time
                        elif index == 6:
                            pass # active sensor led lamp current
                        elif index == 7:
                            pass # active sensor led lamp choice
                        self.instrument.encoder_increment = 0
                else:
                    self.field_list[index].color_index = self.field_not_selected_color_index

            else:
                self.selection_list[ index ].hidden = True

        ## update interface text
        self.sensor_choice_text_area.text = self.spectral_sensors[self.active_sensor_index].choice_label
        self.slider_scale_text_area.text = self.scale_choices[ self.scale_choice ]

        ## get exposure and drive slider, value, label, brackets
        self.spectral_sensors[self.active_sensor_index].read_counts_all()
        exposure_high, exposure_low = self.spectral_sensors[self.active_sensor_index].get_max_min_counts()
        exposure_value_span = self.exposure_max_value

        if exposure_high < self.exposure_max_value:
            self.exposure_label_text_area.color = self.palette[0]
            self.exposure_label_text_area.text = "Exposure Max"
        else:
            self.exposure_label_text_area.color = self.palette[2]
            self.exposure_label_text_area.text = "*SATURATED*"
            #print( "SATURATED" )
        self.exposure_maximum_text_area.text = str(exposure_high)

        if self.scale_choice == 1:
            if exposure_high > 0:
                exposure_high = math.log(exposure_high,10)
            else:
                exposure_high = 0
            if exposure_low > 0:
                exposure_low = math.log(exposure_low,10)
            else:
                exposure_low = 0
            if exposure_value_span > 0:
                exposure_value_span = math.log(exposure_value_span,10)
            else:
                exposure_value_span = 0

        exposure_value_per_pixel = exposure_value_span/ self.slider_pixel_span
        exposure_high_pixel_offset = int(exposure_high/exposure_value_per_pixel)
        exposure_low_pixel_offset = int(exposure_low/exposure_value_per_pixel)
        self.exposure_bracket_high.y = self.slider_min_y - exposure_high_pixel_offset
        self.exposure_bracket_low.y = self.slider_min_y - exposure_low_pixel_offset
        self.exposure_bracket_shading.y = self.exposure_bracket_high.y
        self.exposure_bracket_shading.height = self.exposure_bracket_low.y - self.exposure_bracket_high.y
        exposure_high_triangle_pixel_offset = int(self.exposure_target_fraction_high * self.exposure_max_value/exposure_value_per_pixel)
        exposure_low_triangle_pixel_offset = int(self.exposure_target_fraction_low * self.exposure_max_value/exposure_value_per_pixel)
        if self.scale_choice == 1:
            exposure_high_triangle_pixel_offset = math.log(self.exposure_target_fraction_high * self.exposure_max_value,10)/exposure_value_per_pixel
            exposure_high_triangle_pixel_offset = int(exposure_high_triangle_pixel_offset)
            exposure_low_triangle_pixel_offset = math.log(self.exposure_target_fraction_low * self.exposure_max_value,10)/exposure_value_per_pixel
            exposure_low_triangle_pixel_offset = int(exposure_low_triangle_pixel_offset)
        self.exposure_target_triangle_high.y = self.slider_min_y - exposure_high_triangle_pixel_offset
        self.exposure_target_triangle_low.y = self.slider_min_y - exposure_low_triangle_pixel_offset



        gain = self.spectral_sensors[self.active_sensor_index].gain_list[ self.gain_index[self.active_sensor_index] ]
        self.gain_text_area.text = str( gain )
        max_gain = max(self.spectral_sensors[self.active_sensor_index].gain_list)
        min_gain = min(self.spectral_sensors[self.active_sensor_index].gain_list)
        gain_value_span = max_gain - min_gain
        if self.scale_choice == 1:
            if gain > 0:
                gain = math.log(gain,10)
            else:
                gain = 0
            if max_gain > 0:
                max_gain = math.log(max_gain,10)
            else:
                max_gain = 0
            if min_gain > 0:
                min_gain = math.log(min_gain,10)
            else:
                min_gain = 0
            if gain_value_span > 0:
                gain_value_span = math.log(gain_value_span,10)
            else:
                gain_value_span = 0
        gain_per_pixel = gain_value_span/self.slider_pixel_span
        self.gain_slider.y = self.slider_min_y - int( gain / gain_per_pixel )
        self.gain_shading.y = self.gain_slider.y
        self.gain_shading.height = self.slider_min_y + 6 - self.gain_shading.y




        '''
        self.setting_text_area.text = self.setting_modes_list[ self.setting_mode ]
        ### bring the other page parameters in here as above

        if self.exposure_select_choice == 0:
            #print( "selection == 0" )
            self.return_select.hidden = False
            if self.instrument.button_pressed:
                print( "return whence" )
                self.instrument.button_pressed = False
        else:
            self.return_select.hidden = True

        if self.exposure_select_choice == 1:
            self.sensor_choice_select.hidden = False
            if self.instrument.button_pressed:
                self.sensor_choice_field_selected = not self.sensor_choice_field_selected
                self.instrument.button_pressed = False
        else:
            self.sensor_choice_select.hidden = True

        if self.exposure_select_choice == 2:
            self.setting_select.hidden = False
            if self.instrument.button_pressed:
                self.setting_field_selected = not self.setting_field_selected
                self.instrument.button_pressed = False
        else:
            self.setting_select.hidden = True

        if self.exposure_select_choice == 3:
            self.slider_scale_area.hidden = False
            self.slider_scale_select.hidden = False
            if self.instrument.button_pressed:
                self.slider_scale_field_selected = not self.slider_scale_field_selected
                self.instrument.button_pressed = False
        else:
            self.slider_scale_area.hidden = True
            self.slider_scale_select.hidden = True

        if self.exposure_select_choice == 4:
            if self.instrument.button_pressed:
                self.gain_field_selected = not self.gain_field_selected
                print( "gain field selected = ", self.gain_field_selected )
                self.instrument.button_pressed = False
            self.gain_select.hidden = False
        else:
            self.gain_select.hidden = True

        if self.exposure_select_choice == 5:
            if self.instrument.button_pressed:
                self.integration_time_field_selected = not self.integration_time_field_selected
                self.instrument.button_pressed = False
            self.integration_time_select.hidden = False
        else:
            self.integration_time_select.hidden = True

        if self.exposure_select_choice == 6:
            if self.instrument.button_pressed:
                self.instrument.button_pressed = False
                self.lamp_choice_field_selected = not self.lamp_choice_field_selected
            pass
            self.lamp_choice_select.hidden = False
        else:
            self.lamp_choice_select.hidden = True
            pass


        if self.exposure_select_choice == 7:
            self.lamp_current_select.hidden = False
            if self.instrument.button_pressed:
                self.instrument.button_pressed = False
                self.lamp_current_field_selected = not self.lamp_current_field_selected
        else:
            self.lamp_current_select.hidden = True



        if self.sensor_choice_field_selected:
            self.sensor_choice_area.color_index = self.field_selected_color_index
        else:
            self.sensor_choice_area.color_index = self.field_not_selected_color_index
        if self.setting_field_selected:
            self.setting_area.color_index = self.field_selected_color_index
        else:
            self.setting_area.color_index = self.field_not_selected_color_index
        if self.slider_scale_field_selected:
            self.slider_scale_area.color_index = self.field_selected_color_index
        else:
            self.slider_scale_area.color_index = self.field_not_selected_color_index
        if self.gain_field_selected:
            self.gain_area.color_index = self.field_selected_color_index
        else:
            self.gain_area.color_index = self.field_not_selected_color_index
        if self.integration_time_field_selected:
            self.integration_time_area.color_index = self.field_selected_color_index
        else:
            self.integration_time_area.color_index = self.field_not_selected_color_index
        if self.lamp_choice_field_selected:
            self.lamp_choice_area.color_index = self.field_selected_color_index
        else:
            self.lamp_choice_area.color_index = self.field_not_selected_color_index
        if self.lamp_current_field_selected:
            self.lamp_current_area.color_index = self.field_selected_color_index
        else:
            self.lamp_current_area.color_index = self.field_not_selected_color_index

        if False:#instrument.button_pressed:
            print("button pressed")
            instrument.button_pressed = False

        '''


    def make_group( self ):
        self.group = displayio.Group()
        exposure_control_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240, x=0, y=0 )
        self.group.append( exposure_control_background )
        select_width = 4
        border_width = 2
        text_offset_x = 6
        text_offset_y = 14
        self.selection_list = []
        self.field_list = []

        ## sliders
        slider_select_y = 50
        slider_select_width = 62
        slider_select_height = 136
        slider_min_y = 174
        slider_border_width = slider_select_width - 2*select_width
        slider_width = 42
        shading_fraction = 1#0.3
        slider_shading_width = int(slider_width*shading_fraction)
        slider_shading_offset_x = int((slider_width - slider_shading_width)/2)
        slider_height = 8

        gain_slider_select_x = 4 + select_width
        gain_slider_select_y = slider_select_y
        gain_slider_select_width = slider_select_width
        gain_slider_select_height = slider_select_height
        self.gain_slider_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=gain_slider_select_width,
                                                    height=gain_slider_select_height, x=gain_slider_select_x, y=gain_slider_select_y )
        self.group.append( self.gain_slider_select )
        self.gain_slider_select.hidden = True

        gain_slider_border_width = slider_border_width
        gain_slider_border_height = gain_slider_select_height - 2*select_width
        gain_slider_border_x = gain_slider_select_x+select_width
        gain_slider_border_y = gain_slider_select_y+select_width
        gain_slider_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=gain_slider_border_width,
                                            height=gain_slider_border_height, x=gain_slider_border_x, y=gain_slider_border_y )
        self.group.append( gain_slider_border )

        gain_slider_area_width = gain_slider_border_width - 2*border_width
        gain_slider_area_height = gain_slider_border_height - 2*border_width
        gain_slider_area_x = gain_slider_border_x+border_width
        gain_slider_area_y = gain_slider_border_y+border_width
        gain_slider_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=gain_slider_area_width,
                                            height=gain_slider_area_height, x=gain_slider_area_x, y=gain_slider_area_y )
        self.group.append( gain_slider_area )

        gain_slider_width = slider_width
        gain_slider_height = slider_height
        gain_slider_x = gain_slider_border_x + 3* border_width
        gain_slider_y = slider_min_y
        self.gain_shading = vectorio.Rectangle( pixel_shader=self.palette, color_index = 19, width=slider_shading_width,
                                            height=1, x=gain_slider_x+slider_shading_offset_x, y=gain_slider_y )
        self.group.append( self.gain_shading )
        self.gain_slider = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=gain_slider_width,
                                            height=gain_slider_height, x=gain_slider_x, y=gain_slider_y )
        self.group.append( self.gain_slider )

        integration_slider_select_x = 86
        integration_slider_select_y = slider_select_y
        integration_slider_select_width = slider_select_width
        integration_slider_select_height = slider_select_height
        self.integration_slider_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=integration_slider_select_width,
                                                    height=integration_slider_select_height, x=integration_slider_select_x, y=integration_slider_select_y )
        self.group.append( self.integration_slider_select )
        self.integration_slider_select.hidden = True

        integration_slider_border_width = slider_border_width
        integration_slider_border_height = integration_slider_select_height - 2*select_width
        integration_slider_border_x = integration_slider_select_x+select_width
        integration_slider_border_y = integration_slider_select_y+select_width
        integration_slider_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=integration_slider_border_width,
                                            height=integration_slider_border_height, x=integration_slider_border_x, y=integration_slider_border_y )
        self.group.append( integration_slider_border )

        integration_slider_area_width = integration_slider_border_width - 2*border_width
        integration_slider_area_height = integration_slider_border_height - 2*border_width
        integration_slider_area_x = integration_slider_border_x+border_width
        integration_slider_area_y = integration_slider_border_y+border_width
        integration_slider_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=integration_slider_area_width,
                                            height=integration_slider_area_height, x=integration_slider_area_x, y=integration_slider_area_y )
        self.group.append( integration_slider_area )

        integration_slider_width = slider_width
        integration_slider_height = slider_height
        integration_slider_x = integration_slider_border_x + 3* border_width
        integration_slider_y = slider_min_y
        self.integration_time_shading = vectorio.Rectangle( pixel_shader=self.palette, color_index = 19, width=slider_shading_width,
                                            height=1, x=integration_slider_x+slider_shading_offset_x, y=integration_slider_y )
        self.group.append( self.integration_time_shading )
        self.integration_time_slider = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=integration_slider_width,
                                            height=integration_slider_height, x=integration_slider_x, y=integration_slider_y )
        self.group.append( self.integration_time_slider )

        lamp_current_slider_select_x = 164
        lamp_current_slider_select_y = slider_select_y
        lamp_current_slider_select_width = slider_select_width
        lamp_current_slider_select_height = slider_select_height

        self.lamp_current_slider_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=lamp_current_slider_select_width,
                                                    height=lamp_current_slider_select_height, x=lamp_current_slider_select_x, y=lamp_current_slider_select_y )
        self.group.append( self.lamp_current_slider_select )
        self.lamp_current_slider_select.hidden = True

        lamp_current_slider_border_width = slider_border_width
        lamp_current_slider_border_height = lamp_current_slider_select_height - 2*select_width
        lamp_current_slider_border_x = lamp_current_slider_select_x+select_width
        lamp_current_slider_border_y = lamp_current_slider_select_y+select_width
        lamp_current_slider_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=lamp_current_slider_border_width,
                                            height=lamp_current_slider_border_height, x=lamp_current_slider_border_x, y=lamp_current_slider_border_y )
        self.group.append( lamp_current_slider_border )

        lamp_current_slider_area_width = lamp_current_slider_border_width - 2*border_width
        lamp_current_slider_area_height = lamp_current_slider_border_height - 2*border_width
        lamp_current_slider_area_x = lamp_current_slider_border_x+border_width
        lamp_current_slider_area_y = lamp_current_slider_border_y+border_width
        lamp_current_slider_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=lamp_current_slider_area_width,
                                            height=lamp_current_slider_area_height, x=lamp_current_slider_area_x, y=lamp_current_slider_area_y )
        self.group.append( lamp_current_slider_area )

        lamp_current_slider_width = slider_width
        lamp_current_slider_height = slider_height
        lamp_current_slider_x = lamp_current_slider_border_x + 3* border_width
        lamp_current_slider_y = slider_min_y
        self.lamp_current_shading = vectorio.Rectangle( pixel_shader=self.palette, color_index = 19, width=slider_shading_width,
                                            height=1, x=lamp_current_slider_x+slider_shading_offset_x, y=lamp_current_slider_y )
        self.group.append( self.lamp_current_shading )
        lamp_current_slider = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=lamp_current_slider_width,
                                            height=lamp_current_slider_height, x=lamp_current_slider_x, y=lamp_current_slider_y )
        self.group.append( lamp_current_slider )

        exposure_bracket_border_width = slider_border_width+12
        exposure_bracket_border_height = gain_slider_select_height - 2*select_width
        exposure_bracket_border_x = 240
        exposure_bracket_border_y = gain_slider_border_y
        exposure_bracket_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=exposure_bracket_border_width,
                                            height=exposure_bracket_border_height, x=exposure_bracket_border_x, y=exposure_bracket_border_y )
        self.group.append( exposure_bracket_border )

        exposure_bracket_area_width = exposure_bracket_border_width - 2*border_width
        exposure_bracket_area_height = exposure_bracket_border_height - 2*border_width
        exposure_bracket_area_x = exposure_bracket_border_x+border_width
        exposure_bracket_area_y = exposure_bracket_border_y+border_width
        exposure_bracket_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=exposure_bracket_area_width,
                                            height=exposure_bracket_area_height, x=exposure_bracket_area_x, y=exposure_bracket_area_y )
        self.group.append( exposure_bracket_area )

        exposure_bracket_width = slider_width+12
        exposure_bracket_height = slider_height
        exposure_bracket_x = exposure_bracket_border_x + 3* border_width
        exposure_bracket_high_y = 174
        exposure_bracket_low_y = 174
        exposure_bracket_shading_height = 1
        self.exposure_bracket_shading = vectorio.Rectangle( pixel_shader=self.palette, color_index = 19, width=exposure_bracket_width,
                                            height=exposure_bracket_shading_height, x=exposure_bracket_x, y=exposure_bracket_low_y )
        self.group.append( self.exposure_bracket_shading )
        self.exposure_bracket_high = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=exposure_bracket_width,
                                            height=exposure_bracket_height, x=exposure_bracket_x, y=exposure_bracket_high_y )
        self.group.append( self.exposure_bracket_high )
        self.exposure_bracket_low = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=exposure_bracket_width,
                                            height=exposure_bracket_height, x=exposure_bracket_x, y=exposure_bracket_low_y )
        self.group.append( self.exposure_bracket_low )

        exposure_target_triangle_x = 306
        exposure_target_triangle_size = 10
        exposure_target_triangle_low_y = slider_min_y - 4
        exposure_target_triangle_high_y = exposure_target_triangle_low_y
        self.exposure_target_triangle_low = vectorio.Polygon(
                            pixel_shader=self.palette, color_index = 0, points = [(0, 0), (exposure_target_triangle_size,0),
                            (exposure_target_triangle_size,exposure_target_triangle_size)],
                            x=exposure_target_triangle_x, y=exposure_target_triangle_low_y )
        self.group.append( self.exposure_target_triangle_low )
        self.exposure_target_triangle_high = vectorio.Polygon(
                            pixel_shader=self.palette, color_index = 0, points = [(0, 0), (exposure_target_triangle_size,0),
                            (exposure_target_triangle_size,-exposure_target_triangle_size)],
                            x=exposure_target_triangle_x, y=exposure_target_triangle_high_y )
        self.group.append( self.exposure_target_triangle_high )

        ## top row
        top_row_y = 4
        return_select_x = 4
        return_select_y = top_row_y
        return_select_width = 40
        return_select_height = 40
        self.return_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = self.selection_color_index, width=return_select_width,
                                                    height=return_select_height, x=return_select_x, y=return_select_y )
        self.group.append( self.return_select )
        self.return_select.hidden = True
        self.selection_list.append(self.return_select)

        return_border_width = return_select_width - 2*select_width
        return_border_height = return_select_height - 2*select_width
        return_border_x = return_select_x+select_width
        return_border_y = return_select_y+select_width
        return_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=return_border_width,
                                            height=return_border_height, x=return_border_x, y=return_border_y )
        self.group.append( return_border )

        return_area_width = return_border_width - 2*border_width
        return_area_height = return_border_height - 2*border_width
        return_area_x = return_border_x+border_width
        return_area_y = return_border_y+border_width
        self.return_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=return_area_width,
                                            height=return_area_height, x=return_area_x, y=return_area_y ) #color_index = 19
        self.group.append( self.return_area )
        self.field_list.append( self.return_area )
        self.field_selected.append( False )

        return_triangle_x = return_border_x
        return_triangle_y = return_border_y
        return_triangle = vectorio.Polygon( pixel_shader=self.palette, color_index = 0, points = [(4, 16), (25,4), (25,28)], x=return_triangle_x, y=return_triangle_y )
        self.group.append( return_triangle )

        sensor_choice_select_x = return_select_x + return_select_width
        sensor_choice_select_y = top_row_y
        sensor_choice_select_width = 180
        sensor_choice_select_height = 40
        self.sensor_choice_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = self.selection_color_index, width=sensor_choice_select_width,
                                                    height=sensor_choice_select_height, x=sensor_choice_select_x, y=sensor_choice_select_y )
        self.group.append( self.sensor_choice_select )
        self.sensor_choice_select.hidden = True
        self.selection_list.append(self.sensor_choice_select)

        sensor_choice_border_width = sensor_choice_select_width - 2*select_width
        sensor_choice_border_height = sensor_choice_select_height - 2*select_width
        sensor_choice_border_x = sensor_choice_select_x+select_width
        sensor_choice_border_y = sensor_choice_select_y+select_width
        sensor_choice_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=sensor_choice_border_width,
                                            height=sensor_choice_border_height, x=sensor_choice_border_x, y=sensor_choice_border_y )
        self.group.append( sensor_choice_border )

        sensor_choice_area_width = sensor_choice_border_width - 2*border_width
        sensor_choice_area_height = sensor_choice_border_height - 2*border_width
        sensor_choice_area_x = sensor_choice_border_x+border_width
        sensor_choice_area_y = sensor_choice_border_y+border_width
        self.sensor_choice_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=sensor_choice_area_width,
                                            height=sensor_choice_area_height, x=sensor_choice_area_x, y=sensor_choice_area_y )
        self.group.append( self.sensor_choice_area )
        self.field_list.append( self.sensor_choice_area )
        self.field_selected.append( False )

        sensor_choice_text_x = sensor_choice_area_x+text_offset_x
        sensor_choice_text_y = sensor_choice_area_y+text_offset_y
        sensor_choice_text_group = displayio.Group(scale=2, x=sensor_choice_text_x, y=sensor_choice_text_y)
        sensor_choice_text = " -- "
        self.sensor_choice_text_area = label.Label(terminalio.FONT, text=sensor_choice_text, color=self.palette[0])
        sensor_choice_text_group.append(self.sensor_choice_text_area)
        self.group.append(sensor_choice_text_group)


        setting_select_x = sensor_choice_select_x + sensor_choice_select_width
        setting_select_y = top_row_y
        setting_select_width = 94
        setting_select_height = 40
        self.setting_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = self.selection_color_index, width=setting_select_width,
                                                    height=setting_select_height, x=setting_select_x, y=setting_select_y )
        self.group.append( self.setting_select )
        self.setting_select.hidden = True
        self.selection_list.append(self.setting_select)


        setting_border_width = setting_select_width - 2*select_width
        setting_border_height = setting_select_height - 2*select_width
        setting_border_x = setting_select_x+select_width
        setting_border_y = setting_select_y+select_width
        setting_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=setting_border_width,
                                            height=setting_border_height, x=setting_border_x, y=setting_border_y )
        self.group.append( setting_border )

        setting_area_width = setting_border_width - 2*border_width
        setting_area_height = setting_border_height - 2*border_width
        setting_area_x = setting_border_x+border_width
        setting_area_y = setting_border_y+border_width
        self.setting_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=setting_area_width,
                                            height=setting_area_height, x=setting_area_x, y=setting_area_y )
        self.group.append( self.setting_area )
        self.field_list.append( self.setting_area )
        self.field_selected.append( False )

        setting_text_x = setting_area_x+text_offset_x
        setting_text_y = setting_area_y+text_offset_y
        setting_text_group = displayio.Group(scale=2, x=setting_text_x, y=setting_text_y)
        setting_text = " -- "
        self.setting_text_area = label.Label(terminalio.FONT, text=setting_text, color=self.palette[0])
        setting_text_group.append(self.setting_text_area)
        self.group.append(setting_text_group)

        ## slider scale selector
        slider_scale_select_x = 106
        slider_scale_select_y = 35
        slider_scale_select_width = 100
        slider_scale_select_height = 24
        self.slider_scale_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = self.selection_color_index, width=slider_scale_select_width,
                                                    height=slider_scale_select_height, x=slider_scale_select_x, y=slider_scale_select_y )
        self.group.append( self.slider_scale_select )
        self.slider_scale_select.hidden = True
        self.selection_list.append(self.slider_scale_select)

        slider_scale_border_width = slider_scale_select_width - 2*select_width
        slider_scale_border_height = slider_scale_select_height - 2*select_width
        slider_scale_border_x = slider_scale_select_x+select_width
        slider_scale_border_y = slider_scale_select_y+select_width

        slider_scale_area_width = slider_scale_border_width - 2*border_width
        slider_scale_area_height = slider_scale_border_height - 2*border_width
        slider_scale_area_x = slider_scale_border_x+border_width
        slider_scale_area_y = slider_scale_border_y+border_width
        self.slider_scale_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=slider_scale_area_width,
                                            height=slider_scale_area_height, x=slider_scale_area_x, y=slider_scale_area_y )
        self.group.append( self.slider_scale_area )
        self.field_list.append( self.slider_scale_area )
        self.field_selected.append( False )
        #self.slider_scale_area.hidden = True


        slider_scale_text_x = slider_scale_area_x+text_offset_x
        slider_scale_text_y = slider_scale_area_y+6
        slider_scale_text_group = displayio.Group(scale=1, x=slider_scale_text_x, y=slider_scale_text_y)
        slider_scale_text = " -- "
        self.slider_scale_text_area = label.Label(terminalio.FONT, text=slider_scale_text, color=self.palette[0])
        slider_scale_text_group.append(self.slider_scale_text_area)
        self.group.append(slider_scale_text_group)

        ## bottom row
        gain_select_x = 4
        gain_select_y = 240-40-select_width
        gain_select_width = 70
        gain_select_height = 40
        self.gain_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = self.selection_color_index, width=gain_select_width,
                                                    height=gain_select_height, x=gain_select_x, y=gain_select_y )
        self.group.append( self.gain_select )
        self.gain_select.hidden = True
        self.selection_list.append(self.gain_select)

        gain_border_width = gain_select_width - 2*select_width
        gain_border_height = gain_select_height - 2*select_width
        gain_border_x = gain_select_x+select_width
        gain_border_y = gain_select_y+select_width
        gain_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=gain_border_width,
                                            height=gain_border_height, x=gain_border_x, y=gain_border_y )
        self.group.append( gain_border )

        gain_area_width = gain_border_width - 2*border_width
        gain_area_height = gain_border_height - 2*border_width
        gain_area_x = gain_border_x+border_width
        gain_area_y = gain_border_y+border_width
        self.gain_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=gain_area_width,
                                            height=gain_area_height, x=gain_area_x, y=gain_area_y )
        self.group.append( self.gain_area )
        self.field_list.append( self.gain_area )
        self.field_selected.append( False )

        gain_text_x = gain_area_x+text_offset_x
        gain_text_y = gain_area_y+text_offset_y
        gain_text_group = displayio.Group(scale=2, x=gain_text_x, y=gain_text_y)
        gain_text = " -- "
        self.gain_text_area = label.Label(terminalio.FONT, text=gain_text, color=self.palette[0])
        gain_text_group.append(self.gain_text_area)
        self.group.append(gain_text_group)

        integration_time_select_x = gain_select_x + gain_select_width
        integration_time_select_y = 240-40-select_width
        integration_time_select_width = 84
        integration_time_select_height = 40
        self.integration_time_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = self.selection_color_index, width=integration_time_select_width,
                                                    height=integration_time_select_height, x=integration_time_select_x, y=integration_time_select_y )
        self.group.append( self.integration_time_select )
        self.integration_time_select.hidden = True
        self.selection_list.append(self.integration_time_select)


        integration_time_border_width = integration_time_select_width - 2*select_width
        integration_time_border_height = integration_time_select_height - 2*select_width
        integration_time_border_x = integration_time_select_x+select_width
        integration_time_border_y = integration_time_select_y+select_width
        integration_time_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=integration_time_border_width,
                                            height=integration_time_border_height, x=integration_time_border_x, y=integration_time_border_y )
        self.group.append( integration_time_border )

        integration_time_area_width = integration_time_border_width - 2*border_width
        integration_time_area_height = integration_time_border_height - 2*border_width
        integration_time_area_x = integration_time_border_x+border_width
        integration_time_area_y = integration_time_border_y+border_width
        self.integration_time_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=integration_time_area_width,
                                            height=integration_time_area_height, x=integration_time_area_x, y=integration_time_area_y )
        self.group.append( self.integration_time_area )
        self.field_list.append( self.integration_time_area )
        self.field_selected.append( False )

        integration_time_text_x = integration_time_area_x+text_offset_x
        integration_time_text_y = integration_time_area_y+text_offset_y
        integration_time_text_group = displayio.Group(scale=2, x=integration_time_text_x, y=integration_time_text_y)
        integration_time_text = " -- "
        self.integration_time_text_area = label.Label(terminalio.FONT, text=integration_time_text, color=self.palette[0])
        integration_time_text_group.append(self.integration_time_text_area)
        self.group.append(integration_time_text_group)

        lamp_current_select_x = integration_time_select_x + integration_time_select_width
        lamp_current_select_y = 240-40-select_width
        lamp_current_select_width = 70
        lamp_current_select_height = 40
        self.lamp_current_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = self.selection_color_index, width=lamp_current_select_width,
                                                    height=lamp_current_select_height, x=lamp_current_select_x, y=lamp_current_select_y )
        self.group.append( self.lamp_current_select )
        self.lamp_current_select.hidden = True
        self.selection_list.append(self.lamp_current_select)

        lamp_current_border_width = lamp_current_select_width - 2*select_width
        lamp_current_border_height = lamp_current_select_height - 2*select_width
        lamp_current_border_x = lamp_current_select_x+select_width
        lamp_current_border_y = lamp_current_select_y+select_width
        lamp_current_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=lamp_current_border_width,
                                            height=lamp_current_border_height, x=lamp_current_border_x, y=lamp_current_border_y )
        self.group.append( lamp_current_border )

        lamp_current_area_width = lamp_current_border_width - 2*border_width
        lamp_current_area_height = lamp_current_border_height - 2*border_width
        lamp_current_area_x = lamp_current_border_x+border_width
        lamp_current_area_y = lamp_current_border_y+border_width
        self.lamp_current_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=lamp_current_area_width,
                                            height=lamp_current_area_height, x=lamp_current_area_x, y=lamp_current_area_y )
        self.group.append( self.lamp_current_area )
        self.field_list.append( self.lamp_current_area )
        self.field_selected.append( False )

        lamp_current_text_x = lamp_current_area_x+text_offset_x
        lamp_current_text_y = lamp_current_area_y+text_offset_y
        lamp_current_text_group = displayio.Group(scale=2, x=lamp_current_text_x, y=lamp_current_text_y)
        lamp_current_text = " -- "
        self.lamp_current_text_area = label.Label(terminalio.FONT, text=lamp_current_text, color=self.palette[0])
        lamp_current_text_group.append(self.lamp_current_text_area)
        self.group.append(lamp_current_text_group)

        exposure_maximum_select_x = lamp_current_select_x + lamp_current_select_width + select_width
        exposure_maximum_select_y = 240-40-select_width
        exposure_maximum_select_width = 84
        exposure_maximum_select_height = 40
        self.exposure_maximum_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=exposure_maximum_select_width,
                                                    height=exposure_maximum_select_height, x=exposure_maximum_select_x, y=exposure_maximum_select_y )
        self.group.append( self.exposure_maximum_select )
        self.exposure_maximum_select.hidden = True
        #self.selection_list.append(self.exposure_maximum_select)

        exposure_maximum_border_width = exposure_maximum_select_width - 2*select_width
        exposure_maximum_border_height = exposure_maximum_select_height - 2*select_width
        exposure_maximum_border_x = exposure_maximum_select_x+select_width
        exposure_maximum_border_y = exposure_maximum_select_y+select_width
        exposure_maximum_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=exposure_maximum_border_width,
                                            height=exposure_maximum_border_height, x=exposure_maximum_border_x, y=exposure_maximum_border_y )
        self.group.append( exposure_maximum_border )

        exposure_maximum_area_width = exposure_maximum_border_width - 2*border_width
        exposure_maximum_area_height = exposure_maximum_border_height - 2*border_width
        exposure_maximum_area_x = exposure_maximum_border_x+border_width
        exposure_maximum_area_y = exposure_maximum_border_y+border_width
        exposure_maximum_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=exposure_maximum_area_width,
                                            height=exposure_maximum_area_height, x=exposure_maximum_area_x, y=exposure_maximum_area_y )
        self.group.append( exposure_maximum_area )
        exposure_maximum_text_x = exposure_maximum_area_x+text_offset_x
        exposure_maximum_text_y = exposure_maximum_area_y+text_offset_y
        exposure_maximum_text_group = displayio.Group(scale=2, x=exposure_maximum_text_x, y=exposure_maximum_text_y)
        exposure_maximum_text = " -- " #65535
        self.exposure_maximum_text_area = label.Label(terminalio.FONT, text=exposure_maximum_text, color=self.palette[0])
        exposure_maximum_text_group.append(self.exposure_maximum_text_area)
        self.group.append(exposure_maximum_text_group)

        ## bottom row titles
        label_bar_width = 320
        label_bar_height = 18
        label_bar_x = 0
        label_bar_y = exposure_maximum_select_y - label_bar_height + select_width
        label_bar = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=label_bar_width,
                                            height=label_bar_height, x=label_bar_x, y=label_bar_y )
        self.group.append( label_bar )

        value_label_text_x = 12 +14
        value_label_text_y = gain_area_y - 10
        value_label_text_group = displayio.Group(scale=1, x=value_label_text_x, y=value_label_text_y)
        value_label_text = "Gain"
        value_label_text_area = label.Label(terminalio.FONT, text=value_label_text, color=self.palette[0])
        value_label_text_group.append(value_label_text_area)
        self.group.append(value_label_text_group)

        value_label_text_x = 80
        value_label_text_y = gain_area_y - 10
        value_label_text_group = displayio.Group(scale=1, x=value_label_text_x, y=value_label_text_y)
        value_label_text = "Integ time ms"
        value_label_text_area = label.Label(terminalio.FONT, text=value_label_text, color=self.palette[0])
        value_label_text_group.append(value_label_text_area)
        self.group.append(value_label_text_group)

        ## Lamp select area
        lamp_choice_select_x = 162
        lamp_choice_select_y = gain_area_y - 22
        lamp_choice_select_width = 66
        lamp_choice_select_height = 26
        self.lamp_choice_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = self.selection_color_index, width=lamp_choice_select_width,
                                                    height=lamp_choice_select_height, x=lamp_choice_select_x, y=lamp_choice_select_y )
        self.group.append( self.lamp_choice_select )
        self.lamp_choice_select.hidden = True
        self.selection_list.append(self.lamp_choice_select)

        lamp_choice_border_width = lamp_choice_select_width - 2*select_width
        lamp_choice_border_height = lamp_choice_select_height - 2*select_width
        lamp_choice_border_x = lamp_choice_select_x+select_width
        lamp_choice_border_y = lamp_choice_select_y+select_width
        if False:
            lamp_choice_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=lamp_choice_border_width,
                                            height=lamp_choice_border_height, x=lamp_choice_border_x, y=lamp_choice_border_y )
            self.group.append( lamp_choice_border )

        lamp_choice_area_width = lamp_choice_border_width - 2*border_width
        lamp_choice_area_height = lamp_choice_border_height - 2*border_width
        lamp_choice_area_x = lamp_choice_border_x+border_width
        lamp_choice_area_y = lamp_choice_border_y+border_width
        self.lamp_choice_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=lamp_choice_area_width,
                                            height=lamp_choice_area_height, x=lamp_choice_area_x, y=lamp_choice_area_y )
        self.group.append( self.lamp_choice_area )
        self.field_list.append( self.lamp_choice_area )
        self.field_selected.append( False )

        value_label_text_x = 166+8
        value_label_text_y = gain_area_y - 10
        value_label_text_group = displayio.Group(scale=1, x=value_label_text_x, y=value_label_text_y)
        value_label_text = "Lamp mA"
        self.value_label_text_area = label.Label(terminalio.FONT, text=value_label_text, color=self.palette[0])
        value_label_text_group.append(self.value_label_text_area)
        self.group.append(value_label_text_group)

        exposure_label_text_x = 240
        exposure_label_text_y = gain_area_y - 10
        exposure_label_text_group = displayio.Group(scale=1, x=exposure_label_text_x, y=value_label_text_y)
        exposure_label_text = "Exposure Max"
        self.exposure_label_text_area = label.Label(terminalio.FONT, text=exposure_label_text, color=self.palette[0])
        exposure_label_text_group.append(self.exposure_label_text_area)
        self.group.append(exposure_label_text_group)

        return self.group

def make_exposure_control_page( instrument ):
    page = Exposure_Control_Page( instrument )
    group = page.make_group()
    #page.hide()
    instrument.main_display_group.append( group )
    return page


#### begin instrument class definition

class Instrument:
    def __init__( self, i2c_bus, spi_bus, uart_bus, UID, buzzer):
        self.i2c_bus = i2c_bus
        self.uart_bus = uart_bus
        self.device_type = DEVICE_TYPE
        self.uid = UID
        self.buzzer = buzzer
        #self.usb_serial_out_enabled = usb_serial_out_enabled
        #self.sample_interval_s = preset_sample_interval_s
        #self.burst_count = preset_burst_count
        #self.usb_serial_out_enabled = usb_serial_out_enabled
        self.pages_list = []
        self.palette = make_palette()
        self.main_display_group = initialize_display( spi_bus )
        self.welcome_page = make_welcome_page( self )
        #self.hardware_clock = initialize_hardware_clock( i2c_bus )
        #self.hardware_clock.report()
        #self.hardware_clock.sync_system_clock()
        #self.clock_battery_ok_text =  "clock battery OK: {}".format( self.hardware_clock.battery_ok() )
        #self.welcome_page.announce( self.clock_battery_ok_text )
        #self.datestamp = self.hardware_clock.get_datestamp_now()
        #self.last_datestamp = self.datestamp
        #self.iso_time = self.hardware_clock.get_iso_time_now()
        #self.batch_number = update_batch(self.datestamp)
        #print( "batch number = {}".format( self.batch_number ))
        self.filename = None
        self.sensors_present = []
        self.spectral_sensors_present = []
        self.spectrometry = spectral_sensors_detected
        #self.record = record_on_startup
        #self.session_tag = "{}-{}-session-".format(self.uid, self.iso_time)
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

def initialize_uart( txpin, rxpin ):
    try:
        uart = busio.UART(txpin, rxpin, baudrate=9600, timeout=10)
        print( "uart bus initialized" )
    except:
        uart = False
    return uart

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

def memory_check( message ):
    gc.collect()
    mem_free_kB = gc.mem_free()/1000
    print( "{} memory free: {} kB, {} %".format( message, int(mem_free_kB), int((100* (mem_free_kB)/start_mem_free_kB ))))

def stall():
    print("intentionally stalled, press return to continue")
    input_string = False
    while input_string == False:
        input_string = input().strip()

main()
