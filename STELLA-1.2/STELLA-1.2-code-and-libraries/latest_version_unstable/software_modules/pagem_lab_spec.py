# Lab_Spec page
# version 2.4
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


class Lab_Spec_Page( Page ):
    def __init__( self, instrument, onboard_neopixel):
        super().__init__()
        self.page_name = "Lab_Spec"
        self.instrument = instrument
        self.palette = instrument.palette
        self.onboard_neopixel = onboard_neopixel
        self.selection = 0
        self.last_selection = 0
        self.selection_count = 0
        self.selection_rectangles = []
        self.field_selected = False
        self.field_selected_color_index = 5
        self.field_not_selected_color_index = 9
        if True: # sensor specific selections
            for spectral_sensor in self.instrument.spectral_sensors_present:
                if spectral_sensor.pn == "as7341":
                    self.as7341_spectrometer = spectral_sensor
            self.chA_index = 3
            self.chB_index = 2
            self.number_of_channels = 8
            self.gain_index = 8
            self.as7341_spectrometer.set_gain( self.gain_index )
            self.integration_time_index = 19
            self.as7341_spectrometer.set_integration_time( self.integration_time_index )
            self.number_of_sensors = 1
        self.active_sensor_index = 0
        self.max_counts = 65535
        self.exposure_target_fraction_high = 0.9
        self.exposure_target_fraction_low = 0.5
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
        self.dac_values = [0,0,0,0]
        self.dac_channels = ["a", "b", "c", "d"]
        self.lamp_current_index = 26 # default
        self.lamp_current_options = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,22,24,26,28,30,35,40,45,50,60,70,80,90,100]
        self.last_lamp_current_mA = "None"
        self.mmt_number = 0
        self.measuring = False
        self.mmt_sequence_start = 0
        self.mmt_interval = 10
        self.repetitions = 4 # including source_off mmt
        self.lamp_on = False
        self.display_data = [(""),(""),("")]
        self.supply_5V.disable()
        self.last_lamp_currents = []
        self.measurement_lists = []
        self.lines_per_block = 10
        self.low_current_warning_threshold_mA = 0.01
        self.lamps = [("488nm",3,2),("365nm",1,0),("640nm",7,6),("x_wht",2,6),("r_wht",2,6)] #("lamp designation", chA_index, chB_index)
        self.lamp_in_use = 0
        self.number_of_lamps = len( self.lamps )
        self.plot_register = ["--","--", 0,0,0,0,0,0,0,0]
        self.mmt_register = [self.plot_register, self.plot_register, self.plot_register]

    def plot(self):
        self.plot_register = self.mmt_register[self.selection-9]
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


        # generate pixel values for flinging the points around
        # generate pixel value for setting the x axis bar position

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
                self.status_highlight.color_index = 4
            else:
                self.status_index = 0
                self.status_highlight.color_index = 5
        else:
            self.status_index = 4
            self.status_highlight.color_index = 2
        self.text_areas[6].text = self.status_list[self.status_index]
        self.text_areas[8].text = self.lamps[self.lamp_in_use][0]
        self.set_lamp_current(self.lamp_current_index)
        self.as7341_spectrometer.set_gain(self.gain_index)
        gain = self.as7341_spectrometer.gain_list[self.gain_index]
        if self.selection == 4 and self.field_selected:
            self.text_areas[9].text = "{}%".format(self.lamp_current_options[self.lamp_current_index])
        else:
            if type(self.last_lamp_current_mA) == str:
                self.text_areas[9].text = "{}".format(self.last_lamp_current_mA)
            else:
                if self.last_lamp_current_mA < 10:
                    self.text_areas[9].text = "{}mA".format(self.last_lamp_current_mA)
                else:
                    self.text_areas[9].text = "{}mA".format(int(round(self.last_lamp_current_mA,0)))
        self.text_areas[10].text = "{}".format(gain)
        self.as7341_spectrometer.set_integration_time(self.integration_time_index)
        integration_time_ms = self.as7341_spectrometer.integration_time_ms_list[self.integration_time_index]
        if integration_time_ms < 1000:
            self.text_areas[11].text = "{}ms".format(integration_time_ms)
        else:
            self.text_areas[11].text = "{}s".format(round(integration_time_ms/1000,1))
        self.text_areas[12].text = "{}nm".format(self.as7341_spectrometer.wavelength_bands_nm[self.chA_index])
        self.text_areas[13].text = "{}nm".format(self.as7341_spectrometer.wavelength_bands_nm[self.chB_index])
        if self.chA_index == self.chB_index:
            if self.selection == 7:
                self.value_areas[8].color_index = 4
            if self.selection == 8:
                self.value_areas[7].color_index = 4
        else:
            if self.selection == 8:
                self.value_areas[7].color_index = 9
            if self.selection == 7:
                self.value_areas[8].color_index = 9
        stop = time.monotonic()
        #print( "update values takes {}s".format(stop-start))
        for index in range (0, len(self.mmt_register)): #[self.plot_register, self.plot_register, self.plot_register]
            max_value = max(self.mmt_register[index][2:])
            a_value = self.mmt_register[index][self.chA_index+2]
            b_value = self.mmt_register[index][self.chB_index+2]
            if b_value < 1:
                b_value = 1
            a_b_ratio = round(a_value/b_value,1)
            if a_b_ratio < 10:
                pass
            else:
                a_b_ratio = int(a_b_ratio)
            pct_dr = int(round( 100* max_value/65535, 1))
            if pct_dr<100:
                pass
            else:
                pct_dr = "sa"
            if self.mmt_number>99:
                mmt_text = "{}".format(self.mmt_number)
            else:
                mmt_text = "M{:02}".format(self.mmt_number)
            self.display_data[index] = (self.mmt_register[index][1], "{:5d}".format(a_value), "{:5d}".format(b_value), a_b_ratio, pct_dr)





        location = 14
        for y in range (0,len(self.display_data)):
            for x in range (0, 5):
                self.text_areas[location].text = "{}".format(self.display_data[y][x])
                location += 1


    def action( self ):
        if self.instrument.encoder_increment != 0:
            if self.field_selected:
                if self.selection == 3:
                    self.lamp_in_use = ( self.lamp_in_use + self.instrument.encoder_increment)  % self.number_of_lamps
                    self.chA_index = self.lamps[self.lamp_in_use][1]
                    self.chB_index = self.lamps[self.lamp_in_use][2]
                if self.selection == 4:
                    self.lamp_current_index += self.instrument.encoder_increment
                    if self.lamp_current_index > len (self.lamp_current_options) -1:
                        self.lamp_current_index = len (self.lamp_current_options) -1
                    if self.lamp_current_index < 0:
                        self.lamp_current_index = 0
                if self.selection == 5:
                    self.gain_index = (self.gain_index + self.instrument.encoder_increment )
                    if self.gain_index > len(self.as7341_spectrometer.gain_list) - 1:
                        self.gain_index = len(self.as7341_spectrometer.gain_list) - 1
                    if self.gain_index < 0:
                        self.gain_index = 0
                    self.as7341_spectrometer.set_gain( self.gain_index )
                if self.selection == 6:
                    self.integration_time_index = (self.integration_time_index + self.instrument.encoder_increment )
                    if self.integration_time_index > len(self.as7341_spectrometer.integration_time_ms_list) - 1:
                        self.integration_time_index = len(self.as7341_spectrometer.integration_time_ms_list) - 1
                    if self.integration_time_index < 0:
                        self.integration_time_index = 0
                    self.as7341_spectrometer.set_integration_time( self.integration_time_index )
                if self.selection == 7:
                    self.chA_index = ( self.chA_index + self.instrument.encoder_increment)
                    if self.chA_index > self.number_of_channels -1 :
                        self.chA_index = self.number_of_channels -1
                    if self.chA_index < 0:
                        self.chA_index = 0
                if self.selection == 8:
                    self.chB_index = ( self.chB_index + self.instrument.encoder_increment)
                    if self.chB_index > self.number_of_channels -1 :
                        self.chB_index = self.number_of_channels -1
                    if self.chB_index < 0:
                        self.chB_index = 0
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
                self.run_measurement_sequence()


            else:
                self.field_selected = not self.field_selected
                if self.selection == 3:
                    if self.field_selected:
                        self.value_areas[3].color_index = self.field_selected_color_index
                    else:
                        self.value_areas[3].color_index = self.field_not_selected_color_index
                if self.selection == 4:
                    if self.field_selected:
                        self.value_areas[4].color_index = self.field_selected_color_index
                        self.set_current_text_area.text = "REQ current"
                    else:
                        self.value_areas[4].color_index = self.field_not_selected_color_index
                        self.set_current_text_area.text = "last current"
                if self.selection == 5:
                    if self.field_selected:
                        self.value_areas[5].color_index = self.field_selected_color_index
                    else:
                        self.value_areas[5].color_index = self.field_not_selected_color_index
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
                if self.selection == 8:
                    if self.field_selected:
                        self.value_areas[8].color_index = self.field_selected_color_index
                    else:
                        self.value_areas[8].color_index = self.field_not_selected_color_index
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
            print("average column:", avg_column)

            self.plot_register = []
            self.plot_register.append("B{:02}".format(self.instrument.batch_number))
            if True:
                self.plot_register.append("M{:02}".format(self.mmt_number))
            else:
                self.plot_register.append("R{:02}".format(self.mmt_number))
            for index in range(1, 9):
                self.plot_register.append(avg_column[index])
            #insert the plot register in the 0th position of the mmt_register, shift the others, and trim the list to 3
            self.mmt_register.insert(0,self.plot_register)
            self.mmt_register = self.mmt_register[:3]

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
        readout_list = current_before,f1,f2,f3,f4,f5,f6,f7,f8,current_after
        for index in range (0, len(readout_list)):
            if readout_list[index] < 0:
                readout_list[index] = 0
        return readout_list






    def set_lamp_current(self, req_index):
        self.all_lamps_off()
        req_current_percent = self.lamp_current_options[ req_index ]
        set_min = 12000#13000
        set_max = 20000 #65535
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

    def get_lamp_current(self):
        self.last_lamp_current_mA = 0
        if self.lamp_in_use < self.number_of_lamps - 1:
            if self.adc_sensor:
                self.adc_sensor.read()
                lamp_currrent_voltage = self.adc_sensor.voltage[self.lamp_in_use]
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
        batch_highlight = vectorio.Rectangle(pixel_shader=self.palette, color_index=12, width=56-2*select_width,
                                                            height=height_2-2*select_width, x=42, y=line_y+height_1+select_width)
        self.group.append(batch_highlight)
        self.status_highlight = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=54-2*select_width+14,
                                                            height=height_2-2*select_width, x=154, y=line_y+height_1+select_width)
        self.group.append(self.status_highlight)
        line_names = ["inc", "batch", "battery", "status", "measure & log" ]
        line_values = ["B+","---", "---", "----", "MEASURE"]
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

        line_names = ["excitation","last current"," gain","integration" ]
        line_values = ["--","--","--","--"]
        line_selectable = [ True,True,True,True ]
        line_widths = [90, 80, 68, 80]
        x = start_x
        for index in range(0, len(line_names)):
            text_group = displayio.Group(scale=1, x=x+offset_1, y=line_y+int(height_1/2))
            if index == 1:
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
        line_names = ["view A","mmt#", "A value", "B value", "A/B", "%DR" ]
        line_values = [" --","", "", "", "", "",""]
        line_selectable = [ True, False, False, False, False, False ]
        line_widths = [74,42,66,66,42,30]
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
        line_names = ["view B" ]
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

        view_B_line_y = line_y

        # measured values
        box_offset_y = -8
        box_offset_x = -5
        box_width_mod = 0#4
        box_position_mod = 2
        box_height_mod = -4
        value_width = 66 - int(box_position_mod/2)
        line_y = 128
        #line_names = ["mmt#", "A value", "B value", "A/B", "%DR" ]
        line_values = ["", "", "", "", ""]
        line_widths = [42, value_width, value_width, 42, 30 ]
        line_selectable = [True, False, False, False, False]
        x = 78+box_position_mod
        for index in range(0, len(line_values)):
            if line_selectable[index]:
                selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]+box_width_mod,
                                                                    height=height_2+box_height_mod, x=x+box_offset_x, y=line_y+height_1+box_offset_y)
                selection_rectangle.hidden = True
                self.group.append(selection_rectangle)
                self.selection_rectangles.append(selection_rectangle)
                if False:
                    border_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]+1-2*(select_width-border_width)+box_width_mod,
                                                                        height=height_2-2*(select_width-border_width), x=x+select_width-border_width+box_offset_x, y=line_y+height_1+select_width-border_width+box_offset_y)
                    self.group.append(border_rectangle)

                self.area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=line_widths[index]+1-2*select_width+box_width_mod,
                                                            height=height_2-2*select_width+box_height_mod, x=x+select_width+box_offset_x, y=line_y+height_1+select_width+box_offset_y)
                self.group.append(self.area_rectangle)
                self.value_areas.append(self.area_rectangle)
            text_group = displayio.Group(scale=2, x=x, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)

            x += line_widths[index]

        line_y += 24
        #line_names = ["mmt#", "A value", "B value", "A/B", "%DR" ]
        line_values = ["", "", "", "", ""]
        line_widths = [42, value_width, value_width, 42, 30 ]
        x = 78+box_position_mod
        line_selectable = [True, False, False, False, False]
        for index in range(0, len(line_values)):
            if line_selectable[index]:
                selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]+box_width_mod,
                                                                    height=height_2+box_height_mod, x=x+box_offset_x, y=line_y+height_1+box_offset_y)
                selection_rectangle.hidden = True
                self.group.append(selection_rectangle)
                self.selection_rectangles.append(selection_rectangle)
                if False:
                    border_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]+1-2*(select_width-border_width+box_width_mod),
                                                                        height=height_2-2*(select_width-border_width), x=x+select_width-border_width+box_offset_x, y=line_y+height_1+select_width-border_width+box_offset_y)
                    self.group.append(border_rectangle)

                self.area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=line_widths[index]+1-2*select_width+box_width_mod,
                                                            height=height_2-2*select_width+box_height_mod, x=x+select_width+box_offset_x, y=line_y+height_1+select_width+box_offset_y)
                self.group.append(self.area_rectangle)
                self.value_areas.append(self.area_rectangle)
            text_group = displayio.Group(scale=2, x=x, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)

            x += line_widths[index]

        line_y += 24
        #line_names = ["mmt#", "A value", "B value", "A/B", "%DR" ]
        line_values = ["", "", "", "", ""]
        line_widths = [42, value_width, value_width, 42, 30 ]
        x = 78+box_position_mod
        line_selectable = [True, False, False, False, False]
        for index in range(0, len(line_values)):
            if line_selectable[index]:
                selection_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]+box_width_mod,
                                                                    height=height_2+box_height_mod, x=x+box_offset_x, y=line_y+height_1+box_offset_y)
                selection_rectangle.hidden = True
                self.group.append(selection_rectangle)
                self.selection_rectangles.append(selection_rectangle)
                if False:
                    border_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=line_widths[index]+1-2*(select_width-border_width)+box_width_mod,
                                                                        height=height_2-2*(select_width-border_width), x=x+select_width-border_width+box_offset_x, y=line_y+height_1+select_width-border_width+box_offset_y)
                    self.group.append(border_rectangle)

                self.area_rectangle = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=line_widths[index]+1-2*select_width+box_width_mod,
                                                            height=height_2-2*select_width+box_height_mod, x=x+select_width+box_offset_x, y=line_y+height_1+select_width+box_offset_y)
                self.group.append(self.area_rectangle)
                self.value_areas.append(self.area_rectangle)
            text_group = displayio.Group(scale=2, x=x, y=line_y+int(height_2/2))
            self.text_area = label.Label(terminalio.FONT, text=line_values[index], color=self.palette[0])
            self.text_areas.append(self.text_area)
            text_group.append(self.text_area)
            self.group.append(text_group)
            vertical_separator = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=1,height=80, x=x+line_widths[index]-4, y=124)
            self.group.append(vertical_separator)

            x += line_widths[index]


        line_y = view_B_line_y+ line_spacing - 10
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
        self.x_axis = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=xright_pix-xleft_pix, height=x_axis_pix, x=xleft_pix, y=self.ybottom_pix-int(x_axis_pix/2))
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
            circle = vectorio.Circle(pixel_shader=self.palette, color_index=0, radius = point_radius, x=xpix, y=self.ybottom_pix)
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







def make_lab_spec_page( instrument, onboard_neopixel ):
    instrument.welcome_page.announce( "make_lab_spec_page" )
    page = Lab_Spec_Page( instrument, onboard_neopixel )
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
