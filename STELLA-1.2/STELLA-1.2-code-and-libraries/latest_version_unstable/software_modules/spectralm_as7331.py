SOFTWARE_VERSION_NUMBER = "0.1"
DEVICE_TYPE = "as7331_spectral_sensor"
# Copyright NASA 2025
# Author Paul Mirel

import time
import iorodeo_as7331 as as7331
from .classm_device import Device

def initialize_as7331_spectrometer( instrument ):
    as7331_spectrometer = Null_as7331_Spectrometer()
    try:
        as7331_spectrometer = as7331_Spectrometer( instrument )
        instrument.welcome_page.announce( "initialize_as7331_spectrometer" )
        instrument.spectral_sensors_present.append( as7331_spectrometer )
    except ValueError as err:
        #print( "uv spectrometer failed to initialize: {}".format(err))
        pass
    except Exception as err:
        print( "as7331_spectrometer", err )
        pass
    return as7331_spectrometer

def initialize_spectral_channel( name, sensor_unit, index ):
    #try:
    spectral_channel = Spectral_Channel( name, sensor_unit, index)
    sensor_unit.instrument.welcome_page.announce( "initialize_spectral_channel {}".format( name ) )
    sensor_unit.instrument.sensors_present.append( spectral_channel )
    return spectral_channel

class Spectral_Channel( Device ):
    def __init__( self, name, sensor_unit, index ):
        #super().__init__(name=name, sensor_group=sensor_group )
        super().__init__(name = name, pn = "as7331", address = 0x74, swob = sensor_unit )
        self.sensor_unit = sensor_unit
        self.index = index
        self.parameters = [ "wavelength_nm", "gain", "int_time_ms", "raw_counts", "normal_ct_per_s", "conv_value", "bandwidth_nm",
                            "chip_temp_C"]
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
        return (self.values[3],self.values[4],0,self.values[6])
        
    def read(self):
        raw_values = self.sensor_unit.read_counts_all()
        if raw_values is not None:
            raw = raw_values[ self.index ]
        else:
            raw = 0
        gain = self.sensor_unit.gain_list[self.sensor_unit.gain_index]
        int_time_ms = self.sensor_unit.integration_time_ms_list[self.sensor_unit.integration_time_index]
        normal_ct_per_s = round(1000*raw/(gain*int_time_ms),1)
        converted_values  = self.sensor_unit.read_converted_all()
        if converted_values is not None:
            conv_value = converted_values[ self.index ]
            chip_temp = converted_values[ 3 ]
        else:
            conv_value = 0
            chip_temp = 0
        self.values = [self.wavelength_nm,
                        gain,
                        int_time_ms,
                        raw,
                        normal_ct_per_s,
                        conv_value,
                        self.bandwidth_nm,
                        chip_temp]

    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log

    def printlog(self):
        print( self.log())

