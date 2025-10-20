import time
import board
import busio

from adafruit_as726x import AS726x_I2C


# Initialize I2C bus and sensor.
i2c = busio.I2C(board.SCL, board.SDA)
sensor = AS726x_I2C(i2c)

sensor.conversion_mode = sensor.MODE_2

print( "Default Gain = {}".format( sensor.gain ))
sensor.gain = 16
print( "Gain Now = {}".format( sensor.gain ))

print( "Default Integration Time = {} ms".format( sensor.integration_time ))
sensor.integration_time = 166
print( "Integration Time Now = {} ms".format( sensor.integration_time ))


sensor.driver_led_current = 50 #mA
sensor.driver_led = True
time.sleep(1.0)
sensor.driver_led = False

while True:
    # Wait for data to be ready
    while not sensor.data_ready:
        time.sleep(.1)

#Calibration information from AS7262 datasheet:
#Each channel is tested with GAIN = 16x, Integration Time (INT_T) = 166ms and VDD = VDD1 = VDD2 = 3.3V, TAMB=25°C.
#The accuracy of the channel counts/μW/cm2 is ±12%.
#Sensor Mode 2 is a continuous conversion of light into data on all 6 channels
#450nm, 500nm, 550nm, 570nm, 600nm and 650nm

#sensor.violet returns the calibrated floating point value in the violet channel.
#sensor.raw_violet returns the uncalibrated decimal count value in the violet channel.
#that syntax is the same for all 6 channels


    print( "V:450nm: %0.1f" % sensor.violet )
    print( "B:500nm: %0.1f" % sensor.blue )
    print( "G:550nm: %0.1f" % sensor.green )
    print( "Y:570nm: %0.1f" % sensor.yellow )
    print( "O:600nm: %0.1f" % sensor.orange )
    print( "R:650nm: %0.1f" % sensor.red )
    print( "Sensor Temperature: %0.1f" % sensor.temperature )
    print()
    time.sleep(1)
