# remote sensing page module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import displayio
from adafruit_display_text import label
import vectorio
import terminalio
from .classm_page import Page

class Remote_Sensing_Page( Page ):
    def __init__( self, instrument, spectral_register):#, hdc3022_air_sensor, mlx90614_surface_thermometer ):#, lv_ez_mb1013_rangefinder ):
        super().__init__()
        self.page_name = "Remote"
        self.instrument = instrument
        self.palette = instrument.palette
        self.spectral_register = spectral_register
        self.selection = 0
        self.last_selection = 0
        self.selection_rectangles = []
        self.field_selected_color_index = 5
        self.field_not_selected_color_index = 9
        self.field_selected = False
        self.scale_choices = ["linear", "log"]
        self.scale_index = 0
        self.units_y_choices = ["counts", "cts_per_ms", "irradiance" ]
        self.units_y_index = 0
        self.spectrum_choices = ["uv + vis + nir", "vis + nir", "visible", "near infrared", "ultraviolet"]
        self.spectrum_index = 0
        self.data_source_choices = ["sensors", "reference"]
        self.data_source_index = 0
        self.units_x_choices = ["wavelength nm", "frequency THz", "energy eV", "wavenumber/cm"]
        self.units_x_index = 0
        self.live = True
        self.distance_popup = False

    def update_selection( self ):
        self.selection_rectangles[self.last_selection].hidden = True
        self.selection_rectangles[self.selection].hidden = False


    def action( self ):

        if self.instrument.encoder_increment != 0:
            if self.field_selected:
                if self.selection == 0:
                   self.scale_index = (self.scale_index + self.instrument.encoder_increment) % len(self.scale_choices)
                if self.selection == 1:
                   self.units_y_index = (self.units_y_index + self.instrument.encoder_increment) % len(self.units_y_choices)
                if self.selection == 2:
                    self.spectrum_index = (self.spectrum_index + self.instrument.encoder_increment) % len(self.spectrum_choices)
                if self.selection == 4:
                   self.data_source_index = (self.data_source_index + self.instrument.encoder_increment) % len(self.data_source_choices)
                if self.selection == 5:
                    self.units_x_index = (self.units_x_index + self.instrument.encoder_increment) % len(self.units_x_choices)
                if self.selection == 6:
                    self.distance_popup = not self.distance_popup
                if self.selection == 7:
                    self.live = not self.live
            self.instrument.encoder_increment = 0

        if self.instrument.button_pressed:
            if self.selection == 8:
                self.instrument.active_page_number = self.instrument.pages_dict["Main"]
            elif self.selection == 3:
                self.instrument.active_page_number = self.instrument.pages_dict["Exposure"]
            else:
                self.field_selected = not self.field_selected
                print( "field selected = ", self.field_selected )

                if self.selection == 0:
                    if self.field_selected:
                        self.scale_color.color_index = self.field_selected_color_index
                    else:
                        self.scale_color.color_index = self.field_not_selected_color_index
                if self.selection == 1:
                    if self.field_selected:
                        self.units_y_color.color_index = self.field_selected_color_index
                    else:
                        self.units_y_color.color_index = self.field_not_selected_color_index
                if self.selection == 2:
                    if self.field_selected:
                        self.spectrum_color.color_index = self.field_selected_color_index
                    else:
                        self.spectrum_color.color_index = self.field_not_selected_color_index
                if self.selection == 4:
                    if self.field_selected:
                        self.data_source_color.color_index = self.field_selected_color_index
                    else:
                        self.data_source_color.color_index = self.field_not_selected_color_index
                if self.selection == 5:
                    if self.field_selected:
                        self.units_x_color.color_index = self.field_selected_color_index
                    else:
                        self.units_x_color.color_index = self.field_not_selected_color_index
                if self.selection == 6:
                    print( "open range tab" )
                    if self.field_selected:
                        self.distance_color.color_index = self.field_selected_color_index
                    else:
                        self.distance_color.color_index = self.field_not_selected_color_index
                if self.selection == 7:
                    if self.field_selected:
                        self.live_color.color_index = self.field_selected_color_index
                    else:
                        self.live_color.color_index = self.field_not_selected_color_index
            self.instrument.button_pressed = False

    def update_values( self ):
        self.scale_text_area.text = self.scale_choices[self.scale_index]
        self.units_y_text_area.text = self.units_y_choices[self.units_y_index]
        self.spectrum_text_area.text = self.spectrum_choices[self.spectrum_index]
        self.data_source_text_area.text = self.data_source_choices[self.data_source_index]
        self.units_x_text_area.text = self.units_x_choices[self.units_x_index]
        if self.distance_popup:
            self.distance_text_area.scale = 2
            self.distance_text_area.text = "***"
        else:
            self.distance_text_area.scale = 1
            self.distance_text_area.text = "distance"
        if self.live:
            self.live_text_area.text = "LIVE"
        else:
            self.live_text_area.text = "HOLD"

    def obsolete_update_values( self ):
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

        if self.instrument.remote_sensing_select == 6:
            self.scale_select.hidden = False
            self.spectral_register.scale_linear = not self.spectral_register.scale_linear

        else:
            self.scale_select.hidden = True
        if self.instrument.remote_sensing_select == 7:
            self.units_y_select.hidden = False
            self.spectral_register.y_axis_irradiance = not self.spectral_register.y_axis_irradiance
        else:
            self.units_y_select.hidden = True
        if instrument.remote_sensing_select == 8:
            self.spectrum_select.hidden = False
            self.spectral_register.scope = (self.spectral_register.scope + 1) % self.spectral_register.number_of_scope_choices
        else:
            self.spectrum_select.hidden = True
        if instrument.remote_sensing_select == 9:
            self.exposure_select.hidden = False
            self.spectral_graph_page.banner_group.hidden = False
            self.spectral_graph_page.banner_message_area.text = "autoexposure"
            #self.spectral_register.autoexposure = not self.spectral_register.autoexposure
            time.sleep(banner_duration)
        else:
            self.spectral_graph_page.banner_group.hidden = True
            self.exposure_select.hidden = True
        if instrument.remote_sensing_select == 10:
            self.lamps_select.hidden = False
            self.spectral_register.lamps_on = not self.spectral_register.lamps_on
            for spectral_sensor in self.instrument.spectral_sensors_present:
                if self.spectral_register.lamps_on:
                    spectral_sensor.lamps_on()
                else:
                    spectral_sensor.lamps_off()
        else:
            self.lamps_select.hidden = True
        if instrument.remote_sensing_select == 11:
            self.data_source_select.hidden = False
            self.spectral_graph_page.banner_message_area.text = "sample, ref, s/ref"
            self.spectral_graph_page.banner_group.hidden = False
            #self.spectral_register.data_source = (self.spectral_register.data_source + 1) % self.spectral_register.number_of_data_source_choices
            time.sleep(banner_duration)
        else:
            self.spectral_graph_page.banner_group.hidden = True
            self.data_source_select.hidden = True
        if instrument.remote_sensing_select == 12:
            self.graph_settings_select.hidden = False
            self.spectral_graph_page.banner_message_area.text = "sensor + ref set"
            self.spectral_graph_page.banner_group.hidden = False
            time.sleep(banner_duration)
        else:
            self.graph_settings_select.hidden = True
            self.spectral_graph_page.banner_group.hidden = True
        if instrument.remote_sensing_select == 13:
            self.units_x_select.hidden = False
            self.spectral_register.x_axis_units = (self.spectral_register.x_axis_units + 1) % self.spectral_register.number_of_x_axis_units_choices
        else:
            self.units_x_select.hidden = True
        if instrument.remote_sensing_select == 14:
            self.table_graph_select.hidden = False
            self.spectral_graph_page.banner_message_area.text = "table or graph"
            self.spectral_graph_page.banner_group.hidden = False
            #self.spectral_register.show_table = not self.spectral_register.show_table
            time.sleep(banner_duration)
        else:
            self.table_graph_select.hidden = True
            self.spectral_graph_page.banner_group.hidden = True
        if instrument.remote_sensing_select == 15:
            self.live_select.hidden = False
            self.spectral_register.live = not self.spectral_register.live
        else:
            self.live_select.hidden = True
        if instrument.remote_sensing_select == 16:
            self.return_select.hidden = False
            instrument.active_page_number = 2
        else:
            self.return_select.hidden = True

        if self.spectral_register.live:
            if False: #self.mlx90614_surface_thermometer.pn and self.hdc3022_air_sensor.pn:
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
        self.selection_rectangles.append(self.scale_select)

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
        units_y_select_x = 62
        units_y_color_x = units_y_select_x + select_width
        units_y_select_width = 73
        self.units_y_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=units_y_select_width, height=upper_select_height, x=units_y_select_x, y=upper_select_y)
        self.group.append( self.units_y_select )
        self.selection_rectangles.append(self.units_y_select)

        self.units_y_select.hidden = True
        units_y_control_width = units_y_select_width - 2 * select_width
        self.units_y_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=units_y_control_width, height=upper_control_height, x=units_y_color_x, y=upper_control_y)
        self.group.append( self.units_y_color )
        units_y_text_x = units_y_color_x + 3
        units_y_group = displayio.Group(scale=1, x=units_y_text_x, y=upper_text_y)
        units_y_text = "irradiance"#"counts" #"irradiance"
                                #"cts_per_ms
        self.units_y_text_area = label.Label(terminalio.FONT, text=units_y_text, color=self.palette[0])
        units_y_group.append(self.units_y_text_area)
        self.group.append(units_y_group)

        # spectrum
        spectrum_select_x = 148
        spectrum_color_x = spectrum_select_x + select_width
        spectrum_select_width = 96
        self.spectrum_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=spectrum_select_width, height=upper_select_height, x=spectrum_select_x, y=upper_select_y)
        self.group.append( self.spectrum_select )
        self.selection_rectangles.append(self.spectrum_select)

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
        exposure_select_x = 254 #offset + scale_select_width + units_y_select_width + spectrum_select_width - 3*select_width
        exposure_color_x = exposure_select_x + select_width
        exposure_select_width = 62
        self.exposure_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=exposure_select_width, height=upper_select_height, x=exposure_select_x, y=upper_select_y)
        self.group.append( self.exposure_select )
        self.selection_rectangles.append(self.exposure_select)

        self.exposure_select.hidden = True
        exposure_control_width = exposure_select_width - 2 * select_width
        self.exposure_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=exposure_control_width, height=upper_control_height, x=exposure_color_x, y=upper_control_y)
        self.group.append( self.exposure_color )
        exposure_text_x = exposure_color_x + 3
        exposure_group = displayio.Group(scale=1, x=exposure_text_x, y=upper_text_y)
        exposure_text = "exposure"
        self.exposure_text_area = label.Label(terminalio.FONT, text=exposure_text, color=self.palette[0])
        exposure_group.append(self.exposure_text_area)
        self.group.append(exposure_group)

        # lower controls
        lower_control_height = 14
        lower_select_y = 240 - offset - separator_bar_height - lower_control_height - select_width
        lower_select_height = lower_control_height + 2*select_width
        lower_control_y = lower_select_y + select_width
        lower_text_y = lower_control_y + 6
        # data_source
        data_source_select_x = offset
        data_source_color_x = data_source_select_x + select_width
        data_source_select_width = 64
        self.data_source_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=data_source_select_width, height=lower_select_height, x=data_source_select_x, y=lower_select_y)
        self.group.append( self.data_source_select )
        self.selection_rectangles.append(self.data_source_select)

        self.data_source_select.hidden = True
        data_source_control_width = data_source_select_width - 2 * select_width
        self.data_source_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=data_source_control_width, height=lower_control_height, x=data_source_color_x, y=lower_control_y)
        self.group.append( self.data_source_color )
        data_source_text_x = data_source_color_x + 3
        data_source_group = displayio.Group(scale=1, x=data_source_text_x, y=lower_text_y)
        data_source_text = "filename" #"cal " #"active", "file"
        self.data_source_text_area = label.Label(terminalio.FONT, text=data_source_text, color=self.palette[0])
        data_source_group.append(self.data_source_text_area)
        self.group.append(data_source_group)

        # units_x
        units_x_select_x = 68
        units_x_color_x = units_x_select_x + select_width
        units_x_select_width = 96
        self.units_x_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=units_x_select_width, height=lower_select_height, x=units_x_select_x, y=lower_select_y)
        self.group.append( self.units_x_select )
        self.selection_rectangles.append(self.units_x_select)

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

        # distance
        distance_select_x = 164
        distance_select_width = 60

        distance_color_x = distance_select_x + select_width
        self.distance_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=distance_select_width, height=lower_select_height, x=distance_select_x, y=lower_select_y)
        self.group.append( self.distance_select )
        self.selection_rectangles.append(self.distance_select)

        self.distance_select.hidden = True
        distance_control_width = distance_select_width - 2 * select_width
        self.distance_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=distance_control_width, height=lower_control_height, x=distance_color_x, y=lower_control_y)
        self.group.append( self.distance_color )
        distance_text_x = distance_color_x + 3
        distance_group = displayio.Group(scale=1, x=distance_text_x, y=lower_text_y)
        distance_text = "distance"
        self.distance_text_area = label.Label(terminalio.FONT, text=distance_text, color=self.palette[0])
        distance_group.append(self.distance_text_area)
        self.group.append(distance_group)


        # live
        live_select_width = 36
        live_select_x = 226
        live_color_x = live_select_x + select_width
        self.live_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=live_select_width, height=lower_select_height, x=live_select_x, y=lower_select_y)
        self.group.append( self.live_select )
        self.selection_rectangles.append(self.live_select)

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
        self.selection_rectangles.append(self.return_select)
        self.selection_count = len( self.selection_rectangles )
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


        return self.group

    def add_spectral_graph_page(self, spectral_graph_page):
        self.spectral_graph_page = spectral_graph_page



    def hide_all_selections( self ):
        for item in self.selection_rectangles:
            if item.hidden == False:
                item.hidden = True



def make_remote_sensing_page( instrument, spectral_register):#, hdc3022_air_sensor, mlx90614_surface_thermometer, lv_ez_mb1013_rangefinder ):
    instrument.welcome_page.announce( "make_remote_sensing_page" )
    page = Remote_Sensing_Page( instrument, spectral_register)#, hdc3022_air_sensor, mlx90614_surface_thermometer, lv_ez_mb1013_rangefinder )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page



class Remote_Sensing_Missing_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.page_name = "Remote"
        self.instrument = instrument
        self.palette = instrument.palette
        self.selection = 0
        self.selection_count = 0
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
    def hide_all_selections( self ):
        pass
    def action( self ):
        self.instrument.active_page_number = self.instrument.pages_dict["Main"]

def make_remote_sensing_missing_page( instrument ):
    instrument.welcome_page.announce( "make_remote_sensing_missing_page" )
    page = Remote_Sensing_Missing_Page( instrument )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page
