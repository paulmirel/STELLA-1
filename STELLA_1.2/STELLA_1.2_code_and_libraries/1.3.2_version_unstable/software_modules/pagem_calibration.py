# calibration page
# Copyright NASA 2026 under MIT open source license
# Author Paul Mirel
import displayio
from adafruit_display_text import label
import vectorio
import terminalio
from .classm_page import Page
from software_modules import functionm_file, devicem_neopixel
import time
import gc

class Calibration_Page( Page ):
    def __init__( self, instrument, onboard_neopixel ):
        super().__init__()
        self.page_name = "Calibration"
        self.palette = instrument.palette
        self.instrument = instrument
        self.selection = 0
        self.selection_count = 0
        self.last_selection = 0
        self.field_selected = False
        self.field_selected_color_index = 5
        self.field_not_selected_color_index = 9
        if False: # sensor specific selections
            for spectral_sensor in self.instrument.spectral_sensors_present:
                if spectral_sensor.pn == "as7341":
                    self.as7341_spectrometer = spectral_sensor
            self.as7341_spectrometer.set_gain( self.gain_index )
            self.integration_time_index = 19
            self.as7341_spectrometer.set_integration_time( self.integration_time_index )
            self.number_of_sensors = 1
        self.active_sensor_index = 0
        self.max_counts = 65535
        self.exposure_target_fraction_high = 0.9
        self.exposure_target_fraction_low = 0.5
        self.status_index = 0
        self.status_list = ["OK","BUSY","TBD","LOWB","NOSD","FAIL"]
        self.adc_sensor = False
        self.supply_5V = False
        self.supply_5V_on = False
        self.dac = False
        for sensor in self.instrument.sensors_present:
            if sensor.name == "supply_5V":
                self.supply_5V = sensor
            if sensor.pn == "max1704x":
                self.bat = sensor
            if sensor.name == "gps":
                self.gps = sensor
        self.mmt_number = 0
        self.measuring = False

        self.integration_time_setting_test()

    def integration_time_setting_test( self ):
        integration_setting_ms = 10
        while integration_setting_ms < 24000:
            self.set_integration_time_ms( integration_setting_ms )
            integration_setting_ms = round(integration_setting_ms * 1.1,1)


    def set_integration_time_ms( self, integration_setting_ms ):
        tolerance = 0.05
        cycle_limit = 16
        unit_integration_time_ms = 2.78
        integration_time_actual_ms = 0
        astep_16_bit_value = 0
        atime_8_bit_value = 127
        calculating_integration_settings = True
        #print("calculating")
        cycle = 0
        while calculating_integration_settings:
            #print(".", end = "")
            if integration_setting_ms < 12:
                astep_16_bit_value = 1
                atime_8_bit_value = 1
                integration_time_actual_ms = (astep_16_bit_value+1) * (atime_8_bit_value+1) * unit_integration_time_ms
                calculating_integration_settings = False
            else:
                astep_16_bit_value = int( integration_setting_ms / (unit_integration_time_ms * (atime_8_bit_value + 1)))
                if astep_16_bit_value < 1:
                    atime_8_bit_value = int(atime_8_bit_value / 2)
                if astep_16_bit_value > 65533:
                    atime_8_bit_value = atime_8_bit_value * 2
                if atime_8_bit_value < 1:
                    astep_16_bit_value = astep_16_bit_value - 1
                integration_time_actual_ms = (astep_16_bit_value+1) * (atime_8_bit_value+1) * unit_integration_time_ms
                if (integration_time_actual_ms - integration_setting_ms)/integration_time_actual_ms > tolerance:
                    atime_8_bit_value = atime_8_bit_value - 1
                if (integration_setting_ms - integration_time_actual_ms)/integration_setting_ms > tolerance:
                    atime_8_bit_value = atime_8_bit_value + 1
                if astep_16_bit_value in range (0, 65534) and atime_8_bit_value in range (0, 255):
                    if abs(integration_time_actual_ms - integration_setting_ms)/integration_time_actual_ms < tolerance:
                        calculating_integration_settings = False

            #print(astep_16_bit_value, atime_8_bit_value)
            cycle += 1
            if cycle > cycle_limit:
                calculating_integration_settings = False
        print( "set these:", int(integration_setting_ms), atime_8_bit_value, astep_16_bit_value, int(integration_time_actual_ms), round((integration_time_actual_ms-integration_setting_ms)/integration_setting_ms,2))
        return integration_time_actual_ms


    def plot(self):
        self.plot_register = self.mmt_register[self.selection-9]
        print("register contents")
        print(self.plot_register)
        print(self.reference_register)
        if False: #self.subtract_reference_to_plot: #TBD get this working correctly, don't subtract ref from ref, don't mess up the display data
            for index in range (0, len(self.reference_register)):
                self.plot_register[index+2] = self.plot_register[index+2] - self.reference_register[index]
        print(self.plot_register)
        plot_yvalues = self.plot_register[2:]
        plot_ymax = max(plot_yvalues)
        dr=int(100*plot_ymax/65535)
        plot_ymin = min(plot_yvalues)
        plot_yspan = plot_ymax - plot_ymin
        print(plot_ymax, plot_ymin, plot_yspan)
        if dr >99:
            self.plot_title_area.text = "{}:{}:SATURATED".format(self.plot_register[0], self.plot_register[1])
        else:
            self.plot_title_area.text = "{} : {} : {}% dr".format(self.plot_register[0], self.plot_register[1],dr)
        #TBD add -Rxx to plot title
        self.y_max_area.text = "{}".format(plot_ymax)
        self.y_min_area.text = "{}".format(plot_ymin)
        yspan_pix = self.ybottom_pix - self.ytop_pix
        if plot_yspan < 1:
            plot_yspan = 1
        pix_per_val = yspan_pix/ plot_yspan
        y_pix = []
        for index in range (0, len(plot_yvalues)):
            y_pix.append(self.ytop_pix + yspan_pix - int((plot_yvalues[index]-plot_ymin)*pix_per_val))

        shading_points = []
        shading_points.append((self.plot_xpix[-1], self.ytop_pix + yspan_pix))
        shading_points.append((self.plot_xpix[0], self.ytop_pix + yspan_pix))

        for index in range (0, len(self.plot_xpix)):
            self.plot_points[index].y = y_pix[index]
            shading_points.append((self.plot_xpix[index], y_pix[index]))
        self.shading.points=shading_points


    def update_values( self ):
        self.bat.read()
        self.gps.read()
        start = time.monotonic()
        timenow = self.instrument.hardware_clock.read()
        self.text_areas[0].text = "{}-{:02}-{:02}".format(timenow.tm_year,timenow.tm_mon, timenow.tm_mday)
        self.text_areas[1].text = "{:02}:{:02}:{:02}".format(timenow.tm_hour, timenow.tm_min,timenow.tm_sec)
        self.text_areas[4].text = "{:3d}".format(self.instrument.batch_number)
        self.text_areas[5].text = "{}%".format(int(self.bat.percentage))
        if self.instrument.vfs:
            if self.status_index == 2:
                self.status_highlight.color_index = 2
            elif self.measuring:
                self.status_index = 1
                self.status_highlight.color_index = 3
            else:
                self.status_index = 0
                self.status_highlight.color_index = 5
        else:
            self.status_index = 4
            self.status_highlight.color_index = 2
        self.text_areas[6].text = self.status_list[self.status_index]

    def action( self ):
        if self.instrument.encoder_increment != 0:
            if self.field_selected:
                if self.selection == 3:
                    pass
            self.instrument.encoder_increment = 0
            self.update_values()

        if self.instrument.button_pressed:
            if self.selection == 9 or self.selection == 10 or self.selection == 11 or not self.graph_group.hidden:
                self.graph_group.hidden = not self.graph_group.hidden
                if not self.graph_group.hidden:
                    self.plot()
            elif self.selection == 0:
                self.instrument.active_page_number = self.instrument.pages_dict["Main"]
            elif self.selection == 1:
                self.instrument.update_batch()
            elif self.selection == 2:
                self.mmt_sequence_start = time.monotonic()

            else:
                self.field_selected = not self.field_selected
                if self.selection == 3:
                    pass
                    if False:
                        if self.field_selected:
                            self.value_areas[3].color_index = self.field_selected_color_index
                        else:
                            self.value_areas[3].color_index = self.field_not_selected_color_index

            self.instrument.button_pressed = False
            self.update_values()

    def run_measurement_sequence(self):
        self.as7341_spectrometer.set_integration_time( self.integration_time_index)
        self.as7341_spectrometer.set_gain( self.gain_index)
        if self.status_index == 0 or self.status_index == 2:
            print( "gps has fix:", self.gps.has_fix )
            self.mmt_number += 1
            gc.collect()
            measure_start_free = gc.mem_free()
            uid = self.instrument.uid
            mmt_time = self.instrument.iso_time
            dec_time = self.instrument.decimal_time

            self.bat.read()

            header_line = "UID,iso8601,time hh.hh, 5V supply V,bat V,bat pct"
            header_line += ",gps lat,gps long,gps alt"

            try:
                self.onboard_neopixel.fill(devicem_neopixel.GREEN)
                functionm_file.write_nonsystem_line( self.instrument, header_line)
                for row in range (0,self.lines_per_block):
                    line = "{},".format(uid)
                    line += "{},".format(mmt_time)
                    line += "{},".format(dec_time)
                    line += "{},".format(self.supply_5V.voltage)
                    line += "{},".format(self.bat.voltage)
                    line += "{},".format(self.bat.percentage)
                    line += "{},".format(self.gps.latitude)
                    line += "{},".format(self.gps.longitude)
                    line += "{},".format(self.gps.altitude)

                    functionm_file.write_nonsystem_line( self.instrument, line)
                self.onboard_neopixel.fill(devicem_neopixel.OFF)
                print("data written to file")
            except Exception as err:
                print("failed to write data to file:", err)
                self.instrument.vfs = False
                self.onboard_neopixel.fill(devicem_neopixel.RED)
            print()
            for row in range (0,self.lines_per_block):
                for col in range (0,len(self.measurement_lists)):
                    print( self.measurement_lists[col][row], end=", " )
                print()

            self.measurement_lists = []
            if self.last_lamp_current_mA < self.low_current_warning_threshold_mA: self.status_index = 2
            measure_stop_free = gc.mem_free()

        else:
            print("error, not available to measure")
            #set measure button to grey


    def measure(self):
        pass

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
        batch_highlight = vectorio.Rectangle(pixel_shader=self.palette, color_index=12, width=56-2*select_width,
                                                            height=height_2-2*select_width, x=42, y=line_y+height_1+select_width)
        self.group.append(batch_highlight)
        self.status_highlight = vectorio.Rectangle(pixel_shader=self.palette, color_index=5, width=54-2*select_width+14,
                                                            height=height_2-2*select_width, x=154, y=line_y+height_1+select_width)
        self.group.append(self.status_highlight)
        line_names = ["inc", "batch", "battery", "status", "self-test/reset" ]
        line_values = ["B+","---", "---", "----", "S-TEST"] #RESET #_STOP_
        line_selectable = [ True, False, False, False, True ]
        line_widths = [38,52,58,70,100]
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
                self.area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]-2*select_width,
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


        self.selection_count = len( self.selection_rectangles )

        #graph group

        self.graph_group = displayio.Group()
        self.graph_border = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=280+8, height=200, x=20-4, y=42-4)
        self.graph_group.append(self.graph_border)
        self.graph_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=280, height=200-8, x=20, y=42)
        self.graph_group.append(self.graph_rectangle)
        self.graph_group.hidden = True

        self.ybottom_pix = 240-8-20
        self.ytop_pix = 72

        plot_title_group = displayio.Group(scale=2, x=80, y=54)
        self.plot_title_area = label.Label(terminalio.FONT, text="Bxx : Mxx : xx%dr", color=self.palette[0])
        plot_title_group.append(self.plot_title_area)
        self.graph_group.append(plot_title_group)

        y_units_group = displayio.Group(scale=1, x=26, y=50)
        y_units_area = label.Label(terminalio.FONT, text="counts", color=self.palette[0])
        y_units_group.append(y_units_area)
        self.graph_group.append(y_units_group)

        y_max_group = displayio.Group(scale=1, x=26, y=68)
        self.y_max_area = label.Label(terminalio.FONT, text="65535", color=self.palette[0])
        y_max_group.append(self.y_max_area)
        self.graph_group.append(y_max_group)

        y_min_group = displayio.Group(scale=1, x=26, y=self.ybottom_pix)
        self.y_min_area = label.Label(terminalio.FONT, text="-65535", color=self.palette[0])
        y_min_group.append(self.y_min_area)
        self.graph_group.append(y_min_group)

        x_units_group = displayio.Group(scale=1, x=26, y=self.ybottom_pix+14)
        x_units_area = label.Label(terminalio.FONT, text="WL(nm)", color=self.palette[0])
        x_units_group.append(x_units_area)
        self.graph_group.append(x_units_group)

        point_radius = 6

        xleft_pix = 64
        xright_pix = 320-30
        xspan_pix = xright_pix - xleft_pix

        x_axis_pix = 4
        self.x_axis = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=xright_pix-xleft_pix, height=x_axis_pix, x=xleft_pix, y=self.ybottom_pix-int(x_axis_pix/2))
        self.graph_group.append(self.x_axis)

        plot_xvalues = [415, 445, 480, 515, 555, 590, 630, 682]
        plot_xmax = 700
        plot_xmin = 400
        plot_xspan = plot_xmax - plot_xmin
        self.plot_xpix = []

        for xvalue in plot_xvalues:
            self.plot_xpix.append(int((xspan_pix*(xvalue-plot_xmin)/plot_xspan)+xleft_pix))
        #print(plot_xpix)
        self.shading_points = []
        for xpix in self.plot_xpix:
            self.shading_points.append((xpix, 0))

        self.shading = vectorio.Polygon(pixel_shader=self.palette, color_index=8,points=self.shading_points)
        self.graph_group.append(self.shading)

        self.plot_points=[]
        for xpix in self.plot_xpix:
            circle = vectorio.Circle(pixel_shader=self.palette, color_index=9, radius = point_radius, x=xpix, y=self.ybottom_pix)
            self.plot_points.append(circle)
            self.graph_group.append(circle)
        color_index_list = [25,26,28,29,31,32,33,35]
        for index in range( 0, len(self.plot_points)):
            self.plot_points[index].color_index = color_index_list[index]
            x_value_group = displayio.Group(scale=1, x=self.plot_xpix[index]-8, y=self.ybottom_pix+14)
            x_value_area = label.Label(terminalio.FONT, text="{}".format(plot_xvalues[index]), color=self.palette[0])

            x_value_group.append(x_value_area)
            self.graph_group.append(x_value_group)

        self.group.append(self.graph_group)

        return self.group

    def update_selection( self ):
        self.selection_rectangles[self.last_selection].hidden = True
        self.selection_rectangles[self.selection].hidden = False

    def hide_all_selections( self ):
        for item in self.selection_rectangles:
            if item.hidden == False:
                item.hidden = True



