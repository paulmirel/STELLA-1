SOFTWARE_VERSION_NUMBER = "0.0.2"
DEVICE_TYPE = "STELLA-1.2_Exposure_control"
# Paul Mirel 2025

# set the data_source period = reciprocal of the data_source cadence
#               seconds + ( minutes ) + ( hours )   + ( days )
preset_sample_interval_s = 10.0 + ( 0 * 60 ) + ( 0 * 3600 ) + ( 0 * 3600 * 24 )
preset_burst_count = 1
usb_serial_out_enabled = False
record_on_startup = True #False #

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
import neopixel
from adafruit_seesaw.seesaw import Seesaw
from adafruit_as7341 import AS7341
from adafruit_as7341 import Gain as AS7341_Gain
import qwiic_i2c
import qwiic_as7265x
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

spectral_sensors_detected = True

#### begin main definition

def main():
    BLUE = ( 0, 0, 255 )
    GREEN = ( 255, 0, 0 )
    YELLOW = ( 127, 255, 0 )
    RED = ( 0, 255, 0 )
    OFF = ( 0, 0, 0 )


    displayio.release_displays()
    UID = get_uid()
    spi_bus = board.SPI()
    vfs = initialize_sd_card( spi_bus, board.A5 )
    i2c_bus = initialize_i2c_bus()
    gps_uart_bus = initialize_uart( board.TX, board.RX )
    onboard_neopixel = initialize_neopixel( board.NEOPIXEL )
    if vfs:
        onboard_neopixel.fill(YELLOW)
    else:
        onboard_neopixel.fill(RED)
    buzzer = initialize_qwiic_buzzer( i2c_bus )
    buzzer.mute = False
    buzzer.set(932, 130) # frequency in Hz, time in ms. 932 Hz is B flat in octave 5. Fairly pleasant through this piezo driver, though maybe a bit medical in tone.
    buzzer.beep()
    battery_indicator = initialize_led( board.LED )

    instrument = create_instrument( i2c_bus, spi_bus, gps_uart_bus, UID, buzzer )
    instrument.welcome_page.show()

    as7265x_spectrometer = initialize_as7265x_spectrometer( instrument )
    as7331_spectrometer = initialize_as7331_spectrometer( instrument )
    as7341_spectrometer = initialize_as7341_spectrometer( instrument )



    ### temporary -- gain setting tests
    if False:
        for number in range (0,len(as7265x_spectrometer.gain_list)):
            gain_ratio = as7265x_spectrometer.set_gain( number )
            print( "as7265x gain ratio =", gain_ratio)
            time.sleep( 5 )
    if False:
        print( "is the as7331 gain ratio inverted in the library or in the sensor? check actual value outputs" )
        for number in range (0,len(as7331_spectrometer.gain_list)):
            gain_ratio = as7331_spectrometer.set_gain( number )
            print( "as7331 gain ratio =", gain_ratio)
            time.sleep( 5 )
    if True:#False:
        for number in range (0,len(as7341_spectrometer.gain_list)):
            gain_ratio = as7341_spectrometer.set_gain( number )
            print( "as7341 gain ratio =", gain_ratio)
            time.sleep( 5 )

    instrument.welcome_page.hide()
    exposure_control_page = make_exposure_control_page( instrument )
    exposure_control_page.show()
    stall()







