# STELLA-1.2 wheel positions setter


import time
import board
import busio
import adafruit_tca9548a
import adafruit_as5600
import adafruit_ds3231
from adafruit_pca9685 import PCA9685
import rotaryio
from software_modules import devicem_rotary_encoder

rotary_encoder = devicem_rotary_encoder.initialize_rotary_encoder( pin_a = board.A3, pin_b = board.A4, pin_button = board.A2 )
encoder_increment = 0
button_pressed = False

i2c_bus = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c_bus)
pca.frequency = 60

mux_8_to_1 = adafruit_tca9548a.TCA9548A(i2c_bus)

filter_servo = pca.channels[0]
sensor_servo = pca.channels[15]
sensor_wheel_angle_sensor = adafruit_as5600.AS5600(mux_8_to_1[7])

filter_servo.duty_cycle = 0
sensor_servo.duty_cycle = 0
value = 12000
while True:
    rotary_encoder.read_encoder()
    if rotary_encoder.encoder_flag:
        encoder_increment = rotary_encoder.last_value
        value = value + 16*encoder_increment
        encoder_increment = 0
        rotary_encoder.encoder_flag = False
        print( "servo value =", value, end = ", "  )
        #filter_servo.duty_cycle = value
        sensor_servo.duty_cycle = value
        print("magnetic angle value =",sensor_wheel_angle_sensor.angle)
        #print(f"Magnitude: {sensor_wheel_angle_sensor.magnitude}")

    time.sleep( 0.05 )


filter_servo.duty_cycle = 0
sensor_servo.duty_cycle = 0

pca.deinit()
print("done")


