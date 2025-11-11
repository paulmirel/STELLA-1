SOFTWARE_VERSION_NUMBER = "0.1"
DEVICE_TYPE = "as7331_spectral_sensor"
# Copyright NASA 2025
# Author Paul Mirel

import time
import iorodeo_as7331 as as7331

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

class as7331_Spectrometer( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "as7331_spectrometer", pn = "as7331", address = 0x74, swob = as7331.AS7331( com_bus ))
        self.choice_label = "as7331 UV"
        self.wavelength_bands_nm = 360, 300, 260
        self.bandwidths_nm = 80, 40, 40
        self.chip_number = 1, 1, 1
        self.dict_chip_number= {key:value for key, value in zip(self.wavelength_bands_nm, self.chip_number )}
        self.dict_bandwidths = {key:value for key, value in zip(self.wavelength_bands_nm, self.bandwidths_nm )}
        #https://look.ams-osram.com/m/1856fd2c69c35605/original/AS7331-Spectral-UVA-B-C-Sensor.pdf
        self.afov_deg = (10 * 2)
        self.default_gain_index = 5
        self.gain_list = [ 1,2,4,8,16,32,64,128,256,512,1024,2048 ]
        self.integration_time_ms_list = [ 1,2,4,8,16,32,64,128,256,512,1024,2048,4196,8192,16384 ]
        self.integration_time_number_of_choices = len(self.integration_time_ms_list)
        self.default_integration_time_index = 8
        if self.swob:
            self.set_gain( self.default_gain_index )
            self.set_integration_time( self.default_integration_time_index )
   
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
