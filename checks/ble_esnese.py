import asyncio
import sys
from bleak import BleakClient, BleakScanner

# address = "00:04:79:00:0C:13"  # eSense-0091
MODEL_NBR_UUID = "00002a00-0000-1000-8000-00805f9b34fb"
IMU_DATA_ENABLE_UUID = "0000ff07-0000-1000-8000-00805f9b34fb"
IMU_DATA_UUID = "0000ff08-0000-1000-8000-00805f9b34fb"
BUTTON_UUID = "0000ff09-0000-1000-8000-00805f9b34fb"
IMU_OFFSET_UUID = "0000ff0d-0000-1000-8000-00805f9b34fb"


def print_data(uuid, data, offset):
    decoded = decode(data, offset)
    print(f"Acc: {decoded[0]}", end="\t")
    print(f"Gyro: {decoded[1]}")


def _from_bytes(bytes_pair):
    return int.from_bytes(bytes_pair, 'big', signed=True)


def decode(v, offset):
    g = [_from_bytes(v[4:6]) - offset[0][0], _from_bytes(v[6:8]) -
         offset[0][1], _from_bytes(v[8:10]) - offset[0][2]]
    a = [_from_bytes(v[10:12]) - offset[1][0], _from_bytes(v[12:14]) -
         offset[1][2], _from_bytes(v[14:16]) - offset[1][2]]

    a = [(ai / 8192) * 9.80665 for ai in a]
    g = [gi / 65.5 for gi in g]

    return a, g


def decode_offset(v):
    g = [_from_bytes(v[3:5]), _from_bytes(v[5:7]), _from_bytes(v[7:9])]
    a = [_from_bytes(v[9:11]), _from_bytes(v[11:13]), _from_bytes(v[13:15])]

    # return [a, g]
    return [[0, 0, 0], [0, 0, 0]]


async def on_connect(client):
    # hasServices = False
    # while not hasServices:
    #     print("Looking for services...")
    #     services = await client.get_services()
    #     hasServices = services.services != {} and services.characteristics != {}

    # imu_data = await client.read_gatt_char(IMU_DATA_UUID)
    # print("IMU Data init: {0}".format("".join(map(chr, imu_data))))

    # data = await client.read_gatt_char(BUTTON_UUID)
    # print("Data init: {0}".format("".join(map(chr, data))))

    print("Read the imu offset")
    offset_raw_bytes = await client.read_gatt_char(IMU_OFFSET_UUID)
    offset = decode_offset(offset_raw_bytes)
    print(offset)
    print("Done!")

    # print("Test the button press...")
    # await client.start_notify(BUTTON_UUID, print_data)
    # await asyncio.sleep(5.0)
    # await client.stop_notify(BUTTON_UUID)
    # print("Button test end")

    print("Enabling IMU...")
    await client.write_gatt_char(IMU_DATA_ENABLE_UUID, bytearray([0x53, 0x35, 0x02, 0x01, 0x32]))
    print("IMU enabled")

    print("Test IMU...")
    await client.start_notify(IMU_DATA_UUID, lambda source, data: print_data(source, data, offset))
    await asyncio.sleep(10.0)
    await client.stop_notify(IMU_DATA_UUID)
    print("IMU test end")

    print("Disabling IMU")
    await client.write_gatt_char(IMU_DATA_ENABLE_UUID, bytearray([0x53, 0x02, 0x02, 0x00, 0x00]))
    print("IMU disabled")


async def main():
    # Run this to add it to the bluez cache
    devices = await BleakScanner.discover()
    selected_device = None
    for device in devices:
        print(device)
        if device.name == f"eSense-{sys.argv[1]}":
            selected_device = device

    # Sometimes there are no services/ characteristics found

    client = BleakClient(selected_device)
    await client.connect(timeout=100)
    # await client.pair()

    if client.is_connected:
        model_number = await client.read_gatt_char(MODEL_NBR_UUID)
        print("Model Number: {0}".format("".join(map(chr, model_number))))

        services = {}
        while services == {}:
            services = await client.get_services()
            services = services.services
            print(f"Services: {services}")
            await asyncio.sleep(3)

        await on_connect(client)


asyncio.run(main())