###


    as7265x_gain_number_range = 0,3
    as7265x_gain_number = 3
    as7265x_gain_list = ( 1, 3.7, 16, 64 )
    as7265x_gain_max = max( as7265x_gain_list )
    as7265x_gain_min = min( as7265x_gain_list )
    as7265x_gain_span = as7265x_gain_max - as7265x_gain_min
    as7265x_gain_max_log = math.log( as7265x_gain_max, 10 )
    as7265x_gain_min_log = math.log( as7265x_gain_min, 10 )
    as7265x_gain_span_log = as7265x_gain_max_log - as7265x_gain_min_log



    as7265x_integration_time_ms_min = 2.8
    as7265x_integration_time_ms_max = 714
    as7265x_integration_time_min_log = math.log( as7265x_integration_time_ms_min, 10)
    as7265x_integration_time_max_log = math.log( as7265x_integration_time_ms_max, 10 )
    as7265x_integration_time_span_log = as7265x_integration_time_max_log - as7265x_integration_time_min_log







    exposure_control_page.sensor_choice_text_area.text = "as7265x V+NIR"

    #exposure_control_page.sensor_choice_text_area.text = "as7331 UV"
    #exposure_control_page.sensor_choice_text_area.text = "as7341 Vis"

    exposure_control_page.setting_text_area.text = "Manual"
    #exposure_control_page.setting_text_area.text = "Pre 1" #Preset
    #exposure_control_page.setting_text_area.text = "Auto"
    #exposure_control_page.setting_text_area.text = "Save"  #increment preset number and save current values to that preset

    #exposure_control_page.exposure_label_text_area.text = "*SATURATED*"
    #exposure_control_page.exposure_label_text_area.text = "Exposure Max"
    sensor_choice_dict = {0:"as7265x V+NIR", 1:"as7331 UV", 2:"as7341 Vis"}
    sensor_choice = 0

    slider_max_y = 50
    slider_min_y = 170
    slider_pixel_span = slider_min_y - slider_max_y

    gain_value = 0
    exposure_control_page.gain_text_area.text = str(gain_value)
    as7265x_gain_pixel_per_value_log = slider_pixel_span/as7265x_gain_span_log

    as7265x_integration_number = 1
    as7265x_integration_time_pixel_per_value_log = slider_pixel_span/as7265x_integration_time_span_log
    integration_time_ms = 0
    exposure_control_page.integration_time_text_area.text = str(integration_time_ms)

    lamp_current_mA = 0
    exposure_control_page.lamp_current_text_area.text = str(lamp_current_mA)
    exposure_high = 0
    exposure_max_value = 65535
    exposure_max_value_log = math.log(exposure_max_value, 10)
    #print( "exposure_max_value_log", exposure_max_value_log ) #4.81647
    exposure_control_page.exposure_maximum_text_area.text = str(exposure_high)
    exposure_value_span_log = exposure_max_value_log
    exposure_pixel_per_value_log = slider_pixel_span/exposure_value_span_log

    as7265x_integration_number = 80
    as7265x_integration_time_ms = as7265x_spectrometer.set_integration_number( as7265x_integration_number )
    gain_number = 3
    integration_number = 1
    as7265x_spectrometer.read_counts()
    try:
        operational = True
        while operational:
            exposure_control_page.sensor_choice_text_area.text = sensor_choice_dict[sensor_choice]
            print( "code running" )
            #print( "gain number", gain_number)
            as7265x_gain = as7265x_spectrometer.gain_dict[gain_number]
            as7265x_gain_log = math.log( as7265x_gain, 10 )
            exposure_control_page.gain_text_area.text = str(as7265x_gain)
            gain_pixel_offset = int( as7265x_gain_log * as7265x_gain_pixel_per_value_log )
            exposure_control_page.gain_slider.y = slider_min_y - gain_pixel_offset
            integration_time_ms = integration_number*2.8
            exposure_control_page.integration_time_text_area.text = str(int(round(integration_time_ms,0)))
            as7265x_integration_time_ms = integration_time_ms
            as7265x_integration_time_log = math.log( as7265x_integration_time_ms, 10 )
            integration_time_pixel_offset = int( (as7265x_integration_time_log- as7265x_integration_time_min_log)* as7265x_integration_time_pixel_per_value_log )
            exposure_control_page.integration_time_slider.y = slider_min_y - integration_time_pixel_offset



            as7265x_spectrometer.read_counts()
            #print( max(as7265x_spectrometer.data_counts), min(as7265x_spectrometer.data_counts) )
            exposure_high = max(as7265x_spectrometer.data_counts)
            if exposure_high > 0:
                exposure_high_log = math.log(exposure_high,10)
            else:
                exposure_high_log = 0
            exposure_low = min(as7265x_spectrometer.data_counts)
            if exposure_low > 0:
                exposure_low_log = math.log(exposure_low,10)
            else:
                exposure_low_log = 0
            #print( exposure_high, exposure_low )
            #print( exposure_high_log, exposure_low_log )
            exposure_control_page.exposure_maximum_text_area.text = str(exposure_high)
            exposure_high_pixel_offset = int( exposure_high_log * exposure_pixel_per_value_log )
            exposure_low_pixel_offset = int( exposure_low_log * exposure_pixel_per_value_log )
            exposure_control_page.exposure_bracket_high.y = slider_min_y - exposure_high_pixel_offset
            exposure_control_page.exposure_bracket_low.y = slider_min_y - exposure_low_pixel_offset

            if False: # if both selected and rotated
                sensor_choice = ( sensor_choice + 1 ) % len( sensor_choice_dict )
            as7265x_spectrometer.set_gain_number( as7265x_gain_number )
            if False: # if both selected and rotated
                gain_number = (gain_number + 1 ) % len( as7265x_gain_list ) #active sensor gain list
                if gain_number == 0:
                    as7265x_spectrometer.swob.set_gain(as7265x_spectrometer.swob.kGain1x)
                if gain_number == 1:
                    as7265x_spectrometer.swob.set_gain(as7265x_spectrometer.swob.kGain37x)
                if gain_number == 2:
                    as7265x_spectrometer.swob.set_gain(as7265x_spectrometer.swob.kGain16x)
                if gain_number == 3:
                    as7265x_spectrometer.swob.set_gain(as7265x_spectrometer.swob.kGain64x)
            if False:
                integration_number = ( integration_number + 1 ) % 255
                #print( "integration_number", integration_number )
            else:
                integration_number = 255
            as7265x_integration_time_ms = as7265x_spectrometer.swob.set_integration_cycles( integration_number )
            time.sleep( 5 )
    finally:
        displayio.release_displays()
        print( "displayio displays released" )
        i2c_bus.deinit()
        print( "i2c_bus deinitialized" )


#### begin parent class definitions ###

class Page:
    def __init__( self ):
        pass
    def show(self):
        self.group.hidden = False
    def hide(self):
        self.group.hidden = True
    def update_values(self):
        pass

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

#### begin spectrometer sensor device classes

