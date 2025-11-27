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
        self.palette = instrument.palette
        self.selection = 0
        self.selection_count = 0
        
    def make_group( self ):
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
        interval_value_text = "000s"
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
        burst_value_text = "000"
        self.burst_value_text_area = label.Label(terminalio.FONT, text=burst_value_text, color=self.palette[0])
        burst_value_group.append(self.burst_value_text_area)
        self.group.append(burst_value_group)

        serial_out_group = displayio.Group(scale=2, x=10, y= 18 +3* spacing_y)
        serial_out_text = "USB serial data output:"
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
        serial_out_value_text = "N"
        self.serial_out_value_text_area = label.Label(terminalio.FONT, text=serial_out_value_text, color=self.palette[0])
        serial_out_value_group.append(self.serial_out_value_text_area)
        self.group.append(serial_out_value_group)

        text_group = displayio.Group(scale=2, x=10, y= 18 +4* spacing_y)
        text = "TBD allow user to set vals"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        if False:
            spectral_sensor_group = displayio.Group(scale=2, x=10, y=int(18+4.5*spacing_y))
            spectral_sensor_text = "Spectral Sensor:"
            spectral_sensor_text_area = label.Label(terminalio.FONT, text=spectral_sensor_text, color=self.palette[0])
            spectral_sensor_group.append(spectral_sensor_text_area)
            self.group.append(spectral_sensor_group)

            self.sensor_value_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=select_width,
                                                            height=select_height, x=select_x, y=int( select_start_y + 3.5* spacing_y) )
            self.group.append( self.sensor_value_select )
            self.sensor_value_highlight = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9,
                                                            width=select_width - 2* border_width, height=select_height-2*border_width,
                                                            x=select_x+border_width, y=int( select_start_y+border_width + 3.5* spacing_y) )
            self.group.append( self.sensor_value_highlight )
            self.sensor_value_select.hidden = True

            spectral_sensor_value_group = displayio.Group(scale=2, x=value_x, y=int(18+4.5*spacing_y))
            spectral_sensor_value_text = "as7265x"
            self.spectral_sensor_value_text_area = label.Label(terminalio.FONT, text=spectral_sensor_value_text, color=self.palette[0])
            spectral_sensor_value_group.append(self.spectral_sensor_value_text_area)
            self.group.append(spectral_sensor_value_group)

            gain_group = displayio.Group(scale=2, x=10, y=int(18 + 5.5* spacing_y))
            gain_text = "Gain:"
            gain_text_area = label.Label(terminalio.FONT, text=gain_text, color=self.palette[0])
            gain_group.append(gain_text_area)
            self.group.append(gain_group)

            self.gain_value_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=select_width,
                                                            height=select_height, x=select_x, y=int( select_start_y + 4.5* spacing_y) )
            self.group.append( self.gain_value_select )
            self.gain_value_highlight = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9,
                                                            width=select_width - 2* border_width, height=select_height-2*border_width,
                                                            x=select_x+border_width, y=int( select_start_y+border_width + 4.5* spacing_y) )
            self.group.append( self.gain_value_highlight )
            self.gain_value_select.hidden = True

            gain_value_group = displayio.Group(scale=2, x=value_x, y=int(18 + 5.5* spacing_y))
            gain_value_text = "1X"
            self.gain_value_text_area = label.Label(terminalio.FONT, text=gain_value_text, color=self.palette[0])
            gain_value_group.append(self.gain_value_text_area)
            self.group.append(gain_value_group)

            integration_time_group = displayio.Group(scale=2, x=10, y=int(18+6.5*spacing_y))
            integration_time_text = "Integration Time:"
            integration_time_text_area = label.Label(terminalio.FONT, text=integration_time_text, color=self.palette[0])
            integration_time_group.append(integration_time_text_area)
            self.group.append(integration_time_group)

            self.integration_time_value_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=select_width,
                                                            height=select_height, x=select_x, y=int( select_start_y + 5.5* spacing_y) )
            self.group.append( self.integration_time_value_select )
            self.integration_time_value_highlight = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9,
                                                            width=select_width - 2* border_width, height=select_height-2*border_width,
                                                            x=select_x+border_width, y=int( select_start_y+border_width + 5.5* spacing_y) )
            self.group.append( self.integration_time_value_highlight )
            self.integration_time_value_select.hidden = True

            integration_time_value_group = displayio.Group(scale=2, x=value_x, y=int(18+6.5*spacing_y))
            integration_time_value_text = "166ms"
            self.integration_time_value_text_area = label.Label(terminalio.FONT, text=integration_time_value_text, color=self.palette[0])
            integration_time_value_group.append(self.integration_time_value_text_area)
            self.group.append(integration_time_value_group)

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
        
    def action( self, instrument ):
        instrument.active_page_number = instrument.pages_dict["Main"]
    def update_selection():
        pass
        
    def update_values( self, instrument ):
        if instrument.button_pressed:
            instrument.active_page_number = 2
            instrument.button_pressed = False
        intervals = instrument.sample_interval_s
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
        if instrument.burst_count < 10:
            burst_text = " {}".format(instrument.burst_count)
        else:
            burst_text = "{}".format(instrument.burst_count)
        #if instrument.usb_serial_out:
        #    self.serial_out_value_text_area.text = "Y"
        #else:
        #    self.serial_out_value_text_area.text = "N"


        self.burst_value_text_area.text = burst_text

def make_settings_page( instrument ):
    instrument.welcome_page.announce( "make_settings_page" )
    page = Settings_Page( instrument )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page