class as7331_Spectrometer( Device ):
    def __init__( self, instrument ):
        super().__init__(name = "as7331_spectrometer", pn = "as7331", address = 0x74, swob = as7331.AS7331( instrument.i2c_bus ))
        self.instrument = instrument
        self.choice_label = "as7331 UV"
        self.wavelength_bands_nm = 260, 300, 360
        self.number_of_channels = len( self.wavelength_bands_nm )
        self.bandwidths_nm = 40, 40, 80
        self.chip_number = 1, 1, 1
        self.data_counts = []
        for index in range( 0, self.number_of_channels): self.data_counts.append(0)
        self.max_counts = 0
        self.min_counts = 0
        #https://look.ams-osram.com/m/1856fd2c69c35605/original/AS7331-Spectral-UVA-B-C-Sensor.pdf
        self.afov_deg = (10 * 2)
        self.gain_index = 5
        self.gain_list = [ 1,2,4,8,16,32,64,128,256,512,1024,2048 ]
        self.integration_time_ms_list = [ 1,2,4,8,16,32,64,128,256,512,1024,2048,4196,8192,16384 ]
        self.integration_time_number_of_choices = len(self.integration_time_ms_list)
        self.integration_time_index = 8
        self.lamp_selection_list = None
        self.lamp_current_mA_list = None
        if self.swob:
            self.set_gain( self.gain_index )
            self.set_integration_time( self.integration_time_index )

    def make_spectral_channels( self ):
        index = 0
        for item in self.wavelength_bands_nm:
            name = "{}nm_channel".format(item)
            spectral_channel = initialize_spectral_channel( name, self, index )
            index += 1

    def set_gain(self, index ):
        gain_constant_list = [ as7331.GAIN_1X, as7331.GAIN_2X, as7331.GAIN_4X, as7331.GAIN_8X, as7331.GAIN_16X, as7331.GAIN_32X, as7331.GAIN_64X, as7331.GAIN_128X, as7331.GAIN_256X, as7331.GAIN_512X, as7331.GAIN_1024X, as7331.GAIN_2048X ]
        try:
            self.swob.gain = gain_constant_list[ index ]
            return self.gain_list[ index ]
        except Exception as err:
            print( "failed to set gain: ", err )
            return False

    def set_integration_time( self, index ):
        integration_time_constant_list = [ as7331.INTEGRATION_TIME_1MS, as7331.INTEGRATION_TIME_2MS, as7331.INTEGRATION_TIME_4MS, as7331.INTEGRATION_TIME_8MS, as7331.INTEGRATION_TIME_16MS, as7331.INTEGRATION_TIME_32MS, as7331.INTEGRATION_TIME_64MS, as7331.INTEGRATION_TIME_128MS, as7331.INTEGRATION_TIME_256MS, as7331.INTEGRATION_TIME_512MS, as7331.INTEGRATION_TIME_1024MS, as7331.INTEGRATION_TIME_2048MS, as7331.INTEGRATION_TIME_4096MS, as7331.INTEGRATION_TIME_8192MS, as7331.INTEGRATION_TIME_16384MS ]
        try:
            self.integration_time = integration_time_constant_list[ index ]
            return self.integration_time_ms_list[ index ]
        except Exception as err:
            print( "as7331 set integration time failed: ", err )
            return False

    def read_counts_all( self ):
        self.UVA_counts, self.UVB_counts, self.UVC_counts, self.chip_temp_c_counts = self.swob.raw_values
        self.data_counts = [self.UVC_counts,self.UVB_counts,self.UVA_counts]
        return self.data_counts

    def read_converted_all(self):
        self.UVA_conv, self.UVB_conv, self.UVC_conv, self.chip_temp_c_conv = self.swob.values
        self.data_conv = [round(self.UVC_conv,3),round(self.UVB_conv,3),round(self.UVA_conv,3), int(round(self.chip_temp_c_conv,0))]
        return self.data_conv

    def report_counts_all( self ):
        return self.data_counts

    def get_max_min_counts( self ):
        self.max_counts = max(self.data_counts)
        self.min_counts = min(self.data_counts)
        return self.max_counts, self.min_counts
    '''
    def read_chip_temperatures(self):
        pass

    def lamps_on(self):
        pass
    def lamps_off(self):
        pass
    def read(self):
        self.UVA_counts, self.UVB_counts, self.UVC_counts, self.chip_temp_c_counts = self.swob.raw_values
        self.dict_counts = {360:self.UVA_counts, 300:self.UVB_counts, 260:self.UVC_counts}
        self.UVA, self.UVB, self.UVC, self.chip_temp_c = self.swob.values
        self.dict_fcal = {360:self.UVA, 300:self.UVB, 260:self.UVC}
        self.data_counts = [ self.UVC_counts, self.UVB_counts, self.UVA_counts]
    def read_counts(self):
        self.UVA_counts, self.UVB_counts, self.UVC_counts, self.chip_temp_c_counts = self.swob.raw_values
        self.dict_counts = {360:self.UVA_counts, 300:self.UVB_counts, 260:self.UVC_counts}
        self.data_counts = [ self.UVC_counts, self.UVB_counts, self.UVA_counts]
    def read_fcal(self):
        self.UVA, self.UVB, self.UVC, self.chip_temp_c = self.swob.values
        self.dict_fcal = {360:self.UVA, 300:self.UVB, 260:self.UVC}

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
    '''

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
