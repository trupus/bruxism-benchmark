import time
import grovepi

#Sensor connected to A0 Port
gsr = 14		# Pin 14 is A0 Port.

grovepi.pinMode(gsr,"INPUT")

while True:
    try:
        print(grovepi.analogRead(gsr))
        time.sleep(.5)

    except IOError:
        print ("Error")
