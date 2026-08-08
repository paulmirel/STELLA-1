SOFTWARE_VERSION_NUMBER = "1.0"
DEVICE_TYPE = "as7343_spectral_sensor"
# Copyright NASA 2026
# Author Paul Mirel

from adafruit_as7343_modified import AS7343
from adafruit_as7343_modified import Gain as AS7343_Gain
from .classm_device import Device


def initialize_as7343_spectrometer( instrument ):
    as7343_spectrometer = False
    try:
        as7343_spectrometer = as7343_Spectrometer( instrument )
        instrument.welcome_page.announce( "initialize_as7343_spectrometer" )
        instrument.spectral_sensors_present.append( as7343_spectrometer )
    except Exception as err:
        print( "as7343_spectrometer", err )
        pass
    return as7343_spectrometer


def initialize_spectral_channel( name, sensor_unit, index ):
    #try:
    spectral_channel = Spectral_Channel( name, sensor_unit, index)
    sensor_unit.instrument.welcome_page.announce( "initialize_spectral_channel {}".format( name ) )
    sensor_unit.instrument.sensors_present.append( spectral_channel )
    return spectral_channel


class Spectral_Channel( Device ):
    def __init__( self, name, sensor_unit, index ):
        #super().__init__(name=name, sensor_group=sensor_group )
        super().__init__(name = name, pn = "as7343", address = 0x39, swob = sensor_unit )
        self.sensor_unit = sensor_unit
        self.index = index
        self.parameters = [ "wavelength_nm", "gain", "int_time_ms", "raw_counts", "ct_per_s_nm", "bandwidth_nm", "chip_temp_C"]
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
        raw = self.sensor_unit.data_counts[ self.index ]
        gain = self.sensor_unit.gain_list[self.sensor_unit.gain_index]
        int_time_ms = self.sensor_unit.integration_time_ms_list[self.sensor_unit.integration_time_index]
        bandwidth_nm = self.bandwidth_nm
        normal_ct_per_s_nm = round(1000*raw/(gain*int_time_ms*bandwidth_nm),3)
        chip_temp_C = 0
        self.values = [self.wavelength_nm,
                        gain,
                        int_time_ms,
                        raw,
                        normal_ct_per_s_nm,
                        bandwidth_nm,
                        chip_temp_C]

    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log

    def printlog(self):
        print( self.log())

class as7343_Spectrometer( Device ):
    def __init__( self, instrument ):
        super().__init__(name = "as7343_spectrometer", pn = "as7343", address = 0x39, swob = AS7343( instrument.i2c_bus ))
        self.instrument = instrument
        self.choice_label = "as7343 VNIR"
        self.parameters = [ "all ch" ]
        self.values = [ "" ]
        self.readout_order =        12,  6,  0,  7,  8,  1, 15,  2,  9, 13, 14,  3
        self.wavelength_bands_nm = 405,425,450,475,515,555,550,600,640,690,745,855
        self.bandwidths_nm =        30, 22, 55, 30, 40,100, 35, 80, 50, 55, 60, 54
        self.chip_number =           1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1
        self.dict_chip_number = {key:value for key, value in zip(self.wavelength_bands_nm, self.chip_number )}
        self.dict_bandwidths = {key:value for key, value in zip(self.wavelength_bands_nm, self.bandwidths_nm )}
        #self.colors = ["violet", "indigo", "blue", "cyan", "green", "yellow", "orange", "red"]
        self.swob.led_current = 50
        self.gain_list = [ 0.5, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048 ]
        self.gain_index = 5
        self.integration_time_ms_list = [1,10,20,30,40,50,60,70,80,90,100,110,120,130,140,150,160,170,180,200,250,300,350,400,450,500,550,600,650,700,750,800,850,900,950,1000]
        self.integration_time_number_of_choices = len(self.integration_time_ms_list)
        self.integration_time_index = 8
        self.lamp_selection_list = ["VNIR mA"]
        self.current_index = 0
        self.lamp_current_mA_list = [0,2,4,6,8,10,12,14,16,18,20,30,40,50,60,70,80,90,100 ]
        self.data_counts = [0,0,0,0,0,0,0,0,0,0,0,0]
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
        self.raw = self.swob.all_channels
        self.data_counts = []
        for index in range(0, len(self.wavelength_bands_nm)):
            self.data_counts.append(self.raw[self.readout_order[index]])
        #print(self.raw)
        #print(self.data_counts)


    def get_max_min_counts( self ):
        self.max_counts = max(self.data_counts)
        self.min_counts = min(self.data_counts)
        return self.max_counts, self.min_counts

    def set_gain(self, index):
        # library sets gain to 128
        gain_constant_list = [AS7343_Gain.X0_5,AS7343_Gain.X1,AS7343_Gain.X2,AS7343_Gain.X4,AS7343_Gain.X8,AS7343_Gain.X16,AS7343_Gain.X32,AS7343_Gain.X64,AS7343_Gain.X128,AS7343_Gain.X256,AS7343_Gain.X512,AS7343_Gain.X1024,AS7343_Gain.X2048]
        try:
            self.swob._gain = gain_constant_list[ index ]
            return self.gain_list[ self.swob._gain ]
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
            print( "as7343 set integration time failed: ", err )
            return False

    def lamp_on(self):
        self.swob.led = True
    def lamp_off(self):
        self.swob.led = False
    def blink( self, duration ):
        self.swob.led_current = 50
        self.swob.led = True
        time.sleep( duration )
        self.swob.led = False

    def set_lamp_current_mA( self, current_index, lamp_index ):
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

