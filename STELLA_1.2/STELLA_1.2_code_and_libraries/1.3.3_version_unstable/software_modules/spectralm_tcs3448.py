SOFTWARE_VERSION_NUMBER = "1.0"
DEVICE_TYPE = "tcs3448_spectral_sensor"
# Copyright NASA 2026 under MIT license
# Author Paul Mirel

from adafruit_tcs3448 import TCS3448
from .classm_device import Device
import time


def initialize_tcs3448_spectrometer( instrument, alt_bus = None ):
    tcs3448_spectrometer = False
    try:
        tcs3448_spectrometer = tcs3448_Spectrometer( instrument, alt_bus )
        instrument.welcome_page.announce( "initialize_tcs3448_spectrometer" )
        instrument.spectral_sensors_present.append( tcs3448_spectrometer )
    except Exception as err:
        #print( "tcs3448_spectrometer_offline", err)
        pass
    return tcs3448_spectrometer


def initialize_spectral_channel( name, sensor_unit, index ):
    #try:
    spectral_channel = Spectral_Channel( name, sensor_unit, index)
    sensor_unit.instrument.welcome_page.announce( "initialize_spectral_channel {}".format( name ) )
    sensor_unit.instrument.sensors_present.append( spectral_channel )
    return spectral_channel


class Spectral_Channel( Device ):
    def __init__( self, name, sensor_unit, index ):
        #super().__init__(name=name, sensor_group=sensor_group )
        super().__init__(name = name, pn = "tcs3448", address = 0x59, swob = sensor_unit )
        self.sensor_unit = sensor_unit
        self.index = index
        self.parameters = [ "wavelength_nm", "gain", "int_time_ms", "counts", "ct_per_s_nm", "irradiance", "bandwidth_nm", "chip_temp_C"]
        self.wavelength_nm = sensor_unit.wavelength_bands_nm[self.index]
        self.bandwidth_nm = sensor_unit.bandwidths_nm[self.index]
        self.values = [ self.wavelength_nm,
                        sensor_unit.gain_list[sensor_unit.gain_index],
                        sensor_unit.integration_time_ms_list[sensor_unit.integration_time_index],
                        0,
                        0,
                        0,
                        self.bandwidth_nm,
                        0]

    def get_wavelength( self ):
        return self.wavelength_nm
    def get_plot_values( self ):
        return (self.values[3],self.values[4],self.values[5],self.values[6])


    def read(self):
        #print(len(self.sensor_unit.data_counts), self.index)
        raw = self.sensor_unit.data_counts[self.index]
        gain = self.sensor_unit.gain_list[self.sensor_unit.gain_index]
        int_time_ms = self.sensor_unit.integration_time_ms_list[self.sensor_unit.integration_time_index]
        bandwidth_nm = self.bandwidth_nm
        normal_ct_per_s_nm = round(1000*raw/(gain*int_time_ms*bandwidth_nm),3)
        irradiance = 0
        chip_temp_C = 0
        self.values = [self.wavelength_nm,
                        gain,
                        int_time_ms,
                        raw,
                        normal_ct_per_s_nm,
                        irradiance,
                        bandwidth_nm,
                        chip_temp_C]
        #print(self.values)

    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log

    def printlog(self):
        print( self.log())

