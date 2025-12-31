# controls page
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import displayio
from adafruit_display_text import label
import vectorio
import terminalio
from .classm_page import Page
import time


class Lab_Spec_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.page_name = "Lab_Spec"
        self.instrument = instrument
        self.palette = instrument.palette
        self.selection = 0
        self.last_selection = 0
        self.selection_count = 0
        self.selection_rectangles = []
        self.field_selected = False
        self.chA_index = 0
        self.chB_index = 1
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
    def make_group( self ):
        self.group = displayio.Group()
        background = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=320, height=240, x=0, y=0)
        self.group.append( background )


        line_spacing = 43
        start_x = 1
        line_y = 0
        select_width = 4
        border_width = 2
        height_1 = 10
        offset_1 = 6
        height_2 = 32
        offset_2 = 6
        self.selection_rectangles = []
        self.value_areas = []
        self.text_areas = []

        batch_highlight = vectorio.Rectangle(pixel_shader=self.palette, color_index=12, width=48-2*select_width,
                                                            height=height_2-2*select_width, x=242, y=line_y+height_1+select_width)
        self.group.append(batch_highlight)

        line_names = ["year", "month", "day", "time UTC", "batch", "+=1"]
        line_values = ["YYYY-MM-DD", "", "", "HH:MM:SS", "XX", "B+"]
        line_selectable = [ False, False, False, False, False, True ]
        line_widths = [62, 34, 34, 106, 48, 34]
        x = start_x
        for index in range(0, len(line_names)):
            #area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=index+1, width=line1_widths[index],
            #                                    height=height_1, x=x, y=line1_y)
            #self.group.append(area_rectangle)
            text_group = displayio.Group(scale=1, x=x+offset_1, y=line_y+int(height_1/2))
            text_area = label.Label(terminalio.FONT, text=line_names[index], color=self.palette[0])
            text_group.append(text_area)
            self.group.append(text_group)
            if line_selectable[index]:
                selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index],
                                                                    height=height_2, x=x, y=line_y+height_1)
                selection_rectangle.hidden = True
                self.group.append(selection_rectangle)
                self.selection_rectangles.append(selection_rectangle)

                border_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]-2*(select_width-border_width),
                                                                    height=height_2-2*(select_width-border_width), x=x+select_width-border_width, y=line_y+height_1+select_width-border_width)
                self.group.append(border_rectangle)

                self.area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=line_widths[index]-2*select_width,
                                                            height=height_2-2*select_width, x=x+select_width, y=line_y+height_1+select_width)
                self.group.append(self.area_rectangle)
                self.value_areas.append(self.area_rectangle)

            text_group = displayio.Group(scale=2, x=x+offset_1, y=line_y+height_1 +int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)

            x += line_widths[index]

        #self.text_areas[-2].color = self.palette[6]
        self.value_areas[-1].color_index = 12
        #self.text_areas[-1].color = self.palette[9]


        line_y += line_spacing
        line_names = ["lamp position", "wavelength", "set_current", "ON/OFF" ]
        line_values = ["bottom", "488nm", "--mA", "OFF"]
        line_selectable = [ True, True, True, True ]
        line_widths = [118, 72, 84, 44]
        x = start_x
        for index in range(0, len(line_names)):
            #area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=index+1, width=line1_widths[index],
            #                                    height=height_1, x=x, y=line1_y)
            #self.group.append(area_rectangle)
            text_group = displayio.Group(scale=1, x=x+offset_1, y=line_y+int(height_1/2))
            text_area = label.Label(terminalio.FONT, text=line_names[index], color=self.palette[0])
            text_group.append(text_area)
            self.group.append(text_group)
            if line_selectable[index]:
                selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index],
                                                                    height=height_2, x=x, y=line_y+height_1)
                selection_rectangle.hidden = True
                self.group.append(selection_rectangle)
                self.selection_rectangles.append(selection_rectangle)

                border_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]-2*(select_width-border_width),
                                                                    height=height_2-2*(select_width-border_width), x=x+select_width-border_width, y=line_y+height_1+select_width-border_width)
                self.group.append(border_rectangle)

                self.area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=line_widths[index]-2*select_width,
                                                            height=height_2-2*select_width, x=x+select_width, y=line_y+height_1+select_width)
                self.group.append(self.area_rectangle)
                self.value_areas.append(self.area_rectangle)

            text_group = displayio.Group(scale=2, x=x+offset_1, y=line_y+height_1 +int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)

            x += line_widths[index]

        line_y += line_spacing
        line_names = ["gain", "int_time", "live_current", "status", "data" ]
        line_values = [" --", "---ms", " --mA", " --", "LOG"]
        line_selectable = [ True, True, False, False, True ]
        line_widths = [50, 74, 84, 60, 50]
        x = start_x
        for index in range(0, len(line_names)):
            #area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=index+1, width=line1_widths[index],
            #                                    height=height_1, x=x, y=line1_y)
            #self.group.append(area_rectangle)
            text_group = displayio.Group(scale=1, x=x+offset_1, y=line_y+int(height_1/2))
            text_area = label.Label(terminalio.FONT, text=line_names[index], color=self.palette[0])
            text_group.append(text_area)
            self.group.append(text_group)
            if line_selectable[index]:
                selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index],
                                                                    height=height_2, x=x, y=line_y+height_1)
                selection_rectangle.hidden = True
                self.group.append(selection_rectangle)
                self.selection_rectangles.append(selection_rectangle)

                border_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]-2*(select_width-border_width),
                                                                    height=height_2-2*(select_width-border_width), x=x+select_width-border_width, y=line_y+height_1+select_width-border_width)
                self.group.append(border_rectangle)

                self.area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=line_widths[index]-2*select_width,
                                                            height=height_2-2*select_width, x=x+select_width, y=line_y+height_1+select_width)
                self.group.append(self.area_rectangle)
                self.value_areas.append(self.area_rectangle)

            text_group = displayio.Group(scale=2, x=x+offset_1, y=line_y+height_1 +int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)

            x += line_widths[index]

        self.value_areas[-1].color_index = 5
        #measurement number
        mline_y = line_y + height_2 - 2
        mline_x = 258
        mwidth = 62
        if False:
            selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index],
                                                                    height=height_2, x=mline_x, y=mline_y+height_1)
            selection_rectangle.hidden = True
            self.group.append(selection_rectangle)
            self.selection_rectangles.append(selection_rectangle)

            border_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=mwidth-2*(select_width-border_width),
                                                            height=height_2-2*(select_width-border_width), x=mline_x+select_width-border_width, y=mline_y+height_1+select_width-border_width)
            self.group.append(border_rectangle)

        self.area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=5, width=mwidth-2*select_width,
                                                    height=height_2-2*select_width, x=mline_x+select_width, y=mline_y+height_1+select_width)
        self.group.append(self.area_rectangle)
        self.value_areas.append(self.area_rectangle)

        text_group = displayio.Group(scale=2, x=mline_x+offset_2+2, y=mline_y+height_1 +int(height_2/2))
        self.text_area = label.Label(terminalio.FONT, text="M---", color=self.palette[0])
        self.text_areas.append(self.text_area)
        text_group.append(self.text_area)
        self.group.append(text_group)



        line_y += line_spacing
        line_names = ["ch", "ctr_wavelength", "value_counts", " DR%", "" ]
        line_values = ["A:", " ---nm", " --", "--%", ""]
        line_selectable = [ False, True, False, False, False]
        line_widths = [30, 90, 80, 54, 50]
        x = start_x
        for index in range(0, len(line_names)):
            #area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=index+1, width=line1_widths[index],
            #                                    height=height_1, x=x, y=line1_y)
            #self.group.append(area_rectangle)
            text_group = displayio.Group(scale=1, x=x+offset_1, y=line_y+int(height_1/2))
            text_area = label.Label(terminalio.FONT, text=line_names[index], color=self.palette[0])
            text_group.append(text_area)
            self.group.append(text_group)
            if line_selectable[index]:
                selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index],
                                                                    height=height_2, x=x, y=line_y+height_1)
                selection_rectangle.hidden = True
                self.group.append(selection_rectangle)
                self.selection_rectangles.append(selection_rectangle)

                border_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]-2*(select_width-border_width),
                                                                    height=height_2-2*(select_width-border_width), x=x+select_width-border_width, y=line_y+height_1+select_width-border_width)
                self.group.append(border_rectangle)

                self.area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=line_widths[index]-2*select_width,
                                                            height=height_2-2*select_width, x=x+select_width, y=line_y+height_1+select_width)
                self.group.append(self.area_rectangle)
                self.value_areas.append(self.area_rectangle)

            text_group = displayio.Group(scale=2, x=x+offset_1, y=line_y+height_1 +int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)

            x += line_widths[index]

        line_y += line_spacing - 18
        line_names = ["ch", "ctr_wavelength", "value_counts", " DR%", "A/B" ]
        line_values = ["B:", " ---nm", " --", "--%", " -- "]
        line_selectable = [ False, True, False, False, False]
        line_widths = [30, 90, 80, 48, 68]
        x = start_x
        for index in range(0, len(line_names)):
            #area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=index+1, width=line1_widths[index],
            #                                    height=height_1, x=x, y=line1_y)
            #self.group.append(area_rectangle)
            #text_group = displayio.Group(scale=1, x=x+offset_1, y=line_y+int(height_1/2))
            #text_area = label.Label(terminalio.FONT, text=line_names[index], color=self.palette[0])
            #text_group.append(text_area)
            #self.group.append(text_group)
            if line_selectable[index]:
                selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index],
                                                                    height=height_2, x=x, y=line_y+height_1)
                selection_rectangle.hidden = True
                self.group.append(selection_rectangle)
                self.selection_rectangles.append(selection_rectangle)

                border_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]-2*(select_width-border_width),
                                                                    height=height_2-2*(select_width-border_width), x=x+select_width-border_width, y=line_y+height_1+select_width-border_width)
                self.group.append(border_rectangle)

                self.area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=line_widths[index]-2*select_width,
                                                            height=height_2-2*select_width, x=x+select_width, y=line_y+height_1+select_width)
                self.group.append(self.area_rectangle)
                self.value_areas.append(self.area_rectangle)

            text_group = displayio.Group(scale=2, x=x+offset_1, y=line_y+height_1 +int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)

            x += line_widths[index]


        line_y += line_spacing
        line_names = ["instruction", "do/rep", "next_step", "main" ]
        line_values = ["*instruction", "DO", "NEXT", "MM"]
        line_selectable = [ True, True, True, True ]
        line_widths = [186, 40, 58, 34]
        x = start_x
        for index in range(0, len(line_names)):
            #area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=index+1, width=line1_widths[index],
            #                                    height=height_1, x=x, y=line1_y)
            #self.group.append(area_rectangle)
            text_group = displayio.Group(scale=1, x=x+offset_1, y=line_y+int(height_1/2))
            text_area = label.Label(terminalio.FONT, text=line_names[index], color=self.palette[0])
            text_group.append(text_area)
            self.group.append(text_group)
            if line_selectable[index]:
                selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index],
                                                                    height=height_2, x=x, y=line_y+height_1)
                selection_rectangle.hidden = True
                self.group.append(selection_rectangle)
                self.selection_rectangles.append(selection_rectangle)

                border_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]-2*(select_width-border_width),
                                                                    height=height_2-2*(select_width-border_width), x=x+select_width-border_width, y=line_y+height_1+select_width-border_width)
                self.group.append(border_rectangle)

                self.area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=line_widths[index]-2*select_width,
                                                            height=height_2-2*select_width, x=x+select_width, y=line_y+height_1+select_width)
                self.group.append(self.area_rectangle)
                self.value_areas.append(self.area_rectangle)

            text_group = displayio.Group(scale=2, x=x+offset_1, y=line_y+height_1 +int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)

            x += line_widths[index]

        self.value_areas[-3].color_index = 7
        self.text_areas[-3].color = self.palette[9]
        self.value_areas[-2].color_index = 32
        self.value_areas[-1].color_index = 15
        #self.text_areas[-1].color = self.palette[9]

        if True:
            ratio_y = 164
            ratio_text = "A/B"
            ratio_x = 256
            text_group = displayio.Group(scale=1, x=ratio_x, y=ratio_y)
            self.text_area = label.Label(terminalio.FONT, text=ratio_text, color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)
        self.selection_count = len( self.selection_rectangles )
        return self.group

    def update_selection( self ):
        self.selection_rectangles[self.last_selection].hidden = True
        self.selection_rectangles[self.selection].hidden = False

    def hide_all_selections( self ):
        for item in self.selection_rectangles:
            if item.hidden == False:
                item.hidden = True


    def update_values( self ):
        timenow = self.instrument.hardware_clock.read()
        self.text_areas[0].text = "{}-{:02}-{:02}".format(timenow.tm_year,timenow.tm_mon, timenow.tm_mday)
        self.text_areas[3].text = "{:02}:{:02}:{:02}".format(timenow.tm_hour, timenow.tm_min,timenow.tm_sec)
        self.text_areas[4].text = "{}".format(self.instrument.batch_number)

        self.spectral_sensors[self.active_sensor_index].read_counts_all()
        gain = self.spectral_sensors[self.active_sensor_index].gain_list[ self.gain_index[self.active_sensor_index] ]
        self.text_areas[10].text = "{}".format(gain)
        integration_time_ms = self.spectral_sensors[self.active_sensor_index].integration_time_ms_list[ self.integration_time_index[self.active_sensor_index] ]
        if integration_time_ms < 1000:
            self.text_areas[11].text = "{}ms".format(integration_time_ms)
        else:
            self.text_areas[11].text = "{}s".format(round(integration_time_ms/1000,1))



    def action( self ):
        if self.selection == 13:
            self.instrument.active_page_number = self.instrument.pages_dict["Main"]
        if self.selection == 0:
            self.instrument.update_batch()
        if self.selection == 1:
            print( "enter to select from available lamps by position" )
        if self.selection == 2:
            print( "enter to select from available lamps by wavelength" )
        if self.selection == 3:
            print( "enter to set desired current" )
        if self.selection == 4:
            print( "toggle lamp on/off" )
        if self.selection == 5:
            print( "enter to set gain" )
            self.gain_index[self.active_sensor_index] = (
                                self.gain_index[self.active_sensor_index] + self.instrument.encoder_increment ) % len(
                                self.spectral_sensors[self.active_sensor_index].gain_list )
            self.spectral_sensors[self.active_sensor_index].set_gain( self.gain_index[self.active_sensor_index])
        if self.selection == 6:
            print( "enter to select integration time" )
        if self.selection == 7:
            print( "write current values to file" )
        if self.selection == 8:
            print( "enter to select channel A" )
        if self.selection == 9:
            print( "enter to select channel B" )
        if self.selection == 10:
            print( "enter to select instruction" )
        if self.selection == 11:
            print( "execute measurement sequence" )
        if self.selection == 12:
            print( "advance to the next instruction" )





def make_lab_spec_page( instrument ):
    instrument.welcome_page.announce( "make_lab_spec_page" )
    page = Lab_Spec_Page( instrument )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page
