SOFTWARE_VERSION_NUMBER = "0.0.1"
DEVICE_TYPE = "STELLA-1.2_Exposure_control"
# Paul Mirel 2025

import gc
import time
import os
import microcontroller
import board
import digitalio
import storage
import sdcardio
import busio
import rotaryio
from fourwire import FourWire
import displayio
import terminalio
from adafruit_display_text import label
import vectorio
import rtc
import math
import adafruit_ili9341
import adafruit_focaltouch
import qwiic_buzzer
from adafruit_seesaw.seesaw import Seesaw
from adafruit_as7341 import AS7341
from adafruit_as7341 import Gain as AS7341_Gain
import AS7265X_sparkfun
from AS7265X_sparkfun import AS7265X
import iorodeo_as7331 as as7331

## check i2c devices present
i2c_bus = board.I2C()
i2c_bus.try_lock()
devices_present = i2c_bus.scan()
devices_present_hex = []
for device_address in devices_present:
    devices_present_hex.append(hex(device_address))
print( devices_present_hex )
i2c_bus.unlock()

def main():

    displayio.release_displays()
    spi_bus = board.SPI()
    main_display_group = initialize_display( spi_bus )
    palette = make_palette()
    pin_a = board.A3
    pin_b = board.A4
    pin_button = board.A2
    rotary_encoder = initialize_rotary_encoder( pin_a, pin_b, pin_button )
    i2c_bus = initialize_i2c_bus()
    touch_screen = initialize_touch_screen( i2c_bus )
    buzzer = initialize_qwiic_buzzer( i2c_bus )
    buzzer.mute = False
    buzzer.set(932, 130) # frequency in Hz, time in ms.
    buzzer.beep()
    as7265x_spectrometer = initialize_as7265x_spectrometer()
    as7331_spectrometer = initialize_as7331_spectrometer()
    as7341_spectrometer = initialize_as7341_spectrometer()

    exposure_control_page = make_exposure_control_page( palette, main_display_group )
    exposure_control_page.sensor_choice_text_area.text = "as7265x V+NIR"



    try:
        operational = True
        while operational:
            print( "code running" )
            time.sleep( 1 )

    finally:
        displayio.release_displays()
        print( "displayio displays released" )
        i2c_bus.deinit()
        print( "i2c_bus deinitialized" )


class Page:
    def __init__( self ):
        pass
    def show(self):
        self.group.hidden = False
    def hide(self):
        self.group.hidden = True
    def update_values(self):
        pass