class Calibration_Missing_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.page_name = "Calibration"
        self.instrument = instrument
        self.palette = instrument.palette
        self.selection = 0
        self.selection_count = 0
        self.field_selected = False
    def make_group( self ):
        self.group = displayio.Group()
        status_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240, x=0, y=0 )
        self.group.append( status_background )
        text_spacing_y = 28
        status_title_group = displayio.Group(scale=2, x=10, y=18)
        status_title_text = "Calibration not available"
        status_title_text_area = label.Label(terminalio.FONT, text=status_title_text, color=self.palette[0])
        status_title_group.append(status_title_text_area)
        self.group.append(status_title_group)

        text_group = displayio.Group(scale=2, x=10, y=18+text_spacing_y)
        text = "connect TBD"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)

        text_group = displayio.Group(scale=2, x=10, y=18+2*text_spacing_y)
        text = "and restart"
        text_area = label.Label(terminalio.FONT, text=text, color=self.palette[0])
        text_group.append(text_area)
        self.group.append(text_group)


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
        self.return_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=return_select_width, height=return_select_height, x=return_select_x, y=return_select_y)
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
    def hide_all_selections( self ):
        pass
    def action( self ):
        self.instrument.active_page_number = self.instrument.pages_dict["Main"]
    def update_selection( self ):
        pass
    def update_plot( self ):
        pass

def make_calibration_missing_page( instrument, onboard_neopixel ):
    instrument.welcome_page.announce( "make_calibration_missing_page" )
    page = Calibration_Missing_Page( instrument, onboard_neopixel)
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page




def make_calibration_page( instrument, onboard_neopixel ):
    instrument.welcome_page.announce( "make_calibration_page" )
    page = Calibration_Page( instrument, onboard_neopixel )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page