class as7265x_Spectrometer( Device ):
    # custom library
    # cycle time is a little less than 1 whole second
    def __init__( self, com_bus ):
        super().__init__(name = "as7265x_spectrometer", pn = "as7256x", address = 0x49, swob = qwiic_as7265x.QwiicAS7265x(  )) #
        if self.swob:
            self.swob.disable_indicator()
            self.swob.set_measurement_mode(self.swob.kMeasurementMode6ChanContinuous)
            self.bands = 610, 680, 730, 760, 810, 860, 560, 585, 645, 705, 900, 940, 410, 435, 460, 485, 510, 535
            self.bandwidth = 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20
            self.chip_n = 1,   1,   1,   1,   1,   1,   2,   2,   2,   2,   2,   2,   3,   3,   3,   3,   3,   3
            self.dict_chip_n = {key:value for key, value in zip(self.bands, self.chip_n )}
            self.dict_bandwidths = {key:value for key, value in zip(self.bands, self.bandwidth )}
            self.bands_sorted = sorted( self.bands )
            self.uncertainty_percent = 12
            self.gain_list = [ 1, 3.7, 16, 64 ]
            self.intg_time_ms = 56 #default, number = 20 out of 255
            self.afov_deg = (20.5 * 2) #datasheet reports half angle.
    def set_gain(self, number):
        if number < 1 :
            self.swob.set_gain( self.swob.kGain1x )
        elif number == 1:
            self.swob.set_gain( self.swob.kGain37x )
        elif number == 2:
            self.swob.set_gain( self.swob.kGain16x )
        elif number > 2:
            self.swob.set_gain( self.swob.kGain64x )
        return self.gain_list[ number ]
    def set_integration_number( self, number ):
        # must wait for at least 5 seconds before sending integration time again. If not, signal goes to 0.
        if number in range (1, 256):
            self.swob.set_integration_cycles(number)
            self.intg_time_ms = int(round(2.78*number,0)) # This sensor does not use the ASTEP ATIME combination found in the as7341
        else:
            print( "out of range: set integration cycles to 1-255 for 0-709ms integration time." )
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
        self.data_counts = []
        self.data_counts.append(self.swob.get_g()) #get_value(0) # 0th position raw counts, bands unsorted order
        self.data_counts.append(self.swob.get_h())
        self.data_counts.append(self.swob.get_i())
        self.data_counts.append(self.swob.get_j())
        self.data_counts.append(self.swob.get_k())
        self.data_counts.append(self.swob.get_l())
        self.data_counts.append(self.swob.get_r())
        self.data_counts.append(self.swob.get_s())
        self.data_counts.append(self.swob.get_t())
        self.data_counts.append(self.swob.get_u())
        self.data_counts.append(self.swob.get_v())
        self.data_counts.append(self.swob.get_w())
        self.data_counts.append(self.swob.get_a())
        self.data_counts.append(self.swob.get_b())
        self.data_counts.append(self.swob.get_c())
        self.data_counts.append(self.swob.get_d())
        self.data_counts.append(self.swob.get_e())
        self.data_counts.append(self.swob.get_f())
        #print(self.data_counts)
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
        self.intg_time_ms = 0 #TBD what are the defaults?
        self.gain_list = [ 1,2,4,8,16,32,64,128,256,512,1024,2048 ]


    def set_gain(self, number):
        if number < 1:
            gain_constant = as7331.GAIN_1X
        if number == 1:
            gain_constant = as7331.GAIN_2X
        if number == 2:
            gain_constant = as7331.GAIN_4X
        if number == 3:
            gain_constant = as7331.GAIN_8X
        if number == 4:
            gain_constant = as7331.GAIN_16X
        if number == 5:
            gain_constant = as7331.GAIN_32X
        if number == 6:
            gain_constant = as7331.GAIN_64X
        if number == 7:
            gain_constant = as7331.GAIN_128X
        if number == 8:
            gain_constant = as7331.GAIN_256X
        if number == 9:
            gain_constant = as7331.GAIN_512X
        if number == 10:
            gain_constant = as7331.GAIN_1024X
        if number > 10:
            gain_constant = as7331.GAIN_2048X
        self.swob.gain = gain_constant
        return self.gain_list[ self.swob.gain ]



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
        print( "as7341 Sten O cal counts per irradiance at what gain?  TBD " )
        self.steno_cal_counts_per_irradiance = 4398.0, 6104.0, 7583.0, 9972.0, 11536.0, 13374.0, 17115.0, 20916.0
        self.calibration_error = 0.6
        self.irradiance = [0,0,0,0,0,0,0,0]
        self.dict_stenocal = {}
        self.swob.led_current = 50
        self.gain_list = [ 0.5, 1, 2, 4, 8, 16, 32, 64, 128, 256 ]
        self.gain_number = 5 #default to 16x gain
    def set_gain(self, number):
        if number < 1:
            gain_constant = AS7341_Gain.GAIN_0_5X
        if number == 1:
            gain_constant = AS7341_Gain.GAIN_1X
        if number == 2:
            gain_constant = AS7341_Gain.GAIN_2X
        if number == 3:
            gain_constant = AS7341_Gain.GAIN_4X
        if number == 4:
            gain_constant = AS7341_Gain.GAIN_8X
        if number == 5:
            gain_constant = AS7341_Gain.GAIN_16X
        if number == 6:
            gain_constant = AS7341_Gain.GAIN_32X
        if number == 7:
            gain_constant = AS7341_Gain.GAIN_64X
        if number == 8:
            gain_constant = AS7341_Gain.GAIN_128X
        if number == 9:
            gain_constant = AS7341_Gain.GAIN_256X
        if number > 9:
            gain_constant = AS7341_Gain.GAIN_512X
        self.swob._gain = gain_constant
        return self.gain_list[ self.swob._gain ]
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


