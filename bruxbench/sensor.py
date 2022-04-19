import asyncio
import time
from datetime import datetime
import logging
import csv
import os
from typing import List
from bleak import BleakClient, BleakScanner

logger = logging.getLogger(__name__)


def now_ms():
    return time.time_ns()


class Producer:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.finished_execution = asyncio.Event()

    async def produce(self, data):
        await self.queue.put(data)

    def stop_producer(self):
        self.finished_execution.set()


class Consumer:
    def __init__(self, filename: str, queue: asyncio.Queue, finished_execution: asyncio.Event, csv_headers: list):
        self.filename = filename
        self.queue = queue
        self.finished_execution = finished_execution
        self.csv_headers = csv_headers

    async def consume(self):
        loop = asyncio.get_running_loop()
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        f = open(f"{self.dir}/{self.filename}", 'a')
        writer = csv.writer(f)
        # write the header
        writer.writerow(self.csv_headers)
        f.close()

        while not self.finished_execution.is_set():
            f = open(f"{self.dir}/{self.filename}", 'a')
            writer = csv.writer(f)
            # wait for an item from the producer
            item = await self.queue.get()

            # Print for debug
            # print(item)
            writer.writerow(item.values())
            self.queue.task_done()

            f.close()

    def set_dir_name(self, dir):
        self.dir = self._hash_dir_name(dir)

    def _hash_dir_name(self, dir):
        return f"{dir}@{datetime.now().strftime('%Y_%m_%d__%H_%M_%S')}"


class Sensor:
    """Interface to ease the data collection"""

    def __init__(self, name: str):
        self.name = name
        self.producer = Producer()
        self.consumer = Consumer(filename=f"{self.name}.csv", queue=self.producer.queue,
                                 finished_execution=self.producer.finished_execution, csv_headers=["dt"])

    async def _init(self):
        """Keep the bleak BLE initialisation style
        If there are methods to be awaited for the sensor initialization, add them here.
        Later you can call this method in the main loop
        """
        pass

    async def start_stream(self):
        """Start streaming sensor data
        Should call `self.queue(data)`
        """
        while not self.producer.finished_execution.is_set():
            # Simulate N-Hz sample rate
            await asyncio.sleep(1)

            data = {
                "dt": now_ms()
            }

            await self.queue(data)

    async def queue(self, data):
        """Abstraction to produce data with the producer
        """
        await self.producer.produce(data=data)


