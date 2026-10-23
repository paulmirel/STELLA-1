SOFTWARE_VERSION_NUMBER = "1.0"
DEVICE_TYPE = "as7265x_spectral_sensor"
# Copyright NASA 2025
# Author Paul Mirel

import time
from sparkfun_triad import AS7265x_I2C
from .classm_device import Device

def initialize_as7265x_spectrometer( instrument, alt_bus=None ):
    as7265x_spectrometer = False
    try:
        as7265x_spectrometer = as7265x_Spectrometer( instrument, alt_bus)
        instrument.welcome_page.announce( "initialize_as7265x_spectrometer" )
        instrument.spectral_sensors_present.append( as7265x_spectrometer )
        #as7265x_spectrometer.all_lamps_on()
        time.sleep(0.1)
        #as7265x_spectrometer.all_lamps_off()
    except Exception as err:
        pass
        #print( "as7265x spectrometer failed: {}".format( err ))
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
                        1,#sensor_unit.gain_list[sensor_unit.gain_index],
                        1,#sensor_unit.integration_time_ms_list[sensor_unit.integration_time_index],
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
    def __init__( self, instrument, alt_bus=None ):
        if alt_bus is None:
            super().__init__(name = "spectral", pn = "as7265x", address = 0x49, swob = AS7265x_I2C(instrument.i2c_bus))
        else:
            super().__init__(name = "spectral", pn = "as7265x", address = 0x49, swob = AS7265x_I2C(alt_bus))
        self.choice_label = "as7256x V+NIR"
        self.instrument = instrument
        #self.wavelength_bands_nm = [(610, 680, 730, 760, 810, 860), (560, 585, 645, 705, 900, 940), (410, 435, 460, 485, 510, 535)]
        self.band_designations = [("R", "S", "T", "U", "V", "W"), ("G", "H", "I", "J", "K", "L"), ("A", "B", "C", "D", "E", "F" )]
        self.bandwidths_nm = [20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20]
        self.wavelength_bands_nm = 410, 435, 460, 485, 510, 535, 560, 585, 610, 645, 680, 705, 730, 760, 810, 860, 900, 940
        self.number_of_channels = len( self.wavelength_bands_nm )
        self.band_designations_in_wavelength_order = "A","B","C","D","E","F","G","H","R","I","S","J","T","U","V","W","K","L"
        self.chip_number_in_wavelength_order = [2,2,2,2,2,2,1,1,0,1,0,1,0,0,0,0,1,1]
        self.data_counts = []
        self.data_calibrated = []
        for index in range( 0, self.number_of_channels+1):
            self.data_counts.append(0)
            self.data_calibrated.append(0)

        self.max_counts = 0
        self.min_counts = 0
        self.gain_list = [ 1, 3.7, 16, 64 ]
        self.gain_index = 3

        self.integration_time_ms_step = 2.78
        self.integration_time_index_maximum = 256
        self.integration_time_ms_maximum = self.integration_time_ms_step * self.integration_time_index_maximum
        self.integration_time_number_of_choices = 16
        self.integration_time_index_per_choice = self.integration_time_index_maximum/ self.integration_time_number_of_choices
        self.integration_time_ms_list = []
        self.integration_time_index = 15#int( self.integration_time_number_of_choices / 2)
        self.integration_time_ms_list.append( self.integration_time_ms_step )
        for index in range( 1, self.integration_time_number_of_choices + 1 ):
            integration_time_ms = ((index) * self.integration_time_index_per_choice * self.integration_time_ms_step)
            if integration_time_ms < 100:
                integration_time_ms = round(integration_time_ms, 1)
            else:
                integration_time_ms = int( integration_time_ms)
            self.integration_time_ms_list.append( integration_time_ms )

        if self.swob:
            self.swob.indicator_led = True #needed to establish control
            self.swob.indicator_led = False
            self.swob.conversion_mode = AS7265x_I2C.MODE_2
            self.set_gain( self.gain_index )
            self.set_integration_time( self.integration_time_index )
        self.uncertainty_percent = 12
        self.afov_full_angle_deg = (20.5 * 2) #datasheet reports half angle.

        self.lamp_selection_list = [ "Vis mA", "NIR mA", "UV mA" ]
        self.lamp_current_mA_list = [( 0, 12.5, 25, 50, 100 ),  (0, 12.5, 25),  (0, 12.5)]
        if True:
            self.set_lamp_current_mA(1,0)
            self.set_lamp_current_mA(1,1)
            self.set_lamp_current_mA(1,2)

        self.chip_temperatures = [ 0,0,0 ]

    def make_spectral_channels( self ):
        index = 0
        for item in self.wavelength_bands_nm:
            name = "{}nm_channel".format(item)
            spectral_channel = initialize_spectral_channel( name, self, index )
            index += 1

    def set_gain(self, new_gain_index):
        self.gain_index = new_gain_index
        new_gain = self.gain_list[ new_gain_index ]
        try:
            self.swob.gain = new_gain
            return self.gain_index, self.swob.gain
        except Exception as err:
            print( "failed to set gain: ", err )
            return False

    def set_integration_time( self, index ):
        # must wait for at least 5 seconds before sending integration time again. If not, signal goes to 0.
        integration_time_ms = self.integration_time_ms_list[ index ]
        try:
            self.swob.integration_time = integration_time_ms
            return self.swob.integration_time
        except Exception as err:
            print( "as7265x set integration time failed: ", err )

    def acquire_measurement( self ):
        self.swob.take_measurements()


    def read_counts_by_wavelength( self, wavelength ):
        index = self.wavelength_bands_nm.index(wavelength)
        return self.read_counts_by_index( index )


    def read_counts_by_index( self, index ):
        counts = 0
        try:
            if index in [0,1,2,3,4,5]:
                self.swob.device = 2
                if index == 0: counts = self.swob.raw_channel0
                if index == 1: counts = self.swob.raw_channel1
                if index == 2: counts = self.swob.raw_channel2
                if index == 3: counts = self.swob.raw_channel3
                if index == 4: counts = self.swob.raw_channel4
                if index == 5: counts = self.swob.raw_channel5
            elif index in [6,7,9,11,16,17]:
                self.swob.device = 1
                if index == 6: counts = self.swob.raw_channel0
                if index == 7: counts = self.swob.raw_channel1
                if index == 9: counts = self.swob.raw_channel2
                if index == 11: counts = self.swob.raw_channel3
                if index == 16: counts = self.swob.raw_channel4
                if index == 17: counts = self.swob.raw_channel5
            elif index in [8,10,12,13,14,15]:
                self.swob.device = 0
                if index == 8: counts = self.swob.raw_channel0
                if index == 10: counts = self.swob.raw_channel1
                if index == 12: counts = self.swob.raw_channel2
                if index == 13: counts = self.swob.raw_channel3
                if index == 14: counts = self.swob.raw_channel4
                if index == 15: counts = self.swob.raw_channel5
            self.data_counts[index] = counts
            return counts
        except Exception as err:
            print( "read channel counts failed: ", err )
            return False

    def read_calibrated_by_index( self, index ):
        value = 0

        try:
            if index in [0,1,2,3,4,5]:
                self.swob.device = 2
                if index == 0: value = self.swob.channel0
                if index == 1: value = self.swob.channel1
                if index == 2: value = self.swob.channel2
                if index == 3: value = self.swob.channel3
                if index == 4: value = self.swob.channel4
                if index == 5: value = self.swob.channel5
            elif index in [6,7,9,11,16,17]:
                self.swob.device = 1
                if index == 6: value = self.swob.channel0
                if index == 7: value = self.swob.channel1
                if index == 9: value = self.swob.channel2
                if index == 11: value = self.swob.channel3
                if index == 16: value = self.swob.channel4
                if index == 17: value = self.swob.channel5
            elif index in [8,10,12,13,14,15]:
                self.swob.device = 0
                if index == 8: value = self.swob.channel0
                if index == 10: value = self.swob.channel1
                if index == 12: value = self.swob.channel2
                if index == 13: value = self.swob.channel3
                if index == 14: value = self.swob.channel4
                if index == 15: value = self.swob.channel5
            cal_uW_per_cm2 = value
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
        #print(self.data_counts)

    def report_counts_by_index( self, index ):
        pass
        if False:
            wavelength = self.wavelength_bands_nm[ index ]
            counts = self.data_counts[index]
            return wavelength, counts

    def report_counts_all( self ):
        pass
        if False:
            return self.data_counts

    def get_max_min_counts( self ):
        self.max_counts = max(self.data_counts)
        self.min_counts = min(self.data_counts)
        return self.max_counts, self.min_counts

    def read_chip_temperatures( self ):
        self.chip_temperatures = []
        for chip_number in range (0,3):
            self.swob.device = chip_number
            self.chip_temperatures.append( self.swob.temperature )
        return self.chip_temperatures

    def read_irradiances_all_channels( self ):
        pass
        if False:
            self.data_fcal_irradiances = self.swob.get_value(1) # 1 index returns factory calibrated irradiance values, bands in unsorted order
            self.dict_fcal_irradiances = {key:value for key, value in zip(self.wavelength_bands_nm, self.data_fcal_irradiances)}


    def list_wavelength_bands_nm( self ):
        return self.bands_sorted
    def header( self ):
        return "WL.nm, irrad.uW/(cm^2), irrad.uncty.uW/(cm^2), counts, chip_num, chip_temp_C"
    def get_bandwidth(self, wavelength):
        return self.dict_bandwidths[wavelength]

    def all_lamps_on(self):
        #seems to be nonfunctional
        print( "turn on the lamps")
        for chip in range (0,3):
           self.lamp_on(chip)

    def all_lamps_off(self):
        #seems to be nonfunctional
        print( "turn off the lamps")
        for chip in range (0,3):
            self.lamp_off(chip)

    def lamp_on( self, chip_index ):
        self.swob.device = chip_index
        self.swob.driver_led = True

    def lamp_off( self, chip_index ):
        self.swob.device = chip_index
        self.swob.driver_led = False

    def set_lamp_current_mA( self, current_index, chip_index ):
        #print ("chip_index", chip_index, "current_index", current_index, "current mA", self.lamp_current_mA_list[chip_index][ current_index ])
        self.swob.device = chip_index
        if chip_index == 2: #limit UV lamp to 12.5mA
            if current_index > 1:
                current_index = 1
        if chip_index == 1: #limit NIR lamp to 50mA
            if current_index > 3:
                current_index = 3
        try:
            if current_index == 0: #VIZ
                self.lamp_off( chip_index )
                return 0
            else:
                self.lamp_on( chip_index )
                self.swob.driver_led_current = self.lamp_current_mA_list[chip_index][ current_index ]
                return self.swob.driver_led_current
        except Exception as err:
            print( "failed to set current:", err )
            return False