#### begin spectrometer sensor initialization definitions
def initialize_as7265x_spectrometer( instrument ):
    as7265x_spectrometer = Null_as7265x_Spectrometer()
    try:
        as7265x_spectrometer = as7265x_Spectrometer( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_as7265x_spectrometer" )
        instrument.spectral_sensors_present.append( as7265x_spectrometer )
        as7265x_spectrometer.lamps_on()
        time.sleep(0.1)
        as7265x_spectrometer.lamps_off()
    except Exception as err:
        print( "as7265x spectrometer failed: {}".format( err ))
        pass
    return as7265x_spectrometer

def initialize_as7331_spectrometer( instrument ):
    as7331_spectrometer = Null_as7331_Spectrometer()
    try:
        as7331_spectrometer = as7331_Spectrometer( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_as7331_spectrometer" )
        instrument.spectral_sensors_present.append( as7331_spectrometer )
    except ValueError as err:
        #print( "uv spectrometer failed to initialize: {}".format(err))
        pass
    except Exception as err:
        print( "as7331_spectrometer", err )
        pass
    return as7331_spectrometer

def initialize_as7341_spectrometer( instrument ):
    as7341_spectrometer = Null_as7341_Spectrometer()
    try:
        as7341_spectrometer = as7341_Spectrometer( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_as7341_spectrometer" )
        instrument.spectral_sensors_present.append( as7341_spectrometer )
    except Exception as err:
        print( "as7341_spectrometer", err )
        pass
    return as7341_spectrometer


#### begin spectrometer sensor null class definitions

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




#### begin instrument class definition

class Instrument:
    def __init__( self, i2c_bus, spi_bus, uart_bus, UID, buzzer):
        self.i2c_bus = i2c_bus
        self.uart_bus = uart_bus
        self.device_type = DEVICE_TYPE
        self.uid = UID
        self.buzzer = buzzer
        self.usb_serial_out_enabled = usb_serial_out_enabled
        self.sample_interval_s = preset_sample_interval_s
        self.burst_count = preset_burst_count
        self.usb_serial_out_enabled = usb_serial_out_enabled
        self.pages_list = []
        self.palette = make_palette()
        self.main_display_group = initialize_display( spi_bus )
        self.welcome_page = make_welcome_page( self )
        #self.hardware_clock = initialize_hardware_clock( i2c_bus )
        #self.hardware_clock.report()
        #self.hardware_clock.sync_system_clock()
        #self.clock_battery_ok_text =  "clock battery OK: {}".format( self.hardware_clock.battery_ok() )
        #self.welcome_page.announce( self.clock_battery_ok_text )
        #self.datestamp = self.hardware_clock.get_datestamp_now()
        #self.last_datestamp = self.datestamp
        #self.iso_time = self.hardware_clock.get_iso_time_now()
        #self.batch_number = update_batch(self.datestamp)
        #print( "batch number = {}".format( self.batch_number ))
        self.filename = None
        self.sensors_present = []
        self.spectral_sensors_present = []
        self.spectrometry = spectral_sensors_detected
        self.record = record_on_startup
        #self.session_tag = "{}-{}-session-".format(self.uid, self.iso_time)
        self.measurement_counter = 0
        self.rotary_encoder = initialize_rotary_encoder( pin_a = board.A3, pin_b = board.A4, pin_button = board.A2 )
        self.encoder_increment = 0
        self.button_pressed = False
        self.touch_screen = initialize_touch_screen( self.i2c_bus )
        self.input_flag = False
        self.input_interval_start = 0
        self.input_interval = 1
        self.active_page_number = 2
        self.last_active_page_number = 0
        self.take_burst = False
        self.main_menu_select = 6  # default to first main menu item selected
        self.main_menu_select_count = 17
        self.remote_sensing_select = 2  # default to record/pause
        self.remote_sensing_select_count = 17
    def update_batch(self):
        self.batch_number = update_batch(self.datestamp)
    def update_time(self):
        self.datestamp = self.hardware_clock.get_datestamp_now()
        self.iso_time = self.hardware_clock.get_iso_time_now()
        self.decimal_time = self.hardware_clock.get_decimal_hour_now()
    def update_filename(self):
        update_filename( self )
        print( "filename_in_use:", self.filename )
    def check_calendar_day( self ):
        self.datestamp = self.hardware_clock.get_datestamp_now()
        if self.datestamp != self.last_datestamp:
            self.last_datestamp = self.datestamp
            print( "new calendar day, updating system values" )
            self.update_batch()
            self.update_filename()
            self.session_tag = "{}-{}-session-".format(self.uid, self.iso_time)
            self.measurement_counter = 0
    def make_band_list( self ):
        self.wavelength_bands_list = []
        for sensor in self.spectral_sensors_present:
            for band in sensor.bands:
                self.wavelength_bands_list.append(band)
        self.wavelength_bands_list_sorted = sorted( self.wavelength_bands_list )
        #print( "line 411 -- wavelength_bands_list_sorted: ")
        #print( self.wavelength_bands_list_sorted  )
        self.number_of_plot_points = len( self.wavelength_bands_list_sorted )
        #print( "number of bands: ", end = "")
        #print( self.number_of_plot_points )
    def make_header( self ):
        self.header = "unique_identifier"
        self.header += ", unique_measurement_number"
        self.header += ", timestamp-!-iso8601utc"
        self.header += ", batch_number"
        self.header += ", burst_counter"
        self.header += ", decimal_time-!-hour"
        self.system_header = self.header
        spectral_header_list = []
        spectral_header_list.append( "spectral_sensor_part_number" )
        spectral_header_list.append( "spectral_wavelength-!-nm" )
        spectral_header_list.append( "spectral_bandwidth-!-nm" )
        spectral_header_list.append( "spectral_photodetector_digital_number-!-counts" )
        spectral_header_list.append( "spectral_irradiance-!-uW_per_cm_sq" )
        spectral_header_list.append( "spectral_uncertainty_in_irradiance-!-uW_per_cm_sq" )
        spectral_header_list.append( "spectral_gain-!-" )
        spectral_header_list.append( "spectral_integration_time-!-ms" )
        spectral_header_list.append( "spectral_detector_chip_number" )
        spectral_header_list.append( "spectral_detector_chip_temperature-!-C" )
        self.spectral_header_count = len( spectral_header_list )
        if self.spectrometry:
            for item in spectral_header_list:
                self.header += ", {}".format( item )
        for sensor in self.sensors_present:
            self.header += ", "
            self.header += sensor.header()
        self.header += ("\n")
        #print( self.header )
        #print( "spectral_header_count: ", self.spectral_header_count )
        self.update_filename()
    def hide_all_pages( self ):
        for item in self.pages_list:
            item.hide()
    def build_unique_measurement_number( self ):
        self.unique_measurement_number = "{}{}".format(self.session_tag, self.measurement_counter)
        return self.unique_measurement_number
    def get_system_log( self ):
        self.update_time()
        self.build_unique_measurement_number()
        system_log = "{}".format( self.uid )
        system_log += ", {}".format( self.unique_measurement_number )
        system_log += ", {}".format( self.iso_time )
        system_log += ", {}".format( self.batch_number )
        system_log += ", {}".format( self.burst_counter )
        system_log += ", {}".format( self.decimal_time )
        return system_log
    def check_inputs( self ):
        self.touch_screen.read()
        if not self.touch_screen.flag and self.touch_screen.is_touched:
            self.touch_tx = self.touch_screen.tx
            self.touch_ty = self.touch_screen.ty
            self.input_flag = True
            self.input_interval_start = time.monotonic()
        self.rotary_encoder.read_button()
        if self.rotary_encoder.button_flag:
            self.buzzer.beep()
            self.button_pressed = True
            self.rotary_encoder.button_flag = False
            self.input_flag = True
            self.input_interval_start = time.monotonic()
        self.rotary_encoder.read_encoder()
        if self.rotary_encoder.encoder_flag:
            self.encoder_increment = self.rotary_encoder.last_value
            self.rotary_encoder.encoder_flag = False
            self.input_flag = True
            self.input_interval_start = time.monotonic()
    def add_spectral_graph_page( self, spectral_graph_page ):
        self.spectral_graph_page = spectral_graph_page
    def show_active_page( self ):
        if self.active_page_number != self.last_active_page_number:
            self.last_active_page_number = self.active_page_number
            hide_all_pages( self.pages_list )
            self.pages_list[ self.active_page_number ].show()
            if self.active_page_number == 2 or self.active_page_number == 9: # main menu, remote sensing
                self.pages_list[ 1 ].show()  # controls
            if self.active_page_number == 9:
                if spectral_sensors_detected:
                    self.pages_list[ 10 ].show() # spectral graph
    def update_active_page( self ):
        self.pages_list[ self.active_page_number ].update_values( self )
        if self.active_page_number == 9:
            if spectral_sensors_detected:
                self.spectral_graph_page.update_plot_data()
        if self.encoder_increment != 0:
            if self.active_page_number == 2:
                self.main_menu_select = (self.main_menu_select + self.encoder_increment) % self.main_menu_select_count
            if self.active_page_number == 9:
                self.remote_sensing_select = (self.remote_sensing_select + self.encoder_increment) % self.remote_sensing_select_count
            self.encoder_increment = 0

def create_instrument( i2c_bus, spi_bus, uart_bus, UID, buzzer ):
    instrument = Instrument( i2c_bus, spi_bus, uart_bus, UID, buzzer )
    return instrument



#### begin exposure control page class definition

class Exposure_Control_Page( Page ):
    def __init__( self, palette ):
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

        # top row
        top_row_y = 4
        return_select_x = 4
        return_select_y = top_row_y
        return_select_width = 40
        return_select_height = 40
        self.return_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=return_select_width,
                                                    height=return_select_height, x=return_select_x, y=return_select_y )
        self.group.append( self.return_select )
        self.return_select.hidden = True

        return_border_width = return_select_width - 2*select_width
        return_border_height = return_select_height - 2*select_width
        return_border_x = return_select_x+select_width
        return_border_y = return_select_y+select_width
        return_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=return_border_width,
                                            height=return_border_height, x=return_border_x, y=return_border_y )
        self.group.append( return_border )

        return_area_width = return_border_width - 2*border_width
        return_area_height = return_border_height - 2*border_width
        return_area_x = return_border_x+border_width
        return_area_y = return_border_y+border_width
        return_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=return_area_width,
                                            height=return_area_height, x=return_area_x, y=return_area_y ) #color_index = 19
        self.group.append( return_area )

        return_triangle_x = return_border_x
        return_triangle_y = return_border_y
        return_triangle = vectorio.Polygon( pixel_shader=self.palette, color_index = 0, points = [(4, 16), (25,4), (25,28)], x=return_triangle_x, y=return_triangle_y )
        self.group.append( return_triangle )

        sensor_choice_select_x = return_select_x + return_select_width
        sensor_choice_select_y = top_row_y
        sensor_choice_select_width = 180
        sensor_choice_select_height = 40
        self.sensor_choice_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=sensor_choice_select_width,
                                                    height=sensor_choice_select_height, x=sensor_choice_select_x, y=sensor_choice_select_y )
        self.group.append( self.sensor_choice_select )
        self.sensor_choice_select.hidden = True

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
        sensor_choice_text = " -- "
        self.sensor_choice_text_area = label.Label(terminalio.FONT, text=sensor_choice_text, color=self.palette[0])
        sensor_choice_text_group.append(self.sensor_choice_text_area)
        self.group.append(sensor_choice_text_group)


        setting_select_x = sensor_choice_select_x + sensor_choice_select_width
        setting_select_y = top_row_y
        setting_select_width = 94
        setting_select_height = 40
        self.setting_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=setting_select_width,
                                                    height=setting_select_height, x=setting_select_x, y=setting_select_y )
        self.group.append( self.setting_select )
        self.setting_select.hidden = True

        setting_border_width = setting_select_width - 2*select_width
        setting_border_height = setting_select_height - 2*select_width
        setting_border_x = setting_select_x+select_width
        setting_border_y = setting_select_y+select_width
        setting_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=setting_border_width,
                                            height=setting_border_height, x=setting_border_x, y=setting_border_y )
        self.group.append( setting_border )

        setting_area_width = setting_border_width - 2*border_width
        setting_area_height = setting_border_height - 2*border_width
        setting_area_x = setting_border_x+border_width
        setting_area_y = setting_border_y+border_width
        setting_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=setting_area_width,
                                            height=setting_area_height, x=setting_area_x, y=setting_area_y )
        self.group.append( setting_area )
        setting_text_x = setting_area_x+text_offset_x
        setting_text_y = setting_area_y+text_offset_y
        setting_text_group = displayio.Group(scale=2, x=setting_text_x, y=setting_text_y)
        setting_text = " -- "
        self.setting_text_area = label.Label(terminalio.FONT, text=setting_text, color=self.palette[0])
        setting_text_group.append(self.setting_text_area)
        self.group.append(setting_text_group)

        # bottom row
        gain_select_x = 4
        gain_select_y = 240-40-select_width
        gain_select_width = 70
        gain_select_height = 40
        self.gain_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=gain_select_width,
                                                    height=gain_select_height, x=gain_select_x, y=gain_select_y )
        self.group.append( self.gain_select )
        self.gain_select.hidden = True

        gain_border_width = gain_select_width - 2*select_width
        gain_border_height = gain_select_height - 2*select_width
        gain_border_x = gain_select_x+select_width
        gain_border_y = gain_select_y+select_width
        gain_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=gain_border_width,
                                            height=gain_border_height, x=gain_border_x, y=gain_border_y )
        self.group.append( gain_border )

        gain_area_width = gain_border_width - 2*border_width
        gain_area_height = gain_border_height - 2*border_width
        gain_area_x = gain_border_x+border_width
        gain_area_y = gain_border_y+border_width
        gain_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=gain_area_width,
                                            height=gain_area_height, x=gain_area_x, y=gain_area_y )
        self.group.append( gain_area )
        gain_text_x = gain_area_x+text_offset_x
        gain_text_y = gain_area_y+text_offset_y
        gain_text_group = displayio.Group(scale=2, x=gain_text_x, y=gain_text_y)
        gain_text = " -- "
        self.gain_text_area = label.Label(terminalio.FONT, text=gain_text, color=self.palette[0])
        gain_text_group.append(self.gain_text_area)
        self.group.append(gain_text_group)

        # sliders

        slider_select_y = 46
        slider_select_width = 62
        slider_select_height = 136
        slider_min_y = 170
        slider_border_width = slider_select_width - 2*select_width
        slider_width = 42
        slider_height = 8

        gain_slider_select_x = gain_select_x + select_width
        gain_slider_select_y = slider_select_y
        gain_slider_select_width = slider_select_width
        gain_slider_select_height = slider_select_height
        self.gain_slider_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=gain_slider_select_width,
                                                    height=gain_slider_select_height, x=gain_slider_select_x, y=gain_slider_select_y )
        self.group.append( self.gain_slider_select )
        self.gain_slider_select.hidden = True

        gain_slider_border_width = slider_border_width
        gain_slider_border_height = gain_slider_select_height - 2*select_width
        gain_slider_border_x = gain_slider_select_x+select_width
        gain_slider_border_y = gain_slider_select_y+select_width
        gain_slider_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=gain_slider_border_width,
                                            height=gain_slider_border_height, x=gain_slider_border_x, y=gain_slider_border_y )
        self.group.append( gain_slider_border )

        gain_slider_area_width = gain_slider_border_width - 2*border_width
        gain_slider_area_height = gain_slider_border_height - 2*border_width
        gain_slider_area_x = gain_slider_border_x+border_width
        gain_slider_area_y = gain_slider_border_y+border_width
        gain_slider_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=gain_slider_area_width,
                                            height=gain_slider_area_height, x=gain_slider_area_x, y=gain_slider_area_y )
        self.group.append( gain_slider_area )

        gain_slider_width = slider_width
        gain_slider_height = slider_height
        gain_slider_x = gain_slider_border_x + 3* border_width
        gain_slider_y = slider_min_y
        self.gain_slider = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=gain_slider_width,
                                            height=gain_slider_height, x=gain_slider_x, y=gain_slider_y )
        self.group.append( self.gain_slider )

        integration_slider_select_x = 86
        integration_slider_select_y = slider_select_y
        integration_slider_select_width = slider_select_width
        integration_slider_select_height = slider_select_height
        self.integration_slider_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=integration_slider_select_width,
                                                    height=integration_slider_select_height, x=integration_slider_select_x, y=integration_slider_select_y )
        self.group.append( self.integration_slider_select )
        self.integration_slider_select.hidden = True

        integration_slider_border_width = slider_border_width
        integration_slider_border_height = integration_slider_select_height - 2*select_width
        integration_slider_border_x = integration_slider_select_x+select_width
        integration_slider_border_y = integration_slider_select_y+select_width
        integration_slider_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=integration_slider_border_width,
                                            height=integration_slider_border_height, x=integration_slider_border_x, y=integration_slider_border_y )
        self.group.append( integration_slider_border )

        integration_slider_area_width = integration_slider_border_width - 2*border_width
        integration_slider_area_height = integration_slider_border_height - 2*border_width
        integration_slider_area_x = integration_slider_border_x+border_width
        integration_slider_area_y = integration_slider_border_y+border_width
        integration_slider_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=integration_slider_area_width,
                                            height=integration_slider_area_height, x=integration_slider_area_x, y=integration_slider_area_y )
        self.group.append( integration_slider_area )

        integration_slider_width = slider_width
        integration_slider_height = slider_height
        integration_slider_x = integration_slider_border_x + 3* border_width
        self.integration_slider_y = slider_min_y
        self.integration_time_slider = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=integration_slider_width,
                                            height=integration_slider_height, x=integration_slider_x, y=self.integration_slider_y )
        self.group.append( self.integration_time_slider )

        lamp_current_slider_select_x = 164
        lamp_current_slider_select_y = slider_select_y
        lamp_current_slider_select_width = slider_select_width
        lamp_current_slider_select_height = slider_select_height
        self.lamp_current_slider_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=lamp_current_slider_select_width,
                                                    height=lamp_current_slider_select_height, x=lamp_current_slider_select_x, y=lamp_current_slider_select_y )
        self.group.append( self.lamp_current_slider_select )
        self.lamp_current_slider_select.hidden = True

        lamp_current_slider_border_width = slider_border_width
        lamp_current_slider_border_height = lamp_current_slider_select_height - 2*select_width
        lamp_current_slider_border_x = lamp_current_slider_select_x+select_width
        lamp_current_slider_border_y = lamp_current_slider_select_y+select_width
        lamp_current_slider_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=lamp_current_slider_border_width,
                                            height=lamp_current_slider_border_height, x=lamp_current_slider_border_x, y=lamp_current_slider_border_y )
        self.group.append( lamp_current_slider_border )

        lamp_current_slider_area_width = lamp_current_slider_border_width - 2*border_width
        lamp_current_slider_area_height = lamp_current_slider_border_height - 2*border_width
        lamp_current_slider_area_x = lamp_current_slider_border_x+border_width
        lamp_current_slider_area_y = lamp_current_slider_border_y+border_width
        lamp_current_slider_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=lamp_current_slider_area_width,
                                            height=lamp_current_slider_area_height, x=lamp_current_slider_area_x, y=lamp_current_slider_area_y )
        self.group.append( lamp_current_slider_area )

        lamp_current_slider_width = slider_width
        lamp_current_slider_height = slider_height
        lamp_current_slider_x = lamp_current_slider_border_x + 3* border_width
        self.lamp_current_slider_y = slider_min_y
        lamp_current_slider = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=lamp_current_slider_width,
                                            height=lamp_current_slider_height, x=lamp_current_slider_x, y=self.lamp_current_slider_y )
        self.group.append( lamp_current_slider )

        exposure_bracket_border_width = slider_border_width+12
        exposure_bracket_border_height = gain_slider_select_height - 2*select_width
        exposure_bracket_border_x = 240
        exposure_bracket_border_y = gain_slider_border_y
        exposure_bracket_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=exposure_bracket_border_width,
                                            height=exposure_bracket_border_height, x=exposure_bracket_border_x, y=exposure_bracket_border_y )
        self.group.append( exposure_bracket_border )

        exposure_bracket_area_width = exposure_bracket_border_width - 2*border_width
        exposure_bracket_area_height = exposure_bracket_border_height - 2*border_width
        exposure_bracket_area_x = exposure_bracket_border_x+border_width
        exposure_bracket_area_y = exposure_bracket_border_y+border_width
        exposure_bracket_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=exposure_bracket_area_width,
                                            height=exposure_bracket_area_height, x=exposure_bracket_area_x, y=exposure_bracket_area_y )
        self.group.append( exposure_bracket_area )

        exposure_bracket_width = slider_width+12
        exposure_bracket_height = slider_height
        exposure_bracket_x = exposure_bracket_border_x + 3* border_width
        exposure_bracket_high_y = 170
        self.exposure_bracket_high = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=exposure_bracket_width,
                                            height=exposure_bracket_height, x=exposure_bracket_x, y=exposure_bracket_high_y )
        self.group.append( self.exposure_bracket_high )

        exposure_bracket_low_y = 170
        self.exposure_bracket_low = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=exposure_bracket_width,
                                            height=exposure_bracket_height, x=exposure_bracket_x, y=exposure_bracket_low_y )
        self.group.append( self.exposure_bracket_low )

        integration_time_select_x = gain_select_x + gain_select_width
        integration_time_select_y = 240-40-select_width
        integration_time_select_width = 84
        integration_time_select_height = 40
        self.integration_time_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=integration_time_select_width,
                                                    height=integration_time_select_height, x=integration_time_select_x, y=integration_time_select_y )
        self.group.append( self.integration_time_select )
        self.integration_time_select.hidden = True

        integration_time_border_width = integration_time_select_width - 2*select_width
        integration_time_border_height = integration_time_select_height - 2*select_width
        integration_time_border_x = integration_time_select_x+select_width
        integration_time_border_y = integration_time_select_y+select_width
        integration_time_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=integration_time_border_width,
                                            height=integration_time_border_height, x=integration_time_border_x, y=integration_time_border_y )
        self.group.append( integration_time_border )

        integration_time_area_width = integration_time_border_width - 2*border_width
        integration_time_area_height = integration_time_border_height - 2*border_width
        integration_time_area_x = integration_time_border_x+border_width
        integration_time_area_y = integration_time_border_y+border_width
        integration_time_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=integration_time_area_width,
                                            height=integration_time_area_height, x=integration_time_area_x, y=integration_time_area_y )
        self.group.append( integration_time_area )
        integration_time_text_x = integration_time_area_x+text_offset_x
        integration_time_text_y = integration_time_area_y+text_offset_y
        integration_time_text_group = displayio.Group(scale=2, x=integration_time_text_x, y=integration_time_text_y)
        integration_time_text = " -- "
        self.integration_time_text_area = label.Label(terminalio.FONT, text=integration_time_text, color=self.palette[0])
        integration_time_text_group.append(self.integration_time_text_area)
        self.group.append(integration_time_text_group)

        lamp_current_select_x = integration_time_select_x + integration_time_select_width
        lamp_current_select_y = 240-40-select_width
        lamp_current_select_width = 70
        lamp_current_select_height = 40
        self.lamp_current_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=lamp_current_select_width,
                                                    height=lamp_current_select_height, x=lamp_current_select_x, y=lamp_current_select_y )
        self.group.append( self.lamp_current_select )
        self.lamp_current_select.hidden = True

        lamp_current_border_width = lamp_current_select_width - 2*select_width
        lamp_current_border_height = lamp_current_select_height - 2*select_width
        lamp_current_border_x = lamp_current_select_x+select_width
        lamp_current_border_y = lamp_current_select_y+select_width
        lamp_current_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=lamp_current_border_width,
                                            height=lamp_current_border_height, x=lamp_current_border_x, y=lamp_current_border_y )
        self.group.append( lamp_current_border )

        lamp_current_area_width = lamp_current_border_width - 2*border_width
        lamp_current_area_height = lamp_current_border_height - 2*border_width
        lamp_current_area_x = lamp_current_border_x+border_width
        lamp_current_area_y = lamp_current_border_y+border_width
        lamp_current_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=lamp_current_area_width,
                                            height=lamp_current_area_height, x=lamp_current_area_x, y=lamp_current_area_y )
        self.group.append( lamp_current_area )
        lamp_current_text_x = lamp_current_area_x+text_offset_x
        lamp_current_text_y = lamp_current_area_y+text_offset_y
        lamp_current_text_group = displayio.Group(scale=2, x=lamp_current_text_x, y=lamp_current_text_y)
        lamp_current_text = " -- "
        self.lamp_current_text_area = label.Label(terminalio.FONT, text=lamp_current_text, color=self.palette[0])
        lamp_current_text_group.append(self.lamp_current_text_area)
        self.group.append(lamp_current_text_group)

        exposure_maximum_select_x = lamp_current_select_x + lamp_current_select_width + select_width
        exposure_maximum_select_y = 240-40-select_width
        exposure_maximum_select_width = 84
        exposure_maximum_select_height = 40
        self.exposure_maximum_select = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=exposure_maximum_select_width,
                                                    height=exposure_maximum_select_height, x=exposure_maximum_select_x, y=exposure_maximum_select_y )
        self.group.append( self.exposure_maximum_select )
        self.exposure_maximum_select.hidden = True

        exposure_maximum_border_width = exposure_maximum_select_width - 2*select_width
        exposure_maximum_border_height = exposure_maximum_select_height - 2*select_width
        exposure_maximum_border_x = exposure_maximum_select_x+select_width
        exposure_maximum_border_y = exposure_maximum_select_y+select_width
        exposure_maximum_border = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0, width=exposure_maximum_border_width,
                                            height=exposure_maximum_border_height, x=exposure_maximum_border_x, y=exposure_maximum_border_y )
        self.group.append( exposure_maximum_border )

        exposure_maximum_area_width = exposure_maximum_border_width - 2*border_width
        exposure_maximum_area_height = exposure_maximum_border_height - 2*border_width
        exposure_maximum_area_x = exposure_maximum_border_x+border_width
        exposure_maximum_area_y = exposure_maximum_border_y+border_width
        exposure_maximum_area = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=exposure_maximum_area_width,
                                            height=exposure_maximum_area_height, x=exposure_maximum_area_x, y=exposure_maximum_area_y )
        self.group.append( exposure_maximum_area )
        exposure_maximum_text_x = exposure_maximum_area_x+text_offset_x
        exposure_maximum_text_y = exposure_maximum_area_y+text_offset_y
        exposure_maximum_text_group = displayio.Group(scale=2, x=exposure_maximum_text_x, y=exposure_maximum_text_y)
        exposure_maximum_text = " -- " #65535
        self.exposure_maximum_text_area = label.Label(terminalio.FONT, text=exposure_maximum_text, color=self.palette[0])
        exposure_maximum_text_group.append(self.exposure_maximum_text_area)
        self.group.append(exposure_maximum_text_group)

        # labels
        label_bar_width = 320
        label_bar_height = 18
        label_bar_x = 0
        label_bar_y = exposure_maximum_select_y - label_bar_height + select_width
        label_bar = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=label_bar_width,
                                            height=label_bar_height, x=label_bar_x, y=label_bar_y )
        self.group.append( label_bar )

        value_label_text_x = 12 +14
        value_label_text_y = gain_area_y - 10
        value_label_text_group = displayio.Group(scale=1, x=value_label_text_x, y=value_label_text_y)
        value_label_text = "Gain"
        value_label_text_area = label.Label(terminalio.FONT, text=value_label_text, color=self.palette[0])
        value_label_text_group.append(value_label_text_area)
        self.group.append(value_label_text_group)

        value_label_text_x = 80
        value_label_text_y = gain_area_y - 10
        value_label_text_group = displayio.Group(scale=1, x=value_label_text_x, y=value_label_text_y)
        value_label_text = "Integ time ms"
        value_label_text_area = label.Label(terminalio.FONT, text=value_label_text, color=self.palette[0])
        value_label_text_group.append(value_label_text_area)
        self.group.append(value_label_text_group)

        value_label_text_x = 166+8
        value_label_text_y = gain_area_y - 10
        value_label_text_group = displayio.Group(scale=1, x=value_label_text_x, y=value_label_text_y)
        value_label_text = "Lamp mA"
        value_label_text_area = label.Label(terminalio.FONT, text=value_label_text, color=self.palette[0])
        value_label_text_group.append(value_label_text_area)
        self.group.append(value_label_text_group)

        exposure_label_text_x = 240
        exposure_label_text_y = gain_area_y - 10
        exposure_label_text_group = displayio.Group(scale=1, x=exposure_label_text_x, y=value_label_text_y)
        exposure_label_text = "Exposure Max"
        self.exposure_label_text_area = label.Label(terminalio.FONT, text=exposure_label_text, color=self.palette[0])
        exposure_label_text_group.append(self.exposure_label_text_area)
        self.group.append(exposure_label_text_group)

        return self.group
    def update_values( self ):
        #if instrument.active_page_number == 3:
        if instrument.button_pressed:
            instrument.active_page_number = 2
            instrument.button_pressed = False

