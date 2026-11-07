"""
Example to excercise most functions (some indirectly).

Gives some timings.

"""

import board,time

import AS7265X_sparkfun
from AS7265X_sparkfun import AS7265X

i2c = board.I2C() # can be shared

try:
    start = time.monotonic_ns()
    my_as7265x = AS7265X(i2c)
    print(f"Init took { (time.monotonic_ns()-start)/1e6 }msec")

    # info
    print( f"device type: {my_as7265x.get_devicetype()}")
    print( f"firmware-version {my_as7265x.get_major_firmware_version()}.{my_as7265x.get_patch_firmware_version()}.{my_as7265x.get_build_firmware_version()}")
    print( f"hw-version {my_as7265x.get_hardware_version()}")
    print( f"Temp {my_as7265x.get_temperature_average()}C")

    # Blocking
    start = time.monotonic_ns()
    my_as7265x.take_measurements_with_bulb()
    took = (time.monotonic_ns()-start)/1e6
    print( f"All (in {took}ms): ", my_as7265x.get_value(1)) 

    # Non-blocking:

    start = time.monotonic_ns()
    my_as7265x.set_measurement_mode(AS7265X_sparkfun.MEASUREMENT_MODE_6CHAN_ONE_SHOT)

    while ( not my_as7265x.data_available() ):
        time.sleep(0.1) # or whatever

    start_r = time.monotonic_ns()
    all_values = my_as7265x.get_value(1)
    took_r = (time.monotonic_ns()-start_r)/1e6
    took = (time.monotonic_ns()-start)/1e6
    print( f"All calibrated (total {took}ms, read {took_r}ms): ", all_values)
    # ... B C D etc

    # Non-blocking, raw, with gain x64

    my_as7265x.set_gain(AS7265X_sparkfun.GAIN_64X)

    start = time.monotonic_ns()
    my_as7265x.set_measurement_mode(AS7265X_sparkfun.MEASUREMENT_MODE_6CHAN_ONE_SHOT)
    
    while ( not my_as7265x.data_available() ):
        time.sleep(0.1) # or whatever
    
    start_r = time.monotonic_ns()
    all_values = my_as7265x.get_value(0) # 0==raw, 1==calibrated
    took_r = (time.monotonic_ns()-start_r)/1e6
    took = (time.monotonic_ns()-start)/1e6
    print( f"All raw (total {took}ms, read {took_r}ms): ", all_values)
    # ... B C D etc
        
        
finally:
    # on ^c etc
    try:
        i2c.unlock() # good practice
    except Exception:
        # it can be "de-initialized"
        pass