class Exposure_Control_Page( Page ):
    def __init__( self, palette):
        super().__init__()
        self.palette = palette
    def make_group( self ):
        self.group = displayio.Group()
        exposure_control_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240, x=0, y=0 )
        self.group.append( exposure_control_background )
        select_width = 4
        border_width = 2
        text_offset_x = 6
        text_offset_y = 14
        sensor_choice_select_x = 4
        sensor_choice_select_y = 4
        sensor_choice_select_width = 180
        sensor_choice_select_height = 40
        self.sensor_choice_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=sensor_choice_select_width,
                                                    height=sensor_choice_select_height, x=sensor_choice_select_x, y=sensor_choice_select_y )
        self.group.append( self.sensor_choice_select )
        #self.sensor_choice_select.hidden = True

        sensor_choice_border_width = sensor_choice_select_width - 2*select_width
        sensor_choice_border_height = sensor_choice_select_height - 2*select_width
        sensor_choice_border_x = sensor_choice_select_x+select_width
        sensor_choice_border_y = sensor_choice_select_y+select_width
        sensor_choice_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=sensor_choice_border_width,
                                            height=sensor_choice_border_height, x=sensor_choice_border_x, y=sensor_choice_border_y )
        self.group.append( sensor_choice_border )

        sensor_choice_area_width = sensor_choice_border_width - 2*border_width
        sensor_choice_area_height = sensor_choice_border_height - 2*border_width
        sensor_choice_area_x = sensor_choice_border_x+border_width
        sensor_choice_area_y = sensor_choice_border_y+border_width
        sensor_choice_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=sensor_choice_area_width,
                                            height=sensor_choice_area_height, x=sensor_choice_area_x, y=sensor_choice_area_y )
        self.group.append( sensor_choice_area )
        sensor_choice_text_x = sensor_choice_area_x+text_offset_x
        sensor_choice_text_y = sensor_choice_area_y+text_offset_y
        sensor_choice_text_group = displayio.Group(scale=2, x=sensor_choice_text_x, y=sensor_choice_text_y)
        sensor_choice_text = "none selected"
        self.sensor_choice_text_area = label.Label(terminalio.FONT, text=sensor_choice_text, color=self.palette[0])
        sensor_choice_text_group.append(self.sensor_choice_text_area)
        self.group.append(sensor_choice_text_group)

        spare_function_select_x = 186
        spare_function_select_y = 4
        spare_function_select_width = 130
        spare_function_select_height = 40
        self.spare_function_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=spare_function_select_width,
                                                    height=spare_function_select_height, x=spare_function_select_x, y=spare_function_select_y )
        self.group.append( self.spare_function_select )
        #self.spare_function_select.hidden = True

        spare_function_border_width = spare_function_select_width - 2*select_width
        spare_function_border_height = spare_function_select_height - 2*select_width
        spare_function_border_x = spare_function_select_x+select_width
        spare_function_border_y = spare_function_select_y+select_width
        spare_function_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=spare_function_border_width,
                                            height=spare_function_border_height, x=spare_function_border_x, y=spare_function_border_y )
        self.group.append( spare_function_border )

        spare_function_area_width = spare_function_border_width - 2*border_width
        spare_function_area_height = spare_function_border_height - 2*border_width
        spare_function_area_x = spare_function_border_x+border_width
        spare_function_area_y = spare_function_border_y+border_width
        spare_function_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=spare_function_area_width,
                                            height=spare_function_area_height, x=spare_function_area_x, y=spare_function_area_y )
        self.group.append( spare_function_area )
        spare_function_text_x = spare_function_area_x+text_offset_x
        spare_function_text_y = spare_function_area_y+text_offset_y
        spare_function_text_group = displayio.Group(scale=2, x=spare_function_text_x, y=spare_function_text_y)
        spare_function_text = "spare"
        self.spare_function_text_area = label.Label(terminalio.FONT, text=spare_function_text, color=self.palette[0])
        spare_function_text_group.append(self.spare_function_text_area)
        self.group.append(spare_function_text_group)




        if False:
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
    def update_values( self ):
        #if instrument.active_page_number == 3:
        if instrument.button_pressed:
            instrument.active_page_number = 2
            instrument.button_pressed = False


def make_exposure_control_page( palette, main_display_group ):
    page = Exposure_Control_Page( palette )
    group = page.make_group()
    #page.hide()
    main_display_group.append( group )
    return page


def make_palette():
    # TBD make a color name dictionary
    palette = displayio.Palette(40)
    palette[0] = 0x000000 # black
    palette[1] = 0xA0522D # brown
    palette[2] = 0xFF0000 # red
    palette[3] = 0xFF8C00 # orange
    palette[4] = 0xFFFF00 # yellow
    palette[5] = 0x00FF00 # green
    palette[6] = 0x0000FF # blue
    palette[7] = 0x9400D3 # violet
    palette[8] = 0x808080 # grey
    palette[9] = 0xFFFFFF # white
    palette[10] = 0xFF99FF # light
    palette[11] = 0xFF751A # heat
    palette[12] = 0x66CCFF # light blue, air analyzer
    palette[13] = 0x6FDC6F # plants
    palette[14] = 0xCE954B # here
    palette[15] = 0x8C8C8C # dark grey
    palette[16] = 0x00998F # burst
    palette[17] = 0x0066FF # border
    palette[18] = 0x009900 # GPS flag
    palette[19] = 0xCCCCCC # light grey
    palette[20] = 0x00CC00 # remote sens green
    palette[21] = 0x00CCBE # sensors
    palette[22] = 0xA6A6A6 # medium grey, return
    palette[23] = 0xFF6666 # medium red, not used yet
    palette[24] = 0x000000 # placeholder
    palette[25] = 0x7E00DB # blueviolet, 410nm
    palette[26] = 0x2300FF # blue, 435nm
    palette[27] = 0x007BFF # royalblue, 460nm
    palette[28] = 0x00EAFF # darkturquoise,485nm
    palette[29] = 0x00FF00 # lime, 510nm
    palette[30] = 0x70FF00 # chartreuse, 535nm
    palette[31] = 0xC3FF00 # greenyellow, 560nm
    palette[32] = 0xFFEF00 # yellow, 585nm
    palette[33] = 0xFF9B00 # orange, 610nm
    palette[34] = 0xFE0000 # red1, 645nm
    palette[35] = 0xDF0000 # red2, 680nm
    palette[36] = 0xC90000 # red3, 705nm
    palette[37] = 0xB10000 # firebrick, 730nm
    palette[38] = 0x940000 # darkred, 760nm
    return palette


