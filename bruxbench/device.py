import time
import asyncio
import datetime

from sensor import *


class Device:
    def __init__(self):
        pass

    # def add_sensor()


async def main():
    # redis_con = redis.Redis(host="localhost", port="6379")

    left_esense = BLE_eSense("left_esense", "eSense-0091")
    await left_esense._init()

    sensors = [
        # IMU_BNO055("imu1"),
        # GSR_Grovepi("gsr1"),
        left_esense
    ]

    ts = []

    while True:
        tasks = []
        for sensor in sensors:
            task = asyncio.create_task(sensor.read_data())
            tasks.append(task)

        # TODO: write this data to .csv or a TS DB
        data_list = await asyncio.gather(*tasks)
        ts.append(data_list)

        # 12Hz -> 100Hz

        # For debug purposes
        print(data_list)
        print()
        print()

        # Set the sample rate here
        # time.sleep(0.02)

asyncio.run(main())
