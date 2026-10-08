SOFTWARE_VERSION_NUMBER = "1.0"
DEVICE_TYPE = "as7265x_spectral_sensor"
# Copyright NASA 2025
# Author Paul Mirel

import time
import qwiic_as7265x
from .classm_device import Device

def initialize_as7265x_spectrometer( instrument ):
    as7265x_spectrometer = Null_as7265x_Spectrometer()
    try:
        as7265x_spectrometer = as7265x_Spectrometer( instrument )#.i2c_bus )
        instrument.welcome_page.announce( "initialize_as7265x_spectrometer" )
        instrument.spectral_sensors_present.append( as7265x_spectrometer )
        as7265x_spectrometer.all_lamps_on()
        time.sleep(0.1)
        as7265x_spectrometer.all_lamps_off()
    except Exception as err:
        print( "as7265x spectrometer failed: {}".format( err ))
    return as7265x_spectrometer


def initialize_spectral_channel( name, sensor_unit, index ):
    #try:
    spectral_channel = Spectral_Channel( name, sensor_unit, index)
    sensor_unit.instrument.welcome_page.announce( "initialize_spectral_channel {}".format( name ) )
    sensor_unit.instrument.sensors_present.append( spectral_channel )
    return spectral_channel


class Spectral_Channel( Device ):
    def __init__( self, name, sensor_unit, index ):
        #print( name, index )
        #super().__init__(name=name, sensor_group=sensor_group )
        super().__init__(name = name, pn = "as7265x", address = 0x49, swob = sensor_unit )
        self.sensor_unit = sensor_unit
        self.index = index
        self.parameters = [ "wavelength_nm", "gain", "int_time_ms", "raw_counts", "ct_per_s_nm", "irrad_W_per_m2", "bandwidth_nm",
                            "chip_number", "chip_temp_C"]
        self.wavelength_nm = sensor_unit.wavelength_bands_nm[self.index]
        self.bandwidth_nm = sensor_unit.bandwidths_nm[self.index]
        self.chip_number = sensor_unit.chip_number_in_wavelength_order[self.index]
        self.values = [ self.wavelength_nm,
                        sensor_unit.gain_list[sensor_unit.gain_index],
                        sensor_unit.integration_time_ms_list[sensor_unit.integration_time_index],
                        0,
                        0,
                        0,
                        self.bandwidth_nm,
                        self.chip_number,
                        0]

    def get_wavelength( self ):
        return self.wavelength_nm

    def get_plot_values( self ):
        return (self.values[3],self.values[4],self.values[5],self.values[6])

    def read(self):
        raw = self.sensor_unit.data_counts[self.index] #read_counts_by_index( self.index )
        irradiance = 0# self.sensor_unit.read_calibrated_by_index( self.index )
        gain = self.sensor_unit.gain_list[self.sensor_unit.gain_index]
        int_time_ms = self.sensor_unit.integration_time_ms_list[self.sensor_unit.integration_time_index]
        bandwidth_nm = self.bandwidth_nm
        normal_ct_per_s_nm = round(1000*raw/(gain*int_time_ms*bandwidth_nm),3)
        chip_temp_C = self.sensor_unit.read_chip_temperature_by_chip_number( self.chip_number)
        self.values = [self.wavelength_nm,
                        gain,
                        int_time_ms,
                        raw,
                        normal_ct_per_s_nm,
                        irradiance,
                        bandwidth_nm,
                        self.chip_number,
                        chip_temp_C]

    def log(self):
        log = "{}, {}".format( self.name, self.pn )
        for index in range (0, len(self.parameters)):
            log = log + ", {}, {}".format( self.parameters[index], self.values[index])
        return log

    def printlog(self):
        print( self.log())


