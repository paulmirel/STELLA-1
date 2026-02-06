# time place page
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel
import displayio
from adafruit_display_text import label
import vectorio
import terminalio
from .classm_page import Page
import time

class Time_Place_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.page_name = "Time"
        self.instrument = instrument
        self.palette = instrument.palette
        self.selection = 1
        self.last_selection = 0
        self.field_selected = False
        self.selection_count = 0
        self.serial_set_engaged = False
        for sensor in instrument.sensors_present:
            if sensor.name == "gps":
                self.gps = sensor

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

        line_values = ["Time and Place", "rtc!=gps"]
        line_widths = [198,115]
        x = start_x
        for index in range(0, len(line_values)):
            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            text_group.append(self.text_area)
            self.text_areas.append(self.text_area)
            self.group.append(text_group)
            x += line_widths[index]

        line_y = line_y + line_spacing
        line_values = ["YYYY-MM-DD", "HH:MM:SS", "UTC"]
        line_selectable = [ False, False, False ]
        line_widths = [134,115,68]
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
        line_values = ["Set clock on serial link"]
        line_selectable = [True ]
        line_widths = [310]
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
        line_values = ["GPS fix:", "--", "#Sats:", "--"]
        line_widths = [100,84,74,30]
        x = start_x
        for index in range(0, len(line_values)):
            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)
            x += line_widths[index]

        line_y = line_y + line_spacing
        line_values = ["latitude:", "--"]
        line_widths = [124, 100]
        x = start_x
        for index in range(0, len(line_values)):
            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)
            x += line_widths[index]

        line_y = line_y + line_spacing
        line_values = ["longitude:", "--"]
        line_widths = [124, 100]
        x = start_x
        for index in range(0, len(line_values)):
            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)
            x += line_widths[index]

        line_y = line_y + line_spacing
        line_values = ["altitude:", "--"]
        line_widths = [124, 100]
        x = start_x
        for index in range(0, len(line_values)):
            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+int(height_2/2))
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

        self.selection_count = len( self.selection_rectangles )
        return self.group

    def action( self ):
        if self.selection == 0:
            if self.instrument.rtc_syncd_to_gps:
                self.text_areas[5].text = "rtc sync'd to gps"
                time.sleep(2)
            else:
                print("start time set dialogue")
                self.serial_set_engaged = True
                self.text_areas[5].text = "serial input or reboot"
                self.instrument.hardware_clock.set_time()
                self.serial_set_engaged = False
        if self.selection == 1:
            self.instrument.active_page_number = self.instrument.pages_dict["Main"]

    def update_values( self ):
        timenow = self.instrument.hardware_clock.read()
        if self.instrument.rtc_syncd_to_gps:
            self.text_areas[1].text = "rtc==gps"
        else:
            self.text_areas[1].text = "rtc!=gps"
        self.text_areas[2].text = "{}-{:02}-{:02}".format(timenow.tm_year,timenow.tm_mon, timenow.tm_mday)
        self.text_areas[3].text = "{:02}:{:02}:{:02}".format(timenow.tm_hour,timenow.tm_min,timenow.tm_sec)
        if self.serial_set_engaged:
            self.text_areas[5].text = "serial input or reboot"
        else:
            self.text_areas[5].text = "Set clock on serial link"
        self.text_areas[7].text = "{}".format(self.gps.has_fix)
        self.text_areas[9].text = "{}".format(self.gps.satellites)
        self.text_areas[11].text = "{} deg".format(self.gps.latitude)
        self.text_areas[13].text = "{} deg".format(self.gps.longitude)
        self.text_areas[15].text = "{} m".format(self.gps.altitude)

    def update_selection(self):
        self.selection_rectangles[self.last_selection].hidden = True
        self.selection_rectangles[self.selection].hidden = False

    def hide_all_selections( self ):
        for item in self.selection_rectangles:
            if item.hidden == False:
                item.hidden = True





def make_time_place_page( instrument ):
    instrument.welcome_page.announce( "make_time_place_page" )
    page = Time_Place_Page( instrument )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page


def make_gps_page( main_display_group, palette):
    page = GPS_Page(palette)
    group = page.make_group()
    main_display_group.append( group )
    page.hide()
    return page
