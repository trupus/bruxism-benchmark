import sys
import time
import asyncio
import logging

from bleak import BleakClient

logger = logging.getLogger(__name__)

ADDRESS = "00:04:79:00:0C:13"
IMU_DATA_ENABLE_UUID = "0000ff07-0000-1000-8000-00805f9b34fb"
IMU_DATA_UUID = "0000ff08-0000-1000-8000-00805f9b34fb"


async def run_ble_client(address: str, char_uuid: str, queue: asyncio.Queue):
    async def callback_handler(sender, data):
        await queue.put((time.time(), data))

    async with BleakClient(address) as client:
        logger.info(f"Connected: {client.is_connected}")
        await client.write_gatt_char(IMU_DATA_ENABLE_UUID, bytearray([0x53, 0x35, 0x02, 0x01, 0x32]))
        await client.start_notify(char_uuid, callback_handler)
        await asyncio.sleep(10.0)
        await client.stop_notify(char_uuid)
        # Send an "exit command to the consumer"
        await queue.put((time.time(), None))


async def run_queue_consumer(queue: asyncio.Queue):
    while True:
        # Use await asyncio.wait_for(queue.get(), timeout=1.0) if you want a timeout for getting data.
        epoch, data = await queue.get()
        if data is None:
            logger.info(
                "Got message from client about disconnection. Exiting consumer loop..."
            )
            break
        else:
            logger.info(
                f"Received callback data via async queue at {epoch}: {data}")


async def main(address: str, char_uuid: str):
    queue = asyncio.Queue()
    client_task = run_ble_client(address, char_uuid, queue)
    consumer_task = run_queue_consumer(queue)
    await asyncio.gather(client_task, consumer_task)
    logger.info("Main method done.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(
        main(ADDRESS, IMU_DATA_UUID)
    )