class as7265x_Spectrometer( Device ):
    def __init__( self, instrument ): #com_bus ):
        super().__init__(name = "spectral", pn = "as7265x", address = 0x49, swob = qwiic_as7265x.QwiicAS7265x(  ))
        self.choice_label = "as7256x V+NIR"
        self.instrument = instrument
        #self.wavelength_bands_nm = 610, 680, 730, 760, 810, 860, 560, 585, 645, 705, 900, 940, 410, 435, 460, 485, 510, 535
        self.wavelength_bands_nm = 410, 435, 460, 485, 510, 535, 560, 585, 610, 645, 680, 705, 730, 760, 810, 860, 900, 940
        self.number_of_channels = len( self.wavelength_bands_nm )
        self.band_designations_in_wavelength_order = "A","B","C","D","E","F","G","H","R","I","S","J","T","U","V","W","K","L"
        self.data_counts = []
        self.data_calibrated = []
        for index in range( 0, self.number_of_channels+1):
            self.data_counts.append(0)
            self.data_calibrated.append(0)

        self.max_counts = 0
        self.min_counts = 0
        self.chip_number_in_wavelength_order = [3,3,3,3,3,3,2,2,1,2,1,2,1,1,1,1,2,2]
        #self.band_designations_in_read_all_order = ("R", "S", "T", "U", "V", "W", "G", "H", "I", "J", "K", "L", "A", "B", "C", "D", "E", "F" )
        self.bandwidths_nm = [20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20]

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
        self.chip_temperatures = [ 0,0,0,0 ]

    def make_spectral_channels( self ):
        index = 0
        for item in self.wavelength_bands_nm:
            name = "{}nm_channel".format(item)
            spectral_channel = initialize_spectral_channel( name, self, index )
            index += 1

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

    def read_calibrated_by_index( self, index ):
        try:
            if index == 0: cal_uW_per_cm2 = self.swob.get_calibrated_a()
            if index == 1: cal_uW_per_cm2 = self.swob.get_calibrated_b()
            if index == 2: cal_uW_per_cm2 = self.swob.get_calibrated_c()
            if index == 3: cal_uW_per_cm2 = self.swob.get_calibrated_d()
            if index == 4: cal_uW_per_cm2 = self.swob.get_calibrated_e()
            if index == 5: cal_uW_per_cm2 = self.swob.get_calibrated_f()
            if index == 6: cal_uW_per_cm2 = self.swob.get_calibrated_g()
            if index == 7: cal_uW_per_cm2 = self.swob.get_calibrated_h()
            if index == 8: cal_uW_per_cm2 = self.swob.get_calibrated_r()
            if index == 9: cal_uW_per_cm2 = self.swob.get_calibrated_i()
            if index == 10: cal_uW_per_cm2 = self.swob.get_calibrated_s()
            if index == 11: cal_uW_per_cm2 = self.swob.get_calibrated_j()
            if index == 12: cal_uW_per_cm2 = self.swob.get_calibrated_t()
            if index == 13: cal_uW_per_cm2 = self.swob.get_calibrated_u()
            if index == 14: cal_uW_per_cm2 = self.swob.get_calibrated_v()
            if index == 15: cal_uW_per_cm2 = self.swob.get_calibrated_w()
            if index == 16: cal_uW_per_cm2 = self.swob.get_calibrated_k()
            if index == 17: cal_uW_per_cm2 = self.swob.get_calibrated_l()
            uW_per_W = 1000000
            cm2_per_m2 = 10000
            si_cal_W_per_m2 = round((cal_uW_per_cm2 * cm2_per_m2) / uW_per_W, 4)
            self.data_calibrated[index] = si_cal_W_per_m2
            return si_cal_W_per_m2
        except Exception as err:
            print( "read channel calibrated failed: ", err )
            return False

    def read( self ):
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

    def read_chip_temperature_by_chip_number( self, chip_number):
        self.chip_temperatures[ chip_number] = int(round(self.swob.get_temperature(device = chip_number),0))
        return self.chip_temperatures[ chip_number]

    def read_irradiances_all_channels( self ):
        self.data_fcal_irradiances = self.swob.get_value(1) # 1 index returns factory calibrated irradiance values, bands in unsorted order
        self.dict_fcal_irradiances = {key:value for key, value in zip(self.wavelength_bands_nm, self.data_fcal_irradiances)}


    def list_wavelength_bands_nm( self ):
        return self.bands_sorted
    def header( self ):
        return "WL.nm, irrad.uW/(cm^2), irrad.uncty.uW/(cm^2), counts, chip_num, chip_temp_C"
    def get_bandwidth(self, wavelength):
        return self.dict_bandwidths[wavelength]

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
    def log( self, wavelength):
        pass
    def serial_log(self, wavelength):
        pass
    def printlog(self,ch):
        pass
    def lamps_on(self):
        pass
    def lamps_off(self):
        pass
    def lamp_set_current_mA( self, current_index, lamp_index ):
        pass
    def lamp_set_current_mA_all( self, current_index ):
        pass


