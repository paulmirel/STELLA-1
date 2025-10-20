# AS7265x triad spectrometer sensor test code
# NASA open source software license
# Paul Mirel 2025

#Gain 0: 1x
#Gain 1: 3.7x
#Gain 2: 16x (calibrated at this value)
#Gain 3: 64x
triad_gain = 2

# integration time integer set from 0 to 255
# integration time will be = 2.8ms * [integration cycles + 1]
# 59 cycles = 166ms (calibrated at this value)
# max int time = 717ms
triad_int_cycles = 59 #59

import time
import board
import busio
import AS7265X_sparkfun
from AS7265X_sparkfun import AS7265X

def main():
    i2c_bus = initialize_i2c_bus( board.SCL, board.SDA )
    triad_spectrometer = initialize_triad_spectrometer( i2c_bus )
    triad_spectrometer.found()
    triad_spectrometer.report()
    triad_spectrometer.read()

    ## triad_spectrometer check and set gain ##
    #Gain 0: 1x
    #Gain 1: 3.7x
    #Gain 2: 16x
    #Gain 3: 64x
    print(triad_spectrometer.swob._gain)
    triad_spectrometer.swob.set_gain( triad_gain )
    confirm_gain = triad_spectrometer.swob._gain
    if confirm_gain < 1:
        gain_ratio = 1
    elif confirm_gain == 1:
        gain_ratio = 3.7
    elif confirm_gain == 2:
        gain_ratio = 16
    elif confirm_gain == 3:
        gain_ratio = 64
    print("triad spectrometer gain set to {} == {}X".format(confirm_gain, gain_ratio))

    ## triad_spectrometer check and set integration time ##
    #print( triad_spectrometer.swob.virtual_read_register(INTERGRATION_TIME))
    triad_spectrometer.swob.set_integration_cycles(triad_int_cycles)
    int_time_ms = round((2.8*(triad_int_cycles+1)),0)
    print("triad spectrometer integration time set to {} == {}ms".format(triad_int_cycles, int_time_ms))


    triad_spectrometer.lamps_on()
    time.sleep(1)
    triad_spectrometer.lamps_off()
    triad_spectrometer.read()
    for item in triad_spectrometer.bands_sorted:
        print("{}, {}, {}, {}, {}, {}".format( item,
            triad_spectrometer.dict_cal[item],
            triad_spectrometer.dict_cal[item] * triad_spectrometer.uncert_percent/100,
            triad_spectrometer.dict_counts[item], triad_spectrometer.dict_chip_n[item],
            triad_spectrometer.chip_temps[triad_spectrometer.dict_chip_n[item]] ))

    try:
        while True:
            triad_spectrometer.read()

            spectral_data_sorted = []
            for item in triad_spectrometer.bands_sorted:
                spectral_data_sorted.append(0)
                spectral_data_sorted.append(triad_spectrometer.dict_cal[item])
                #print(item, triad_spectrometer.dict_cal[item],
                #    triad_spectrometer.dict_cal[item] * triad_spectrometer.uncert_percent/100,
                #    triad_spectrometer.dict_counts[item], triad_spectrometer.dict_chip_n[item],
                #    triad_spectrometer.chip_temps[triad_spectrometer.dict_chip_n[item]] )
            print( spectral_data_sorted )

    finally:  # clean up the busses when ctrl-c'ing out of the loop
        i2c_bus.deinit()
        print( "i2c_bus deinitialized" )

class Device: #parent class
    def __init__(self, name = None, pn = None, address = None, swob = None):
        self.name = name
        self.swob = swob
        self.pn = pn
        self.address = address
    def report(self):
        if self.swob is not None:
            print("report:", self.name, self.pn, hex(self.address), "found" )

def initialize_triad_spectrometer( i2c_bus ):
    triad_spectrometer = Null_Triad_Spectrometer()
    try:
        triad_spectrometer = as7265x_Triad_Spectrometer( i2c_bus )
    except:
        pass
    return triad_spectrometer

class as7265x_Triad_Spectrometer( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "triad_spectrometer", pn = "as7256x", address = 0x00, swob = AS7265X( com_bus ))
        self.swob.disable_indicator()
        self.swob.set_measurement_mode(AS7265X_sparkfun.MEASUREMENT_MODE_6CHAN_CONTINUOUS)
        self.bands = 610, 680, 730, 760, 810, 860, 560, 585, 645, 705, 900, 940, 410, 435, 460, 485, 510, 535
        self.chip_n = 1,   1,   1,   1,   1,   1,   2,   2,   2,   2,   2,   2,   3,   3,   3,   3,   3,   3
        self.dict_chip_n = {key:value for key, value in zip(self.bands, self.chip_n)}
        self.bands_sorted = sorted( self.bands )
        self.uncert_percent = 12
    def found(self):
        print("found", self.pn, self.swob)
    def read(self):
        self.chip_temps = {1:self.swob.get_temperature(1), 2:self.swob.get_temperature(2), 3:self.swob.get_temperature(3)}
        self.data_counts = self.swob.get_value(0)
        self.dict_counts = {key:value for key, value in zip(self.bands, self.data_counts)}
        self.data_cal = self.swob.get_value(1)
        self.dict_cal = {key:value for key, value in zip(self.bands, self.data_cal)}
    def list_channels():
        return self.bands_sorted
    def header( self ):
        return "WL.nm, irrad.uW/(cm^2), irrad.uncty.uW/(cm^2), counts, chip_num, chip_temp_C"
    def log( self ):
        print( self.data_counts )
        print( self.data_cal )
        #self.irradiance[ch] = self.data[ch]/self.tsis_cal_counts_per_irradiance[ch]
        #self.irradiance[ch] = self.data[ch]/self.steno_cal_counts_per_irradiance[ch]
        #return "{}, {}, {}, {}".format( self.center_wavelengths_nm[ch], self.data[ch],
        #    self.irradiance[ch], self.irradiance[ch]*self.calibration_error )
    def printlog(self,ch):
        print( self.log(ch) )
    def lamps_on(self):
        print( "turn on the lamps")
        self.swob.enable_bulb(0)   # white
        self.swob.enable_bulb(1)   # NIR
        self.swob.enable_bulb(2)   # UV
    def lamps_off(self):
        print( "turn off the lamps")
        self.swob.disable_bulb(0)   # white
        self.swob.disable_bulb(1)   # NIR
        self.swob.disable_bulb(2)   # UV

class Null_Triad_Spectrometer():
    def __init__( self ):
        self.swob = None
        self.bands_sorted = [0,0]
        self.dict_chip_n = [0,0]
        self.chip_temps = [0,0]
        self.dict_cal = {0:10}
        self.dict_counts = {0:10}
        self.uncert_percent = 10
    def found(self):
        pass
    def read(self):
        pass
    def log(self):
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

def initialize_i2c_bus( SCL_pin, SDA_pin ):
    try:
        i2c_bus = busio.I2C( SCL_pin, SDA_pin )
        print( "initialized i2c_bus" )
    except ValueError as err:
        i2c_bus = False
        print( "i2c bus fail: {} -- press reset button, or power off to restart".format( err ))
    return i2c_bus

def stall():
    print("intentionally stalled, press return to continue")
    input_string = False
    while input_string == False:
        input_string = input().strip()

main()
