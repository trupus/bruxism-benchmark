import asyncio

from bleak import BleakClient

IMU_DATA_ENABLE_UUID = "0000ff07-0000-1000-8000-00805f9b34fb"
IMU_DATA_UUID = "0000ff08-0000-1000-8000-00805f9b34fb"

ADDRESS1 = "00:04:79:00:0D:46"
ADDRESS2 = "00:04:79:00:0C:13"


def callback(sender, data, address):
    print(address, data)


async def connect_to_device(client):
    print("connect to", client.address)
    try:
        await client.start_notify(IMU_DATA_UUID, lambda sender, data: callback(sender, data, client.address))
        await asyncio.sleep(3.0)
        await client.stop_notify(IMU_DATA_UUID)
    except Exception as e:
        print(e)

    print("disconnect from", client.address)


async def main(addresses):
    client1 = BleakClient(addresses[0])
    client2 = BleakClient(addresses[1])

    await client1.connect()
    await client1.write_gatt_char(IMU_DATA_ENABLE_UUID, bytearray([0x53, 0x35, 0x02, 0x01, 0x32]))

    await client2.connect(timeout=100)
    await client2.write_gatt_char(IMU_DATA_ENABLE_UUID, bytearray([0x53, 0x35, 0x02, 0x01, 0x32]))

    await asyncio.gather(connect_to_device(client1), connect_to_device(client2))


if __name__ == "__main__":
    asyncio.run(main([ADDRESS1, ADDRESS2]))
