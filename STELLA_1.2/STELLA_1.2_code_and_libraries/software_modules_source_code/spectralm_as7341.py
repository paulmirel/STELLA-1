SOFTWARE_VERSION_NUMBER = "1.0"
DEVICE_TYPE = "as7341_spectral_sensor"
# Copyright NASA 2025
# Author Paul Mirel

from adafruit_as7341 import AS7341
from adafruit_as7341 import Gain as AS7341_Gain
from .classm_device import Device


def initialize_as7341_spectrometer( instrument ):
    as7341_spectrometer = Null_as7341_Spectrometer()
    try:
        as7341_spectrometer = as7341_Spectrometer( instrument )
        instrument.welcome_page.announce( "initialize_as7341_spectrometer" )
        instrument.spectral_sensors_present.append( as7341_spectrometer )
    except Exception as err:
        print( "as7341_spectrometer", err )
        pass
    return as7341_spectrometer


def initialize_spectral_channel( name, sensor_unit, index ):
    #try:
    spectral_channel = Spectral_Channel( name, sensor_unit, index)
    sensor_unit.instrument.welcome_page.announce( "initialize_spectral_channel {}".format( name ) )
    sensor_unit.instrument.sensors_present.append( spectral_channel )
    return spectral_channel


class Spectral_Channel( Device ):
    def __init__( self, name, sensor_unit, index ):
        #super().__init__(name=name, sensor_group=sensor_group )
        super().__init__(name = name, pn = "as7341", address = 0x39, swob = sensor_unit )
        self.sensor_unit = sensor_unit
        self.index = index
        self.parameters = [ "wavelength_nm", "gain", "int_time_ms", "raw_counts", "normal_ct_per_s", "bandwidth_nm"]
        self.wavelength_nm = sensor_unit.wavelength_bands_nm[self.index]
        self.bandwidth_nm = sensor_unit.bandwidths_nm[self.index]
        self.values = [ self.wavelength_nm,
                        sensor_unit.gain_list[sensor_unit.gain_index],
                        sensor_unit.integration_time_ms_list[sensor_unit.integration_time_index],
                        0,
                        0,
                        self.bandwidth_nm]


    def read(self):
        raw = self.sensor_unit.read_counts_by_index( self.index )
        gain = self.sensor_unit.gain_list[self.sensor_unit.gain_index]
        int_time_ms = self.sensor_unit.integration_time_ms_list[self.sensor_unit.integration_time_index]
        normal_ct_per_s = round(1000*raw/(gain*int_time_ms),1)
        self.values = [self.wavelength_nm,
                        gain,
                        int_time_ms,
                        raw,
                        normal_ct_per_s,
                        self.bandwidth_nm]

    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log

    def printlog(self):
        print( self.log())

