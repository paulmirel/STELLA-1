# sensor list page
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
        self.selection_count = 0

    def make_group( self ):
        self.group = displayio.Group()
        status_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240, x=0, y=0 )
        self.group.append( status_background )
        text_spacing_y = 28
        status_title_group = displayio.Group(scale=2, x=14, y=18)
        status_title_text = "Active Sensors: "
        status_title_text_area = label.Label(terminalio.FONT, text=status_title_text, color=self.palette[0])
        status_title_group.append(status_title_text_area)
        self.group.append(status_title_group)

        select_width = 4
        selection_x = 10
        selection_start_y = 8 + text_spacing_y
        selection_width = 260
        selection_height = 24
        selection_rectangles = []
        text_areas = []
        for index in range (0,6):
            selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=selection_width, height=selection_height, x=selection_x, y=selection_start_y+text_spacing_y*index)
            selection_rectangles.append( selection_rectangle )
            self.group.append( selection_rectangle )
            area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=selection_width-2*select_width, height=selection_height-2*select_width, x=selection_x+select_width, y=select_width+selection_start_y+text_spacing_y*index)
            self.group.append( area_rectangle )

            text_group = displayio.Group(scale=2, x=selection_x+2*select_width, y=8+select_width+selection_start_y+text_spacing_y*index)
            text = "name : part number"
            text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
            text_group.append(text_area)
            text_areas.append( text_group )
            self.group.append(text_group)


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
        selection_rectangles.append( self.return_select )
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

    def action( self ):
        self.instrument.active_page_number = self.instrument.pages_dict["Main"]
    def update_selection():
        pass


def make_sensors_page( instrument ):
    instrument.welcome_page.announce( "make_sensors_page" )
    page = Sensors_Page( instrument )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page
