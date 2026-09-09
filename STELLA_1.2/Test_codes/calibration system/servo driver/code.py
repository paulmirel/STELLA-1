import board
import time
import digitalio
import analogio
import adafruit_bus_device
import adafruit_register
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

i2c_bus = board.I2C()
pca = PCA9685(i2c_bus)

def get_voltage(pin):
    return (pin.value * 3.3) / 65536 * 2

ON = True
OFF = False
enable_5V = digitalio.DigitalInOut( board.D10 )
enable_5V.direction = digitalio.Direction.OUTPUT
enable_5V.value = ON
monitor_5V = analogio.AnalogIn( board.A1)
time.sleep(1)
print( "5V ON: voltage on the 5V line = ", get_voltage(monitor_5V))



pca.frequency = 60
servo0 = servo.Servo(pca.channels[0])
servo15 = servo.Servo(pca.channels[15])

servo0.angle = 150
servo15.angle = 90


print("moving")
time.sleep(2)



increment = 10
for index in range (1,15):
    value = index * increment
    servo0.angle = value
    servo15.angle = value
    print( "moving to value =", value)
    time.sleep(3)

enable_5V.value = OFF
print("off")
time.sleep(1)
print( "5V OFF: voltage on the 5V line = ", get_voltage(monitor_5V))


pca.deinit()
print( "done" )

