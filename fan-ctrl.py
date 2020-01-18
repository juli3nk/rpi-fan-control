#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import os
import RPi.GPIO as GPIO
import signal
import sys
import time

# Configuration
FAN_PIN = int(os.getenv('FAN_CTRL_PIN')) # BCM pin used to drive transistor's base
WAIT_TIME = 1  # [s] Time to wait between each refresh
FAN_SPEED = 100 # [%] Fan speed
PWM_FREQ = 50  # [Hz] Change this value if fan has strange behavior

# Configurable temperature and fan speed steps
TEMP_THRESHOLD = int(os.getenv('FAN_CTRL_TEMPERATURE_THRESHOLD', 50))

# Logging level
logging.basicConfig(level=logging.INFO)


class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        logging.info('captured signal %d' % signum)
        self.kill_now = True

        fan.stop()
        GPIO.cleanup()

        logging.info('stopped fan and exiting...')
        sys.exit(0)



def get_temp():
    # Read CPU temperature
    cpuTempFile = open('/sys/class/thermal/thermal_zone0/temp', 'r')
    cpuTemp = float(cpuTempFile.read()) / 1000
    cpuTempFile.close()

    return cpuTemp

def get_fan_status():
    fanValueFile = open('/sys/class/gpio/gpio{0}/value'.format(FAN_PIN), 'r')
    fanValue = int(fanValueFile.read())
    fanValueFile.close()

    return fanValue


if __name__ == '__main__':
    if FAN_PIN is None:
        logging.error('"FAN_CTRL_PIN" env var is not set')
        sys.exit(1)

    # Setup GPIO pin
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(FAN_PIN, GPIO.OUT, initial=GPIO.LOW)
    fan = GPIO.PWM(FAN_PIN, PWM_FREQ)
    fan.start(0);

    killer = GracefulKiller()
    counterOn = 0
    counterOff = 0
    while not killer.kill_now:
        temp = get_temp()
        fanV = get_fan_status()

        if fanV == 0 and temp > TEMP_THRESHOLD:
            counterOn += 1

            if counterOn < 5:
                continue

            fan.ChangeDutyCycle(FAN_SPEED)

            logging.info('temp is {0}'.format(temp))
            logging.info('turn fan on')

            counterOn = 0
        if fanV == 1 and temp < TEMP_THRESHOLD:
            counterOff += 1

            if counterOff < 5:
                continue

            fan.ChangeDutyCycle(0)

            logging.info('temp is {0}'.format(temp))
            logging.info('turn fan off')

            counterOff = 0

        # Wait until next refresh
        time.sleep(WAIT_TIME)
