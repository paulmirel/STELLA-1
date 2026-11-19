# STELLA-1.2 filter wheel positions setter


import time
import board
import busio
import adafruit_tca9548a
import adafruit_as5600
import adafruit_ds3231
from adafruit_pca9685 import PCA9685
import rotaryio
from software_modules import devicem_rotary_encoder

def main():

    filter_wheel_F = 4 #2, 3, 4

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
    filter_wheel_angle_sensor = adafruit_as5600.AS5600(i2c_bus, address = 0x46)

    if filter_wheel_angle_sensor.max_gain_overflow is True:
        print("ALERT Magnet is too weak")
    if filter_wheel_angle_sensor.min_gain_overflow is True:
        print("ALERT Magnet is too strong")

    filter_servo.duty_cycle = 0
    sensor_servo.duty_cycle = 0
    value = 5800

    if filter_wheel_F == 2:
        from configuration_files import cal_lookup_wheel_F2
        filter_config_file = cal_lookup_wheel_F2
    if filter_wheel_F == 3:
        from configuration_files import cal_lookup_wheel_F3
        filter_config_file = cal_lookup_wheel_F3
    if filter_wheel_F == 4:
        from configuration_files import cal_lookup_wheel_F4
        filter_config_file = cal_lookup_wheel_F4

    magnetic_angle_values = getattr(filter_config_file, "magnetic_angle_values", False)
    angle_offsets = getattr(filter_config_file, "magnetic_angle_offsets", False)
    servo_position_values = getattr(filter_config_file, "servo_position_values", False)

    print( "magnetic_angle_values", magnetic_angle_values)
    print( "magnetic_angle_offsets", angle_offsets)
    print( "servo_position_values", servo_position_values)
    waypoints = []
    for index in range (0, len(servo_position_values)-1):
        waypoints.append(int((servo_position_values[index]+servo_position_values[index+1])/2))
    print( "waypoints", waypoints)
    dwell = 0.06 #0.07
    position = 0
    rotary_encoder.encoder_flag = True
    while True:
        rotary_encoder.read_encoder()
        if rotary_encoder.encoder_flag:
            encoder_increment = rotary_encoder.last_value
            position = (position + encoder_increment) % 9
            encoder_increment = 0
            rotary_encoder.encoder_flag = False
            print("position", position)
            if position < 8:
                filter_servo.duty_cycle =  waypoints[position]
            else:
                filter_servo.duty_cycle =  waypoints[position-1]
            time.sleep(0.6)
            wheel_angle = filter_wheel_angle_sensor.angle
            if position == 8:
                while wheel_angle >  magnetic_angle_values[position]+ angle_offsets[position]:
                    filter_servo.duty_cycle =  filter_servo.duty_cycle - 16
                    time.sleep(dwell)
                    wheel_angle =  filter_wheel_angle_sensor.angle
            else:
                while wheel_angle <  magnetic_angle_values[position]+ angle_offsets[position]:
                    filter_servo.duty_cycle =  filter_servo.duty_cycle + 16
                    time.sleep(dwell)
                    wheel_angle =  filter_wheel_angle_sensor.angle
            filter_servo.duty_cycle = 0
            print( "wheel angle reading:", filter_wheel_angle_sensor.angle )
        last_angle = filter_wheel_angle_sensor.angle
        time.sleep(0.1)
        angle = filter_wheel_angle_sensor.angle
        angle_difference = last_angle - angle
        if angle_difference != 0:
            print( angle - magnetic_angle_values[position] )


    filter_servo.duty_cycle = 0
    sensor_servo.duty_cycle = 0

    pca.deinit()
    print("done")


main()
