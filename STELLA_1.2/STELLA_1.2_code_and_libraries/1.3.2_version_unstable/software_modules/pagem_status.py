# status page
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel
import displayio
from adafruit_display_text import label
import vectorio
import terminalio
from .classm_page import Page
import os

class Status_Page( Page ):
    def __init__( self, instrument, battery_monitor ):
        super().__init__()
        self.page_name = "Status"
        self.palette = instrument.palette
        self.instrument = instrument
        self.selection = 0
        self.selection_count = 0
        self.last_selection = 0
        self.field_selected = False
        self.battery_monitor = battery_monitor

        sdcard_status = os.statvfs("/sd")
        sdf_block_size = sdcard_status[0]
        sdf_blocks_avail = sdcard_status[4]
        sd_bytes_avail_B = sdf_blocks_avail * sdf_block_size
        self.sd_bytes_avail_MB = round(sd_bytes_avail_B/ 1000000,1)
        self.sd_bytes_avail_GB = round(self.sd_bytes_avail_MB/ 1000,1)
        sdfssize = sdcard_status[2]
        self.sdbytessize_MB = int (round(( sdfssize * sdf_block_size/ 1000000 ), 0))
        self.sdbytessize_GB = int( round( self.sdbytessize_MB /1000, 0 ))
        self.sdavail_percent = int( self.sd_bytes_avail_MB/ self.sdbytessize_MB * 100)

    def make_group( self ):
        self.group = displayio.Group()
        status_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240, x=0, y=0 )
        self.group.append( status_background )
        text_spacing_y = 28
        status_title_group = displayio.Group(scale=2, x=10, y=18)
        status_title_text = "Status: UID {}".format(self.instrument.uid)
        status_title_text_area = label.Label(terminalio.FONT, text=status_title_text, color=self.palette[0])
        status_title_group.append(status_title_text_area)
        self.group.append(status_title_group)

        line_spacing = 30
        start_x = 1
        line_y = 2 + line_spacing
        select_width = 4
        border_width = 2
        height_1 = 10
        offset_1 = 6
        height_2 = 32
        offset_2 = 9
        self.selection_rectangles = []
        self.value_areas = []
        self.text_areas = []

        line_values = ["Battery", "0.0 V", "00%"]
        line_widths = [100,90,70]
        x = start_x
        for index in range(0, len(line_values)):
            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            text_group.append(self.text_area)
            self.text_areas.append(self.text_area)
            self.group.append(text_group)
            x += line_widths[index]

        line_y += line_spacing

        line_values = ["Clock battery", "---"]
        line_widths = [170,70]
        x = start_x
        for index in range(0, len(line_values)):
            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            text_group.append(self.text_area)
            self.text_areas.append(self.text_area)
            self.group.append(text_group)
            x += line_widths[index]

        line_y += line_spacing

        line_values = ["SD card", "--- MB" ]
        line_widths = [100,70]
        x = start_x
        for index in range(0, len(line_values)):
            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            text_group.append(self.text_area)
            self.text_areas.append(self.text_area)
            self.group.append(text_group)
            x += line_widths[index]

        line_y += line_spacing

        line_values = [ "--- MB free", "--% free"]
        line_widths = [190,70]
        x = start_x
        for index in range(0, len(line_values)):
            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            text_group.append(self.text_area)
            self.text_areas.append(self.text_area)
            self.group.append(text_group)
            x += line_widths[index]

        line_y += line_spacing

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

    def action( self ):
        self.instrument.active_page_number = self.instrument.previous_page_number

    def update_values( self ):

        self.text_areas[1].text = "{}V".format( self.battery_monitor.voltage )
        self.text_areas[2].text = "{}%".format( int(round(self.battery_monitor.percentage,0)) )
        if self.instrument.hardware_clock.battery_ok():
            self.text_areas[4].text = "OK"
        else:
            self.text_areas[4].text = "LOW"

        if self.sdbytessize_MB < 1000:
            self.text_areas[6].text = "{} MB".format(self.sdbytessize_MB)
        else:
            self.text_areas[6].text = "{} GB".format(self.sdbytessize_GB)
        if self.sd_bytes_avail_MB < 1000:
            self.text_areas[7].text = "{} MB free =".format(self.sd_bytes_avail_MB)
        else:
            self.text_areas[7].text = "{} GB free =".format(self.sd_bytes_avail_GB)
        self.text_areas[8].text = "{}% free".format(self.sdavail_percent)


    def update_selection(self):
        self.selection_rectangles[self.last_selection].hidden = True
        self.selection_rectangles[self.selection].hidden = False

    def hide_all_selections( self ):
        for item in self.selection_rectangles:
            if item.hidden == False:
                item.hidden = True


def make_status_page( instrument, battery_monitor ):
    instrument.welcome_page.announce( "make_status_page" )
    page = Status_Page( instrument, battery_monitor )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page
