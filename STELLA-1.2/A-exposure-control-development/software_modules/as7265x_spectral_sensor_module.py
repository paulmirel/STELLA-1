SOFTWARE_VERSION_NUMBER = "0.1"
DEVICE_TYPE = "as7265x_spectral_sensor"
# Copyright NASA 2025
# Author Paul Mirel

import time
import qwiic_as7265x


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

class as7265x_Spectrometer( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "as7265x_spectrometer", pn = "as7256x", address = 0x49, swob = qwiic_as7265x.QwiicAS7265x(  ))
        self.choice_label = "as7256x V+NIR"
        #self.wavelength_bands_nm = 610, 680, 730, 760, 810, 860, 560, 585, 645, 705, 900, 940, 410, 435, 460, 485, 510, 535
        self.wavelength_bands_nm = 410, 435, 460, 485, 510, 535, 560, 585, 610, 645, 680, 705, 730, 760, 810, 860, 900, 940
        self.number_of_channels = len( self.wavelength_bands_nm )
        self.band_designations_in_wavelength_order = "A","B","C","D","E","F","G","H","R","I","S","J","T","U","V","W","K","L"
        self.data_counts = []
        for index in range( 0, self.number_of_channels): self.data_counts.append(0)
        self.max_counts = 0
        self.min_counts = 0
        self.chip_number_in_wavelength_order = 3,3,3,3,3,3,2,2,1,2,1,2,2,2,2,1,1
        #self.band_designations_in_read_all_order = ("R", "S", "T", "U", "V", "W", "G", "H", "I", "J", "K", "L", "A", "B", "C", "D", "E", "F" )
        self.bandwidths_nm = 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20
        
        #self.dict_chip_number = {key:value for key, value in zip(self.wavelength_bands_nm, self.chip_number )}
        #self.dict_bandwidths = {key:value for key, value in zip(self.wavelength_bands_nm, self.bandwidths_nm )}
        #self.bands_sorted = sorted( self.wavelength_bands_nm )
        self.uncertainty_percent = 12
        self.afov_deg = (20.5 * 2) #datasheet reports half angle.
        # settings
        self.gain_list = [ 1, 3.7, 16, 64 ]
        self.gain_index = 2
        self.integration_time_ms_step = 2.78
        self.integration_time_index_maximum = 255
        self.integration_time_ms_maximum = self.integration_time_ms_step * self.integration_time_index_maximum
        self.integration_time_number_of_choices = 16
        self.integration_time_index_per_choice = self.integration_time_index_maximum/ self.integration_time_number_of_choices
        self.integration_time_ms_list = []
        self.integration_time_index = 8
        self.integration_time_ms_list.append( self.integration_time_ms_step )
        for index in range( 1, self.integration_time_number_of_choices + 1 ):
            integration_time_ms = ((index) * self.integration_time_index_per_choice * self.integration_time_ms_step)
            if integration_time_ms < 100:
                integration_time_ms = round(integration_time_ms, 1)
            else:
                integration_time_ms = int( integration_time_ms)
            self.integration_time_ms_list.append( integration_time_ms )
        
        #self.lamp_current_mA_index = 0
        self.lamp_device_constant_list = [ self.swob.kLedUv, self.swob.kLedWhite, self.swob.kLedIr ]
        self.lamp_selection_list = [ "UV mA", "Vis mA", "NIR mA" ]
        self.lamp_current_mA_list = []
        self.lamp_current_mA_list.append([ 0, 12.5 ])
        self.lamp_current_mA_list.append([ 0, 12.5, 25, 50, 100 ])
        self.lamp_current_mA_list.append([ 0, 12.5, 25, 50 ])
        self.lamp_current_constant_list = [  self.swob.kLedCurrentLimit12_5mA, self.swob.kLedCurrentLimit25mA, self.swob.kLedCurrentLimit50mA, self.swob.kLedCurrentLimit100mA ]
        if self.swob:
            self.swob.begin()
            self.swob.disable_indicator()
            self.swob.set_measurement_mode(self.swob.kMeasurementMode6ChanContinuous)
            self.set_gain( self.gain_index )
            self.set_integration_time( self.integration_time_index )
        
            
    def set_gain(self, new_gain_index):
        self.gain_index = new_gain_index
        gain_constant_list = [ self.swob.kGain1x, self.swob.kGain37x, self.swob.kGain16x, self.swob.kGain64x ]
        try:
            self.swob.set_gain( gain_constant_list[ self.gain_index ])
            return self.gain_index, self.gain_list[ self.gain_index ]
        except Exception as err:
            print( "failed to set gain: ", err )
            return False
        
    def set_integration_time( self, index ):
        # must wait for at least 5 seconds before sending integration time again. If not, signal goes to 0.
        integration_time_ms = self.integration_time_ms_list[ index ]
        integration_index = integration_time_ms / self.integration_time_ms_step
        integration_index = int( integration_index)
        try:
            self.swob.set_integration_cycles(integration_index)
            return integration_time_ms
        except Exception as err:
            print( "as7265x set integration time failed: ", err )
    
    def acquire_measurement( self ):
        self.swob.take_measurements()
            
    def read_counts_by_wavelength( self, wavelength ):
        index = self.wavelength_bands_nm.index(wavelength)
        return self.read_counts_by_index( index )

    
    def read_counts_by_index( self, index ):
        try:
            if index == 0: counts = self.swob.get_a()
            if index == 1: counts = self.swob.get_b()
            if index == 2: counts = self.swob.get_c()
            if index == 3: counts = self.swob.get_d()
            if index == 4: counts = self.swob.get_e()
            if index == 5: counts = self.swob.get_f()
            if index == 6: counts = self.swob.get_g()
            if index == 7: counts = self.swob.get_h()
            if index == 8: counts = self.swob.get_r()
            if index == 9: counts = self.swob.get_i()
            if index == 10: counts = self.swob.get_s()
            if index == 11: counts = self.swob.get_j()
            if index == 12: counts = self.swob.get_t()
            if index == 13: counts = self.swob.get_u()
            if index == 14: counts = self.swob.get_v()
            if index == 15: counts = self.swob.get_w()
            if index == 16: counts = self.swob.get_k()
            if index == 17: counts = self.swob.get_l()
            self.data_counts[index] = counts
            return counts
        except Exception as err:
            print( "read channel counts failed: ", err )
            return False
            
    def read_counts_all( self ):
        for index in range( 0, self.number_of_channels):
            self.read_counts_by_index( index )
    
    def report_counts_by_index( self, index ):
        wavelength = self.wavelength_bands_nm[ index ]
        counts = self.data_counts[index]
        return wavelength, counts
    
    def report_counts_all( self ):
        return self.data_counts
    
    def get_max_min_counts( self ):
        self.max_counts = max(self.data_counts)
        self.min_counts = min(self.data_counts)
        return self.max_counts, self.min_counts
        
        
    def read_chip_temperatures( self ):
        self.chip_temperatures_c_dict = { 1:self.swob.get_temperature(1), 2:self.swob.get_temperature(2), 3:self.swob.get_temperature(3) }
        

    
    def read_irradiances_all_channels( self ):
        self.data_fcal_irradiances = self.swob.get_value(1) # 1 index returns factory calibrated irradiance values, bands in unsorted order
        self.dict_fcal_irradiances = {key:value for key, value in zip(self.wavelength_bands_nm, self.data_fcal_irradiances)}


    def list_wavelength_bands_nm( self ):
        return self.bands_sorted
    def header( self ):
        return "WL.nm, irrad.uW/(cm^2), irrad.uncty.uW/(cm^2), counts, chip_num, chip_temp_C"
    def get_bandwidth(self, wavelength):
        return self.dict_bandwidths[wavelength]
    '''
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
    '''
    def all_lamps_on(self):
        #print( "turn on the lamps")
        self.swob.enable_bulb(0)   # white
        self.swob.enable_bulb(1)   # NIR
        self.swob.enable_bulb(2)   # UV
    def all_lamps_off(self):
        #print( "turn off the lamps")
        self.swob.disable_bulb(0)   # white
        self.swob.disable_bulb(1)   # NIR
        self.swob.disable_bulb(2)   # UV
    def lamp_on( self, lamp_index ):
        self.swob.enable_bulb( self.lamp_device_constant_list[ lamp_index ])
    def lamp_off( self, lamp_index ):
        self.swob.disable_bulb( self.lamp_device_constant_list[ lamp_index ])
    def set_lamp_current_mA( self, current_index, lamp_index ):
        if lamp_index == 0: #limit UV lamp to 12.5mA
            if current_index > 1:
                current_index = 1
        if lamp_index == 2: #limit NIR lamp to 50mA
            if current_index > 3:
                current_index = 3
        try:
            if current_index == 0:
                self.lamp_off( lamp_index )
                return 0
            else:
                self.lamp_on( lamp_index )
                self.swob.set_bulb_current( self.lamp_current_constant_list[ current_index-1 ], self.lamp_device_constant_list[ lamp_index ] )
                return self.lamp_current_mA_list[lamp_index][ current_index ]
        except Exception as err:
            print( "failed to set current:", err )
            return False
            

