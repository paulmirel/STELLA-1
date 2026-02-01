# settings page
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import displayio
from adafruit_display_text import label
import vectorio
import terminalio
from .classm_page import Page

class Settings_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.page_name = "Settings"
        self.instrument = instrument
        self.palette = instrument.palette
        self.selection = 0
        self.selection_count = 0
        self.last_selection = 0
        self.field_selected = False

    def make_group( self ):
        self.group = displayio.Group()
        background = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=320, height=240, x=0, y=0)
        self.group.append( background )

        line_spacing = 30
        start_x = 1
        line_y = 2
        select_width = 4
        border_width = 2
        height_1 = 10
        offset_1 = 6
        height_2 = 32
        offset_2 = 9
        self.selection_rectangles = []
        self.value_areas = []
        self.text_areas = []

        line_values = ["System Settings:"]
        line_widths = [300]
        x = start_x
        for index in range(0, len(line_values)):
            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            text_group.append(self.text_area)
            self.text_areas.append(self.text_area)
            self.group.append(text_group)
            x += line_widths[index]

        line_y = line_y + line_spacing
        line_values = ["Sample interval:", " --"]
        line_selectable = [ False, True ]
        line_widths = [200,115]
        x = start_x
        for index in range(0, len(line_values)):
            if line_selectable[index]:
                selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index],
                                                                    height=height_2, x=x, y=line_y)
                selection_rectangle.hidden = False # True
                self.group.append(selection_rectangle)
                self.selection_rectangles.append(selection_rectangle)

                border_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]-2*(select_width-border_width),
                                                                    height=height_2-2*(select_width-border_width), x=x+select_width-border_width, y=line_y+select_width-border_width)
                self.group.append(border_rectangle)

                self.area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=line_widths[index]-2*select_width,
                                                            height=height_2-2*select_width, x=x+select_width, y=line_y+select_width)
                self.group.append(self.area_rectangle)
                self.value_areas.append(self.area_rectangle)

            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)
            x += line_widths[index]

        line_y = line_y + line_spacing
        line_values = ["Burst count:", " --"]
        line_selectable = [False, True ]
        line_widths =[200,115]
        x = start_x
        for index in range(0, len(line_values)):
            if line_selectable[index]:
                selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index],
                                                                    height=height_2, x=x, y=line_y)
                selection_rectangle.hidden = True
                self.group.append(selection_rectangle)
                self.selection_rectangles.append(selection_rectangle)

                border_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]-2*(select_width-border_width),
                                                                    height=height_2-2*(select_width-border_width), x=x+select_width-border_width, y=line_y+select_width-border_width)
                self.group.append(border_rectangle)

                self.area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=line_widths[index]-2*select_width,
                                                            height=height_2-2*select_width, x=x+select_width, y=line_y+select_width)
                self.group.append(self.area_rectangle)
                self.value_areas.append(self.area_rectangle)

            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)
            x += line_widths[index]

        line_y = line_y + line_spacing
        line_values = ["Serial output:", " -- "]
        line_selectable = [False, True ]
        line_widths = [200,115]
        x = start_x
        for index in range(0, len(line_values)):
            if line_selectable[index]:
                selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index],
                                                                    height=height_2, x=x, y=line_y)
                selection_rectangle.hidden = True
                self.group.append(selection_rectangle)
                self.selection_rectangles.append(selection_rectangle)

                border_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]-2*(select_width-border_width),
                                                                    height=height_2-2*(select_width-border_width), x=x+select_width-border_width, y=line_y+select_width-border_width)
                self.group.append(border_rectangle)

                self.area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=line_widths[index]-2*select_width,
                                                            height=height_2-2*select_width, x=x+select_width, y=line_y+select_width)
                self.group.append(self.area_rectangle)
                self.value_areas.append(self.area_rectangle)

            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)
            x += line_widths[index]

        line_y = line_y + line_spacing
        line_values = ["Serial interval:", " --"]
        line_selectable = [False, True ]
        line_widths = [200,115]
        x = start_x
        for index in range(0, len(line_values)):
            if line_selectable[index]:
                selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index],
                                                                    height=height_2, x=x, y=line_y)
                selection_rectangle.hidden = True
                self.group.append(selection_rectangle)
                self.selection_rectangles.append(selection_rectangle)

                border_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]-2*(select_width-border_width),
                                                                    height=height_2-2*(select_width-border_width), x=x+select_width-border_width, y=line_y+select_width-border_width)
                self.group.append(border_rectangle)

                self.area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=line_widths[index]-2*select_width,
                                                            height=height_2-2*select_width, x=x+select_width, y=line_y+select_width)
                self.group.append(self.area_rectangle)
                self.value_areas.append(self.area_rectangle)

            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)
            x += line_widths[index]

        line_y = line_y + line_spacing+14
        line_values = ["Set default values in the user_settings.py file"]
        line_selectable = [False ]
        line_widths = [320]
        x = start_x +10
        for index in range(0, len(line_values)):
            text_group = displayio.Group(scale=1, x=x+offset_1, y=line_y+int(height_1/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)
            x += line_widths[index]

        line_y = line_y + height_1+2
        line_values = ["in the CIRCUITPY/configuration_files/ folder"]
        line_selectable = [False ]
        line_widths = [320]
        x = start_x +10
        for index in range(0, len(line_values)):
            text_group = displayio.Group(scale=1, x=x+offset_1, y=line_y+int(height_1/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)
            x += line_widths[index]

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
        self.selection_rectangles.append(self.return_select)
        self.selection_count += 1
        self.return_select.hidden = True
        return_control_width = return_select_width - 2 * select_width
        self.return_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=return_control_width, height=return_height, x=return_x, y=return_y)
        self.group.append( self.return_color )
        return_text_x = return_x + 10
        return_group = displayio.Group(scale=2, x=return_text_x, y=return_text_y)
        return_text = "RETURN"
        self.return_text_area = label.Label(terminalio.FONT, text=return_text, color=self.palette[0])
        return_group.append(self.return_text_area)
        self.group.append(return_group)

        self.selection_count = len( self.selection_rectangles )
        return self.group

    def action( self ):
        if self.selection == 0:
            print("set sample interval")
        if self.selection == 1:
            print("set burst count")
        if self.selection == 2:
            print("set serial output")
        if self.selection == 3:
            print("set serial interval")
        if self.selection == 4:
            self.instrument.active_page_number = self.instrument.pages_dict["Main"]

    def update_values( self ):
        self.text_areas[2].text = self.interval_units( self.instrument.sample_interval_s )
        self.text_areas[4].text = "{}".format(self.instrument.burst_count)
        if self.instrument.serial_out:
            self.text_areas[6].text = "enabled"
        else:
            self.text_areas[6].text = "disabled"
        self.text_areas[8].text = self.interval_units( self.instrument.serial_interval_s )

    def update_selection(self):
        self.selection_rectangles[self.last_selection].hidden = True
        self.selection_rectangles[self.selection].hidden = False

    def hide_all_selections( self ):
        for item in self.selection_rectangles:
            if item.hidden == False:
                item.hidden = True


    def interval_units( self, intervals ):
        intervalm = intervals / 60
        intervalh = intervalm / 60
        intervald = intervalh / 24
        if intervals < 60:
            interval_text = "{}s".format(int(intervals))
        elif intervalm < 60:
            interval_text = "{}m".format(int(intervalm))
        elif intervalh < 24:
            interval_text = "{}h".format(int(intervalh))
        else:
            interval_text = "{}d".format(int(intervald))
        return interval_text
    ####
    '''
    def old_code():
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
        interval_value_text = " -- "
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
        burst_value_text = " -- "
        self.burst_value_text_area = label.Label(terminalio.FONT, text=burst_value_text, color=self.palette[0])
        burst_value_group.append(self.burst_value_text_area)
        self.group.append(burst_value_group)

        serial_out_group = displayio.Group(scale=2, x=10, y= 18 +3* spacing_y)
        serial_out_text = "Serial output:"
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
        serial_out_value_text = " --"
        self.serial_out_value_text_area = label.Label(terminalio.FONT, text=serial_out_value_text, color=self.palette[0])
        serial_out_value_group.append(self.serial_out_value_text_area)
        self.group.append(serial_out_value_group)

        text_group = displayio.Group(scale=2, x=10, y= 18 +4* spacing_y)
        text = "TBD allow user to set vals"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)


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

    def action( self ):
        self.instrument.active_page_number = self.instrument.previous_page_number

    def update_selection( self ):
        pass

    def hide_all_selections( self ):
        pass

    def update_values( self ):
        self.instrument.active_page_number = 2
        intervals = self.instrument.sample_interval_s
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
        if self.instrument.burst_count < 10:
            burst_text = " {}".format(self.instrument.burst_count)
        else:
            burst_text = "{}".format(self.instrument.burst_count)
        #if instrument.usb_serial_out:
        #    self.serial_out_value_text_area.text = "Y"
        #else:
        #    self.serial_out_value_text_area.text =

        self.burst_value_text_area.text = burst_text
    '''
def make_settings_page( instrument ):
    instrument.welcome_page.announce( "make_settings_page" )
    page = Settings_Page( instrument )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page
