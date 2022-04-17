import asyncio
from bleak import BleakClient, BleakScanner

# address = "00:04:79:00:0C:13"  # eSense-0091
MODEL_NBR_UUID = "00002a00-0000-1000-8000-00805f9b34fb"
IMU_DATA_ENABLE_UUID = "0000ff07-0000-1000-8000-00805f9b34fb"
IMU_DATA_UUID = "0000ff08-0000-1000-8000-00805f9b34fb"
BUTTON_UUID = "0000ff09-0000-1000-8000-00805f9b34fb"


def print_data(uuid, data):
    print(f"Data: {data}")


async def main():
    # Run this to add it to the bluez cache
    devices = await BleakScanner.discover()
    selected_device = None
    for device in devices:
        print(device)
        if device.name == "eSense-0398":
            selected_device = device.address

    # Sometimes there are no services/ characteristics found

    client = BleakClient(selected_device)
    await client.connect(timeout=100)
    # await client.pair()

    if client.is_connected:

        # hasServices = False
        # while not hasServices:
        #     print("Looking for services...")
        #     services = await client.get_services()
        #     hasServices = services.services != {} and services.characteristics != {}

        model_number = await client.read_gatt_char(MODEL_NBR_UUID)
        print("Model Number: {0}".format("".join(map(chr, model_number))))

        services = await client.get_services()
        print(f"Services: {services.services}")

        # imu_data = await client.read_gatt_char(IMU_DATA_UUID)
        # print("IMU Data init: {0}".format("".join(map(chr, imu_data))))

        # data = await client.read_gatt_char(BUTTON_UUID)
        # print("Data init: {0}".format("".join(map(chr, data))))

        print("Test the button press...")
        await client.start_notify(BUTTON_UUID, print_data)
        await asyncio.sleep(5.0)
        await client.stop_notify(BUTTON_UUID)
        print("Button test end")

        print("Enabling IMU...")
        await client.write_gatt_char(IMU_DATA_ENABLE_UUID, bytearray([0x53, 0x35, 0x02, 0x01, 0x32]))
        print("IMU enabled")

        print("Test IMU...")
        await client.start_notify(IMU_DATA_UUID, print_data)
        await asyncio.sleep(10.0)
        await client.stop_notify(IMU_DATA_UUID)
        print("IMU test end")

        print("Disabling IMU")
        await client.write_gatt_char(IMU_DATA_ENABLE_UUID, bytearray([0x53, 0x02, 0x02, 0x00, 0x00]))
        print("IMU disabled")


asyncio.run(main())
