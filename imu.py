import adafruit_bno055
import board
import time

i2c = board.I2C()

sensor = adafruit_bno055.BNO055_I2C(i2c, address=0x28)

while True:
    print(sensor.temperature)
    print(sensor.euler)
    print(sensor.gravity)
    time.sleep(1)