class Null_as7265x_Spectrometer( Device ):
    def __init__( self ):
        super().__init__(name = None, swob = None)
        self.swob = None
        self.choice_label = None
        self.wavelength_bands_nm = None
        self.band_designations_in_read_all_order = None
        self.bandwidths_nm =None
        self.chip_number = None
        self.dict_chip_number = None
        self.dict_bandwidths = None
        self.bands_sorted = None
        self.uncertainty_percent = None
        self.afov_deg = None
        # settings
        self.gain_list = None
        self.default_gain_index = None
        self.integration_time_ms_step = None
        self.integration_time_index_maximum = None
        self.integration_time_ms_maximum = None
        self.integration_time_number_of_choices = None
        self.integration_time_index_per_choice = None
        self.integration_time_ms_list = None
        self.default_integration_time_index = None
        self.lamp_current_mA_list = None
    def set_gain(self, index):
        pass
    def set_integration_time( self, index ):
        pass
    def read_chip_temperatures( self ):
        pass
    def read_counts_all_channels( self ):
        pass
    def read_irradiances_all_channels( self ):
        pass

    def read_counts( self, index ):
        pass
    def list_wavelength_bands_nm( self ):
        pass
    def header( self ):
        pass
    def get_bandwidth(self, wavelength):
        return self.dict_bandwidths[wavelength]
    '''
    def log( self, wavelength):
        pass
    def serial_log(self, wavelength):
        pass
    def printlog(self,ch):
        pass
    '''
    def lamps_on(self):
        pass
    def lamps_off(self):
        pass
    def lamp_set_current_mA( self, current_index, lamp_index ):
        pass
    def lamp_set_current_mA_all( self, current_index ):
        pass
        
def initialize_as7265x_spectrometer( instrument ):
    as7265x_spectrometer = Null_as7265x_Spectrometer()
    try:
        as7265x_spectrometer = as7265x_Spectrometer( instrument.i2c_bus )
        instrument.welcome_page.announce( "initialize_as7265x_spectrometer" )
        instrument.spectral_sensors_present.append( as7265x_spectrometer )
        as7265x_spectrometer.all_lamps_on()
        time.sleep(0.1)
        as7265x_spectrometer.all_lamps_off()
    except Exception as err:
        print( "as7265x spectrometer failed: {}".format( err ))
    return as7265x_spectrometer
