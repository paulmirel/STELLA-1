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
    def make_group( self ):
        self.group = displayio.Group()
        background = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=320, height=240, x=0, y=0)
        self.group.append( background )

        start_x = 6
        line1_y = 2
        select_width = 4
        border_width = 2
        height_1 = 14
        offset_1 = 6
        height_2 = 28
        offset_2 = 6
        self.selectables = []
        self.value_areas = []
        self.text_areas = []

        line1_names = ["year", "month", "day", "time UTC", "batch", "+=1"]
        line1_values = ["YYYY", "MM", "DD", "HH:MM:SS", "XX", "B+"]
        line1_selectable = [ False, False, False, False, False, True ]
        line1_widths = [60, 34, 34, 108, 40, 34]
        x = start_x
        for index in range(0, len(line1_names)):
            #area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=index+1, width=line1_widths[index],
            #                                    height=height_1, x=x, y=line1_y)
            #self.group.append(area_rectangle)
            text_group = displayio.Group(scale=1, x=x+offset_1, y=line1_y+int(height_1/2))
            text_area = label.Label(terminalio.FONT, text=line1_names[index], color=self.palette[0])
            text_group.append(text_area)
            self.group.append(text_group)
            if line1_selectable[index]:
                selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line1_widths[index],
                                                                    height=height_2, x=x, y=line1_y+height_1)
                self.group.append(selection_rectangle)
                self.selectables.append(selection_rectangle)

                border_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line1_widths[index]-2*(select_width-border_width),
                                                                    height=height_2-2*(select_width-border_width), x=x+select_width-border_width, y=line1_y+height_1+select_width-border_width)
                self.group.append(border_rectangle)

                self.area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=line1_widths[index]-2*select_width,
                                                            height=height_2-2*select_width, x=x+select_width, y=line1_y+height_1+select_width)
                self.group.append(self.area_rectangle)
                self.value_areas.append(self.area_rectangle)

            text_group = displayio.Group(scale=2, x=x+offset_1, y=line1_y+height_1 +int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line1_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)

            x += line1_widths[index]

        self.value_areas[-1].color_index = 6
        self.text_areas[-1].color = self.palette[9]


        '''
        title_string = " year    month day       time UTC      batch  +=1"
        text_group = displayio.Group(scale=1, x=12, y= 10)
        text_area = label.Label(terminalio.FONT, text=title_string, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        test_string = "YYYY-MM-DD HH:MM:SS NN [+]"
        text_group = displayio.Group(scale=2, x=6, y=14+16)
        text_area = label.Label(terminalio.FONT, text=test_string, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        second_row_y = 42
        title_string = "lamp position      wavelength     set_current ON/OFF"
        text_group = displayio.Group(scale=1, x=6, y=10+second_row_y)
        text_area = label.Label(terminalio.FONT, text=title_string, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        test_string = "Backlight XXXnm  XXXmA OFF"
        text_group = displayio.Group(scale=2, x=6, y=14+16+second_row_y)
        text_area = label.Label(terminalio.FONT, text=test_string, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        third_row_y = 42*2
        title_string = "gain       int_time    current    status  write_data"
        text_group = displayio.Group(scale=1, x=6, y=10+third_row_y)
        text_area = label.Label(terminalio.FONT, text=title_string, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        test_string = "16x VVVVms XXXmA  OK WRITE"
        text_group = displayio.Group(scale=2, x=6, y=14+16+third_row_y)
        text_area = label.Label(terminalio.FONT, text=test_string, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        fourth_row_y = 42*3
        title_string = "ch  center_wavelength value   %DR         A/B"
        text_group = displayio.Group(scale=1, x=6, y=10+fourth_row_y)
        text_area = label.Label(terminalio.FONT, text=title_string, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        test_string = "A: VVVnm CCCCC XX%"
        text_group = displayio.Group(scale=2, x=6, y=14+16+fourth_row_y)
        text_area = label.Label(terminalio.FONT, text=test_string, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        test_string = "B: VVVnm CCCCC XX%"
        text_group = displayio.Group(scale=2, x=6, y=16*3+6+fourth_row_y)
        text_area = label.Label(terminalio.FONT, text=test_string, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        test_string = "0.398"
        text_group = displayio.Group(scale=2, x=238, y=16*3-6+fourth_row_y)
        text_area = label.Label(terminalio.FONT, text=test_string, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        fifth_row_y = 42*4+16+6
        title_string = "instruction             do/repeat   next_step   main"
        text_group = displayio.Group(scale=1, x=6, y=10+fifth_row_y)
        text_area = label.Label(terminalio.FONT, text=title_string, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        test_string = "instruction   DO  NEXT  MM"
        text_group = displayio.Group(scale=2, x=6, y=14+16+fifth_row_y)
        text_area = label.Label(terminalio.FONT, text=test_string, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)
        '''

        return self.group

    def update_selection( self ):
        self.selection_rectangles[self.last_selection].hidden = True
        self.selection_rectangles[self.selection].hidden = False

    def hide_all_selections( self ):
        for item in self.selection_rectangles:
            if item.hidden == False:
                item.hidden = True


    def update_values( self ):
        if False:
            while True:
                time.sleep(1)
                print( "hide" )
                self.selectables[0].hidden = True
                time.sleep(1)
                print( "show" )
                self.selectables[0].hidden = False
        pass
        '''
        if self.gps.fix():
            self.gps_value_text_area.text = " FIX"
            self.gps_color.color_index = 18
        else:
            self.gps_value_text_area.text = "nofix"
            self.gps_color.color_index = 8
        battery_level = int(self.battery_monitor.percentage)
        if battery_level < 100:
            battery_text = "{}%".format(battery_level)
        else:
            battery_text = "{}".format(battery_level)
        self.battery_value_text_area.text =  battery_text

        if self.instrument.burst_counter < self.instrument.burst_count:
            value =  self.instrument.burst_count - self.instrument.burst_counter
            if value < 10:
                self.burst_value_text_area.text = " {}".format(value)
            else:
                self.burst_value_text_area.text = "{}".format(value)
        else:
            self.burst_color.color_index = 16
            if self.instrument.burst_count < 10:
                self.burst_value_text_area.text = " {}".format(self.instrument.burst_count)
            else:
                self.burst_value_text_area.text = "{}".format(self.instrument.burst_count)
        if self.instrument.record:
            self.record_circle.hidden = False
        else:
            self.record_circle.hidden = True
        self.batch_value_text_area.text = "{}".format(self.instrument.batch_number)
        if self.instrument.batch_number < 10:
            self.batch_value_group.x = self.batch_text_x+7
        elif self.instrument.batch_number < 100:
            self.batch_value_group.x = self.batch_text_x+5
        else:
            self.batch_value_group.x = self.batch_text_x-3
        '''

    def action( self ):
        self.instrument.active_page_number = self.instrument.pages_dict["Main"]
        pass
        '''
        if False:#self.selection == 0:
            self.instrument.active_page_number = self.instrument.pages_dict["Time"] #TBD send to page when it exists
        if self.selection == 1:
            self.instrument.update_batch()
        if self.selection == 2:
            self.instrument.record = not self.instrument.record
        if self.selection == 3:
            self.instrument.take_burst = True
            self.instrument.record = False
            self.burst_color.color_index = 6
        else:
            self.burst_color.color_index = 16
            self.instrument.take_burst = False
        if self.selection == 4:
            pass#self.instrument.active_page_number = self.instrument.pages_dict["Settings"]
        if self.selection == 5:
            self.instrument.active_page_number = self.instrument.pages_dict["Status"]
        '''



def make_lab_spec_page( instrument ):
    instrument.welcome_page.announce( "make_lab_spec_page" )
    page = Lab_Spec_Page( instrument )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page