class Device: #parent class
    def __init__(self, name = None, pn = None, address = None, swob = None ):
        self.name = name
        self.swob = swob
        self.pn = pn
        self.address = address
    def report(self):
        found = False
        if self.swob is not None:
            print("report:", hex(self.address), self.pn, "\t", self.name, "found" )
            found = True
        return found
    def found(self):
        if self.swob is not None:
            return True
        else:
            return False


def initialize_as7265x_spectrometer():
    as7265x_spectrometer = Null_as7265x_Spectrometer()
    try:
        as7265x_spectrometer = as7265x_Spectrometer( instrument.i2c_bus )
        as7265x_spectrometer.lamps_on()
        time.sleep(0.1)
        as7265x_spectrometer.lamps_off()
    except Exception as err:
        #print( "as7265x spectrometer failed: {}".format( err ))
        pass
    return as7265x_spectrometer

class as7265x_Spectrometer( Device ):
    # custom library
    # cycle time is a little less than 1 whole second
    def __init__( self, com_bus ):
        super().__init__(name = "as7265x_spectrometer", pn = "as7256x", address = 0x49, swob = AS7265X( com_bus ))
        if self.swob:
            self.swob.disable_indicator()
            self.swob.set_measurement_mode(AS7265X_sparkfun.MEASUREMENT_MODE_6CHAN_CONTINUOUS)
            #MEASUREMENT_MODE_6CHAN_ONE_SHOT
            self.bands = 610, 680, 730, 760, 810, 860, 560, 585, 645, 705, 900, 940, 410, 435, 460, 485, 510, 535
            self.bandwidth = 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20
            self.chip_n = 1,   1,   1,   1,   1,   1,   2,   2,   2,   2,   2,   2,   3,   3,   3,   3,   3,   3
            self.dict_chip_n = {key:value for key, value in zip(self.bands, self.chip_n )}
            self.dict_bandwidths = {key:value for key, value in zip(self.bands, self.bandwidth )}
            self.bands_sorted = sorted( self.bands )
            self.uncertainty_percent = 12
            self.gain_ratio = 16 #default, calibrated at
            self.intg_time_ms = 166 #default, calibrated at
            self.afov_deg = (20.5 * 2) #datasheet reports half angle.
    def check_gain_ratio(self):
        gain_number = self.swob._gain
        if gain_number < 1:
            self.gain_ratio = 1
        elif gain_number == 1:
            self.gain_ratio = 3.7
        elif gain_number == 2:
            self.gain_ratio = 16
        elif gain_number == 3:
            self.gain_ratio = 64
        return self.gain_ratio
    def set_gain_number(self, gain_number):
        if gain_number in range (0,4):
            self.swob.set_gain( gain_number )
        else:
            print( "out of range: set gain number to 0-3 to get gain_ratios of 1, 3.7, 16, 64" )
    def set_integration_cycles( self, cycles ):
        if cycles in range (0, 256):
            self.swob.set_integration_cycles(cycles)
            self.intg_time_ms = int(round((2.8*(cycles+1)),0))
        else:
            print( "out of range: set integration cycles to 0-255 for 0-717ms integration time." )
        return self.intg_time_ms
    def read(self):
        self.chip_temp_c = {1:self.swob.get_temperature(1), 2:self.swob.get_temperature(2), 3:self.swob.get_temperature(3)}
        self.data_counts = self.swob.get_value(0) # 0th position raw counts, bands unsorted order
        # dictionary where key = WL and value = raw counts
        self.dict_counts = {key:value for key, value in zip(self.bands, self.data_counts)}
        self.data_fcal = self.swob.get_value(1) # 1th position factory calibrated irrad value, bands unsorted order
        # dictionary where key = WL and value = factory cal irradiance
        self.dict_fcal = {key:value for key, value in zip(self.bands, self.data_fcal)}
        # OMIT as it's always 12% # self.dict_uncty_fcal = {key:value for key, value in zip(self.bands, (self.data_fcal*self.uncert_percent/100))}
        # TBD self.dict_scal = {key:value for key, value in zip(self.bands, 0)}
        # TBD self.dict_uncty_scal = {key:value for key, value in zip(self.bands, (0))}
        # print( self.data_counts )
    def read_counts(self):
        self.data_counts = self.swob.get_value(0) # 0th position raw counts, bands unsorted order
        self.dict_counts = {key:value for key, value in zip(self.bands, self.data_counts)}
    def read_fcal(self):
        self.data_fcal = self.swob.get_value(1) # 1th position factory calibrated irrad value, bands unsorted order
        self.dict_fcal = {key:value for key, value in zip(self.bands, self.data_fcal)}
        #print( self.data_fcal )
    def read_temperatures(self):
        self.chip_temp_c = {1:self.swob.get_temperature(1), 2:self.swob.get_temperature(2), 3:self.swob.get_temperature(3)}
    def list_channels():
        return self.bands_sorted
    def header( self ):
        return "WL.nm, irrad.uW/(cm^2), irrad.uncty.uW/(cm^2), counts, chip_num, chip_temp_C"
    def get_bandwidth(self, wavelength):
        return self.dict_bandwidths[wavelength]
    def log( self, wavelength):
        if wavelength in self.bands:
            logline = "{}".format( self.pn )
            logline += ", {}".format( wavelength )
            logline += ", {}".format( self.dict_bandwidths[wavelength] )
            logline += ", {}".format( self.dict_counts[wavelength] )
            logline += ", {}".format( self.dict_fcal[wavelength] )
            logline += ", {}".format( self.dict_fcal[wavelength]*self.uncertainty_percent/100 )
            logline += ", {}".format( self.gain_ratio )#gain
            logline += ", {}".format( self.intg_time_ms )#integration time
            logline += ", {}".format( self.dict_chip_n[wavelength] )#chip number
            logline += ", {}".format( self.chip_temp_c[self.dict_chip_n[wavelength]] )#chip temperature
            return logline
    def serial_log(self, wavelength):
        if wavelength in self.bands:
            loglist = "pn: {}".format( self.pn )
            loglist += ", WL-!-nm: {}".format( wavelength )
            loglist += ", BW-!-nm: {}".format( self.dict_bandwidths[wavelength] )
            loglist += ", raw-!-counts: {}".format( self.dict_counts[wavelength] )
            loglist += ", irrad-!-uW_per_cm_sq: {}".format( self.dict_fcal[wavelength] )
            loglist += ", gain-!-: {}".format( self.gain_ratio )
            loglist += ", intg-!-ms: {}".format( self.intg_time_ms )
            return loglist

    def printlog(self,ch):
        print( self.log(ch) )
    def lamps_on(self):
        #print( "turn on the lamps")
        self.swob.enable_bulb(0)   # white
        self.swob.enable_bulb(1)   # NIR
        self.swob.enable_bulb(2)   # UV
    def lamps_off(self):
        #print( "turn off the lamps")
        self.swob.disable_bulb(0)   # white
        self.swob.disable_bulb(1)   # NIR
        self.swob.disable_bulb(2)   # UV

