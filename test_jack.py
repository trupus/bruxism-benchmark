#!/usr/bin/python
import RPi.GPIO as GPIO
from signal import pause
import subprocess


# GPIO initialisieren
GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.IN)

# internen Pullup-Widerstand aktivieren.
GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP)


# Callback-Funktion fuer beide Flanken
def measure(channel):
    if GPIO.input(26) == 0:  # fallende Flanke, Startzeit speichern
        bashCMD = "sudo amixer -c 0 sset Speaker,0 0"
        output = subprocess.check_output(['bash', '-c', bashCMD])
    else:  # steigende Flanke, Endezeit speichern
        bashCMD = "sudo amixer -c 0 sset Speaker,0 122"
        output = subprocess.check_output(['bash', '-c', bashCMD])


# Interrupt fuer beide Flanken aktivieren
GPIO.add_event_detect(26, GPIO.BOTH, callback=measure, bouncetime=300)
pause()
