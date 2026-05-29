import board
import busio as io
import adafruit_mlx90614
import time

# the mlx90614 must be run at 100kHz [normal speed]
# i2c default mode is is 400kHz [full speed]
# the mlx90614 will not appear at the default 400kHz speed
i2c = io.I2C(board.SCL, board.SDA, frequency=100000)
mlx = adafruit_mlx90614.MLX90614(i2c)

# temperature results in celsius
while True:
    #print("Ambent Temp: ", mlx.ambient_temperature)
    print("Object Temp: {} C".format(mlx.object_temperature))
    time.sleep(1.0)
