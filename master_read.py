import time
import grovepi
import adafruit_bno055
import board
import time

# IMY init
i2c = board.I2C()
sensor = adafruit_bno055.BNO055_I2C(i2c)

# GSR init
# Pin 14 is A0 Port.
gsr = 14
grovepi.pinMode(gsr, "INPUT")

while True:
    try:
        # IMU Read
        print("IMU")
        print(sensor.temperature)
        print(sensor.euler)
        print(sensor.gravity)
        print()

        # GSR Read
        print("GSR")
        print(grovepi.analogRead(gsr))
        print()

        time.sleep(.5)

    except IOError:
        print("Error")
