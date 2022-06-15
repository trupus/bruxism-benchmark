import sys
import time
import asyncio
import logging

from bleak import BleakClient

logger = logging.getLogger(__name__)

ADDRESS1 = "00:04:79:00:0D:46"
ADDRESS2 = "00:04:79:00:0C:13"
IMU_DATA_ENABLE_UUID = "0000ff07-0000-1000-8000-00805f9b34fb"
IMU_DATA_UUID = "0000ff08-0000-1000-8000-00805f9b34fb"


async def prepare_ble_device(client):
    address = client.address
    logger.info(f"Connected {address}: {client.is_connected}")
    await client.write_gatt_char(IMU_DATA_ENABLE_UUID, bytearray([0x57, 0x2d, 0x08, 0x00, 0xc8, 0x01, 0x2c, 0x00, 0x10, 0x00, 0x20]))
    logger.info("Configured for 100Hz")

    await client.disconnect()
    await asyncio.sleep(3)
    await client.connect()
    await client.write_gatt_char(IMU_DATA_ENABLE_UUID, bytearray([0x53, 0x67, 0x02, 0x01, 0x64]))
    logger.info("Enabled stream of 100Hz")


async def run_ble_client(client, char_uuid: str, queue: asyncio.Queue):
    async def callback_handler(sender, data):
        await queue.put((time.time_ns(), data))

    try:
        address = client.address
        logger.info(f"Connected {address}: {client.is_connected}")

        await client.start_notify(char_uuid, callback_handler)
        await asyncio.sleep(3.0)
        await client.stop_notify(char_uuid)
        # Send an "exit command to the consumer"
        await queue.put((time.time_ns(), None))
    except Exception as e:
        print(e)


async def run_queue_consumer(queue: asyncio.Queue, address: str):
    sample_rate_histogram = {}
    while True:
        # Use await asyncio.wait_for(queue.get(), timeout=1.0) if you want a timeout for getting data.
        epoch, data = await queue.get()
        if data is None:
            logger.info(
                f"Got message from client about disconnection of {address}. Exiting consumer loop..."
            )
            for s, sr in sample_rate_histogram.items():
                logger.info(f"{s}s: {sr}Hz")
            scanned_sr = list(sample_rate_histogram.values())[1:-1]
            if len(scanned_sr) > 0:
                logger.info(
                    f"{address} - Avg.: {sum(scanned_sr)/len(scanned_sr)}")
            else:
                logger.info(
                    f"{address} - Avg.: {scanned_sr}")

            logger.info("*"*10)

            break
        else:
            k = str(int(epoch/1000))
            if k in sample_rate_histogram:
                sample_rate_histogram[k] = sample_rate_histogram[k] + 1
            else:
                sample_rate_histogram[k] = 1
            logger.info(
                f"Received callback data via async queue at {epoch}: {data}")


async def main(address1: str, address2: str, char_uuid: str):
    # Define buffer
    queue1 = asyncio.Queue()
    # queue2 = asyncio.Queue()

    # Definde clients
    client1 = BleakClient(address1)
    # client2 = BleakClient(address2)

    # Connect to them
    await client1.connect()
    # await client2.connect()

    # Set them up
    await prepare_ble_device(client1)
    # await prepare_ble_device(client2)

    client_task1 = run_ble_client(client1, char_uuid, queue1)
    consumer_task1 = run_queue_consumer(queue1, client1.address)
    # client_task2 = run_ble_client(client2, char_uuid, queue2)
    # consumer_task2 = run_queue_consumer(queue2, client2.address)
    start = time.time()
    await asyncio.gather(client_task1, consumer_task1)
    # await asyncio.gather(client_task1, consumer_task1, client_task2, consumer_task2)
    end = time.time()

    await client1.disconnect()
    # await client2.disconnect()

    logger.info(f"Main method done. Took: {end - start}s")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(
        main(ADDRESS1, ADDRESS2, IMU_DATA_UUID)
    )
