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
import board
import busio
import rtc
import adafruit_tca9548a
import adafruit_as5600
from software_modules import spectralm_as7341
from software_modules import spectralm_as7343
from software_modules import spectralm_as7265x
from software_modules import spectralm_tcs3448



import adafruit_ds3231
from adafruit_pca9685 import PCA9685

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
        self.field_greyed_index = 19
        self.field_selected_color_index = 5
        self.field_not_selected_color_index = 9
        self.active_sensor_index = 0
        self.max_counts = 65535
        self.high_value = False
        self.exposure_quality = False
        self.exposure_target_fraction_high = 0.9
        self.exposure_target_fraction_low = 0.5
        self.saturated = False
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
        self.precision_real_time_clock = adafruit_ds3231.DS3231(self.instrument.i2c_bus)
        time_struture = self.precision_real_time_clock.datetime
        self.year = time_struture.tm_year
        self.month = time_struture.tm_mon
        self.day = time_struture.tm_mday
        self.hour = time_struture.tm_hour
        self.minute = time_struture.tm_min
        self.second = time_struture.tm_sec
        print( self.year, self.month, self.day, self.hour, self.minute, self.second)
        self.sync_system_clock()
        self.mux_8_to_1 = adafruit_tca9548a.TCA9548A(self.instrument.i2c_bus)
        self.spectral_sensors = []
        self.auto_exposure = True

        for index in range (0,7):
            active_sensor = False
            active_sensor = spectralm_as7265x.initialize_as7265x_spectrometer( self.instrument, alt_bus=self.mux_8_to_1[index] )
            if not active_sensor:
                active_sensor = spectralm_as7343.initialize_as7343_spectrometer(self.instrument, alt_bus=self.mux_8_to_1[index])
            if not active_sensor:
                active_sensor = spectralm_as7341.initialize_as7341_spectrometer(self.instrument, alt_bus=self.mux_8_to_1[index])
            if not active_sensor:
                active_sensor = spectralm_tcs3448.initialize_tcs3448_spectrometer(self.instrument, alt_bus=self.mux_8_to_1[index])

            if active_sensor:
                self.spectral_sensors.append ( active_sensor )
                if active_sensor.pn == "as7341" or active_sensor.pn == "as7343" or active_sensor.pn == "tcs3448":
                    active_sensor.lamp_on()
                    time.sleep(0.5)
                    active_sensor.lamp_off()
                if active_sensor.pn == "as7265x":
                    active_sensor.lamp_on(0)
                    time.sleep(0.5)
                    active_sensor.lamp_off(0)
        self.sensor_wheel_number = False
        if self.spectral_sensors[0].pn == "as7341":
            self.sensor_wheel_number = 1
            from configuration_files import cal_lookup_wheel_1
            self.magnetic_angle_values = getattr(cal_lookup_wheel_1, "magnetic_angle_values", False)
            self.angle_offsets = getattr(cal_lookup_wheel_1, "magnetic_angle_offsets", False)
            self.servo_position_values = getattr(cal_lookup_wheel_1, "servo_position_values", False)
            self.spectral_sensor_tracking_numbers = getattr(cal_lookup_wheel_1, "tracking_numbers", False)
        elif self.spectral_sensors[0].pn == "as7343":
            self.sensor_wheel_number = 3
            from configuration_files import cal_lookup_wheel_3
            self.magnetic_angle_values = getattr(cal_lookup_wheel_3, "magnetic_angle_values", False)
            self.angle_offsets = getattr(cal_lookup_wheel_3, "magnetic_angle_offsets", False)
            self.servo_position_values = getattr(cal_lookup_wheel_3, "servo_position_values", False)
            self.spectral_sensor_tracking_numbers = getattr(cal_lookup_wheel_3, "tracking_numbers", False)
        elif self.spectral_sensors[0].pn == "tcs3448":
            self.sensor_wheel_number = 8
            from configuration_files import cal_lookup_wheel_8
            self.magnetic_angle_values = getattr(cal_lookup_wheel_8, "magnetic_angle_values", False)
            self.angle_offsets = getattr(cal_lookup_wheel_8, "magnetic_angle_offsets", False)
            self.servo_position_values = getattr(cal_lookup_wheel_8, "servo_position_values", False)
            self.spectral_sensor_tracking_numbers = getattr(cal_lookup_wheel_8, "tracking_numbers", False)
        elif self.spectral_sensors[0].pn == "as7265x":
            self.sensor_wheel_number = 5
            from configuration_files import cal_lookup_wheel_5
            self.magnetic_angle_values = getattr(cal_lookup_wheel_5, "magnetic_angle_values", False)
            self.angle_offsets = getattr(cal_lookup_wheel_5, "magnetic_angle_offsets", False)
            self.servo_position_values = getattr(cal_lookup_wheel_5, "servo_position_values", False)
            self.spectral_sensor_tracking_numbers = getattr(cal_lookup_wheel_5, "tracking_numbers", False)
        print()
        print( "sensor_wheel_number =", self.sensor_wheel_number )
        #print( "magnetic_angle_values =",self.magnetic_angle_values )
        #print( "servo_position_values =",self.servo_position_values )
        #print( "spectral_sensor_tracking_numbers = ", self.spectral_sensor_tracking_numbers )
        print()
        self.sensor_wheel_waypoints = []
        for index in range (0, len(self.servo_position_values)-1):
            self.sensor_wheel_waypoints.append(int((self.servo_position_values[index]+self.servo_position_values[index+1])/2))


        from configuration_files import cal_lookup_wheel_F0
        self.filter_wheel_number = "F0"
        self.filter_wheel_magnetic_angle_values = getattr(cal_lookup_wheel_F0, "magnetic_angle_values", False)
        self.filter_wheel_angle_offsets = getattr(cal_lookup_wheel_F0, "magnetic_angle_offsets", False)
        self.filter_wheel_servo_position_values = getattr(cal_lookup_wheel_F0, "servo_position_values", False)
        self.filter_part_numbers = getattr(cal_lookup_wheel_F0, "part_numbers", False)
        self.filter_manufacturer = getattr(cal_lookup_wheel_F0, "manufacturer", False)
        self.filter_optical_values = getattr(cal_lookup_wheel_F0, "optical_values", False)
        self.filter_optical_value_abbreviations = getattr(cal_lookup_wheel_F0, "optical_value_abbreviations", False)


        print( "filter_wheel_number =", self.filter_wheel_number )
        #print( "filter_wheel_magnetic_angle_values =",self.filter_wheel_magnetic_angle_values )
        #print( "filter_wheel_servo_position_values =",self.filter_wheel_servo_position_values )

        self.filter_wheel_waypoints = []
        for index in range (0, len(self.filter_wheel_servo_position_values)-1):
            self.filter_wheel_waypoints.append(int((self.filter_wheel_servo_position_values[index]+self.filter_wheel_servo_position_values[index+1])/2))
        #print( "filter_wheel_waypoints =",self.filter_wheel_waypoints )
        pca = PCA9685(self.instrument.i2c_bus)
        pca.frequency = 60
        self.filter_servo = pca.channels[0]
        self.sensor_servo = pca.channels[15]
        self.filter_servo.duty_cycle = 0
        self.sensor_servo.duty_cycle = 0

        self.sensor_wheel_angle_sensor = adafruit_as5600.AS5600(self.mux_8_to_1[7])
        self.filter_wheel_angle_sensor = adafruit_as5600.AS5600(self.instrument.i2c_bus, address = 0x46 )

        self.sensor_wheel_position_known = False
        self.filter_wheel_position_known = False
        self.sensor_wheel_position = 0
        self.filter_wheel_position = 0
        self.filter_wheel_position_labels = ["A","B","C","D","E","F","G","H","i"]
        self.pause = False

    def integration_time_setting_test( self ):
        integration_setting_ms = 10
        while integration_setting_ms < 24000:
            self.set_integration_time_ms( integration_setting_ms )
            integration_setting_ms = round(integration_setting_ms * 1.1,1)


    def set_integration_time_ms( self, integration_setting_ms ):
        pass
        if False:
            tolerance = 0.05
            cycle_limit = 16
            unit_integration_time_ms = 0.00278
            integration_time_actual_ms = 0
            astep_16_bit_value = 0
            atime_8_bit_value = 127
            calculating_integration_settings = True
            #print("calculating")
            cycle = 0
            while calculating_integration_settings:
                #print(".", end = "")
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





    def update_values( self ):
        self.bat.read()

        #print( self.filter_servo.duty_cycle, self.filter_wheel_angle_sensor.angle )
        timenow = self.precision_real_time_clock.datetime
        self.text_areas[0].text = "{}-{:02}-{:02}".format(timenow.tm_year,timenow.tm_mon, timenow.tm_mday)
        self.text_areas[1].text = "{:02}:{:02}:{:02}".format(timenow.tm_hour, timenow.tm_min,timenow.tm_sec)
        self.text_areas[3].text = "{}%".format(int(self.bat.percentage))
        self.text_areas[5].text = "{:3d}".format(self.instrument.batch_number)

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
        #self.text_areas[7].text = " --"
        if self.auto_exposure:
            self.text_areas[8].text = "AUTO"
        else:
            self.text_areas[8].text = "MAN"
        if self.high_value:
            if self.high_value > self.exposure_target_fraction_high * self.max_counts:
                self.exposure_quality = "HIGH"
            elif self.high_value > self.exposure_target_fraction_low * self.max_counts:
                self.exposure_quality = "GOOD"
            else:
                self.exposure_quality = "LOW"
            percent_of_dynamic_range = int(100*self.high_value/self.max_counts)
            if percent_of_dynamic_range > 99:
                self.exposure_quality = "SAT"
                self.text_areas[12].text = "SA"
                self.saturated = True
            else:
                self.saturated = False
                self.text_areas[12].text = "{}".format(percent_of_dynamic_range)
            self.text_areas[11].text = " {}".format(self.exposure_quality)
        else:
            self.text_areas[12].text = " -"
            self.text_areas[11].text = " -"

        self.text_areas[13].text = "{}".format(self.sensor_wheel_number)
        self.text_areas[14].text = "{}".format(len(self.spectral_sensors))
        if self.sensor_wheel_position_known:
            self.text_areas[9].text = "{}".format(self.spectral_sensors[self.sensor_wheel_position].read_gain())
            intg_ms = self.spectral_sensors[self.sensor_wheel_position].read_integration_time_ms()
            if intg_ms <1000:
                self.text_areas[10].text = "{}ms".format(intg_ms)
            else:
                self.text_areas[10].text = "{}s".format(round(intg_ms/1000),1)
            self.text_areas[15].text = "{}".format(self.sensor_wheel_position)
            self.text_areas[17].text = "{}".format(self.spectral_sensor_tracking_numbers[self.sensor_wheel_position])
        else:
            self.text_areas[9].text = " -"
            self.text_areas[10].text = " -"
            self.text_areas[15].text = " -"
            self.text_areas[17].text = " -"
        self.text_areas[16].text = self.spectral_sensors[self.sensor_wheel_position].pn
        self.text_areas[18].text = "{}".format( self.filter_wheel_number )
        self.text_areas[19].text = "9" ### TBD"{}".format(len(self.filters))
        if self.filter_wheel_position_known:
            self.text_areas[20].text = "{}".format(self.filter_wheel_position_labels[self.filter_wheel_position])
            self.text_areas[21].text = self.filter_part_numbers[self.filter_wheel_position]
            self.text_areas[22].text = self.filter_optical_value_abbreviations[self.filter_wheel_position]
        else:
            self.text_areas[20].text = " -"
            self.text_areas[21].text = " -"
            self.text_areas[22].text = " -"
        if self.pause:
            self.text_areas[26].text = "pause"
        else:
            self.text_areas[26].text = " --"

    def reset(self):
        self.cancel = True
        self.measuring = False
        self.auto_exposure = True
        self.go_to_sensor_position(0)
        self.go_to_filter_position(0)

    def action( self ):
        if self.instrument.encoder_increment != 0:
            if self.field_selected:
                if self.selection == 3:
                    self.auto_exposure = not self.auto_exposure
                if not self.auto_exposure:
                    active_sensor = self.spectral_sensors[self.sensor_wheel_position]
                    if self.selection == 4:
                        active_sensor.gain_index = (active_sensor.gain_index + self.instrument.encoder_increment) % len(active_sensor.gain_list)
                        active_sensor.set_gain()
                    if self.selection == 5:
                        active_sensor.integration_time_index = (active_sensor.integration_time_index + self.instrument.encoder_increment) % len(active_sensor.integration_time_ms_list)
                        active_sensor.set_integration_time()
                if not self.measuring:
                    if self.selection == 6:
                        self.sensor_wheel_position = (self.sensor_wheel_position + self.instrument.encoder_increment) % len(self.spectral_sensors)
                        self.go_to_sensor_position()
                    if self.selection == 7:
                        self.filter_wheel_position = (self.filter_wheel_position + self.instrument.encoder_increment) % 9
                        self.go_to_filter_position()
            self.instrument.encoder_increment = 0
            self.update_values()

        if self.instrument.button_pressed:
            if False:#self.selection == 9 or self.selection == 10 or self.selection == 11 or not self.graph_group.hidden:
                self.graph_group.hidden = not self.graph_group.hidden
                if not self.graph_group.hidden:
                    self.plot()
            elif self.selection == 0:
                pass#self.instrument.active_page_number = self.instrument.pages_dict["Main"]
            elif self.selection == 1:
                self.instrument.update_batch()
            elif self.selection == 2:
                self.reset()
            elif self.selection == 8:
                if not self.measuring:
                    self.make_a_single_measurement()
            elif self.selection == 9:
                if self.pause:
                    self.pause = False
                if not self.measuring:
                    self.run_measurement_sequence()
            elif self.selection == 10:
                self.pause = True

            else:
                self.field_selected = not self.field_selected
                if self.selection == 3:
                    if self.field_selected:
                        self.value_areas[3].color_index = self.field_selected_color_index
                    else:
                        self.value_areas[3].color_index = self.field_not_selected_color_index
                if self.auto_exposure:
                    exposure_control_color_index = self.field_greyed_index
                else:
                   exposure_control_color_index =  self.field_selected_color_index
                if self.selection == 4:
                    if self.field_selected:
                        self.value_areas[4].color_index = exposure_control_color_index
                    else:
                        self.value_areas[4].color_index = self.field_not_selected_color_index
                if self.selection == 5:
                    if self.field_selected:
                        self.value_areas[5].color_index = exposure_control_color_index
                    else:
                        self.value_areas[5].color_index = self.field_not_selected_color_index
                if self.measuring:
                    position_control_color_index = self.field_greyed_index
                else:
                    position_control_color_index = self.field_selected_color_index
                if self.selection == 6:
                    if self.field_selected:
                        self.value_areas[6].color_index = position_control_color_index
                    else:
                        self.value_areas[6].color_index = self.field_not_selected_color_index
                if self.selection == 7:
                    if self.field_selected:
                        self.value_areas[7].color_index = position_control_color_index
                    else:
                        self.value_areas[7].color_index = self.field_not_selected_color_index
            self.instrument.button_pressed = False
            self.update_values()

    def make_a_single_measurement(self):
        self.measuring = True
        if not self.sensor_wheel_position_known:
            self.go_to_sensor_position()
        if not self.filter_wheel_position_known:
            self.go_to_filter_position()
        self.latest_data_list = self.measure()
        print(self.latest_data_list)
        print("write single measurement to file")
        self.measuring = False

    def run_measurement_sequence(self):
        self.cancel = False
        self.measuring = True
        self.instrument.update_batch()
        print("starting measurement sequence")
        for sensor_position in range(0, len(self.spectral_sensors)):
            if not self.cancel:
                data_list = []
                print("next sensor")
                self.go_to_sensor_position(position = sensor_position)
                self.instrument.handle_inputs()
                self.update_values()
                for filter_position in range(0, 9):
                    if not self.cancel:
                        print("next filter")
                        self.go_to_filter_position(position = filter_position)
                        self.update_values()
                        print("Set exposure parmeters to low middle values")
                        temporary_data_list = self.measure()
                        print("calculate best exposure (if saturated, drop values and test expose again)")
                        print("set exposure parameters to best")
                        #print("(omit bracketing as not useful information, come back to it if I find out that I need it specifically)")
                        for cycle in range (0,3):
                            print("measurement cycle", cycle)
                            data_list.append( self.measure())
                            time.sleep(1)
                            print("write values to file")
                            self.instrument.handle_inputs()
                            while self.pause:
                                self.instrument.handle_inputs()
                                self.update_values()
                                time.sleep(0.1)
        self.measuring = False

        if False:
            self.as7341_spectrometer.set_integration_time( self.integration_time_index)
            self.as7341_spectrometer.set_gain( self.gain_index)
            if self.status_index == 0 or self.status_index == 2:

                self.mmt_number += 1
                gc.collect()
                measure_start_free = gc.mem_free()
                uid = self.instrument.uid
                mmt_time = self.instrument.iso_time
                dec_time = self.instrument.decimal_time

                self.bat.read()

                header_line = "UID,iso8601,time hh.hh,bat_V,bat_pct"
                header_line += ""

                try:
                    self.onboard_neopixel.fill(devicem_neopixel.GREEN)
                    functionm_file.write_nonsystem_line( self.instrument, header_line)
                    for row in range (0,self.lines_per_block):
                        line = "{},".format(uid)
                        line += "{},".format(mmt_time)
                        line += "{},".format(dec_time)
                        line += "{},".format(self.bat.voltage)
                        line += "{},".format(self.bat.percentage)


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
        self.latest_data_list = self.spectral_sensors[self.sensor_wheel_position].read()
        self.high_value = max(self.latest_data_list)
        return self.latest_data_list

    def go_to_sensor_position( self, position = None):
        self.sensor_wheel_position_known = True
        self.text_areas[15].text = " -"
        if position is None:
            position = self.sensor_wheel_position
        if position < 6:
            self.sensor_servo.duty_cycle = self.sensor_wheel_waypoints[position]
        else:
            self.sensor_servo.duty_cycle = self.sensor_wheel_waypoints[position-1]
        time.sleep(0.6)
        sensor_wheel_angle = self.sensor_wheel_angle_sensor.angle
        if position == 6:
            while sensor_wheel_angle > self.magnetic_angle_values[position]+self.angle_offsets[position]:
                self.sensor_servo.duty_cycle = self.sensor_servo.duty_cycle - 16
                time.sleep(0.03)
                sensor_wheel_angle = self.sensor_wheel_angle_sensor.angle
                #print( self.sensor_servo.duty_cycle, sensor_wheel_angle )
        else:
            while sensor_wheel_angle < self.magnetic_angle_values[position]+self.angle_offsets[position]:
                self.sensor_servo.duty_cycle = self.sensor_servo.duty_cycle + 16
                time.sleep(0.03)
                sensor_wheel_angle = self.sensor_wheel_angle_sensor.angle
                #print( self.sensor_servo.duty_cycle, sensor_wheel_angle )
        self.sensor_servo.duty_cycle = 0
        self.sensor_wheel_position = position
        self.text_areas[15].text = "{}".format(self.sensor_wheel_position)
        return position


    def go_to_filter_position( self, position = None):
        self.filter_wheel_position_known = True
        self.text_areas[20].text = " -"
        if position is None:
            position = self.filter_wheel_position
        if position != 8:
            self.filter_servo.duty_cycle = self.filter_wheel_waypoints[position]
        else:
            self.filter_servo.duty_cycle = self.filter_wheel_waypoints[position-1]
        time.sleep(0.4)
        filter_wheel_angle = self.filter_wheel_angle_sensor.angle
        if position == 8:
            while filter_wheel_angle > self.filter_wheel_magnetic_angle_values[position]+self.filter_wheel_angle_offsets[position]:
                self.filter_servo.duty_cycle = self.filter_servo.duty_cycle - 16
                time.sleep(0.04)
                filter_wheel_angle = self.filter_wheel_angle_sensor.angle
                #print( self.filter_servo.duty_cycle, filter_wheel_angle )
        else:
            while filter_wheel_angle < self.filter_wheel_magnetic_angle_values[position]+self.filter_wheel_angle_offsets[position]:
                self.filter_servo.duty_cycle = self.filter_servo.duty_cycle + 16
                time.sleep(0.04)
                filter_wheel_angle = self.filter_wheel_angle_sensor.angle
                #print( self.filter_servo.duty_cycle, filter_wheel_angle )
        self.filter_servo.duty_cycle = 0
        self.filter_wheel_position = position
        self.text_areas[20].text = "{}".format(self.filter_wheel_position_labels[self.filter_wheel_position])
        return position

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
                                                            height=height_2-2*select_width, x=98, y=line_y+height_1+select_width)
        self.group.append(batch_highlight)
        self.status_highlight = vectorio.Rectangle(pixel_shader=self.palette, color_index=5, width=54-2*select_width+14,
                                                            height=height_2-2*select_width, x=154, y=line_y+height_1+select_width)
        self.group.append(self.status_highlight)
        line_names = ["battery", "inc", "  batch", "status", "   override" ]
        line_values = ["---","B+","---", "----", " RESET"] #SELF-TS #RESET #_STOP_
        line_selectable = [ False, True, False, False, True ]
        line_widths = [54,38,56,70,100]
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
        self.value_areas[-1].color_index = 9

        line_y += line_spacing
        line_names = ["control", "gain", "integration", " exposure", "%DR" ]
        line_values = [" - "," - "," - ", " - ", "-"] #AUTO #MAN // #SAT #OVER #UNDER #GOOD
        line_selectable = [ True, True, True, False, False ]
        line_widths = [68,68,77,68,36]
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
        line_names = ["wheel", "sensors", "position", " part number", "tracking"]
        line_values = ["", "",""," --", " - "]
        line_selectable = [ False, False, True, False, False ]
        line_widths = [44,50,56,100,60]
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
        line_names = ["wheel", "filters", "position", " part number", "value"]
        line_values = ["-", "-","-","-", "-"]
        line_selectable = [ False, False, True, False, False ]
        line_widths = [44,50,56,76,80]
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

        line_y += line_spacing - height_1
        line_names = ["", "", "", "", ""]
        line_values = ["ONE", "RUN","PAUSE"," -- ", "PLOT"] #ready
        line_selectable = [ True, True, True, False, True ]
        line_widths = [50,52,74,78,62]
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

    def sync_system_clock(self):
        try:
            system_clock = rtc.RTC()
            system_clock.datetime = self.precision_real_time_clock.datetime
            print( "system clock synchronized to precision hardware clock" )
        except:
            print( "failed to synchronize system clock to precision hardware clock" )

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






def make_calibration_missing_page( instrument ):
    instrument.welcome_page.announce( "make_calibration_missing_page" )
    page = Calibration_Missing_Page( instrument )
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
