import logging
import asyncio
import sys
from sensor import *
from bruxi import Bruxi
import aioconsole

logger = logging.getLogger(__name__)


async def ainput(halt_event):
    while not halt_event.is_set():
        line = await aioconsole.ainput('')
        if 'c' in line:
            halt_event.set()
        await asyncio.sleep(1)

async def main(dir_name, halt_event):
    SENSORS = [
        # Sensor(name="mock-s0"),
        # Sensor(name="mock-s1"),
        # Sensor(name="mock-s2"),
        # Sensor(name="mock-s3"),
        # Sensor(name="mock-s4"),
        BLE_eSense(name="ble-left", ble_device_name="eSense-0091"),
        BLE_eSense(name="ble-right", ble_device_name="eSense-0398"),
        GSR_Grovepi(name="gsr"),
        EMG_Olimex_x4(name="emg"),
        BNO055_x2(name="bno"),
        # ...
    ]

    device = Bruxi(dir_name=dir_name, sensors=SENSORS, halt_event=halt_event)

    logger.info(
        f"Initialising {len(device.sensors)}/ {len(SENSORS)} sensors..")
    await device.initialize_sensors()
    logger.info("Done.")

    cli_event_handler = ainput(halt_event)

    logger.info("Spawning workers..")
    await asyncio.gather(*device.spawn_coroutines(), cli_event_handler)
    logger.info("All workers exited.")


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(message)s',
                        datefmt='%d.%m.%Y %H:%M:%S', level=logging.INFO)

    dir_name = sys.argv[1]
    halt_event = asyncio.Event()
    asyncio.run(main(dir_name, halt_event))