class as7341_Spectrometer( Device ):
    def __init__( self, instrument ):
        super().__init__(name = "as7341_spectrometer", pn = "as7341", address = 0x39, swob = AS7341( instrument.i2c_bus ))
        self.instrument = instrument
        self.choice_label = "as7341 VIS"
        self.wavelength_bands_nm = 415, 445, 480, 515, 555, 590, 630, 682
        self.bandwidths_nm = 26, 30, 36, 39, 39, 40, 50, 52
        self.chip_number = 1, 1, 1, 1, 1, 1, 1, 1
        self.dict_chip_number = {key:value for key, value in zip(self.wavelength_bands_nm, self.chip_number )}
        self.dict_bandwidths = {key:value for key, value in zip(self.wavelength_bands_nm, self.bandwidths_nm )}
        self.colors = ["violet", "indigo", "blue", "cyan", "green", "yellow", "orange", "red"]
        #self.tsis_cal_counts_per_irradiance = 1405.9, 2079.6, 2631.6, 3556.8, 4246.0, 5060.6, 6888.9, 9130.9
        # first principles calibration by Sten Odenwald of NASA Heliophysics
        # TBD print( "as7341 Sten O cal counts per irradiance at what gain?  TBD " )
        self.steno_cal_counts_per_irradiance = 4398.0, 6104.0, 7583.0, 9972.0, 11536.0, 13374.0, 17115.0, 20916.0
        self.calibration_error = 0.6
        self.irradiance = [0,0,0,0,0,0,0,0]
        self.dict_stenocal = {}
        self.swob.led_current = 50
        self.gain_list = [ 0.5, 1, 2, 4, 8, 16, 32, 64, 128, 256 ]
        self.gain_index = 5
        self.integration_time_ms_list = [1,10,20,30,40,50,60,70,80,90,100,110,120,130,140,150,160,170,180]
        self.integration_time_number_of_choices = len(self.integration_time_ms_list)
        self.integration_time_index = 8
        self.lamp_selection_list = ["Vis mA"]
        self.current_index = 0
        self.lamp_current_mA_list = [0,2,4,6,8,10,12,14,16,18,20,30,40,50,60,70,80,90,100 ]
        self.data_counts = [0,0,0,0,0,0,0,0]
        if self.swob:
            self.set_gain( self.gain_index )
            self.set_integration_time( self.integration_time_index )

    def make_spectral_channels( self ):
        index = 0
        for item in self.wavelength_bands_nm:
            name = "{}nm_channel".format(item)
            spectral_channel = initialize_spectral_channel( name, self, index )
            index += 1


    def read_counts_by_index( self, index ):
        try:
            if index == 0: counts = self.swob.channel_415nm
            if index == 1: counts = self.swob.channel_445nm
            if index == 2: counts = self.swob.channel_480nm
            if index == 3: counts = self.swob.channel_515nm
            if index == 4: counts = self.swob.channel_555nm
            if index == 5: counts = self.swob.channel_590nm
            if index == 6: counts = self.swob.channel_630nm
            if index == 7: counts = self.swob.channel_680nm
            self.data_counts[index] = counts
            return counts
        except Exception as err:
            print( "read channel counts failed: ", err )
            return False

    def read_counts_all(self):
        self.raw = self.swob.all_channels
        self.data_counts = []
        for item in self.raw:
            self.data_counts.append(item)

    def get_max_min_counts( self ):
        self.max_counts = max(self.data_counts)
        self.min_counts = min(self.data_counts)
        return self.max_counts, self.min_counts

    def set_gain(self, index):
        # library sets gain to 128
        gain_constant_list = [ AS7341_Gain.GAIN_0_5X, AS7341_Gain.GAIN_1X, AS7341_Gain.GAIN_2X, AS7341_Gain.GAIN_4X, AS7341_Gain.GAIN_8X, AS7341_Gain.GAIN_16X, AS7341_Gain.GAIN_32X, AS7341_Gain.GAIN_64X, AS7341_Gain.GAIN_128X, AS7341_Gain.GAIN_256X, AS7341_Gain.GAIN_512X ]
        try:
            self.swob._gain = gain_constant_list[ index ]
            return self.gain_list[ self.swob._gain ]
        except Exception as err:
            print( "failed to set gain: ", err )
            return False

    def set_integration_time( self, index ):
        #library sets atime = 100, astep = 999, which is an unusable combination, ADC saturated at 101000.
        # (astep, atime)
        integration_time_settings_list = [ (127,2),(127,27),(127,54),(127,82),(127,111),(127,140),(127,167),(127,196),(127,225),(127,252),(255,140),(255,154),(255,168),(255,182),(255,196),(255,210),(255,224),(255,238),(255,252) ]
        try:
            self.swob.astep = integration_time_settings_list[index][0]
            self.swob.atime = integration_time_settings_list[index][1]
            return self.integration_time_ms_list[ index ]
        except Exception as err:
            print( "as7341 set integration time failed: ", err )
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

    '''
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
'''

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