def make_exposure_control_page( instrument ):
    page = Exposure_Control_Page( instrument.palette )
    group = page.make_group()
    #page.hide()
    instrument.main_display_group.append( group )
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

class Welcome_Page( Page ):
    def __init__( self ):
        super().__init__()
    def make_group( self ):
        self.group = displayio.Group()
        try:
            bitmap = displayio.OnDiskBitmap("/lib/stella_logo.bmp")
            #print( "Bitmap image file found" )
            # Create a TileGrid to hold the bitmap
            tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
            self.group.append(tile_grid)

            version_group = displayio.Group( scale=2, x=40, y=185 )
            text = "STELLA-1.2 ver {}".format( SOFTWARE_VERSION_NUMBER )
            version_area = label.Label( terminalio.FONT, text=text, color=0x000000 )
            version_group.append( version_area )
            self.group.append( version_group )

            message_group = displayio.Group( scale=2, x=4, y=220 )
            text = ""
            self.message_area = label.Label( terminalio.FONT, text=text, color=0x000000 )
            message_group.append( self.message_area )
            self.group.append( message_group )

            #battery_group = displayio.Group( scale=2, x=90, y=215 )
            #text = "battery {}%".format( battery_level )
            #battery_area = label.Label( terminalio.FONT, text=text, color=0x000000 )
            #battery_group.append( battery_area )
            #welcome_group.append( battery_group )
            #print( "showing welcome screen with logo")
        except (MemoryError, OSError):
            print( "bitmap image file not found or memory not available" )
            border_color = 0xFF0022 # red
            front_color = 0x0000FF # blue
            if (display == False):
                print("No display")
                return
            border = displayio.Palette(1)
            border[0] = border_color
            front = displayio.Palette(1)
            front[0] = front_color
            outer_rectangle = vectorio.Rectangle(pixel_shader=border, width=320, height=240, x=0, y=0)
            self.group.append( outer_rectangle )
            front_rectangle = vectorio.Rectangle(pixel_shader=front, width=280, height=200, x=20, y=20)
            self.group.append( front_rectangle )
            text_group = displayio.Group( scale=4, x=45, y=110 )
            text = "STELLA-1.2"
            text_area = label.Label( terminalio.FONT, text=text, color=0xFFFFFF )
            text_group.append( text_area )
            self.group.append( text_group )

            version_group = displayio.Group( scale=2, x=27, y=200 )
            text = "software version {}".format( SOFTWARE_VERSION_NUMBER )
            version_area = label.Label( terminalio.FONT, text=text, color=0xFFFFFF )
            version_group.append( version_area )
            self.group.append( version_group )

            message_group = displayio.Group( scale=2, x=4, y=220 )
            text = "message here"
            self.message_area = label.Label( terminalio.FONT, text=text, color=0xFFFFFF )
            message_group.append( self.message_area )
            self.group.append( message_group )

        return self.group
    def announce( self, text ):
        self.message_area.text = text
        print( text )
    def update_values( self ):
        pass

