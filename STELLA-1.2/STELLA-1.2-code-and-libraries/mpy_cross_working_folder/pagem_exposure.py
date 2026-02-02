# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import displayio
from adafruit_display_text import label
import vectorio
import terminalio
from .classm_page import Page
import math

class Exposure_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.instrument = instrument
        self.palette = self.instrument.palette
        self.page_name = "Exposure"
        self.selection_color_index = 6
        self.field_selected_color_index = 5
        self.field_not_selected_color_index = 9
        self.field_selected = []
        self.slider_max_y = 54
        self.slider_min_y = 174
        self.slider_pixel_span = self.slider_min_y - self.slider_max_y
        self.setting_modes = [ "Manual", "Auto" ]#, "Sunny", "Cloudy", "Indoor", "Dark", "Save" ] #append to this list when configurations are saved
        self.setting_mode = 0
        self.last_setting_mode = 0
        self.auto_exposure_engaged = False
        self.scale_choices = "linear scale", "log scale"
        self.scale_choice = 1
        self.selection = 0
        self.last_selection = -1
        self.selection_count = 1
        self.field_selected = False
        self.field_selected_list = []
        self.spectral_sensors = self.instrument.spectral_sensors_present
        self.active_sensor_index = 0
        self.exposure_max_value = 65535
        self.exposure_target_fraction_high = 0.9
        self.exposure_target_fraction_low = 0.5
        self.number_of_sensors = len( self.spectral_sensors )
        self.gain_index = []
        for sensor_index in range (0, self.number_of_sensors):
            self.gain_index.append( self.spectral_sensors[sensor_index].gain_index )
        self.integration_time_index = []
        for sensor_index in range (0, self.number_of_sensors):
            self.integration_time_index.append( self.spectral_sensors[sensor_index].integration_time_index )
        self.lamp_current_mA_index = []
        for sensor_index in range (0, self.number_of_sensors):
            self.lamp_current_mA_index.append( 0 )
        self.lamp_selection_index = 0
        self.selection_rectangles = []
        self.no_lamp = False
        self.last_no_lamp = False

    def update_selection( self ):
        if self.spectral_sensors[self.active_sensor_index].lamp_selection_list is None:
            self.no_lamp = True
        else:
            self.no_lamp = False
        if self.no_lamp:
            if self.last_selection == 5 and self.selection == 6:
                self.selection = 0

            if self.last_selection == 0 and self.selection == 7:
                self.selection = 5
        if self.setting_mode != 0:
            if self.no_lamp:
                if self.last_selection == 3 and self.selection == 4:
                    self.selection = 0
                if self.last_selection == 0 and self.selection == 7:
                    self.selection = 3
            else:
                if self.last_selection == 3 and self.selection == 4:
                    self.selection = 6
                if self.last_selection == 6 and self.selection == 5:
                    self.selection = 3
        self.selection_rectangles[self.last_selection].hidden = True
        self.selection_rectangles[self.selection].hidden = False

    def action( self ):
        if self.instrument.encoder_increment != 0:
            if self.field_selected:
                if self.selection == 1:
                    self.active_sensor_index = ( self.active_sensor_index + self.instrument.encoder_increment ) % self.number_of_sensors
                elif self.selection == 2:
                    self.last_setting_mode = self.setting_mode
                    self.setting_mode = ( self.setting_mode + self.instrument.encoder_increment) % len( self.setting_modes )
                elif self.selection == 3:
                    self.scale_choice = ( self.scale_choice + self.instrument.encoder_increment ) % len( self.scale_choices )
                elif self.selection == 4:
                    if self.setting_mode == 0:
                        self.gain_index[self.active_sensor_index] = (self.gain_index[self.active_sensor_index] + self.instrument.encoder_increment )
                        if self.gain_index[self.active_sensor_index] < 0:
                            self.gain_index[self.active_sensor_index] = 0
                        if self.gain_index[self.active_sensor_index] > len(self.spectral_sensors[self.active_sensor_index].gain_list) - 1:
                            self.gain_index[self.active_sensor_index] = len(self.spectral_sensors[self.active_sensor_index].gain_list) - 1
                        self.spectral_sensors[self.active_sensor_index].set_gain( self.gain_index[self.active_sensor_index])
                elif self.selection == 5:
                    if self.setting_mode == 0:
                        self.integration_time_index[self.active_sensor_index] = (self.integration_time_index[self.active_sensor_index] + self.instrument.encoder_increment )
                        if self.integration_time_index[self.active_sensor_index] < 0 :
                            self.integration_time_index[self.active_sensor_index] = 0
                        if self.integration_time_index[self.active_sensor_index] > len(self.spectral_sensors[self.active_sensor_index].integration_time_ms_list ) -1:
                            self.integration_time_index[self.active_sensor_index] = len(self.spectral_sensors[self.active_sensor_index].integration_time_ms_list ) -1
                        self.spectral_sensors[self.active_sensor_index].set_integration_time( self.integration_time_index[self.active_sensor_index])
                elif self.selection == 6:
                    try:
                        if len( self.spectral_sensors[self.active_sensor_index].lamp_selection_list ) < 2:
                            number_of_current_states = len( self.spectral_sensors[self.active_sensor_index].lamp_current_mA_list )
                        else:
                            number_of_current_states = len( self.spectral_sensors[self.active_sensor_index].lamp_current_mA_list[ self.lamp_selection_index ])
                        self.lamp_current_mA_index[self.active_sensor_index] = ( self.lamp_current_mA_index[self.active_sensor_index] + self.instrument.encoder_increment )
                        if self.lamp_current_mA_index[self.active_sensor_index] < 0:
                            self.lamp_current_mA_index[self.active_sensor_index] = 0
                        if self.lamp_current_mA_index[self.active_sensor_index] > number_of_current_states - 1:
                            self.lamp_current_mA_index[self.active_sensor_index] = number_of_current_states - 1
                        self.spectral_sensors[self.active_sensor_index].set_lamp_current_mA( self.lamp_current_mA_index[self.active_sensor_index], self.lamp_selection_index )
                        hide_limit = True


                        if len( self.spectral_sensors[self.active_sensor_index].lamp_selection_list ) < 2:
                            if self.lamp_current_mA_index[self.active_sensor_index] == ( len( self.spectral_sensors[self.active_sensor_index].lamp_current_mA_list) - 1) :
                                hide_limit = False
                        else:
                            if self.lamp_current_mA_index[self.active_sensor_index] == ( len( self.spectral_sensors[self.active_sensor_index].lamp_current_mA_list[self.lamp_selection_index] ) - 1) :
                                hide_limit = False
                        if hide_limit:
                            self.current_limit_text_area.hidden = True
                        else:
                            self.current_limit_text_area.hidden = False
                    except Exception as err:
                        print( "current out of range, reduce value ", err )

                elif self.selection == 7:
                    if self.spectral_sensors[self.active_sensor_index].lamp_selection_list is not None:
                        #self.last_lamp_selection_index = self.lamp_selection_index
                        self.lamp_selection_index = ( self.lamp_selection_index + self.instrument.encoder_increment ) % len(
                                self.spectral_sensors[self.active_sensor_index].lamp_selection_list )


            self.instrument.encoder_increment = 0

        if self.instrument.button_pressed:
            if self.selection == 0:
                self.instrument.active_page_number = self.instrument.pages_dict["Light"]
            else:
                self.field_selected = not self.field_selected
                if self.selection == 1:
                    if self.field_selected:
                        self.sensor_choice_area.color_index = self.field_selected_color_index
                    else:
                        self.sensor_choice_area.color_index = self.field_not_selected_color_index
                if self.selection == 2:
                    if self.field_selected:
                        self.setting_area.color_index = self.field_selected_color_index
                    else:
                        self.setting_area.color_index = self.field_not_selected_color_index
                if self.selection == 3:
                    if self.field_selected:
                        self.slider_scale_area.color_index = self.field_selected_color_index
                    else:
                        self.slider_scale_area.color_index = self.field_not_selected_color_index
                if self.selection == 4:
                    if self.field_selected:
                        if self.setting_mode != 0:
                            self.gain_area.color_index = 19
                        else:
                            self.gain_area.color_index = self.field_selected_color_index
                    else:
                        self.gain_area.color_index = self.field_not_selected_color_index
                if self.selection == 5:
                    if self.field_selected:
                        if self.setting_mode != 0:
                            self.integration_time_area.color_index = 19
                        else:
                            self.integration_time_area.color_index = self.field_selected_color_index
                    else:
                        self.integration_time_area.color_index = self.field_not_selected_color_index
                if self.selection == 6:
                    if self.field_selected:
                        self.lamp_current_area.color_index = self.field_selected_color_index
                    else:
                        self.lamp_current_area.color_index = self.field_not_selected_color_index
                if self.selection == 7:
                    if self.field_selected:
                        self.lamp_choice_area.color_index = self.field_selected_color_index
                    else:
                        self.lamp_choice_area.color_index = self.field_not_selected_color_index
            self.instrument.button_pressed = False
        if self.setting_mode == 0 and (self.selection == 4 or self.selection ==5 ) :
           pass
        else:
            self.update_values()

    def update_values( self ):
        greyed_out = 19
        if self.setting_mode != 0:
            self.gain_area.color_index = greyed_out
            self.integration_time_area.color_index = greyed_out
        elif self.last_setting_mode != self.setting_mode:
            self.gain_area.color_index = self.field_not_selected_color_index
            self.integration_time_area.color_index = self.field_not_selected_color_index

        if self.no_lamp:
            self.lamp_current_area.color_index = greyed_out
            self.last_no_lamp = True
        elif ( not self.no_lamp ) and self.last_no_lamp:
            self.lamp_current_area.color_index = self.field_not_selected_color_index
            self.last_no_lamp = False

        if self.selection == 3:
            self.slider_scale_area.hidden = False
        else:
            self.slider_scale_area.hidden = True

        self.sensor_choice_text_area.text = self.spectral_sensors[self.active_sensor_index].choice_label
        self.setting_text_area.text = self.setting_modes[self.setting_mode]
        self.slider_scale_text_area.text = self.scale_choices[ self.scale_choice ]
        if self.spectral_sensors[self.active_sensor_index].lamp_selection_list is None:
            self.lamp_choice_text_area.text = "No Lamp"
        else:
            self.lamp_choice_text_area.text = self.spectral_sensors[self.active_sensor_index].lamp_selection_list[ self.lamp_selection_index ]

        if False:
            if self.setting_mode != 0:
                self.gain_area.color_index = 19
                self.integration_time_area.color_index = 19
            else:
                if not self.field_selected_list[4]:
                    self.gain_area.color_index = 9
                if not self.field_selected_list[5]:
                    self.integration_time_area.color_index = 9
        ## get exposure and drive slider, value, label, brackets
        #self.spectral_sensors[self.active_sensor_index].read_counts_all()
        exposure_high, exposure_low = self.spectral_sensors[self.active_sensor_index].get_max_min_counts()
        gain = self.spectral_sensors[self.active_sensor_index].gain_list[ self.gain_index[self.active_sensor_index] ]
        max_gain = max(self.spectral_sensors[self.active_sensor_index].gain_list)
        min_gain = min(self.spectral_sensors[self.active_sensor_index].gain_list)
        integration_time_ms = self.spectral_sensors[self.active_sensor_index].integration_time_ms_list[ self.integration_time_index[self.active_sensor_index] ]
        max_integration_time_ms = max(self.spectral_sensors[self.active_sensor_index].integration_time_ms_list)
        min_integration_time_ms = min(self.spectral_sensors[self.active_sensor_index].integration_time_ms_list)

        ### autoexposure control
        if self.setting_mode == 1:
            if exposure_high > 0:
                target_multiplier = (self.exposure_target_fraction_high * self.exposure_max_value)/exposure_high
            else:
                target_multiplier = 1
            gain_integration_time_product = gain * integration_time_ms
            max_gain_integration_time_product = max_gain * max_integration_time_ms
            if target_multiplier * gain_integration_time_product > max_gain_integration_time_product:
                # if target exposure is unreachable, set both to their maximum values
                self.gain_index[self.active_sensor_index] = len( self.spectral_sensors[self.active_sensor_index].gain_list ) - 1
                self.spectral_sensors[self.active_sensor_index].set_gain( self.gain_index[self.active_sensor_index])
                self.integration_time_index[self.active_sensor_index] = len( self.spectral_sensors[self.active_sensor_index].integration_time_ms_list ) - 1
                self.spectral_sensors[self.active_sensor_index].set_integration_time( self.integration_time_index[self.active_sensor_index])
            elif exposure_high > (self.exposure_max_value - 1):
                #drop the gain by 1, drop the integration time by 4
                self.gain_index[self.active_sensor_index] = self.gain_index[self.active_sensor_index] - 1
                if self.gain_index[self.active_sensor_index] < 0: self.gain_index[self.active_sensor_index] = 0
                self.spectral_sensors[self.active_sensor_index].set_gain( self.gain_index[self.active_sensor_index])
                self.integration_time_index[self.active_sensor_index] = self.integration_time_index[self.active_sensor_index] - 4
                if self.integration_time_index[self.active_sensor_index] < 0: self.integration_time_index[self.active_sensor_index] = 0
                self.spectral_sensors[self.active_sensor_index].set_integration_time( self.integration_time_index[self.active_sensor_index])
            elif exposure_high > (self.exposure_target_fraction_high * self.exposure_max_value):
                #drop the integration time by 1
                self.integration_time_index[self.active_sensor_index] = self.integration_time_index[self.active_sensor_index] - 1
                if self.integration_time_index[self.active_sensor_index] < 0: self.integration_time_index[self.active_sensor_index] = 0
                self.spectral_sensors[self.active_sensor_index].set_integration_time( self.integration_time_index[self.active_sensor_index])
            elif exposure_high < (self.exposure_target_fraction_low * self.exposure_max_value):
                #raise the gain by 1 and the integration time by 4
                self.gain_index[self.active_sensor_index] = self.gain_index[self.active_sensor_index] + 1
                if self.gain_index[self.active_sensor_index] > len( self.spectral_sensors[self.active_sensor_index].gain_list ) - 1:
                    self.gain_index[self.active_sensor_index] = len( self.spectral_sensors[self.active_sensor_index].gain_list ) -1
                self.spectral_sensors[self.active_sensor_index].set_gain( self.gain_index[self.active_sensor_index])
                self.integration_time_index[self.active_sensor_index] = self.integration_time_index[self.active_sensor_index] + 4
                if self.integration_time_index[self.active_sensor_index] > len( self.spectral_sensors[self.active_sensor_index].integration_time_ms_list ) -1:
                    self.integration_time_index[self.active_sensor_index] = len( self.spectral_sensors[self.active_sensor_index].integration_time_ms_list ) -1
                self.spectral_sensors[self.active_sensor_index].set_integration_time( self.integration_time_index[self.active_sensor_index])


        dr_percentage = round(100*exposure_high/self.exposure_max_value,1)
        if dr_percentage >9.9:
            dr_percentage = int(dr_percentage)
        self.dr_text_area.text = "{}% DR".format(dr_percentage)

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

        ## read and display gain
        self.gain_text_area.text = str( gain )
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

        ## read and display integration_time
        if integration_time_ms < 1000:
            self.integration_time_text_area.text = str( integration_time_ms )
        else:
            self.integration_time_text_area.text = "{}s".format( round( integration_time_ms/1000, 1))
        integration_time_value_span = max_integration_time_ms - min_integration_time_ms
        if self.scale_choice == 1:
            if integration_time_ms > 0:
                integration_time_ms = math.log(integration_time_ms,10)
            else:
                integration_time_ms = 0
            if max_integration_time_ms > 0:
                max_integration_time_ms = math.log(max_integration_time_ms,10)
            else:
                max_integration_time_ms = 0
            if min_integration_time_ms > 0:
                min_integration_time_ms = math.log(min_integration_time_ms,10)
            else:
                min_integration_time_ms = 0
            if integration_time_value_span > 0:
                integration_time_value_span = math.log(integration_time_value_span,10)
            else:
                integration_time_value_span = 0
        integration_time_per_pixel = integration_time_value_span/self.slider_pixel_span
        if integration_time_ms == min_integration_time_ms:
            integration_time_pixel_offset = 0
        else:
            integration_time_pixel_offset = int( integration_time_ms / integration_time_per_pixel )
        self.integration_time_slider.y = self.slider_min_y - integration_time_pixel_offset
        self.integration_time_shading.y = self.integration_time_slider.y
        self.integration_time_shading.height = self.slider_min_y + 6 - self.integration_time_shading.y

        ## read and display lamp current
        if self.spectral_sensors[self.active_sensor_index].lamp_selection_list is not None:
            try:
                if len( self.spectral_sensors[self.active_sensor_index].lamp_selection_list ) < 2:
                    lamp_current_mA = self.spectral_sensors[self.active_sensor_index].lamp_current_mA_list[ self.lamp_current_mA_index[self.active_sensor_index] ]
                else:
                    lamp_current_mA = self.spectral_sensors[self.active_sensor_index].lamp_current_mA_list[ self.lamp_selection_index ][ self.lamp_current_mA_index[self.active_sensor_index] ]
                if lamp_current_mA > 90:
                    self.current_limit_text_area.hidden = True
                self.lamp_current_text_area.text = str( lamp_current_mA )
                max_lamp_current_mA = 100 #max(self.spectral_sensors[self.active_sensor_index].lamp_current_mA_list)
                min_lamp_current_mA = 0#min(self.spectral_sensors[self.active_sensor_index].lamp_current_mA_list[ self.lamp_selection_index ])
                lamp_current_mA_value_span = max_lamp_current_mA - min_lamp_current_mA
                if self.scale_choice == 1: #"log"
                    if lamp_current_mA > 0:
                        lamp_current_mA = math.log(lamp_current_mA,10)
                    else:
                        lamp_current_mA = 0
                    if max_lamp_current_mA > 0:
                        max_lamp_current_mA = math.log(max_lamp_current_mA,10)
                    else:
                        max_lamp_current_mA = 0
                    if min_lamp_current_mA > 0:
                        min_lamp_current_mA = math.log(min_lamp_current_mA,10)
                    else:
                        min_lamp_current_mA = 0
                    if lamp_current_mA_value_span > 0:
                        lamp_current_mA_value_span = math.log(lamp_current_mA_value_span,10)
                    else:
                        lamp_current_mA_value_span = 0
                lamp_current_mA_per_pixel = lamp_current_mA_value_span/self.slider_pixel_span
                self.lamp_current_slider.y = self.slider_min_y - int( lamp_current_mA / lamp_current_mA_per_pixel )
                self.lamp_current_shading.y = self.lamp_current_slider.y
                self.lamp_current_shading.height = self.slider_min_y + 6 - self.lamp_current_shading.y
            except Exception as err:
                print( "selected current is out of range for that lamp. select a different value ", err )

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
        self.lamp_current_slider = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=lamp_current_slider_width,
                                            height=lamp_current_slider_height, x=lamp_current_slider_x, y=lamp_current_slider_y )
        self.group.append( self.lamp_current_slider )

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
        self.return_select.hidden = False#True
        self.selection_rectangles.append( self.return_select)

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
        self.field_selected_list.append( False )

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
        self.selection_rectangles.append( self.sensor_choice_select )

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
        self.field_selected_list.append( False )

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
        self.selection_rectangles.append( self.setting_select )


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
        self.field_selected_list.append( False )

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
        self.selection_rectangles.append( self.slider_scale_select )

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
        self.field_selected_list.append( False )
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
        self.selection_rectangles.append( self.gain_select )

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
        self.field_selected_list.append( False )

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
        self.selection_rectangles.append( self.integration_time_select )


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
        self.field_selected_list.append( False )

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
        self.selection_rectangles.append( self.lamp_current_select )

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
        self.field_selected_list.append( False )

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
        value_label_text_group = displayio.Group(scale=1, x=value_label_text_x, y=value_label_text_y)
        value_label_text = "Integ time ms"
        value_label_text_area = label.Label(terminalio.FONT, text=value_label_text, color=self.palette[0])
        value_label_text_group.append(value_label_text_area)
        self.group.append(value_label_text_group)

        dr_text_x = 250
        dr_text_group = displayio.Group(scale=1, x=dr_text_x, y=value_label_text_y)
        dr_text = "--% DR"
        self.dr_text_area = label.Label(terminalio.FONT, text=dr_text, color=self.palette[0])
        dr_text_group.append(self.dr_text_area)
        self.group.append(dr_text_group)


        ## Lamp select area
        lamp_choice_select_x = 162
        lamp_choice_select_y = gain_area_y - 22
        lamp_choice_select_width = 66
        lamp_choice_select_height = 26
        self.lamp_choice_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = self.selection_color_index, width=lamp_choice_select_width,
                                                    height=lamp_choice_select_height, x=lamp_choice_select_x, y=lamp_choice_select_y )
        self.group.append( self.lamp_choice_select )
        self.lamp_choice_select.hidden = True
        self.selection_rectangles.append( self.lamp_choice_select )

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
        self.field_selected_list.append( False )

        lamp_choice_text_x = 166+6
        lamp_choice_text_y = gain_area_y - 10
        lamp_choice_text_group = displayio.Group(scale=1, x=lamp_choice_text_x, y=lamp_choice_text_y)
        lamp_choice_text = "Lamp mA"
        self.lamp_choice_text_area = label.Label(terminalio.FONT, text=lamp_choice_text, color=self.palette[0])
        lamp_choice_text_group.append(self.lamp_choice_text_area)
        self.group.append(lamp_choice_text_group)

        current_limit_text_x = lamp_choice_text_x + 8
        current_limit_text_y = 64
        current_limit_text_group = displayio.Group(scale=1, x=current_limit_text_x, y=current_limit_text_y)
        current_limit_text = "LIMIT"
        self.current_limit_text_area = label.Label(terminalio.FONT, text=current_limit_text, color=self.palette[0])
        current_limit_text_group.append(self.current_limit_text_area)
        self.group.append(current_limit_text_group)
        self.current_limit_text_area.hidden = True

        exposure_label_text_x = 240
        exposure_label_text_y = gain_area_y - 10
        exposure_label_text_group = displayio.Group(scale=1, x=exposure_label_text_x, y=value_label_text_y)
        exposure_label_text = "Exposure Max"
        self.exposure_label_text_area = label.Label(terminalio.FONT, text=exposure_label_text, color=self.palette[0])
        exposure_label_text_group.append(self.exposure_label_text_area)
        self.group.append(exposure_label_text_group)
        self.exposure_label_text_area.hidden = True
        self.selection_count = len( self.selection_rectangles )
        return self.group



def make_exposure_page( instrument ):
    page = Exposure_Page( instrument )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page
