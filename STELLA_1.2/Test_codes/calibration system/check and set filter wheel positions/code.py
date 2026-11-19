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

def main():

    filter_wheel_F = 2 #2, 3, 4

    sensor_wheel = 1 #1, 3, 5, 8

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

    filter_servo.duty_cycle = 0
    sensor_servo.duty_cycle = 0
    value = 5800

    if sensor_wheel == 1:
        from configuration_files import cal_lookup_wheel_1
        magnetic_angle_values = getattr(cal_lookup_wheel_1, "magnetic_angle_values", False)
        angle_offsets = getattr(cal_lookup_wheel_1, "magnetic_angle_offsets", False)
        servo_position_values = getattr(cal_lookup_wheel_1, "servo_position_values", False)
        spectral_sensor_tracking_numbers = getattr(cal_lookup_wheel_1, "tracking_numbers", False)
    elif  sensor_wheel == 3:
        from configuration_files import cal_lookup_wheel_3
        magnetic_angle_values = getattr(cal_lookup_wheel_3, "magnetic_angle_values", False)
        angle_offsets = getattr(cal_lookup_wheel_3, "magnetic_angle_offsets", False)
        servo_position_values = getattr(cal_lookup_wheel_3, "servo_position_values", False)
        spectral_sensor_tracking_numbers = getattr(cal_lookup_wheel_3, "tracking_numbers", False)
    elif  sensor_wheel == 8:
        from configuration_files import cal_lookup_wheel_8
        magnetic_angle_values = getattr(cal_lookup_wheel_8, "magnetic_angle_values", False)
        angle_offsets = getattr(cal_lookup_wheel_8, "magnetic_angle_offsets", False)
        servo_position_values = getattr(cal_lookup_wheel_8, "servo_position_values", False)
        spectral_sensor_tracking_numbers = getattr(cal_lookup_wheel_8, "tracking_numbers", False)
    elif sensor_wheel == 5:
        from configuration_files import cal_lookup_wheel_5
        magnetic_angle_values = getattr(cal_lookup_wheel_5, "magnetic_angle_values", False)
        angle_offsets = getattr(cal_lookup_wheel_5, "magnetic_angle_offsets", False)
        servo_position_values = getattr(cal_lookup_wheel_5, "servo_position_values", False)
        spectral_sensor_tracking_numbers = getattr(cal_lookup_wheel_5, "tracking_numbers", False)
    print( "magnetic_angle_values", magnetic_angle_values)
    print( "magnetic_angle_offsets", angle_offsets)
    print( "servo_position_values", servo_position_values)
    sensor_wheel_waypoints = []
    for index in range (0, len(servo_position_values)-1):
        sensor_wheel_waypoints.append(int((servo_position_values[index]+servo_position_values[index+1])/2))
    print( "sensor_wheel_waypoints", sensor_wheel_waypoints)

    position = 0
    while True:
        rotary_encoder.read_encoder()
        if rotary_encoder.encoder_flag:
            encoder_increment = rotary_encoder.last_value
            position = (position + encoder_increment) % 7
            encoder_increment = 0
            rotary_encoder.encoder_flag = False
            print("position", position)
            if position < 6:
                sensor_servo.duty_cycle =  sensor_wheel_waypoints[position]
            else:
                sensor_servo.duty_cycle =  sensor_wheel_waypoints[position-1]
            time.sleep(0.6)
            sensor_wheel_angle = sensor_wheel_angle_sensor.angle
            if position == 6:
                while sensor_wheel_angle >  magnetic_angle_values[position]+ angle_offsets[position]:
                    sensor_servo.duty_cycle =  sensor_servo.duty_cycle - 16
                    time.sleep(0.03)
                    sensor_wheel_angle =  sensor_wheel_angle_sensor.angle
            else:
                while sensor_wheel_angle <  magnetic_angle_values[position]+ angle_offsets[position]:
                    sensor_servo.duty_cycle =  sensor_servo.duty_cycle + 16
                    time.sleep(0.03)
                    sensor_wheel_angle =  sensor_wheel_angle_sensor.angle
                    #print(  sensor_servo.duty_cycle, sensor_wheel_angle )
            sensor_servo.duty_cycle = 0


    filter_servo.duty_cycle = 0
    sensor_servo.duty_cycle = 0

    pca.deinit()
    print("done")


def go_to_filter_position( self, position = None):
    filter_wheel_position_known = True
    text_areas[20].text = " -"
    if position is None:
        position =  filter_wheel_position
    if position != 8:
        filter_servo.duty_cycle =  filter_wheel_waypoints[position]
    else:
        filter_servo.duty_cycle =  filter_wheel_waypoints[position-1]
    time.sleep(0.4)
    filter_wheel_angle =  filter_wheel_angle_sensor.angle
    if position == 8:
        while filter_wheel_angle >  filter_wheel_magnetic_angle_values[position]+ filter_wheel_angle_offsets[position]:
            filter_servo.duty_cycle =  filter_servo.duty_cycle - 16
            time.sleep(0.04)
            filter_wheel_angle =  filter_wheel_angle_sensor.angle
            #print(  filter_servo.duty_cycle, filter_wheel_angle )
    else:
        while filter_wheel_angle <  filter_wheel_magnetic_angle_values[position]+ filter_wheel_angle_offsets[position]:
            filter_servo.duty_cycle =  filter_servo.duty_cycle + 16
            time.sleep(0.04)
            filter_wheel_angle =  filter_wheel_angle_sensor.angle
            #print(  filter_servo.duty_cycle, filter_wheel_angle )
    filter_servo.duty_cycle = 0
    filter_wheel_position = position
    return position
main()
