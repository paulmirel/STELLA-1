# controls page
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import displayio
from adafruit_display_text import label
import vectorio
import terminalio
from .classm_page import Page


class Controls_Page( Page ):
    def __init__( self, palette, gps, battery_monitor ):
        super().__init__()
        self.page_name = "Controls"
        self.palette = palette
        self.gps = gps
        self.battery_monitor = battery_monitor
        self.select_value = 2
        self.number_of_select_values = 7
    def make_group( self ):
        self.group = displayio.Group()
        control_bar_height = 54
        text_y1 = 16
        text_y2 = text_y1 + 14 + 3
        select_width = 4
        offset = 4
        select_height = control_bar_height - 2 * offset
        select_y = offset
        control_y = select_y + select_width
        control_height = select_height - 2 * select_width
        controls_background = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=320, height=control_bar_height, x=0, y=0)
        self.group.append( controls_background )
        # gps
        gps_select_x = offset - 1
        gps_color_x = gps_select_x + select_width
        gps_select_width = 44
        self.gps_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=gps_select_width, height=select_height, x=gps_select_x, y=select_y)
        self.group.append( self.gps_select )
        self.gps_select.hidden = True
        gps_control_width = gps_select_width - 2 * select_width
        self.gps_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=8, width=gps_control_width, height=control_height, x=gps_color_x, y=control_y)
        self.group.append( self.gps_color )
        gps_text_x = gps_color_x + 3
        gps_group = displayio.Group(scale=1, x=gps_text_x, y=text_y1+2)
        gps_text = " GPS"
        gps_text_area = label.Label(terminalio.FONT, text=gps_text, color=self.palette[9])
        gps_group.append(gps_text_area)
        self.group.append(gps_group)
        gps_value_group = displayio.Group(scale=1, x=gps_text_x, y=text_y2)
        gps_value_text = "nofix"
        self.gps_value_text_area = label.Label(terminalio.FONT, text=gps_value_text, color=self.palette[9])
        gps_value_group.append(self.gps_value_text_area)
        self.group.append(gps_value_group)
        # batch
        batch_select_x = 2*offset+gps_select_width-3
        batch_color_x = batch_select_x + select_width
        batch_select_width = 52
        self.batch_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=batch_select_width, height=select_height, x=batch_select_x, y=select_y)
        self.group.append( self.batch_select )
        self.batch_select.hidden = True
        batch_control_width = batch_select_width - 2 * select_width
        batch_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=6, width=batch_control_width, height=control_height, x=batch_color_x, y=control_y)
        self.group.append( batch_color )
        self.batch_text_x = batch_color_x + 5
        batch_group = displayio.Group(scale=1, x=self.batch_text_x+1, y=text_y1)
        batch_text = "batch"
        batch_text_area = label.Label(terminalio.FONT, text=batch_text, color=self.palette[9])
        batch_group.append(batch_text_area)
        self.group.append(batch_group)
        self.batch_value_group = displayio.Group(scale=2, x=self.batch_text_x, y=text_y2)
        batch_value_text = "000"
        self.batch_value_text_area = label.Label(terminalio.FONT, text=batch_value_text, color=self.palette[9])
        self.batch_value_group.append(self.batch_value_text_area)
        self.group.append(self.batch_value_group)
        # pause and record
        pause_record_select_x = 2*offset+gps_select_width+batch_select_width+2
        pause_record_x = pause_record_select_x + select_width
        pause_record_select_width = select_height
        self.pause_record_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=pause_record_select_width, height=select_height, x=pause_record_select_x, y=select_y)
        self.group.append( self.pause_record_select )
        pause_record_control_width = pause_record_select_width - 2 * select_width
        pause_record_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=pause_record_control_width, height=control_height, x=pause_record_x, y=control_y)
        self.group.append( pause_record_color )
        pause_record_offset_x = 6
        pause_record_y = 14
        pause_base = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=26, height=26, x=pause_record_x+pause_record_offset_x, y=pause_record_y)
        self.group.append( pause_base )
        pause_split = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=8, height=26, x=pause_record_x+9+pause_record_offset_x, y=pause_record_y)
        self.group.append( pause_split )
        self.record_circle = vectorio.Circle( pixel_shader=self.palette, color_index=2, radius=18, x=pause_record_x+12+pause_record_offset_x, y=pause_record_y+13 )
        self.group.append( self.record_circle )
        #self.record_circle.hidden = True
        self.pause_record_select.hidden = True
        # burst
        burst_select_x = pause_record_select_width + pause_record_x # - offset
        burst_color_x = burst_select_x + select_width
        burst_select_width = 44
        self.burst_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=burst_select_width, height=select_height, x=burst_select_x, y=select_y)
        self.group.append( self.burst_select )
        self.burst_select.hidden = True
        burst_control_width = burst_select_width - 2 * select_width
        self.burst_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=16, width=burst_control_width, height=control_height, x=burst_color_x, y=control_y)
        self.group.append( self.burst_color )
        burst_text_x = burst_color_x + 6
        burst_group = displayio.Group(scale=1, x=burst_text_x-2, y=text_y1)
        burst_text = "burst"
        burst_text_area = label.Label(terminalio.FONT, text=burst_text, color=self.palette[9])
        burst_group.append(burst_text_area)
        self.group.append(burst_group)
        burst_value_group = displayio.Group(scale=2, x=burst_text_x+1, y=text_y2)
        burst_value_text = "00"
        self.burst_value_text_area = label.Label(terminalio.FONT, text=burst_value_text, color=self.palette[9])
        burst_value_group.append(self.burst_value_text_area)
        self.group.append(burst_value_group)
        # interval
        interval_select_x = burst_select_width + burst_color_x - 2
        interval_color_x = interval_select_x + select_width
        interval_select_width = 58
        self.interval_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=interval_select_width, height=select_height, x=interval_select_x, y=select_y)
        self.group.append( self.interval_select )
        self.interval_select.hidden = True
        interval_control_width = interval_select_width - 2 * select_width
        interval_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=7, width=interval_control_width, height=control_height, x=interval_color_x, y=control_y)
        self.group.append( interval_color )
        interval_text_x = interval_color_x + 5
        interval_group = displayio.Group(scale=1, x=interval_text_x-3, y=text_y1)
        interval_text = "settings"
        interval_text_area = label.Label(terminalio.FONT, text=interval_text, color=self.palette[9])
        interval_group.append(interval_text_area)
        self.group.append(interval_group)
        interval_value_group = displayio.Group(scale=2, x=interval_text_x+3, y=text_y2)
        interval_value_text = " >>"
        self.interval_value_text_area = label.Label(terminalio.FONT, text=interval_value_text, color=self.palette[9])
        interval_value_group.append(self.interval_value_text_area)
        self.group.append(interval_value_group)
        # battery
        battery_select_x = interval_select_width + interval_color_x - 2
        battery_color_x = battery_select_x + select_width
        battery_select_width = 56
        self.battery_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=battery_select_width, height=select_height, x=battery_select_x, y=select_y)
        self.group.append( self.battery_select )
        self.battery_select.hidden = True
        battery_control_width = battery_select_width - 2 * select_width
        battery_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=15, width=battery_control_width, height=control_height, x=battery_color_x, y=control_y)
        self.group.append( battery_color )
        battery_text_x = battery_color_x + 6
        battery_group = displayio.Group(scale=1, x=battery_text_x-2, y=text_y1)
        battery_text = "battery"
        battery_text_area = label.Label(terminalio.FONT, text=battery_text, color=self.palette[9])
        battery_group.append(battery_text_area)
        self.group.append(battery_group)
        battery_value_group = displayio.Group(scale=2, x=battery_text_x+1, y=text_y2)
        battery_value_text = "00%"
        self.battery_value_text_area = label.Label(terminalio.FONT, text=battery_value_text, color=self.palette[9])
        battery_value_group.append(self.battery_value_text_area)
        self.group.append(battery_value_group)
        return self.group
    def update_burst_countdown( self, value ):
        if value < 10:
            self.burst_value_text_area.text = " {}".format(value)
        else:
            self.burst_value_text_area.text = "{}".format(value)
    def update_values( self, instrument ):
        if self.gps.fix():
            self.gps_value_text_area.text = " FIX"
            self.gps_color.color_index = 18
        else:
            self.gps_value_text_area.text = "nofix"
            self.gps_color.color_index = 8
        self.battery_value_text_area.text = "{}%".format( int(self.battery_monitor.percentage))
        if instrument.burst_count < 10:
            self.burst_value_text_area.text = " {}".format(instrument.burst_count)
        else:
            self.burst_value_text_area.text = "{}".format(instrument.burst_count)
        if instrument.record:
            self.record_circle.hidden = False
        else:
            self.record_circle.hidden = True
        self.batch_value_text_area.text = "{}".format(instrument.batch_number)
        if instrument.batch_number < 10:
            self.batch_value_group.x = self.batch_text_x+7
        elif instrument.batch_number < 100:
            self.batch_value_group.x = self.batch_text_x+5
        else:
            self.batch_value_group.x = self.batch_text_x-3

        ## processing inputs


        if instrument.active_page_number == 2: # main menu
            if instrument.main_menu_select == 0:
                self.gps_select.hidden = False
                if instrument.button_pressed:
                    instrument.active_page_number = 7
                    instrument.button_pressed = False
            else:
                self.gps_select.hidden = True
            if instrument.main_menu_select == 1:
                self.batch_select.hidden = False
                if instrument.button_pressed:
                    instrument.update_batch()
                    instrument.button_pressed = False
            else:
                self.batch_select.hidden = True
            if instrument.main_menu_select == 2:
                self.pause_record_select.hidden = False
                if instrument.button_pressed:
                    instrument.record = not instrument.record
                    instrument.button_pressed = False
            else:
                self.pause_record_select.hidden = True
            if instrument.main_menu_select == 3:
                self.burst_select.hidden = False
                if instrument.button_pressed:
                    instrument.take_burst = True
                    instrument.record = False
                    self.burst_color.color_index = 6
                    instrument.button_pressed = False
            else:
                self.burst_select.hidden = True
            if instrument.main_menu_select == 4:
                self.interval_select.hidden = False
                if instrument.button_pressed:
                    instrument.active_page_number = 4
                    instrument.button_pressed = False
            else:
                self.interval_select.hidden = True
            if instrument.main_menu_select == 5:
                self.battery_select.hidden = False
                if instrument.button_pressed:
                    instrument.active_page_number = 3
                    instrument.button_pressed = False
            else:
                self.battery_select.hidden = True

        if instrument.active_page_number == 9: # remote sensing
            if instrument.remote_sensing_select == 0:
                self.gps_select.hidden = False
                if instrument.button_pressed:
                    instrument.active_page_number = 7
                    instrument.button_pressed = False
            else:
                self.gps_select.hidden = True
            if instrument.remote_sensing_select == 1:
                self.batch_select.hidden = False
                if instrument.button_pressed:
                    instrument.update_batch()
                    instrument.button_pressed = False
            else:
                self.batch_select.hidden = True
            if instrument.remote_sensing_select == 2:
                self.pause_record_select.hidden = False
                if instrument.button_pressed:
                    instrument.record = not instrument.record
                    instrument.button_pressed = False
            else:
                self.pause_record_select.hidden = True
            if instrument.remote_sensing_select == 3:
                self.burst_select.hidden = False
                if instrument.button_pressed:
                    instrument.take_burst = True
                    instrument.record = False
                    self.burst_color.color_index = 6
                    instrument.button_pressed = False
            else:
                self.burst_select.hidden = True
            if instrument.remote_sensing_select == 4:
                self.interval_select.hidden = False
                if instrument.button_pressed:
                    instrument.active_page_number = 4
                    instrument.button_pressed = False
            else:
                self.interval_select.hidden = True
            if instrument.remote_sensing_select == 5:
                self.battery_select.hidden = False
                if instrument.button_pressed:
                    instrument.active_page_number = 3
                    instrument.button_pressed = False
            else:
                self.battery_select.hidden = True


def make_controls_page( instrument, gps, battery_monitor ):
    instrument.welcome_page.announce( "make_controls_page" )
    page = Controls_Page( instrument.palette, gps, battery_monitor )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page