class Null_as7265x_Spectrometer( Device ):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.swob = None
        self.bands = None
        self.bands_sorted = [0,0]   # empty list
        self.dict_chip_n = [0,0]
        self.chip_temps = [0,0]
        self.dict_fcal = {0:0}      # empty dictionary
        self.dict_counts = {0:0}
        self.uncert_percent = 10
    def check_gain_ratio(self):
        pass
    def set_gain_number(self, gain_number):
        pass
    def read(self):
        pass
    def read_counts(self):
        pass
    def read_fcal(self):
        pass
    def read_temperatures(self):
        pass
    def log(self, value):
        pass
    def get_bandwidth(self, wavelength):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def blink(self, duration):
        pass
    def header(self):
        pass
    def lamps_on(self):
        pass
    def lamps_off(self):
        pass
    def set_integration_cycles(self):
        pass
    def serial_log(self, wavelength):
        pass

def initialize_as7331_spectrometer():
    as7331_spectrometer = Null_as7331_Spectrometer()
    try:
        as7331_spectrometer = as7331_Spectrometer( instrument.i2c_bus )
    except ValueError as err:
        #print( "uv spectrometer failed to initialize: {}".format(err))
        pass
    except Exception as err:
        pass
    return as7331_spectrometer

class as7331_Spectrometer( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "as7331_spectrometer", pn = "as7331", address = 0x74, swob = as7331.AS7331( com_bus ))
        self.bands = 360, 300, 260
        self.bandwidth = 80, 40, 40
        self.chip_n = 1, 1, 1
        self.dict_chip_n = {key:value for key, value in zip(self.bands, self.chip_n )}
        self.dict_bandwidths = {key:value for key, value in zip(self.bands, self.bandwidth )}
        #https://look.ams-osram.com/m/1856fd2c69c35605/original/AS7331-Spectral-UVA-B-C-Sensor.pdf
        self.afov_deg = (10 * 2)
        self.fcal_unct_percent = 0 # no reported value
        self.gain_ratio = 0 #TBD what are the defaults?
        self.intg_time_ms = 0 #TBD what are the defaults?
    def check_gain_ratio(self):
        gain_callout = self.swob.gain
        if gain_callout == 11:
            self.gain_ratio = 1
        elif gain_callout == 10:
            self.gain_ratio = 2
        elif gain_callout == 9:
            self.gain_ratio = 4
        elif gain_callout == 8:
            self.gain_ratio = 8
        elif gain_callout == 7:
            self.gain_ratio = 16
        elif gain_callout == 6:
            self.gain_ratio = 32
        elif gain_callout == 5:
            self.gain_ratio = 64
        elif gain_callout == 4:
            self.gain_ratio = 128
        elif gain_callout == 3:
            self.gain_ratio = 256
        elif gain_callout == 2:
            self.gain_ratio = 512
        elif gain_callout == 1:
            self.gain_ratio = 1024
        elif gain_callout == 0:
            self.gain_ratio = 2048
        return self.gain_ratio

    def set_gain_number(self, gain_number):
        if gain_number in range (0,12):
            if gain_number == 11:
                gain_constant = as7331.GAIN_2048X
            if gain_number == 10:
                gain_constant = as7331.GAIN_1024X
            if gain_number == 9:
                gain_constant = as7331.GAIN_512X
            if gain_number == 8:
                gain_constant = as7331.GAIN_256X
            if gain_number == 7:
                gain_constant = as7331.GAIN_128X
            if gain_number == 6:
                gain_constant = as7331.GAIN_64X
            if gain_number == 5:
                gain_constant = as7331.GAIN_32X
            if gain_number == 4:
                gain_constant = as7331.GAIN_16X
            if gain_number == 3:
                gain_constant = as7331.GAIN_8X
            if gain_number == 2:
                gain_constant = as7331.GAIN_4X
            if gain_number == 1:
                gain_constant = as7331.GAIN_2X
            if gain_number == 0:
                gain_constant = as7331.GAIN_1X
            self.swob.gain = gain_constant
        else:
            print( "out of range: set gain number to 0-11 to get gain_ratios from 1 to 2048" )

    def set_integration_time( self, intg_number ):
        if intg_number == 0:
            self.integration_time = as7331.INTEGRATION_TIME_1MS
            self.intg_time_ms = 1
        if intg_number == 1:
            self.integration_time = as7331.INTEGRATION_TIME_2MS
            self.intg_time_ms = 2
        if intg_number == 2:
            self.integration_time = as7331.INTEGRATION_TIME_4MS
            self.intg_time_ms = 4
        if intg_number == 3:
            self.integration_time = as7331.INTEGRATION_TIME_8MS
            self.intg_time_ms = 8
        if intg_number == 4:
            self.integration_time = as7331.INTEGRATION_TIME_16MS
            self.intg_time_ms = 16
        if intg_number == 5:
            self.integration_time = as7331.INTEGRATION_TIME_32MS
            self.intg_time_ms = 32
        if intg_number == 6:
            self.integration_time = as7331.INTEGRATION_TIME_64MS
            self.intg_time_ms = 64
        if intg_number == 7:
            self.integration_time = as7331.INTEGRATION_TIME_128MS
            self.intg_time_ms = 128
        if intg_number == 8:
            self.integration_time = as7331.INTEGRATION_TIME_256MS
            self.intg_time_ms = 256
        if intg_number == 9:
            self.integration_time = as7331.INTEGRATION_TIME_512MS
            self.intg_time_ms = 512
        if intg_number == 10:
            self.integration_time = as7331.INTEGRATION_TIME_1024MS
            self.intg_time_ms = 1024
        if intg_number == 11:
            self.integration_time = as7331.INTEGRATION_TIME_2048MS
            self.intg_time_ms = 2048
        if intg_number == 12:
            self.integration_time = as7331.INTEGRATION_TIME_4096MS
            self.intg_time_ms = 4096
        if intg_number == 13:
            self.integration_time = as7331.INTEGRATION_TIME_8192MS
            self.intg_time_ms = 8192
        if intg_number == 14:
            self.integration_time = as7331.INTEGRATION_TIME_16384MS
            self.intg_time_ms = 16384
        return self.intg_time_ms
    def lamps_on(self):
        pass
    def lamps_off(self):
        pass
    def read(self):
        self.UVA_counts, self.UVB_counts, self.UVC_counts, self.chip_temp_c_counts = self.swob.raw_values
        self.dict_counts = {360:self.UVA_counts, 300:self.UVB_counts, 260:self.UVC_counts}
        self.UVA, self.UVB, self.UVC, self.chip_temp_c = self.swob.values
        self.dict_fcal = {360:self.UVA, 300:self.UVB, 260:self.UVC}
    def read_counts(self):
        self.UVA_counts, self.UVB_counts, self.UVC_counts, self.chip_temp_c_counts = self.swob.raw_values
        self.dict_counts = {360:self.UVA_counts, 300:self.UVB_counts, 260:self.UVC_counts}
    def read_fcal(self):
        self.UVA, self.UVB, self.UVC, self.chip_temp_c = self.swob.values
        self.dict_fcal = {360:self.UVA, 300:self.UVB, 260:self.UVC}
    def read_temperatures(self):
        pass
    def header(self):
        return "sensorPN, Wl.nm, raw_counts, irrad.stella.cal, irrad.stella.uncty, irrad_factory.cal, irrad_factory.uncty, gain, integration_time_ms, chip_temp_C"
        #return "UVC.WL.nm, UVC_uncal, UVB.WL.nm, UVB_uncal, UVA.WL.nm, UVA_uncal, UVS.temp.C"
    def log( self, wavelength):
        if wavelength in self.bands:
            logline = "{}".format( self.pn )
            logline += ", {}".format( wavelength )
            logline += ", {}".format( self.dict_bandwidths[wavelength] )
            logline += ", {}".format( self.dict_counts[wavelength] )
            logline += ", {}".format( self.dict_fcal[wavelength] )
            logline += ", {}".format( " - " )
            logline += ", {}".format( self.gain_ratio )#gain
            logline += ", {}".format( self.intg_time_ms )#integration time
            logline += ", {}".format( self.dict_chip_n[wavelength] )#chip number
            logline += ", {}".format( " - " )#self.chip_temp_c[self.dict_chip_n[wavelength]] )#chip temperature
            return logline
    def serial_log(self, wavelength):
        if wavelength in self.bands:
            loglist = "pn: {}".format( self.pn )
            loglist += ", WL-!-nm: {}".format( wavelength )
            loglist += ", BW-!-nm: {}".format( self.dict_bandwidths[wavelength] )
            loglist += ", raw-!-counts: {}".format( self.dict_counts[wavelength] )
            loglist += ", irrad-!-uW_per_cm_sq: {}".format( self.dict_fcal[wavelength] )
            loglist += ", gain-!-: {}".format( self.gain_ratio )
            loglist += ", intg-!-ms: {}".format( self.intg_time_ms )
            return loglist
    def get_bandwidth(self, wavelength):
        return self.dict_bandwidths[wavelength]
    def printlog(self):
        print( self.log())

