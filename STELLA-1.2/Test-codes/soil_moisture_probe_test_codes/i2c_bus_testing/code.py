import adafruit_ads1x15.ads1015 as ADS1015
from adafruit_ads1x15.analog_in import AnalogIn as ADS1x15_AnalogIn
import busio
import board
import digitalio
import time

i2c_bus = board.I2C()
#i2c_bus.try_lock()

ads1015_12_bit_adc = ADS1015.ADS1015( i2c_bus )
adc_ch0 = ADS1x15_AnalogIn(ads1015_12_bit_adc, ADS1015.P0)
adc_ch1 = ADS1x15_AnalogIn(ads1015_12_bit_adc, ADS1015.P1)
adc_ch2 = ADS1x15_AnalogIn(ads1015_12_bit_adc, ADS1015.P2)
adc_ch3 = ADS1x15_AnalogIn(ads1015_12_bit_adc, ADS1015.P3)

while True:
    print (adc_ch0.value, adc_ch1.value, adc_ch2.value, adc_ch3.value, "   ", adc_ch0.voltage, adc_ch1.voltage, adc_ch2.voltage, adc_ch3.voltage)
    time.sleep(0.1)

