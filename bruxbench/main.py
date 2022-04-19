import logging
import asyncio
import sys
from sensor import *
from bruxi import Bruxi

logger = logging.getLogger(__name__)


async def main(dir_name, halt_event):
    SENSORS = [
        Sensor(name="mock-s1"),
        BLE_eSense(name="ble-left", ble_device_name="eSense-0091"),
        BLE_eSense(name="ble-right", ble_device_name="eSense-0398"),
        # ...
    ]

    device = Bruxi(dir_name=dir_name, sensors=SENSORS, halt_event=halt_event)

    logger.info(
        f"Initialising {len(device.sensors)}/ {len(SENSORS)} sensors..")
    await device.initialize_sensors()
    logger.info("Done.")

    logger.info("Spawning workers..")
    await asyncio.gather(*device.spawn_coroutines())
    logger.info("All workers exited.")


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(message)s',
                        datefmt='%d.%m.%Y %H:%M:%S', level=logging.INFO)

    dir_name = sys.argv[1]
    halt_event = asyncio.Event()
    try:
        asyncio.run(main(dir_name, halt_event))
    except KeyboardInterrupt:
        logger.info("Halt received! Shuting down..")
        halt_event.set()