class Null_as7331_Spectrometer(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def read_counts(self):
        pass
    def read_fcal(self):
        pass
    def read_temperatures(self):
        pass
    def lamps_on(self):
        pass
    def lamps_off(self):
        pass
    def log(self, value):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def get_bandwidth(self, wavelength):
        pass
    def header(self):
        pass
    def check_gain_ratio(self):
        pass
    def serial_log(self, wavelength):
        pass

def initialize_as7341_spectrometer():
    as7341_spectrometer = Null_as7341_Spectrometer()
    try:
        as7341_spectrometer = as7341_Spectrometer( instrument.i2c_bus )
    except:
        pass
    return as7341_spectrometer

class as7341_Spectrometer( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "as7341_spectrometer", pn = "as7341", address = 0x39, swob = AS7341( com_bus ))
        self.bands = 415, 445, 480, 515, 555, 590, 630, 682
        self.bandwidth = 26, 30, 36, 39, 39, 40, 50, 52
        self.chip_n = 1, 1, 1, 1, 1, 1, 1, 1
        self.dict_chip_n = {key:value for key, value in zip(self.bands, self.chip_n )}
        self.dict_bandwidths = {key:value for key, value in zip(self.bands, self.bandwidth )}
        self.colors = ["violet", "indigo", "blue", "cyan", "green", "yellow", "orange", "red"]
        #self.tsis_cal_counts_per_irradiance = 1405.9, 2079.6, 2631.6, 3556.8, 4246.0, 5060.6, 6888.9, 9130.9
        # first principles calibration by Sten Odenwald of NASA Heliophysics
        self.steno_cal_counts_per_irradiance = 4398.0, 6104.0, 7583.0, 9972.0, 11536.0, 13374.0, 17115.0, 20916.0
        self.calibration_error = 0.6
        self.irradiance = [0,0,0,0,0,0,0,0]
        self.dict_stenocal = {}
        self.swob.led_current = 50
    def check_gain_ratio(self):
        pass
    def lamps_on(self):
        self.swob.led = True
    def lamps_off(self):
        self.swob.led = False
    def blink( self, duration ):
        self.swob.led_current = 50
        self.swob.led = True
        time.sleep( duration )
        self.swob.led = False
    def read(self):
        self.raw = self.swob.all_channels
        self.dict_counts = {key:value for key, value in zip(self.bands, self.raw )}
        for ch in range (0,8):
            self.irradiance[ch] = self.raw[ch]/self.steno_cal_counts_per_irradiance[ch]
        self.dict_stenocal = {key:value for key, value in zip(self.bands, self.irradiance )}
    def list_channels():
        return self.center_wavelengths
    def header(self, ch):
        return " {}.WL.nm, {}.counts, {}.W/(m^2*nm), {}.uncty.W/(m^2*nm)".format( self.colors[ch], self.colors[ch], self.colors[ch], self.colors[ch] )
    def log( self, wavelength):
        if wavelength in self.bands:
            logline = "{}".format( self.pn )
            logline += ", {}".format( wavelength )
            logline += ", {}".format( self.dict_bandwidths[wavelength] )
            logline += ", {}".format( self.dict_counts[wavelength] )
            logline += ", {}".format( self.dict_stenocal[wavelength] )
            logline += ", {}".format( " - " )
            logline += ", {}".format( " - " )#gain
            logline += ", {}".format( " - " )#integration time
            logline += ", {}".format( " - " )#chip number
            logline += ", {}".format( " - " )#chip temperature
            return logline
    def serial_log(self, wavelength):
        if wavelength in self.bands:
            loglist = "pn: {}".format( self.pn )
            loglist += ", WL-!-nm: {}".format( wavelength )
            loglist += ", BW-!-nm: {}".format( self.dict_bandwidths[wavelength] )
            loglist += ", raw-!-counts: {}".format( self.dict_counts[wavelength] )
            loglist += ", irrad-!-uW_per_cm_sq: {}".format( self.dict_stenocal[wavelength] )
            loglist += ", gain-!-: {}".format( '-' ) #self.gain_ratio )
            loglist += ", intg-!-ms: {}".format( '-' )#self.intg_time_ms )
            return loglist
    def get_bandwidth(self, wavelength):
        return self.dict_bandwidths[wavelength]
    def printlog(self,ch):
        print( self.log(ch))

class Null_as7341_Spectrometer(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def log(self, value):
        pass
    def serial_log(self, wavelength):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def lamps_on(self):
        pass
    def lamps_off(self):
        pass
    def blink(self, duration):
        pass
    def get_bandwidth(self, wavelength):
        pass
    def header(self):
        pass
    def check_gain_ratio(self):
        pass

def initialize_qwiic_buzzer( i2c_bus ):
    buzzer = Null_Qwiic_Buzzer()
    try:
        buzzer = Qwiic_Buzzer( i2c_bus )
    except Exception as err:
        print( "buzzer failed to initialize: {}".format(err) )
        pass
    return buzzer

class Qwiic_Buzzer( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "qwiic_buzzer", pn = "BOB-24474", address = 0x34, swob = qwiic_buzzer.QwiicBuzzer(i2c_driver = com_bus))
        self.swob.configure( self.swob.VOLUME_MAX )
        self.mute = False
    def read(self):
        pass
    def beep(self):
        if self.mute:
            pass
        else:
            self.swob.on()
    def stop(self):
        self.swob.off()
    def set(self, frequency_hz, time_ms ):
        self.swob.configure( frequency_hz, time_ms )
    def header(self):
        return ""
    def log(self):
        return ""
    def printlog(self):
        print( self.log())

class Null_Qwiic_Buzzer(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def beep(self):
        pass
    def stop(self):
        pass
    def set(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass


def increment_select( page ):
    select_value = (page.select_value + encoder_move) % page.number_of_select_positions

def initialize_rotary_encoder( pin_a, pin_b, pin_button ):
    encoder = Null_Rotary_Encoder()
    try:
        encoder = Rotary_Encoder( pin_a, pin_b, pin_button )
    except Exception as err:
        print( "encoder failed: {}".format(err))
    return encoder

class Rotary_Encoder( Device ):
    def __init__( self, pin_a, pin_b, pin_button ):
        super().__init__(name = "rotary_encoder", pn = "encoder", address = 00, swob = rotaryio.IncrementalEncoder( pin_b, pin_a ))
        self.button = digitalio.DigitalInOut( pin_button )
        self.button.direction = digitalio.Direction.INPUT
        self.button.pull = digitalio.Pull.UP
        self.button_pressed = False
        self.button_last_pressed = False
        self.encoder_flag = False
        self.button_flag = False
        self.last_position = None
        self.last_value = 0
        self.last_button_read = time.monotonic()
        self.button_cycle_time_s = 0
        self.slowest_button_cycle_time_s = 0
    def read_encoder(self):
        try:
            self.position = self.swob.position
            if not self.encoder_flag:
                if self.last_position is not None and self.position != self.last_position:
                    self.last_value = self.position - self.last_position
                    if self.last_value > 1:
                        self.last_value = 1
                    if self.last_value < -1:
                        self.last_value = -1
                    if self.last_value != 0:
                        self.encoder_flag = True
                self.last_position = self.position
        except Exception as err:
            print( err )
    def read_button(self):
        self.last_button_read = time.monotonic()
        try:
            self.button_pressed = not self.button.value
            if self.button_pressed:
                if self.button_last_pressed:
                    pass
                else:
                    self.button_flag = True
                self.button_last_pressed = True
            else:
                self.button_last_pressed = False
        except Exception as err:
            print( err )
    def log(self):
        pass
    def printlog(self):
        pass

class Null_Rotary_Encoder(Device):
    def __init__( self ):
        self.swob = None
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        print( "encoder failed to initialize" )
    def printlog(self):
        pass

def initialize_touch_screen( bus ):
    touch_screen = Null_Touch_Screen()
    try:
        touch_screen = Focal_Touch_Screen( bus )
    except Exception as err:
        print( "touch screen fail: {}".format(err))
    return touch_screen

class Focal_Touch_Screen( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "touch_screen", pn = "FocalTouch", address = 0x38, swob = adafruit_focaltouch.Adafruit_FocalTouch(com_bus, debug=False))
        self.flag = False
    def read(self):
        try:
            self.is_touched = self.swob.touched
            if self.is_touched:
                #print( "touched" )
                self.dict = self.swob.touches
                self.tx = 320 - self.dict[0]['y'] #transform
                self.ty = self.dict[0]['x'] #transform
        except Exception as err:
            print( err )
    def log(self):
        pass
    def printlog(self):
        print( self.log())

class Null_Touch_Screen(Device):
    def __init__( self ):
        self.swob = None
        self.is_touched = False
    def read(self):
        pass
    def log(self):
        pass
    def report(self):
        pass
    def printlog(self):
        pass

def initialize_display( spi_bus ):
    try:
        # displayio/dafruit_ili9341 library owns the pins until display release
        displayio.release_displays()
        tft_dc = board.D11
        tft_cs = board.D12
        display_bus = FourWire(spi_bus, command=tft_dc, chip_select=tft_cs )
        display = adafruit_ili9341.ILI9341(display_bus, width=320, height=240, rotation=0)
        print( "display initialized")

    except ValueError as err:
        print("Error: display failed to initialize {:}".format(err))
        display = False
    if display:
        display_group = displayio.Group()
        display.root_group = display_group
    return display_group

def initialize_i2c_bus():
    try:
        i2c_bus = board.I2C() #TBD might need to limit speed to 100kHz for the mlx90614
        print( "i2c bus initialized" )
    except:
        print( "i2c bus failed to initialize" )
        i2c_bus = False
    return i2c_bus

def memory_check( message ):
    gc.collect()
    mem_free_kB = gc.mem_free()/1000
    print( "{} memory free: {} kB, {} %".format( message, int(mem_free_kB), int((100* (mem_free_kB)/start_mem_free_kB ))))

def stall():
    print("intentionally stalled, press return to continue")
    input_string = False
    while input_string == False:
        input_string = input().strip()

main()
