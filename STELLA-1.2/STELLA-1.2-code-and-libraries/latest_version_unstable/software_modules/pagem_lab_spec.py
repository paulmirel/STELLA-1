# Lab_Spec page
# version 2.1
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import displayio
from adafruit_display_text import label
import vectorio
import terminalio
from .classm_page import Page
from software_modules import functionm_file, devicem_neopixel
import time
import gc



class Lab_Spec_Page( Page ):
    def __init__( self, instrument, as7341_spectrometer, onboard_neopixel):
        super().__init__()
        self.page_name = "Lab_Spec"
        self.instrument = instrument
        self.palette = instrument.palette
        self.as7341_spectrometer = as7341_spectrometer
        self.onboard_neopixel = onboard_neopixel
        self.selection = 0
        self.last_selection = 0
        self.selection_count = 0
        self.selection_rectangles = []
        self.field_selected = False
        self.field_selected_color_index = 5
        self.field_not_selected_color_index = 9
        self.chA_index = 3
        self.chB_index = 2
        self.number_of_channels = 8 #TBD for alternate sensors
        self.active_sensor_index = 0
        self.max_counts = 65535
        self.exposure_target_fraction_high = 0.9
        self.exposure_target_fraction_low = 0.5
        self.number_of_sensors = 1
        self.gain_index = 8
        self.as7341_spectrometer.set_gain( self.gain_index )
        self.integration_time_index = 19
        self.as7341_spectrometer.set_integration_time( self.integration_time_index )
        self.status_index = 0
        self.status_list = ["OK","BUSY","0mA","LOWB","NOSD","FAIL"]
        self.adc_sensor = False
        self.supply_5V = False
        self.supply_5V_on = False
        self.dac = False
        for sensor in self.instrument.sensors_present:
            if sensor.pn == "ads1015":
                self.adc_sensor = sensor
            if sensor.name == "supply_5V":
                self.supply_5V = sensor
            if sensor.pn == "mcp4728":
                self.dac = sensor
            if sensor.pn == "max1704x":
                self.bat = sensor
            if sensor.name == "gps":
                self.gps = sensor

        if self.adc_sensor:
            self.adc_sensor.swob.gain = self.adc_sensor.gain_list[3] #set ADC gain to 4x, for 0 to 1.024V
        self.mmt_number = 0
        self.dac_values = [0,0,0,0]
        self.dac_channels = ["a", "b", "c", "d"]
        self.lamp_current_index = 9 # default
        self.lamp_current_options = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,22,24,26,28,30,35,40,45,50,60,70,80,90,100]
        self.last_lamp_current_mA = "None"
        self.file_write_request = False
        self.mmt_number = 0
        self.measuring = False
        self.mmt_sequence_start = 0
        self.mmt_interval = 10
        self.repetitions = 4 # including source off mmt
        self.lamp_on = False
        self.display_data = []
        #self.display_data[0] = " "," "," "," "," "
        #self.display_data[1] = " "," "," "," "," "
        #self.display_data[2] = " "," "," "," "," "
        self.supply_5V.disable()
        self.last_lamp_currents = []
        self.measurement_lists = []
        self.lines_per_block = 10
        self.lamps = [("488nm","scattr"),("365nm","scattr"),("640nm","scattr"),("white","x-mit"),("white","reflct")]
        self.lamp_in_use = 0
        self.number_of_lamps = 5


    def set_lamp_current(self, req_index):
        self.all_lamps_off()
        req_current_percent = self.lamp_current_options[ req_index ]
        set_min = 12000#13000
        set_max = 30000 #65535
        set_span = set_max - set_min
        set_value = int( req_current_percent/100 * set_span + set_min )
        if set_value > set_max: set_value = set_max
        if self.lamp_in_use < self.number_of_lamps - 1:
            self.dac.set( self.dac_channels[self.lamp_in_use], set_value )
        return set_value

    def all_lamps_off(self):
        self.dac.set("a", 0)
        self.dac.set("b", 0)
        self.dac.set("c", 0)
        self.dac.set("d", 0)


    def right_justify(self,value):
        if value<10:
            text = "    {}".format(value)
        if value<100:
            text = "   {}".format(value)
        if value<1000:
            text = "  {}".format(value)
        if value<10000:
            text = " {}".format(value)
        else:
            text = "{}".format(value)
        return text

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
            note = "note goes here"
            instruction = "instruction goes here"
            lamp_wl = self.lamps[self.lamp_in_use][0]
            #TBD lamp_pn = "GC VJLPL1.13-KQKS-V2V3-1"
            light_path = self.lamps[self.lamp_in_use][1]
            gain = self.as7341_spectrometer.gain_list[ self.gain_index]
            int_time = self.as7341_spectrometer.integration_time_ms_list[ self.integration_time_index ]
            parameters = ["lamp mA before", 415, 445, 480, 515, 555, 590, 630, 682, "lamp mA after"]
            self.supply_5V.disable()
            # move previous data down one line on the display
            tag_column = []
            for row in range (0,self.lines_per_block):
                tag_column.append("B{:02}_M{:02}_{:02}".format(self.instrument.batch_number, self.mmt_number, row))
            self.measurement_lists.append(tag_column)
            dwell_s = 0.5 ## to allow chemistry to respond to excitation and to separate measurements, both for consistency
            self.measuring = True
            self.update_values() #to show the current mmt number
            data = []
            saturated = False
            for n in range (0, self.repetitions):
                if n > 0:
                    self.supply_5V.enable()
                time.sleep(dwell_s)
                self.supply_5V.read()
                data_column = self.measure()
                if max(data_column) > 65534:
                    saturated = True
                data.append(data_column)
                self.measurement_lists.append(data_column)
                del data_column
                self.supply_5V.disable()
                time.sleep(dwell_s)
            self.measuring = False
            stop = time.monotonic()
            self.sequence_elapsed_s = stop - self.mmt_sequence_start
            print( "sequence elapsed time = {}s".format(self.sequence_elapsed_s))
            avg_column = []
            for row in range (0,self.lines_per_block):
                avg_column.append(int(round(((data[1][row] + data[2][row] + data[3][row])/3)-data[0][row],0)))
            self.measurement_lists.append(avg_column)
            dr_column = []
            dr_column.append(" ")
            bw_column = []
            bw_column.append(" ")
            for row in range (1,self.lines_per_block-1):
                dr_column.append(round(100*avg_column[row]/65535,1))
                bw_column.append(self.as7341_spectrometer.bandwidths_nm[row-1])
            dr_column.append(" ")
            bw_column.append(" ")
            self.measurement_lists.append(dr_column)
            self.measurement_lists.append(bw_column)
            norm_ct_column =[]
            norm_ct_column.append(" ")
            for row in range (1,self.lines_per_block-1):
                norm_ct_column.append( avg_column[row] / bw_column[row] /  gain /  int_time )
            norm_ct_column.append(" ")
            self.measurement_lists.append(norm_ct_column)
            current_before_after_average = round((avg_column[0]+avg_column[self.lines_per_block-1])/2,1)
            if current_before_after_average < 0.01: current_before_after_average = 0.01
            norm_ct_per_a =[]
            norm_ct_per_a.append(" ")
            for row in range (1,self.lines_per_block-1):
                norm_ct_per_a.append(1000*1000*norm_ct_column[row]/current_before_after_average)
            norm_ct_per_a.append(" ")
            self.measurement_lists.append(norm_ct_per_a)

            self.bat.read()

            header_line = "UID,iso8601,time hh.hh,note,instruction,lamp wavelength nm,lamp pn,lamp location"
            header_line += ",batch,mmt,tag,parameter/band,rep 0,rep 1,rep 2,rep 3,average,DR_pct,gain,int_time ms"
            header_line += ",bandwidth nm,ct/nm/[gain]/ms,avg current mA,cts/nm/s/A,5V supply V,bat V,bat pct"
            header_line += ",gps lat,gps long,gps alt"

            try:
                self.onboard_neopixel.fill(devicem_neopixel.GREEN)
                functionm_file.write_nonsystem_line( self.instrument, header_line)
                for row in range (0,self.lines_per_block):
                    line = "{},".format(uid)
                    line += "{},".format(mmt_time)
                    line += "{},".format(dec_time)
                    line += "{},".format(note)
                    line += "{},".format(instruction)
                    line += "{},".format(lamp_wl)
                    line += "{},".format("lamp_pn TBD")
                    line += "{},".format(light_path)
                    line += "{},".format(self.instrument.batch_number)
                    line += "{},".format(self.mmt_number)
                    line += "{},".format(tag_column[row])
                    line += "{},".format(parameters[row])
                    line += "{},".format(self.measurement_lists[1][row])
                    line += "{},".format(self.measurement_lists[2][row])
                    line += "{},".format(self.measurement_lists[3][row])
                    line += "{},".format(self.measurement_lists[4][row])
                    line += "{},".format(avg_column[row])
                    line += "{},".format(dr_column[row])
                    line += "{},".format(gain)
                    line += "{},".format(int_time)
                    line += "{},".format(bw_column[row])
                    line += "{},".format(norm_ct_column[row])
                    line += "{},".format(current_before_after_average)
                    line += "{},".format(norm_ct_per_a[row])
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






            if True:
                for row in range (0,self.lines_per_block):
                    for col in range (0,len(self.measurement_lists)):
                        print( self.measurement_lists[col][row], end=", " )
                    print()


            b_value = avg_column[self.chB_index+1]
            if b_value < 1:
                b_value = 1
            a_b_values = avg_column[self.chA_index+1], b_value
            if a_b_values[1] < 1:
                a_b_values[1] = 1
            a_b_ratio = round(a_b_values[0]/a_b_values[1],1)
            pct_dr = int(round( 100* max(a_b_values)/65535, 1))
            if saturated:
                pct_dr = "sa" #"OL" #"S1" "sa"

            print( self.mmt_number, a_b_values[0], a_b_values[1],a_b_ratio,pct_dr)
            if self.mmt_number>99:
                mmt_text = "{}".format(self.mmt_number)
            else:
                mmt_text = "M{:02}".format(self.mmt_number)
            if True:
                self.display_data.insert(0,(mmt_text, self.right_justify(a_b_values[0]), self.right_justify(a_b_values[1]), a_b_ratio, pct_dr))
                self.display_data = self.display_data[:3] # list slicing, keep only first three elements
                #update these only on a new mmt having been made
                location = 18
                for y in range (0,len(self.display_data)):
                    for x in range (0, 5):
                        self.text_areas[location].text = "{}".format(self.display_data[y][x])
                        location += 1
            # save data out to display register and to file_write_request
            # use the same file, but write a header line before every block
            # then clear the measurement_lists
            self.measurement_lists = []
            if self.last_lamp_current_mA < 0.01: self.status_index = 2
            measure_stop_free = gc.mem_free()
        else:
            print("error, not available to measure")
            #set measure button to grey

    def measure(self):

        timeout_interval = 5
        timeout = False
        data_ready = False
        current_before = self.get_lamp_current()
        self.as7341_spectrometer.swob._configure_f1_f4()
        start = time.monotonic()
        print("begin f1-f4 channel detect")
        while not data_ready and not timeout:
            data_ready = self.as7341_spectrometer.swob._data_ready_bit
            print(".", end = "")
            time.sleep(0.01)
            if time.monotonic() > start + timeout_interval:
                timeout = True
        stop = time.monotonic()
        print()
        print( "f1-f4 elapsed time = {}s".format(stop-start))
        f1,f2,f3,f4 = self.as7341_spectrometer.swob.read_channel_register
        #print(f1,f2,f3,f4)

        self.as7341_spectrometer.swob._configure_f5_f8()
        start = time.monotonic()
        print("begin f5-f8 channel detect")
        data_ready = False
        while not data_ready and not timeout:
            data_ready = self.as7341_spectrometer.swob._data_ready_bit
            print(".", end = "")
            time.sleep(0.01)
            if time.monotonic() > start + timeout_interval:
                timeout = True
        stop = time.monotonic()
        print()
        print( "f5-f8 elapsed time = {}s".format(stop-start))
        current_after = self.get_lamp_current()
        f5,f6,f7,f8 = self.as7341_spectrometer.swob.read_channel_register
        #print(f5,f6,f7,f8)
        return (current_before,f1,f2,f3,f4,f5,f6,f7,f8,current_after)

    def update_values( self ):
        self.gps.read()
        # this is taking too long. Need to be selective about what we update and skip everything else
        start = time.monotonic()
        # always update these
        timenow = self.instrument.hardware_clock.read()
        self.text_areas[0].text = "{}-{:02}-{:02}".format(timenow.tm_year,timenow.tm_mon, timenow.tm_mday)
        self.text_areas[1].text = "{:02}:{:02}:{:02}".format(timenow.tm_hour, timenow.tm_min,timenow.tm_sec)
        self.text_areas[3].text = self.lamps[self.lamp_in_use][0]
        self.text_areas[4].text = self.lamps[self.lamp_in_use][1]

        self.text_areas[11].text = "{}".format(self.instrument.batch_number)
        if self.instrument.vfs:
            if self.status_index == 2:
                self.status_highlight.color_index = 2
            elif self.measuring:
                self.status_index = 1
                self.status_highlight.color_index = 4
            else:
                self.status_index = 0
                self.status_highlight.color_index = 5
        else:
            self.status_index = 4
            self.status_highlight.color_index = 2
        self.text_areas[8].text = self.status_list[self.status_index]

        self.set_lamp_current(self.lamp_current_index)
        self.as7341_spectrometer.set_gain(self.gain_index)
        gain = self.as7341_spectrometer.gain_list[self.gain_index]
        self.text_areas[9].text = "{}".format(gain)
        self.as7341_spectrometer.set_integration_time(self.integration_time_index)
        integration_time_ms = self.as7341_spectrometer.integration_time_ms_list[self.integration_time_index]
        if integration_time_ms < 1000:
            self.text_areas[10].text = "{}ms".format(integration_time_ms)
        else:
            self.text_areas[10].text = "{}s".format(round(integration_time_ms/1000,1))
        self.text_areas[5].text = "{}nm".format(self.as7341_spectrometer.wavelength_bands_nm[self.chA_index])
        self.text_areas[6].text = "{}nm".format(self.as7341_spectrometer.wavelength_bands_nm[self.chB_index])
        if self.chA_index == self.chB_index:
            if self.selection == 3:
                self.value_areas[4].color_index = 4
            if self.selection == 4:
                self.value_areas[3].color_index = 4
        else:
            if self.selection == 3:
                self.value_areas[4].color_index = 9
            if self.selection == 4:
                self.value_areas[3].color_index = 9
        if self.selection == 5 and self.field_selected:
            self.text_areas[7].text = "{}%".format(self.lamp_current_options[self.lamp_current_index])
        else:
            if type(self.last_lamp_current_mA) == str:
                self.text_areas[7].text = "{}".format(self.last_lamp_current_mA)
            else:
                if self.last_lamp_current_mA < 10:
                    self.text_areas[7].text = "{}mA".format(self.last_lamp_current_mA)
                else:
                    self.text_areas[7].text = "{}mA".format(int(round(self.last_lamp_current_mA,0)))


    stop = time.monotonic()
    #print( "update values takes {}s".format(stop-start))



    def action( self ):
        if self.instrument.encoder_increment != 0:
            if self.field_selected:
                if self.selection == 1:
                    self.lamp_in_use = ( self.lamp_in_use + self.instrument.encoder_increment)
                    if self.lamp_in_use > self.number_of_lamps -1 :
                        self.lamp_in_use = self.number_of_lamps -1
                    if self.lamp_in_use < 0:
                        self.lamp_in_use = 0
                if self.selection == 3:
                    self.chA_index = ( self.chA_index + self.instrument.encoder_increment)
                    if self.chA_index > self.number_of_channels -1 :
                        self.chA_index = self.number_of_channels -1
                    if self.chA_index < 0:
                        self.chA_index = 0
                if self.selection == 4:
                    self.chB_index = ( self.chB_index + self.instrument.encoder_increment)
                    if self.chB_index > self.number_of_channels -1 :
                        self.chB_index = self.number_of_channels -1
                    if self.chB_index < 0:
                        self.chB_index = 0
                if self.selection == 5:
                    self.lamp_current_index += self.instrument.encoder_increment
                    if self.lamp_current_index > len (self.lamp_current_options) -1:
                        self.lamp_current_index = len (self.lamp_current_options) -1
                    if self.lamp_current_index < 0:
                        self.lamp_current_index = 0
                if self.selection == 6:
                    self.gain_index = (self.gain_index + self.instrument.encoder_increment )
                    if self.gain_index > len(self.as7341_spectrometer.gain_list) - 1:
                        self.gain_index = len(self.as7341_spectrometer.gain_list) - 1
                    if self.gain_index < 0:
                        self.gain_index = 0
                    self.as7341_spectrometer.set_gain( self.gain_index )
                if self.selection == 7:
                    self.integration_time_index = (self.integration_time_index + self.instrument.encoder_increment )
                    if self.integration_time_index > len(self.as7341_spectrometer.integration_time_ms_list) - 1:
                        self.integration_time_index = len(self.as7341_spectrometer.integration_time_ms_list) - 1
                    if self.integration_time_index < 0:
                        self.integration_time_index = 0
                    self.as7341_spectrometer.set_integration_time( self.integration_time_index )


            self.instrument.encoder_increment = 0
            self.update_values()

        if self.instrument.button_pressed:
            if self.selection == 0:
                self.instrument.active_page_number = self.instrument.pages_dict["Main"]
            elif self.selection == 8:
                self.instrument.update_batch()
            elif self.selection == 9:
                self.mmt_sequence_start = time.monotonic()
                self.run_measurement_sequence()
            else:
                self.field_selected = not self.field_selected
                if self.selection == 1:
                    if self.field_selected:
                        self.value_areas[1].color_index = self.field_selected_color_index
                    else:
                        self.value_areas[1].color_index = self.field_not_selected_color_index
                if self.selection == 3:
                    if self.field_selected:
                        self.value_areas[3].color_index = self.field_selected_color_index
                    else:
                        self.value_areas[3].color_index = self.field_not_selected_color_index
                if self.selection == 4:
                    if self.field_selected:
                        self.value_areas[4].color_index = self.field_selected_color_index
                    else:
                        self.value_areas[4].color_index = self.field_not_selected_color_index
                if self.selection == 5:
                    if self.field_selected:
                        self.value_areas[5].color_index = self.field_selected_color_index
                        self.set_current_text_area.text = "REQ current"
                    else:
                        self.value_areas[5].color_index = self.field_not_selected_color_index
                        self.set_current_text_area.text = "last current"
                if self.selection == 6:
                    if self.field_selected:
                        self.value_areas[6].color_index = self.field_selected_color_index
                    else:
                        self.value_areas[6].color_index = self.field_not_selected_color_index
                if self.selection == 7:
                    if self.field_selected:
                        self.value_areas[7].color_index = self.field_selected_color_index
                    else:
                        self.value_areas[7].color_index = self.field_not_selected_color_index
            self.instrument.button_pressed = False
            self.update_values()


    def get_lamp_current(self):
        if self.adc_sensor:
            self.adc_sensor.read()
            lamp_currrent_voltage = self.adc_sensor.voltage[0]
        else:
            lamp_currrent_voltage = 0
        self.last_lamp_current_mA = round(lamp_currrent_voltage*1000,2)
        return self.last_lamp_current_mA

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
        line_names = ["excitation", "light path", "inspect A", "inspect B" ]
        line_values = ["488nm","scattr", " --", " --"] #"x-mit" "reflct"
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
        batch_line_y = line_y
        #batch_highlight = vectorio.Rectangle(pixel_shader=self.palette, color_index=12, width=48-2*select_width,
        #                                                    height=height_2-2*select_width, x=138, y=line_y+height_1+select_width)
        #self.group.append(batch_highlight)


        self.status_highlight = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=54-2*select_width+4,
                                                            height=height_2-2*select_width, x=84, y=batch_line_y+height_1+select_width)
        self.group.append(self.status_highlight)

        line_names = ["last current", "status" ]
        line_values = [" -- ", " --"]
        line_selectable = [ True, False ]
        line_widths = [78, 54]
        x = start_x
        for index in range(0, len(line_names)):
            text_group = displayio.Group(scale=1, x=x+offset_1, y=line_y+int(height_1/2))
            if index == 0:
                self.set_current_text_area = label.Label(terminalio.FONT, text=line_names[index], color=self.palette[0])
                text_group.append(self.set_current_text_area)
            else:
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
        line_names = ["gain", "mmt#", "A value", "B value", "A/B", "%DR" ]
        line_values = [" --", "", "", "", "", ""]
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
            if index == 0:
                text_group = displayio.Group(scale=2, x=x+offset_2, y=line_y+height_1 +int(height_2/2))
                self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
                self.text_areas.append(self.text_area)
                text_group.append(self.text_area)
                self.group.append(text_group)

            x += line_widths[index]

        line_y += line_spacing
        line_names = ["integration" ]
        line_values = [" -- "]
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


        batch_highlight = vectorio.Rectangle(pixel_shader=self.palette, color_index=12, width=48-2*select_width,
                                                            height=height_2-2*select_width, x=138, y=batch_line_y+height_1+select_width)
        self.group.append(batch_highlight)


        line_names = ["batch", "+=1", "measure & log" ]
        line_values = ["--", "B+", "MEASURE"]
        line_selectable = [ False, True, True ]
        line_widths = [48, 38, 100]
        x = 78+ 54
        for index in range(0, len(line_names)):
            text_group = displayio.Group(scale=1, x=x+offset_1, y=batch_line_y+int(height_1/2))
            text_area = label.Label(terminalio.FONT, text=line_names[index], color=self.palette[0])
            text_group.append(text_area)
            self.group.append(text_group)
            if line_selectable[index]:
                selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index],
                                                                    height=height_2, x=x, y=batch_line_y+height_1)
                selection_rectangle.hidden = True
                self.group.append(selection_rectangle)
                self.selection_rectangles.append(selection_rectangle)

                border_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]-2*(select_width-border_width),
                                                                    height=height_2-2*(select_width-border_width), x=x+select_width-border_width, y=batch_line_y+height_1+select_width-border_width)
                self.group.append(border_rectangle)

                self.area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=line_widths[index]-2*select_width,
                                                            height=height_2-2*select_width, x=x+select_width, y=batch_line_y+height_1+select_width)
                self.group.append(self.area_rectangle)
                self.value_areas.append(self.area_rectangle)

            text_group = displayio.Group(scale=2, x=x+offset_2, y=batch_line_y+height_1 +int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)

            x += line_widths[index]
        self.value_areas[-2].color_index = 12
        self.value_areas[-1].color_index = 5


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
        line_values = ["", "", "", "", ""]
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
        line_values = ["", "", "", "", ""]
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
        line_values = ["", "", "", "", ""]
        line_widths = [42, 66, 66, 42, 30 ]
        x = 78
        for index in range(0, len(line_values)):

            text_group = displayio.Group(scale=2, x=x, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)
            vertical_separator = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=1,height=80, x=x+line_widths[index]-4, y=124)
            self.group.append(vertical_separator)

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







def make_lab_spec_page( instrument, as7341_spectrometer, onboard_neopixel ):
    instrument.welcome_page.announce( "make_lab_spec_page" )
    page = Lab_Spec_Page( instrument, as7341_spectrometer, onboard_neopixel )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page

class Lab_Spec_Missing_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.page_name = "Lab_Spec"
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
        status_title_text = "Lab_Spec sensors not found:"
        status_title_text_area = label.Label(terminalio.FONT, text=status_title_text, color=self.palette[0])
        status_title_group.append(status_title_text_area)
        self.group.append(status_title_group)

        text_group = displayio.Group(scale=2, x=10, y=18+text_spacing_y)
        text = "connect Lab_Spec plugin "
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
    def hide_all_selections( self ):
        pass
    def action( self ):
        self.instrument.active_page_number = self.instrument.pages_dict["Main"]
    def update_selection( self ):
        pass
    def update_plot( self ):
        pass

def make_lab_spec_missing_page( instrument ):
    instrument.welcome_page.announce( "make_lab_spec_missing_page" )
    page = Lab_Spec_Missing_Page( instrument )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page