class BLE_eSense(Sensor):
    """Abstract API to read data from the eSense Earable"""
    IMU_ENABLE_UUID = "0000ff07-0000-1000-8000-00805f9b34fb"
    IMU_DATA_UUID = "0000ff08-0000-1000-8000-00805f9b34fb"
    IMU_SCALE_RANGE_UUID = "0000ff0e-0000-1000-8000-00805f9b34fb"

    def __init__(self, name: str, ble_device_name: str, sample_rate: int = 100):
        self.ble_device_name = ble_device_name
        self.sample_rate = sample_rate
        self.client = None
        super().__init__(name)

    async def _init(self):
        """Setup the eSense device. If connection was succesfull,
        it will listen for IMU notifications
        """
        self.device = await self._find_device()
        if self.device:
            self.client = BleakClient(self.device)
            await self.client.connect()
            logger.info(
                f"Connected {self.client.address}: {self.client.is_connected}")
            await self.client.write_gatt_char(self.IMU_ENABLE_UUID, bytearray([0x57, 0x2d, 0x08, 0x00, 0xc8, 0x01, 0x2c, 0x00, 0x10, 0x00, 0x20]))
            logger.info(f"Configured for 100Hz {self.client.address}")
            logger.info(f"Disconnecting {self.client.address}")
            await self.client.disconnect()
            logger.info(f"Sleeping.. {self.client.address}")
            await asyncio.sleep(3)
            await self.client.connect()
            logger.info(
                f"Reconnected {self.client.address}: {self.client.is_connected}")
            await self._check_scale_range()

            await self.client.write_gatt_char(
                self.IMU_ENABLE_UUID,
                self._enable_imu_payload()
            )
            logger.info(f"Enabled stream of 100Hz {self.client.address}")
        else:
            logger.info(f"{self.ble_device_name} not found!")
            # Kill the producer!
            self.producer.stop_producer()

    async def _check_scale_range(self):
        scale_range = await self.client.read_gatt_char(self.IMU_SCALE_RANGE_UUID)
        assert (scale_range[3], scale_range[4], scale_range[5],
                scale_range[6]) == (0x06, 0x08, 0x08, 0x06)

    async def start_stream(self):
        """Start streaming sensor data
        `self.queue(data)` is being passed as a callback
        """
        if self.client == None:
            return

        if self.client.is_connected:
            logger.info(f"Starting streaming.. {self.client.address}")
            await self._start_notifications()

    def _decode(self, v: bytearray):
        g = [gx, gy, gz] = [v[4]*256+v[5], v[6]*256+v[7], v[8]*256+v[9]]
        a = [ax, ay, az] = [v[10]*256+v[11], v[12]*256+v[13], v[14]*256+v[15]]

        a = [(ai / 8192) * 9.80665 for ai in a]
        g = [gi / 65.5 for gi in g]

        return a, g

    async def _queue(self, _, raw_data):
        """Wrapper to comply with the Bleak BLE callback format
        """
        [[ax, ay, az], [gx, gy, gz]] = self._decode(raw_data)
        data = {
            "dt": now_ms(),
            "raw_data": raw_data,
            'acceleration_x': ax,
            'acceleration_y': ay,
            'acceleration_z': az,
            'gyro_x': gx,
            'gyro_y': gy,
            'gyro_z': gz,
        }
        await self.queue(data)

    async def _start_notifications(self):
        """Start listen to notifications"""
        await self.client.start_notify(self.IMU_DATA_UUID, self._queue)

        while not self.producer.finished_execution.is_set():
            # Check every 1ms if stream was stopped
            await asyncio.sleep(0.01)

        await self.client.stop_notify(self.IMU_DATA_UUID)
        logger.info(f"Stream stoped {self.client.address}")
        await self.client.disconnect()
        logger.info(f"Disconnected {self.client.address}")

    async def _find_device(self):
        """Find device by name in the list of discovered devices.
        If this part fails try fixes in the following order:
            1. Restart earable (long press until red, then nothing)
            2. Hard reset (put in the case, hold case button for 15-20s)
            3. Power cycle rpi (on very rare ocasions)
        """
        devices = await BleakScanner.discover()
        for device in devices:
            if device.name == self.ble_device_name:
                return device

    def _enable_imu_payload(self) -> bytearray:
        """Refer to eSense BLE specifications.
        Flips the bit, that enables IMU data broadcast,
        and also sets the sample rate
        """
        return self._imu_payload(True)

    def _imu_payload(self, enable: bool):
        """Refer to eSense BLE specifications.
        Helper function to build the required payload
        """
        cmd_head = 0x53
        data_size = 0x02
        data_enable = int(enable)
        checksum = (data_size + data_enable + self.sample_rate) & 0xFF

        return bytearray([cmd_head, checksum, data_size, data_enable, self.sample_rate])


async def time_bomb(time_s: float, sensors: List[Sensor]):
    """Will activate the stop signal for the producer after `time_s` seconds
    """
    await asyncio.sleep(time_s)
    for s in sensors:
        if not s.producer.finished_execution.is_set():
            s.producer.stop_producer()


async def halt_event_listener(event: asyncio.Event, sensors: List[Sensor]):
    while True:
        if event.is_set():
            for s in sensors:
                if not s.producer.finished_execution.is_set():
                    s.producer.stop_producer()
            break
        await asyncio.sleep(10)


async def main(halt_event: asyncio.Event):
    sensors = [
        Sensor(name="s1"),
        # BLE_eSense(name="ble1", ble_device_name="eSense-0091",
        #            dir_name=dir_name),
        # BLE_eSense(name="ble2", ble_device_name="eSense-0398",
        #            dir_name=dir_name),
    ]

    for s in sensors:
        await s._init()

    halt_event_listener_task = halt_event_listener(halt_event, sensors)

    await asyncio.gather(*[s.start_stream() for s in sensors], *[s.consumer.consume() for s in sensors], halt_event_listener_task)


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(message)s',
                        datefmt='%d.%m.%Y %H:%M:%S', level=logging.INFO)
    dir_name = "am982512"

    halt_event = asyncio.Event()
    try:
        asyncio.run(main(dir_name, halt_event))
    except KeyboardInterrupt:
        logger.info("Halt received! Shuting down..")
        halt_event.set()
