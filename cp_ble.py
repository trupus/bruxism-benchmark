import sys
import time
import asyncio
import logging

from bleak import BleakClient

logger = logging.getLogger(__name__)

ADDRESS = "00:04:79:00:0D:46"
# ADDRESS = "00:04:79:00:0C:13"
IMU_DATA_ENABLE_UUID = "0000ff07-0000-1000-8000-00805f9b34fb"
IMU_DATA_UUID = "0000ff08-0000-1000-8000-00805f9b34fb"


async def prepare_ble_device(address: str):
    async with BleakClient(address) as client:
        logger.info(f"Connected: {client.is_connected}")
        await client.write_gatt_char(IMU_DATA_ENABLE_UUID, bytearray([0x57, 0x2d, 0x08, 0x00, 0xc8, 0x01, 0x2c, 0x00, 0x10, 0x00, 0x20]))
        logger.info("Configured for 100Hz")


async def run_ble_client(address: str, char_uuid: str, queue: asyncio.Queue):
    async def callback_handler(sender, data):
        await queue.put((time.time_ns()/1000000, data))

    await prepare_ble_device(address)

    async with BleakClient(address) as client:
        logger.info(f"Connected: {client.is_connected}")
        await client.write_gatt_char(IMU_DATA_ENABLE_UUID, bytearray([0x53, 0x67, 0x02, 0x01, 0x64]))

        await client.start_notify(char_uuid, callback_handler)
        await asyncio.sleep(60.0)
        await client.stop_notify(char_uuid)
        # Send an "exit command to the consumer"
        await queue.put((time.time_ns()/1000000, None))


async def run_queue_consumer(queue: asyncio.Queue):
    sample_rate_histogram = {}
    while True:
        # Use await asyncio.wait_for(queue.get(), timeout=1.0) if you want a timeout for getting data.
        epoch, data = await queue.get()
        if data is None:
            logger.info(
                "Got message from client about disconnection. Exiting consumer loop..."
            )
            for s, sr in sample_rate_histogram.items():
                logger.info(f"{s}s: {sr}Hz")
            scanned_sr = list(sample_rate_histogram.values())[1:-1]
            logger.info(
                f"Avg.: {sum(scanned_sr)/len(scanned_sr)}")

            break
        else:
            k = str(int(epoch/1000))
            if k in sample_rate_histogram:
                sample_rate_histogram[k] = sample_rate_histogram[k] + 1
            else:
                sample_rate_histogram[k] = 1
        #     logger.info(
        #         f"Received callback data via async queue at {epoch}: {data}")


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
