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

        # dictionary data from datasheet. key is wavelength, entry is: (chip_number, channel_number, raw_value, calibrated_value, temperature, bandwidth, designation)
        self.dictionary = {}
        self.dictionary[410] = (3,0,0,0,0,20,"A")
        self.dictionary[435] = (3,1,0,0,0,20,"B")
        self.dictionary[460] = (3,2,0,0,0,20,"C")
        self.dictionary[485] = (3,3,0,0,0,20,"D")
        self.dictionary[510] = (3,4,0,0,0,20,"E")
        self.dictionary[535] = (3,5,0,0,0,20,"F")
        self.dictionary[560] = (2,0,0,0,0,20,"G")
        self.dictionary[585] = (2,1,0,0,0,20,"H")
        self.dictionary[610] = (1,0,0,0,0,20,"R")
        self.dictionary[645] = (2,2,0,0,0,20,"i")
        self.dictionary[680] = (1,1,0,0,0,20,"S")
        self.dictionary[705] = (2,3,0,0,0,20,"J")
        self.dictionary[730] = (1,2,0,0,0,20,"T")
        self.dictionary[760] = (1,3,0,0,0,20,"U")
        self.dictionary[810] = (1,4,0,0,0,20,"V")
        self.dictionary[860] = (1,5,0,0,0,20,"W")
        self.dictionary[900] = (2,4,0,0,0,20,"K")
        self.dictionary[940] = (2,5,0,0,0,20,"L")

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

        self.integration_time_index = 11
        self.integration_time_ms_list = [4,10,20,30,40,50,60,70,80,90,100,120,130,140,150,160,170,180,200,250,300,350,400,450,500,550,600,650,700,711]
        self.integration_time_number_of_choices = len(self.integration_time_ms_list)
        if self.swob:
            self.swob.indicator_led = True #needed to establish control
            self.swob.indicator_led = False
            self.swob.conversion_mode = 3 #"ONE_SHOT" #2 CONTINUOUS ALL
            #print("conversion mode =", self.swob.conversion_mode)
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

        self.read()

    def read( self ):
        #print("start measurement")
        start = time.monotonic()
        self.swob.start_measurement()
        now = time.monotonic()
        data_ready = False
        #print(now-start, data_ready)
        #print("waiting for data ready")
        data_ready = False
        timeout = 2
        while not data_ready and now < start + timeout:
            #print(".", end = "")
            now = time.monotonic()
            data_ready = self.swob.data_ready
            #print(now-start, data_ready)
            time.sleep(0.1)
        #print()
        for key in self.wavelength_bands_nm:
            entry = self.dictionary.get(key)
            #print(key,entry)
            device = entry[0]-1
            self.swob.device = device
            time.sleep(0.01)
            channel = entry[1]
            counts = entry[2]
            print("key",key," device", device, " channel", channel," counts", counts)
            counts = 0
            if channel == 0:
                counts = self.swob.raw_channel0
            elif channel == 1:
                counts = self.swob.raw_channel1
            elif channel == 2:
                counts = self.swob.raw_channel2
            elif channel == 3:
                counts = self.swob.raw_channel3
            elif channel == 4:
                counts = self.swob.raw_channel4
            elif channel == 5:
                counts = self.swob.raw_channel5
            else:
                pass
            if False:
                entry[2] = counts
                print("key",key," device", device, " channel", channel," counts", counts, " entry", entry)

                self.dictionary[key] = entry
                entry = self.dictionary.get(key)
                print("key",key," device", device, " channel", channel," counts", entry[2], " entry", entry)

        temporary_data_counts = []
        for wavelength in self.wavelength_bands_nm:
            temporary_data_counts.append(wavelength) #look up the count values in the dictionary
        return temporary_data_counts

    def make_spectral_channels( self ):
        index = 0
        for item in self.wavelength_bands_nm:
            name = "{}nm_channel".format(item)
            spectral_channel = initialize_spectral_channel( name, self, index )
            index += 1

    def set_gain(self, index = None):
        if index is None:
            new_gain = self.gain_list[ self.gain_index ]
        else:
            self.gain_index = index
            new_gain = self.gain_list[ index ]
        try:
            self.swob.gain = new_gain
            return self.swob.gain
        except Exception as err:
            print( "failed to set gain: ", err )
            return False

    def read_gain(self):
        return self.swob.gain

    def set_integration_time( self, index = None ):
        # must wait for at least 5 seconds before sending integration time again. If not, signal goes to 0.
        if index is None:
            integration_time_ms = self.integration_time_ms_list[self.integration_time_index]
        else:
            self.integration_time_index = index
            integration_time_ms = self.integration_time_ms_list[ index ]
        if integration_time_ms < 4: integration_time_ms = 4
        if integration_time_ms >711: integration_time_ms = 711
        try:
            self.swob.integration_time = integration_time_ms
            return self.swob.integration_time
        except Exception as err:
            print( "as7265x set integration time failed: ", err )

    def read_integration_time_ms(self):
        return self.swob.integration_time



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



