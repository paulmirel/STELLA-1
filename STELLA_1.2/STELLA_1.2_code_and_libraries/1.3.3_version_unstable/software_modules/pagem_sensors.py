# generic sensor page
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import displayio
from adafruit_display_text import label
import vectorio
import terminalio
from .classm_page import Page


class Sensors_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.page_name = "Sensors"
        self.instrument = instrument
        self.palette = instrument.palette
        self.selection = 0
        self.last_selection = 1
        self.selection_count = 0
        self.sensor_choice = 0
        self.field_selected = False

    def make_group( self ):
        self.group = displayio.Group()
        generic_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240, x=0, y=0 )
        self.group.append( generic_background )
        text_spacing_y = 28
        self.rows = 7
        select_width = 4
        selection_x = 8
        selection_start_y = 8 + text_spacing_y
        selection_width = 180
        selection_height = 32
        self.selection_rectangles = []
        self.parameter_areas = []
        title_selection_width = 320-4
        self.title_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0,
                                                width=title_selection_width, height=selection_height+2,
                                                x=2, y=2)
        #self.title_select.hidden = True
        self.selection_rectangles.append( self.title_select )
        self.group.append( self.title_select )
        self.selection_count += 1
        self.title_area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9,
                                    width=title_selection_width-2*select_width, height=2+selection_height-2*select_width,
                                    x=select_width+2, y=select_width+2)
        self.group.append( self.title_area_rectangle )
        title_group = displayio.Group(scale=2, x=16, y=18)
        title_text = ""
        self.title_text_area = label.Label(terminalio.FONT, text=title_text, color=self.palette[0])
        title_group.append(self.title_text_area)
        self.group.append(title_group)


        for index in range (0,self.rows):
            if False:
                self.selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=selection_width, height=selection_height, x=selection_x, y=selection_start_y+text_spacing_y*index)
                self.selection_rectangle.hidden = True
                self.selection_rectangles.append( self.selection_rectangle )
                self.group.append( self.selection_rectangle )
                self.selection_count += 1
                area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=selection_width-2*select_width, height=selection_height-2*select_width, x=selection_x+select_width, y=select_width+selection_start_y+text_spacing_y*index)
                self.group.append( area_rectangle )

            text_group = displayio.Group(scale=2, x=selection_x+2*select_width, y=10+select_width+selection_start_y+text_spacing_y*index)
            text = ""#"parameter_units "
            self.parameter_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
            text_group.append( self.parameter_area )
            self.parameter_areas.append( self.parameter_area )
            self.group.append( text_group )
        #self.selection_rectangles[0].hidden = False
        value_selection_width = 60
        value_x = 190+24
        self.value_areas = []
        for index in range (0,self.rows):
            if False:
                self.selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=value_selection_width, height=selection_height, x=value_x, y=selection_start_y+text_spacing_y*index)
                self.selection_rectangle.hidden = True
                self.selection_rectangles.append( self.selection_rectangle )
                self.group.append( self.selection_rectangle )
                self.selection_count += 1
                area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=value_selection_width-2*select_width, height=selection_height-2*select_width, x=value_x+select_width, y=select_width+selection_start_y+text_spacing_y*index)
                self.group.append( area_rectangle )

            text_group = displayio.Group(scale=2, x=value_x+2*select_width, y=10+select_width+selection_start_y+text_spacing_y*index)
            text = ""#"value "
            self.value_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
            text_group.append( self.value_area )
            self.value_areas.append( self.value_area )
            self.group.append( text_group )

        # RETURN

        return_height = 14
        return_select_y = 240 - 4 - 2 - return_height - select_width
        return_select_height = return_height + 2*select_width
        return_y = return_select_y + select_width
        return_text_y = return_y + 7
        return_select_width = 50
        return_select_x = 320 - 4 - return_select_width
        return_x = return_select_x + select_width
        self.return_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=return_select_width, height=return_select_height, x=return_select_x, y=return_select_y)
        self.group.append( self.return_select )
        self.selection_count += 1
        self.selection_rectangles.append( self.return_select )
        self.return_select.hidden = True

        return_control_width = return_select_width - 2 * select_width
        self.return_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=return_control_width, height=return_height, x=return_x, y=return_y)
        self.group.append( self.return_color )
        return_text_x = return_x + 3
        return_group = displayio.Group(scale=1, x=return_text_x, y=return_text_y)
        return_text = "RETURN"
        self.return_text_area = label.Label(terminalio.FONT, text=return_text, color=self.palette[0])
        return_group.append(self.return_text_area)
        self.group.append(return_group)

        return self.group

    def update_selection( self ):
        self.selection_rectangles[self.last_selection].hidden = True
        self.selection_rectangles[self.selection].hidden = False

    def hide_all_selections( self ):
        for item in self.selection_rectangles:
            if item.hidden == False:
                item.hidden = True

    def action( self ):
        if self.selection == 0:
            if self.instrument.encoder_increment != 0:
                self.sensor_choice = (self.sensor_choice + self.instrument.encoder_increment) % len(self.instrument.sensors_present)
                self.update_values()
                self.instrument.encoder_increment = 0
            if self.instrument.button_pressed:
                self.field_selected = not self.field_selected
                if self.field_selected:
                    self.title_area_rectangle.color_index = 5
                else:
                    self.title_area_rectangle.color_index = 9
                self.instrument.button_pressed = False
        if self.selection == 1:
            self.selection = 0
            self.instrument.active_page_number = self.instrument.pages_dict["Main"]


    def update_values( self ):
        self.sensor = self.instrument.sensors_present[ self.sensor_choice ]
        if self.sensor:
            self.title_text_area.text = "{} : {}".format( self.sensor.name, self.sensor.pn )
            index_max = len(self.sensor.parameters)
            if index_max > self.rows: index_max = self.rows
            for index in range (0, index_max):
                self.parameter_areas[index].text = self.sensor.parameters[index]
                self.value_areas[index].text = "{}".format(self.sensor.values[index])
            for index in range ( index_max, self.rows ):
                self.parameter_areas[index].text = ""
                self.value_areas[index].text = ""


def make_sensors_page( instrument ):
    instrument.welcome_page.announce( "make_sensors_page" )
    page = Sensors_Page( instrument )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page
