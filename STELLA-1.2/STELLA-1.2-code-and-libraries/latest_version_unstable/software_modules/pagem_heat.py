# heat page module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import displayio
from adafruit_display_text import label
import vectorio
import terminalio
from .classm_page import Page

class Heat_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.page_name = "Heat"
        self.instrument = instrument
        self.palette = instrument.palette
        self.selection = 0
        self.last_selection = 0
        self.selection_count = 1
        self.field_selected = False

    def update_values( self ):
        air_sensor_in_use = False
        surface_sensor_in_use = False
        for sensor in self.instrument.sensors_present:
            if sensor.pn == "hdc3022":
                air_sensor_in_use = sensor
            if sensor.pn == "mlx90614":
                surface_sensor_in_use = sensor
        if air_sensor_in_use:
            air_sensor_values = air_sensor_in_use.get_values()
            air_temp_C = air_sensor_values[0]
            self.tair_text_area.text = "{}C".format( air_temp_C )
        if surface_sensor_in_use:
            surface_sensor_values = surface_sensor_in_use.get_values()
            surface_temp_C = surface_sensor_values[0]
            self.tsurface_text_area.text = "{}C".format( surface_temp_C )
        if air_sensor_in_use and surface_sensor_in_use:
            self.tdiff_text_area.text = "{}C".format( round(surface_temp_C - air_temp_C,1) )
        if not air_sensor_in_use and not surface_sensor_in_use:
            self.banner_group.hidden = False

    def make_group( self ):
        self.group = displayio.Group()
        start_y = 54
        status_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240-start_y, x=0, y=start_y )
        self.group.append( status_background )


        label_x_start = 18
        value_x_start = 12
        value_y_start = 80
        column_spacing = 106
        label_y_start = value_y_start  + 20

        label_group = displayio.Group(scale=1, x=label_x_start, y=label_y_start)
        label_text = "Tsurface"
        label_text_area = label.Label(terminalio.FONT, text=label_text, color=self.palette[0])
        label_group.append(label_text_area)
        self.group.append(label_group)

        value_group = displayio.Group(scale=2, x=value_x_start, y=value_y_start)
        value_text = " -- "
        self.tsurface_text_area = label.Label(terminalio.FONT, text=value_text, color=self.palette[0])
        value_group.append(self.tsurface_text_area)
        self.group.append(value_group)

        label_group = displayio.Group(scale=1, x=label_x_start+64+3, y=label_y_start)
        label_text = "-"
        label_text_area = label.Label(terminalio.FONT, text=label_text, color=self.palette[0])
        label_group.append(label_text_area)
        self.group.append(label_group)

        label_group = displayio.Group(scale=2, x=label_x_start+64, y=value_y_start)
        label_text = "-"
        label_text_area = label.Label(terminalio.FONT, text=label_text, color=self.palette[0])
        label_group.append(label_text_area)
        self.group.append(label_group)

        label_group = displayio.Group(scale=1, x=label_x_start+column_spacing+20, y=label_y_start)
        label_text = "Tair"
        label_text_area = label.Label(terminalio.FONT, text=label_text, color=self.palette[0])
        label_group.append(label_text_area)
        self.group.append(label_group)

        value_group = displayio.Group(scale=2, x=value_x_start+column_spacing, y=value_y_start)
        value_text = " -- "
        self.tair_text_area = label.Label(terminalio.FONT, text=value_text, color=self.palette[0])
        value_group.append(self.tair_text_area)
        self.group.append(value_group)

        label_group = displayio.Group(scale=1, x=label_x_start+ 186+3, y=label_y_start)
        label_text = "="
        label_text_area = label.Label(terminalio.FONT, text=label_text, color=self.palette[0])
        label_group.append(label_text_area)
        self.group.append(label_group)

        label_group = displayio.Group(scale=2, x=label_x_start+ 186, y=value_y_start)
        label_text = "="
        label_text_area = label.Label(terminalio.FONT, text=label_text, color=self.palette[0])
        label_group.append(label_text_area)
        self.group.append(label_group)

        label_group = displayio.Group(scale=1, x=label_x_start+2*column_spacing+8+12, y=label_y_start)
        label_text = "Tdiff"
        label_text_area = label.Label(terminalio.FONT, text=label_text, color=self.palette[0])
        label_group.append(label_text_area)
        self.group.append(label_group)

        value_group = displayio.Group(scale=2, x=value_x_start+2*column_spacing+12, y=value_y_start)
        value_text = " -- "
        self.tdiff_text_area = label.Label(terminalio.FONT, text=value_text, color=self.palette[0])
        value_group.append(self.tdiff_text_area)
        self.group.append(value_group)

        label_group = displayio.Group(scale=1, x=label_x_start, y=160)
        label_text = "TBD humidity, dew point, heat index"
        label_text_area = label.Label(terminalio.FONT, text=label_text, color=self.palette[0])
        label_group.append(label_text_area)
        self.group.append(label_group)

        label_group = displayio.Group(scale=1, x=label_x_start, y=180)
        label_text = "TBD co2 ppm, ch4 ppm, h20 ppm"
        label_text_area = label.Label(terminalio.FONT, text=label_text, color=self.palette[0])
        label_group.append(label_text_area)
        self.group.append(label_group)

        label_group = displayio.Group(scale=1, x=label_x_start, y=200)
        label_text = "TBD C/F/K"
        label_text_area = label.Label(terminalio.FONT, text=label_text, color=self.palette[0])
        label_group.append(label_text_area)
        self.group.append(label_group)

        label_group = displayio.Group(scale=1, x=label_x_start, y=220)
        label_text = "TBD auto choose available sensor"
        label_text_area = label.Label(terminalio.FONT, text=label_text, color=self.palette[0])
        label_group.append(label_text_area)
        self.group.append(label_group)


        self.selection_rectangles = []
        select_width = 4
        offset = 4

        # lower controls
        separator_bar_height = 2
        lower_control_height = 14
        lower_select_y = 240 - offset - separator_bar_height - lower_control_height - select_width
        lower_select_height = lower_control_height + 2*select_width
        lower_control_y = lower_select_y + select_width
        lower_text_y = lower_control_y + 6

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

        self.banner_group = displayio.Group()
        banner_bar = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=320-2*5, height=60, x=0+5, y=70)
        self.banner_group.append( banner_bar )
        banner_text_group = displayio.Group(scale=2, x=20, y=70+16)
        banner_text = "Connect a temperature"
        banner_text_area = label.Label(terminalio.FONT, text=banner_text, color=self.palette[0])
        banner_text_group.append(banner_text_area)
        self.banner_group.append(banner_text_group)
        banner_text_group_2 = displayio.Group(scale=2, x=20, y=70+28+16)
        banner_text = "sensor and restart"
        banner_text_area_2 = label.Label(terminalio.FONT, text=banner_text, color=self.palette[0])
        banner_text_group_2.append(banner_text_area_2)
        self.banner_group.append(banner_text_group_2)
        self.group.append(self.banner_group)
        self.banner_group.hidden = True

        return self.group

    def update_selection( self ):
        self.selection_rectangles[self.last_selection].hidden = True
        self.selection_rectangles[self.selection].hidden = False

    def hide_all_selections( self ):
        for item in self.selection_rectangles:
            if item.hidden == False:
                item.hidden = True

    def action( self ):
        self.instrument.active_page_number = self.instrument.previous_page_number



def make_heat_page( instrument ):
    instrument.welcome_page.announce( "make_heat_page" )
    page = Heat_Page(instrument)
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page
