# Lab_Spec page
# version 2.0
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
        self.chA_index = 3
        self.chB_index = 2
        self.spectral_sensors = self.instrument.spectral_sensors_present
        self.active_sensor_index = 0
        self.max_counts = 65535
        self.exposure_target_fraction_high = 0.9
        self.exposure_target_fraction_low = 0.5
        self.number_of_sensors = len( self.spectral_sensors )
        self.gain_index = []
        for sensor_index in range (0, self.number_of_sensors):
            self.gain_index.append( self.spectral_sensors[sensor_index].gain_index )
        self.integration_time_index = []
        for sensor_index in range (0, self.number_of_sensors):
            self.integration_time_index.append( self.spectral_sensors[sensor_index].integration_time_index )
        self.status_index = 0
        self.status_list = ["OK", "BUSY", "FAIL", "LOWB", "NOSD"]
        self.adc_sensor = False
        self.supply_5V = False
        self.supply_5V_on = False
        for sensor in self.instrument.sensors_present:
            if sensor.pn == "ads1015":
                self.adc_sensor = sensor
            if sensor.name == "supply_5V":
                self.supply_5V = sensor
        if self.adc_sensor:
            self.adc_sensor.swob.gain = self.adc_sensor.gain_list[3] #set ADC gain to 4x, for 0 to 1.024V
        self.mmt_number = 0

    def make_group( self ):
        self.group = displayio.Group()
        background = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=320, height=240, x=0, y=0)
        self.group.append( background )

        line_spacing = 43
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

        line_values = ["YYYY-MM-DD", "HH:MM:SS", "Main"]
        line_selectable = [ False, False, True ]
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

        self.selection_rectangles[-1].hidden = False

        line_y += line_spacing - height_1
        line_names = ["excitation", "position", "inspect A", "inspect B" ]
        line_values = ["488nm","below", "515nm", "480nm"]
        line_selectable = [ True, True, True, True ]
        line_widths = [78,86,77,77]
        x = start_x
        for index in range(0, len(line_names)):
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
            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+height_1 +int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)
            x += line_widths[index]

        line_y += line_spacing
        batch_highlight = vectorio.Rectangle(pixel_shader=self.palette, color_index=12, width=48-2*select_width,
                                                            height=height_2-2*select_width, x=138, y=line_y+height_1+select_width)
        self.group.append(batch_highlight)
        line_names = ["last current", "status", "batch", "+=1", "measure & log" ]
        line_values = ["800mA", "OK", "265", "B+", "MEASURE"]
        line_selectable = [ True, False, False, True, True ]
        line_widths = [78, 54, 48, 38, 100]
        x = start_x
        for index in range(0, len(line_names)):
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

            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+height_1 +int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)

            x += line_widths[index]
        self.value_areas[-2].color_index = 12
        self.value_areas[-1].color_index = 5

        line_y += line_spacing
        line_names = ["gain", "mmt#", "A value", "B value", "A/B", "%DR" ]
        line_values = ["265", "", "", "", "", ""]
        line_selectable = [ True, False, False, False, False, False, False]
        line_widths = [74, 46, 66, 66, 38, 30 ]
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

            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+height_1 +int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)

            x += line_widths[index]

        line_y += line_spacing
        line_names = ["integration" ]
        line_values = ["800ms"]
        line_selectable = [ True]
        line_widths = [74]
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

            text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+height_1 +int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)

            x += line_widths[index]


        line_y += line_spacing - 10
        line_names = ["", "", "", "" ]
        line_values = ["*instruction", "<", "DO", ">"]
        line_selectable = [ True, True, True, True ]
        line_widths = [232, 24, 38, 24]
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

        # measured values
        line_y = 128
        #line_names = ["mmt#", "A value", "B value", "A/B", "%DR" ]
        line_values = ["M03", "65535", "65535", "1.0", "20"]
        line_widths = [42, 66, 66, 42, 30 ]
        x = 78
        for index in range(0, len(line_values)):

            text_group = displayio.Group(scale=2, x=x, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)

            x += line_widths[index]

        line_y += 24
        #line_names = ["mmt#", "A value", "B value", "A/B", "%DR" ]
        line_values = ["M02", "65535", "65535", "1.0", "20"]
        line_widths = [42, 66, 66, 42, 30 ]
        x = 78
        for index in range(0, len(line_values)):

            text_group = displayio.Group(scale=2, x=x, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)

            x += line_widths[index]

        line_y += 24
        #line_names = ["mmt#", "A value", "B value", "A/B", "%DR" ]
        line_values = ["M01", "65535", "65535", "1.0", "20"]
        line_widths = [42, 66, 66, 42, 30 ]
        x = 78
        for index in range(0, len(line_values)):

            text_group = displayio.Group(scale=2, x=x, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)

            x += line_widths[index]









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
        self.text_areas[1].text = "{:02}:{:02}:{:02}".format(timenow.tm_hour, timenow.tm_min,timenow.tm_sec)

        if False:

            self.text_areas[4].text = "{}".format(self.instrument.batch_number)
            if self.supply_5V_on:
                self.text_areas[9].text = "ON"
                self.value_areas[4].color_index = 4
            else:
                self.text_areas[9].text = "OFF"
                self.value_areas[4].color_index = 9
            if self.adc_sensor:
                self.adc_sensor.read()
                lamp_currrent_voltage = self.adc_sensor.voltage[0]
            else:
                lamp_currrent_voltage = 0
            self.text_areas[12].text = "{}mA".format(int(round(lamp_currrent_voltage*1000,1)))
            self.text_areas[13].text = self.status_list[ self.status_index ]
            self.text_areas[15].text = "M{:03}".format( self.mmt_number )
            if len(self.spectral_sensors) >0:
                self.spectral_sensors[self.active_sensor_index].read_counts_all()
                gain = self.spectral_sensors[self.active_sensor_index].gain_list[ self.gain_index[self.active_sensor_index] ]
                self.text_areas[10].text = "{}".format(gain)
                integration_time_ms = self.spectral_sensors[self.active_sensor_index].integration_time_ms_list[ self.integration_time_index[self.active_sensor_index] ]
                if integration_time_ms < 1000:
                    self.text_areas[11].text = "{}ms".format(integration_time_ms)
                else:
                    self.text_areas[11].text = "{}s".format(round(integration_time_ms/1000,1))

                self.text_areas[17].text = "{}nm".format(self.spectral_sensors[self.active_sensor_index].wavelength_bands_nm[self.chA_index])
                chA_counts = self.spectral_sensors[self.active_sensor_index].data_counts[self.chA_index]
                chB_counts = self.spectral_sensors[self.active_sensor_index].data_counts[self.chB_index]
                self.text_areas[18].text = "{:05}".format(chA_counts)
                chA_pdr = 100*chA_counts/self.max_counts
                if chA_pdr < 10:
                    self.text_areas[19].text = "{}%".format(round(chA_pdr,1))
                else:
                    self.text_areas[19].text = "{}%".format(int(round(chA_pdr,0)))
                self.text_areas[22].text = "{}nm".format(self.spectral_sensors[self.active_sensor_index].wavelength_bands_nm[self.chB_index])
                self.text_areas[23].text = "{:05}".format(chB_counts)
                chB_pdr = 100*chB_counts/self.max_counts
                if chB_pdr < 10:
                    self.text_areas[24].text = "{}%".format(round(chB_pdr,1))
                else:
                    self.text_areas[24].text = "{}%".format(int(round(chB_pdr,0)))
                if chB_counts>0:
                    ratio_ab = chA_counts/ chB_counts
                else:
                    ratio_ab = 0
                if ratio_ab < 10:
                    self.text_areas[25].text = "{}".format(round(ratio_ab,1))
                else:
                    self.text_areas[25].text = "{}".format(int(round(ratio_ab,0)))




    def action( self ):
        self.instrument.active_page_number = self.instrument.pages_dict["Main"]
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
            self.supply_5V_on = not self.supply_5V_on
            if self.supply_5V_on:
                self.supply_5V.enable()
            else:
                self.supply_5V.disable()

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
