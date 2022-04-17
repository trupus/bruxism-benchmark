import adafruit_bno055
import adafruit_tca9548a
import board
import time
import busio

# i2c = board.I2C()
i2c = busio.I2C(board.SCL, board.SDA)

tca = adafruit_tca9548a.TCA9548A(i2c)

for channel in range(8):
    if tca[channel].try_lock():
        print("Channel {}:".format(channel), end="")
        addresses = tca[channel].scan()
        print([hex(address) for address in addresses if address != 0x70])
        tca[channel].unlock()

sensor = adafruit_bno055.BNO055_I2C(tca[0])
sensor1 = adafruit_bno055.BNO055_I2C(tca[1])

while True:
    print(sensor1.temperature)
    print(sensor1.euler)
    print(sensor1.gravity)
    print(sensor.temperature)
    print(sensor.euler)
    print(sensor.gravity)
    time.sleep(1)