def make_welcome_page( instrument ):
    welcome_page = Welcome_Page()
    group = welcome_page.make_group()
    welcome_page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( welcome_page )
    return welcome_page

def hide_all_pages( pages_list ):
    for page in pages_list:
        page.hide()


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

def initialize_sd_card( spi_bus, sd_cs_pin ):
    try:
        sdcard = sdcardio.SDCard( spi_bus, sd_cs_pin )
        vfs = storage.VfsFat(sdcard)
        storage.mount(vfs, "/sd")
        print( "SD card initialized" )
    except Exception as err:
        print("SD card fail: missing or full: {}".format(err))
        print( "*** The card may be missing, or you may need to create a folder named sd in the root directory of CIRCUITPY ***" )
        vfs = False
    return vfs

def get_uid():
    try:
        UID = int.from_bytes(microcontroller.cpu.uid, "big") % 100000
        print("unique identifier (UID) : {0}".format( UID ))
    except:
        UID = False
        print("unique identifier (UID) not available")
    return UID

def initialize_uart( txpin, rxpin ):
    try:
        uart = busio.UART(txpin, rxpin, baudrate=9600, timeout=10)
        print( "uart bus initialized" )
    except:
        uart = False
    return uart

def initialize_neopixel( pin ):
    try:
        num_pixels = 1
        ORDER = neopixel.RGB
        neopixel_instance = neopixel.NeoPixel( pin, num_pixels, brightness=0.3, auto_write=True, pixel_order=ORDER )
        print( "neopixel initialized" )
    except:
        neopixel_instance = False
        print( "neopixel failed to initialize" )
    return neopixel_instance

def initialize_led( pin ):
    LED = digitalio.DigitalInOut( pin )
    LED.direction = digitalio.Direction.OUTPUT
    count = 4
    interval = 0.1
    LED.value = True
    time.sleep(interval)
    LED.value = False
    return LED

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
