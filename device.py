import time
import asyncio

from sensor import *


async def main():
    left_esense = BLE_eSense("left_esense", "eSense-0091")
    await left_esense._init()

    sensors = [
        IMU_BNO055("imu1"),
        GSR_Grovepi("gsr1"),
        left_esense
    ]

    while True:
        tasks = []
        for sensor in sensors:
            task = asyncio.create_task(sensor.read_data())
            tasks.append(task)

        # TODO: write this data to .csv or a TS DB
        data_list = await asyncio.gather(*tasks)

        # For debug purposes
        print(data_list)
        print()
        print()

        # Set the sample rate here
        time.sleep(0.02)

asyncio.run(main())