class tcs3448_Spectrometer( Device ):
    def __init__( self, instrument, alt_bus = None ):
        if alt_bus is None:
            super().__init__(name = "tcs3448_spectrometer", pn = "tcs3448", address = 0x39, swob = TCS3448( instrument.i2c_bus ))
        else:
            super().__init__(name = "tcs3448_spectrometer", pn = "tcs3448", address = 0x39, swob = TCS3448( alt_bus ))
        self.instrument = instrument
        self.choice_label = "tcs3448 VIS"
        self.wavelength_bands_nm = 407, 424, 450, 473, 516, 560, 546, 596, 636, 687, 748, 855
        self.band_designations = "F1", "F2", "FZ", "F3", "F4", "FY", "F5","FXL", "F6", "F7", "F8", "NIR"
        self.bandwidths_nm = 28, 29, 67, 38, 48, 123, 44, 93, 58, 63, 77, 61
        self.chip_number = 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1
        self.dict_chip_number = {key:value for key, value in zip(self.wavelength_bands_nm, self.chip_number )}
        self.dict_bandwidths = {key:value for key, value in zip(self.wavelength_bands_nm, self.bandwidths_nm )}


        self.swob.led_current = 50
        self.irradiance = [0,0,0,0,0,0,0,0,0,0,0,0,0]
        self.gain_list = [ 0.5, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048 ]
        self.gain_index = 5
        self.integration_time_ms_list = [1,10,20,30,40,50,60,70,80,90,100,110,120,130,140,150,160,170,180,200,250,300,350,400,450,500,550,600,650,700,750,800,850,900,950,1000]
        self.integration_time_number_of_choices = len(self.integration_time_ms_list)
        self.integration_time_index = 8
        self.lamp_selection_list = ["Vis mA"]
        self.current_index = 6
        self.lamp_current_mA_list = [0,2,4,6,8,10,12,14,16,18,20,30,40,50,60,70,80,90,100 ]
        self.data_counts = [0,0,0,0,0,0,0,0,0,0,0,0,0]
        if self.swob:
            self.set_gain( self.gain_index )
            self.set_integration_time( self.integration_time_index )

    def make_spectral_channels( self ):
        index = 0
        for item in self.wavelength_bands_nm:
            name = "{}nm_channel".format(item)
            spectral_channel = initialize_spectral_channel( name, self, index )
            index += 1

    def read(self):
        try:
            self.raw = self.swob.all_channels
            #print(self.raw)
            self.data_counts = []
            for index in range(0,len(self.raw)):
                self.data_counts.append(self.raw[index])

        except Exception as err:
            print(err)


    def get_max_min_counts( self ):
        self.max_counts = max(self.data_counts)
        self.min_counts = min(self.data_counts)
        return self.max_counts, self.min_counts

    def set_gain(self, index):
        try:
            self.swob.gain = index
            return self.gain_list[ self.swob.gain ]
        except Exception as err:
            print( "failed to set gain: ", err )
            return False

    def set_integration_time( self, index ):
        #library sets atime = 100, astep = 999, which is an unusable combination, ADC saturated at 101000.
        # (astep, atime)
        integration_time_settings_list = [ (127,2),(127,27),(127,54),(127,82),(127,111),(127,140),
                                            (127,167),(127,196),(127,225),(127,252),(255,140),(255,154),
                                            (255,168),(255,182),(255,196),(255,210),(255,224),(255,238),(255,252),
                                            (300,239),(376,239),(450,239),(525,239),(600,239),(675,239),(750,239),
                                            (825,239),(900,239),(975,239),(1050,239),(1125,239),(1200,239),(1275,239),
                                            (1350,239),(1425,239),(1500,239)]
        try:
            self.swob.astep = integration_time_settings_list[index][0]
            self.swob.atime = integration_time_settings_list[index][1]
            return self.integration_time_ms_list[ index ]
        except Exception as err:
            print( "tcs3448 set integration time failed: ", err )
            return False

    def lamp_on(self):
        self.swob.led_enabled = True
    def lamp_off(self):
        self.swob.led_enabled = False
    def blink( self, duration ):
        self.swob.led_current = 50
        self.swob.led = True
        time.sleep( duration )
        self.swob.led = False

    def set_lamp_current_mA( self, current_index, lamp_index=None ):
        try:
            if current_index == 0:
                self.lamp_off()
                return 0
            else:
                self.lamp_on()
                current_mA = self.lamp_current_mA_list[current_index]
                self.swob.led_current = current_mA
                return current_mA
        except Exception as err:
            print( "failed to set current:", err )
            return False

