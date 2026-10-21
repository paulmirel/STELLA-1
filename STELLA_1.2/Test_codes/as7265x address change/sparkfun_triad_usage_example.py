import board
import busio
import time
from sparkfun_triad import AS7265x_I2C
i2c = busio.I2C(board.SCL, board.SDA, frequency = 100000) # or 400000

time.sleep(1)

sensor = AS7265x_I2C(i2c)

sensor.device = 0
sensor.indicator_led = True # needed for turning off later
sensor.indicator_led = False
#sensor.driver_led = True
#sensor.device = 1
#sensor.driver_led = True
#sensor.device = 2
#sensor.driver_led = True

a = 0

time.sleep(1)

while True:
    time.sleep(0.01)
    sensor.device = 0
    r610, r680, r730, r760, r810, r860 = sensor.channel0, sensor.channel1, sensor.channel2, sensor.channel3, sensor.channel4, sensor.channel5
    time.sleep(0.01)
    sensor.device = 1
    r560, r585, r645, r705, r900, r940 = sensor.channel0, sensor.channel1, sensor.channel2, sensor.channel3, sensor.channel4, sensor.channel5
    time.sleep(0.01)
    sensor.device = 2
    r410, r435, r460, r485, r510, r535 = sensor.channel0, sensor.channel1, sensor.channel2, sensor.channel3, sensor.channel4, sensor.channel5
    time.sleep(0.1)
    print({'id':a, '410':r410, '435':r435, '460':r460, '485':r485, '510':r510, '535':r535, '560':r560,
    '585':r585, '610':r610, '645':r645, '680':r680, '705':r705, '730':r730, '760':r760, '810':r810, '860':r860,  '900':r900, '940':r940})



    a = a + 1
