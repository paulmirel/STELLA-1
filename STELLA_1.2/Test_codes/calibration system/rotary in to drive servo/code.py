# STELLA-1.2 wheel positions


import time
import board
import busio
import adafruit_tca9548a
import adafruit_as5600
from adafruit_as7343 import AS7343
from adafruit_as7341 import AS7341
import adafruit_ds3231
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
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
        print( value )
        #filter_servo.duty_cycle = value
        sensor_servo.duty_cycle = value
    time.sleep( 0.05 )


filter_servo.duty_cycle = 0
sensor_servo.duty_cycle = 0

pca.deinit()









if False:


    sensor_wheel_angle_sensor = adafruit_as5600.AS5600(mux_8_to_1[7])
    if True:
        if sensor_wheel_angle_sensor.magnet_detected:
            if sensor_wheel_angle_sensor.max_gain_overflow is True:
                print("Magnet is too weak")
            if sensor_wheel_angle_sensor.min_gain_overflow is True:
                print("Magnet is too strong")
            print(f"Raw angle: {sensor_wheel_angle_sensor.raw_angle}")
            print(f"Scaled angle: {sensor_wheel_angle_sensor.angle}")
            print(f"Magnitude: {sensor_wheel_angle_sensor.magnitude}")

    print()

    if True:
        filter_wheel_angle_sensor = adafruit_as5600.AS5600(i2c_bus, address = 0x46)
        if filter_wheel_angle_sensor.magnet_detected:
            if filter_wheel_angle_sensor.max_gain_overflow is True:
                print("Magnet is too weak")
            if filter_wheel_angle_sensor.min_gain_overflow is True:
                print("Magnet is too strong")
            print(f"Raw angle: {filter_wheel_angle_sensor.raw_angle}")
            print(f"Scaled angle: {filter_wheel_angle_sensor.angle}")
            print(f"Magnitude: {filter_wheel_angle_sensor.magnitude}")

print("done")


