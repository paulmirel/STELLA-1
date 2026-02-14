# Lab_Spec page
# version 2.0
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
        self.chA_index = 3
        self.chB_index = 2
        self.number_of_channels = 8 #TBD for alternate sensors
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
        self.lamp_current_index = 10
        self.lamp_current_options = [0,1,3,5,7,9,12,14,16,18,20,25,30,35,40,45,50,60,70,80,90,100,150,200,250,300,350,400,450,500,550,600]
        self.last_lamp_current_mA = "-- "
        self.file_write_request = False
        self.mmt_number = 0
        self.measuring = False
        self.mmt_sequence_start = 0
        self.mmt_interval = 10
        self.repetitions = 4 # including source off mmt
        self.lamp_on = False
        self.display_data = []
        self.display_data.append(("M00", 63218, 13827, 3.2, 10))
        self.display_data.insert(0,("M01", 43218, 19927, 2.2, 8))
        self.display_data.insert(0,("M03", 21218, 00927, 4.4, 99))

        self.supply_5V.disable()
        self.last_lamp_currents = []
        self.measurement_lists = []
        self.lines_per_block = 10
        self.request_write = False
        self.line_to_write = ""



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
        if self.status_index == 0:
            print( "gps has fix:", self.gps.has_fix )
            self.mmt_number += 1
            gc.collect()
            measure_start_free = gc.mem_free()
            uid = self.instrument.uid
            mmt_time = self.instrument.iso_time
            dec_time = self.instrument.decimal_time
            note = "note goes here"
            instruction = "instruction goes here"
            lamp_wl = "488nm"
            lamp_pn = "GC VJLPL1.13-KQKS-V2V3-1"
            lamp_loc = "bottom"
            gain = self.spectral_sensors[self.active_sensor_index].gain_list[ self.gain_index[self.active_sensor_index] ]
            int_time = self.spectral_sensors[self.active_sensor_index].integration_time_ms_list[ self.integration_time_index[self.active_sensor_index] ]
            parameters = ["lamp mA before", 415, 445, 480, 515, 555, 590, 630, 682, "lamp mA after"]
            self.supply_5V.disable()
            self.dac.set("a", 14000) # set to REQ current here
            #self.dac.set("a", 0) # turn off the DAC output so that the base current doesn't show
            # move previous data down one line on the display
            tag_column = []
            for row in range (0,self.lines_per_block):
                tag_column.append("B{:02}_M{:02}_{:02}".format(self.instrument.batch_number, self.mmt_number, row))
            self.measurement_lists.append(tag_column)
            dwell_s = 0.5 ## to allow chemistry to respond to excitation and to separate measurements, both for consistency
            self.measuring = True
            self.update_values() #to show the current mmt number
            data = []
            for n in range (0, self.repetitions):
                if n > 0:
                    self.supply_5V.enable()
                time.sleep(dwell_s)
                self.supply_5V.read()
                data_column = self.measure()
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
                bw_column.append(self.spectral_sensors[self.active_sensor_index].bandwidths_nm[row-1])
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
            if current_before_after_average <1:
                self.status_index = 2
                current_before_after_average = 1
            norm_ct_per_a =[]
            norm_ct_per_a.append(" ")
            for row in range (1,self.lines_per_block-1):
                norm_ct_per_a.append(1000*1000*norm_ct_column[row]/current_before_after_average)
            norm_ct_per_a.append(" ")
            self.measurement_lists.append(norm_ct_per_a)

            self.bat.read()

            header_line = "UID,iso8601,time hh.hh,note,instruction,lamp wavelength nm,lamp pn,lamp location"
            header_line += ",batch,mmt,tag,parameter/band,rep 0,rep 1,rep 2,rep 3,average,DR_pct,gain,int_time ms"
            header_line += ",bandwidth nm,ct/nm/[gain]/s,avg current mA,cts/nm/s/A,5V supply V,bat V,bat pct"
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
                    line += "{},".format(lamp_pn)
                    line += "{},".format(lamp_loc)
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




            #self.last_lamp_currents = self.last_lamp_currents[:2*self.repetitions]
            #self.last_lamp_current_mA = int(round(sum(self.last_lamp_currents)/len(self.last_lamp_currents),0))
            #self.display_data.insert(0,("M04", self.right_justify(218), 06927, 6.0, 87))
            #self.display_data = self.display_data[:3] # list slicing, keep only first three elements
            #post processing: append calculations, auxilliary information
            if True:
                for row in range (0,self.lines_per_block):
                    for col in range (0,len(self.measurement_lists)):
                        print( self.measurement_lists[col][row], end=", " )
                    print()
            # save data out to display register and to file_write_request
            # use the same file, but write a header line before every block
            # then clear the measurement_lists
            self.measurement_lists = []
            measure_stop_free = gc.mem_free()
        else:
            print("error, not available to measure")
            #set measure button to grey

    def measure(self):
        timeout_interval = 5
        timeout = False
        data_ready = False
        current_before = self.get_lamp_current()
        self.spectral_sensors[self.active_sensor_index].swob._configure_f1_f4()
        start = time.monotonic()
        print("begin f1-f4 channel detect")
        while not data_ready and not timeout:
            data_ready = self.spectral_sensors[self.active_sensor_index].swob._data_ready_bit
            print(".", end = "")
            time.sleep(0.01)
            if time.monotonic() > start + timeout_interval:
                timeout = True
        stop = time.monotonic()
        print()
        print( "f1-f4 elapsed time = {}s".format(stop-start))
        f1,f2,f3,f4 = self.spectral_sensors[self.active_sensor_index].swob.read_channel_register
        #print(f1,f2,f3,f4)

        self.spectral_sensors[self.active_sensor_index].swob._configure_f5_f8()
        start = time.monotonic()
        print("begin f5-f8 channel detect")
        data_ready = False
        while not data_ready and not timeout:
            data_ready = self.spectral_sensors[self.active_sensor_index].swob._data_ready_bit
            print(".", end = "")
            time.sleep(0.01)
            if time.monotonic() > start + timeout_interval:
                timeout = True
        stop = time.monotonic()
        print()
        print( "f5-f8 elapsed time = {}s".format(stop-start))
        current_after = self.get_lamp_current()
        f5,f6,f7,f8 = self.spectral_sensors[self.active_sensor_index].swob.read_channel_register
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
        self.text_areas[11].text = "{}".format(self.instrument.batch_number)
        if self.instrument.vfs:
            if self.status_index == 2:
                self.status_highlight.color_index = 2
            else:
                if self.measuring:
                    self.status_index = 1
                    self.status_highlight.color_index = 4
                else:
                    self.status_index = 0
                    self.status_highlight.color_index = 5
        else:
            self.status_index = 4
            self.status_highlight.color_index = 2
        self.text_areas[8].text = self.status_list[self.status_index]

        # update these if input changes values
        if len(self.spectral_sensors) >0:
            gain = self.spectral_sensors[self.active_sensor_index].gain_list[ self.gain_index[self.active_sensor_index] ]
            self.text_areas[9].text = "{}".format(gain)
            integration_time_ms = self.spectral_sensors[self.active_sensor_index].integration_time_ms_list[ self.integration_time_index[self.active_sensor_index] ]
            if integration_time_ms < 1000:
                self.text_areas[10].text = "{}ms".format(integration_time_ms)
            else:
                self.text_areas[10].text = "{}s".format(round(integration_time_ms/1000,1))
            self.text_areas[5].text = "{}nm".format(self.spectral_sensors[self.active_sensor_index].wavelength_bands_nm[self.chA_index])
            self.text_areas[6].text = "{}nm".format(self.spectral_sensors[self.active_sensor_index].wavelength_bands_nm[self.chB_index])
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
                self.text_areas[7].text = "{}mA".format(self.lamp_current_options[self.lamp_current_index])
            else:
                self.text_areas[7].text = "{}mA".format(self.last_lamp_current_mA)



            if False:
                #update these only on a new mmt having been made
                location = 18
                for y in range (0,3):
                    for x in range (0, 5):
                        self.text_areas[location].text = "{}".format(self.display_data[y][x])
                        location += 1


            if False:
                # temporary live readings


                #self.spectral_sensors[self.active_sensor_index].read_counts_all()
                chA_counts = self.spectral_sensors[self.active_sensor_index].data_counts[self.chA_index]
                chB_counts = self.spectral_sensors[self.active_sensor_index].data_counts[self.chB_index]
                self.text_areas[19].text = "{}".format(self.right_justify(chA_counts))
                self.text_areas[20].text = "{}".format(self.right_justify(chB_counts))
                data_ready = self.spectral_sensors[self.active_sensor_index].swob._data_ready_bit
                #print(data_ready)
                self.spectral_sensors[self.active_sensor_index].swob._color_meas_enabled = False


        if False:

            self.text_areas[15].text = "M{:03}".format( self.mmt_number )
            chA_counts = self.spectral_sensors[self.active_sensor_index].data_counts[self.chA_index]
            chB_counts = self.spectral_sensors[self.active_sensor_index].data_counts[self.chB_index]
            self.text_areas[18].text = "{:05}".format(chA_counts)
            chA_pdr = 100*chA_counts/self.max_counts
            if chA_pdr < 10:
                self.text_areas[19].text = "{}%".format(round(chA_pdr,1))
            else:
                self.text_areas[19].text = "{}%".format(int(round(chA_pdr,0)))
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
        stop = time.monotonic()
        #print( "update values takes {}s".format(stop-start))



    def action( self ):
        if self.instrument.encoder_increment != 0:
            if self.field_selected:
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
                    self.gain_index[self.active_sensor_index] = (self.gain_index[self.active_sensor_index] + self.instrument.encoder_increment )
                    if self.gain_index[self.active_sensor_index] > len(self.spectral_sensors[self.active_sensor_index].gain_list) - 1:
                        self.gain_index[self.active_sensor_index] = len(self.spectral_sensors[self.active_sensor_index].gain_list) - 1
                    if self.gain_index[self.active_sensor_index] < 0:
                        self.gain_index[self.active_sensor_index] = 0
                    self.spectral_sensors[self.active_sensor_index].set_gain( self.gain_index[self.active_sensor_index])
                if self.selection == 7:
                    self.integration_time_index[self.active_sensor_index] = (self.integration_time_index[self.active_sensor_index] + self.instrument.encoder_increment )
                    if self.integration_time_index[self.active_sensor_index] > len(self.spectral_sensors[self.active_sensor_index].integration_time_ms_list) - 1:
                        self.integration_time_index[self.active_sensor_index] = len(self.spectral_sensors[self.active_sensor_index].integration_time_ms_list) - 1
                    if self.integration_time_index[self.active_sensor_index] < 0:
                        self.integration_time_index[self.active_sensor_index] = 0
                    self.spectral_sensors[self.active_sensor_index].set_integration_time( self.integration_time_index[self.active_sensor_index])


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
        self.last_lamp_current_mA = int(round(lamp_currrent_voltage*1000,1))
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
        line_names = ["excitation", "position", "inspect A", "inspect B" ]
        line_values = ["488nm","below", " --", " --"]
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







def make_lab_spec_page( instrument, onboard_neopixel ):
    instrument.welcome_page.announce( "make_lab_spec_page" )
    page = Lab_Spec_Page( instrument,onboard_neopixel )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page
