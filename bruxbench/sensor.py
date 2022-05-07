import serial
from time import time_ns
from logging import getLogger
from typing import List
from asyncio import sleep
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from reactor import Producer, Consumer
from busio import I2C
from board import SCL, SDA
from adafruit_bno055 import BNO055_I2C
from adafruit_tca9548a import TCA9548A
from grovepi import analogRead, pinMode

logger = getLogger("sensor")


def now_ms():
    """Helper function to get the POSIX time in ms for the current moment
    """
    return time_ns()


class Sensor:
    """Interface to ease the data collection"""

    def __init__(self, name: str, sample_rate_s: float = 1, csv_headers: List[str] = ["dt", "column0"]):
        self.name = name
        self.sample_rate_s = sample_rate_s
        self.producer = Producer()
        self.consumer = Consumer(filename=f"{self.name}.csv", queue=self.producer.queue,
                                 finished_execution=self.producer.finished_execution, csv_headers=csv_headers)

    async def _init(self):
        """Keep the bleak BLE initialisation style
        If there are methods to be awaited for the sensor initialization, add them here.
        Later you can call this method in the main loop
        """
        pass

    def get_data(self):
        """Override this method with proper pyshical sensor read
        """
        return {
            "dt": now_ms(),
            "column0": 42.0
        }

    async def start_stream(self):
        """Start streaming sensor data
        Should call `self.queue(data)`
        """
        while not self.producer.finished_execution.is_set():
            # Simulate N-Hz sample rate
            await sleep(self.sample_rate_s)

            data = self.get_data()

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
        super().__init__(name=name, csv_headers=[
            "dt",
            # "raw_data",
            'acceleration_x',
            'acceleration_y',
            'acceleration_z',
            'gyro_x',
            'gyro_y',
            'gyro_z',
        ])

    async def _init(self) -> None:
        """Setup the eSense device. If connection was succesfull,
        it will listen for IMU notifications
        """
        self.device = await self._find_device()
        if self.device:
            # Connect
            self.client = BleakClient(self.device)
            await self.client.connect()
            logger.info(
                f"Connected {self.client.address}: {self.client.is_connected}")

            # Configure
            await self.client.write_gatt_char(self.IMU_ENABLE_UUID, bytearray([0x57, 0x2d, 0x08, 0x00, 0xc8, 0x01, 0x2c, 0x00, 0x10, 0x00, 0x20]))
            logger.info(f"Configured for 100Hz {self.client.address}")
            logger.info(f"Disconnecting {self.client.address}")
            await self.client.disconnect()
            logger.info(f"Sleeping.. {self.client.address}")
            await sleep(3)
            await self.client.connect()
            logger.info(
                f"Reconnected {self.client.address}: {self.client.is_connected}")

            # Config check
            await self._check_scale_range()

            # Prepare streaming
            await self.client.write_gatt_char(
                self.IMU_ENABLE_UUID,
                self._enable_imu_payload()
            )
            logger.info(
                f"Enabled stream of {self.sample_rate}Hz {self.client.address}")
        else:
            logger.info(f"{self.ble_device_name} not found!")
            # Kill the producer if device not available!
            self.producer.stop_producer()

    async def _check_scale_range(self) -> None:
        """The data would make 0 sens if wrong scaling factors will be used
        """
        scale_range = await self.client.read_gatt_char(self.IMU_SCALE_RANGE_UUID)
        # assert for default imu scale ranges
        assert (scale_range[3], scale_range[4], scale_range[5],
                scale_range[6]) == (0x06, 0x08, 0x08, 0x06)

    async def start_stream(self) -> None:
        """Start streaming sensor data
        `self.queue(data)` is being passed as a callback
        """
        if self.client == None:
            return

        if self.client.is_connected:
            logger.info(f"Starting streaming.. {self.client.address}")
            await self._start_notifications()

    def _decode(self, v: bytearray) -> List[List[float]]:
        """Transform raw data into readable accelerometer and gyroscope data
        The resulting units are m/s^2 and deg/s respectively
        The axis for acc and gyro are in the order `x, y, z`
        """
        def _from_bytes(bytes_pair):
            return int.from_bytes(bytes_pair, 'big', signed=True)

        g = [_from_bytes(v[4:6]), _from_bytes(v[6:8]), _from_bytes(v[8:10])]
        a = [_from_bytes(v[10:12]), _from_bytes(
            v[12:14]), _from_bytes(v[14:16])]

        a = [ai / 8192 for ai in a]
        g = [gi / 65.5 for gi in g]

        return a, g

    async def _queue(self, _, raw_data) -> None:
        """Wrapper to comply with the Bleak BLE callback format
        """
        [[ax, ay, az], [gx, gy, gz]] = self._decode(raw_data)
        data = {
            "dt": now_ms(),
            # "raw_data": raw_data,
            'acceleration_x': ax,
            'acceleration_y': ay,
            'acceleration_z': az,
            'gyro_x': gx,
            'gyro_y': gy,
            'gyro_z': gz,
        }
        await self.queue(data)

    async def _start_notifications(self) -> None:
        """Start listen to notifications"""
        await self.client.start_notify(self.IMU_DATA_UUID, self._queue)

        while not self.producer.finished_execution.is_set():
            # Check every 10ms if stream was stopped
            await sleep(0.01)

        await self.client.stop_notify(self.IMU_DATA_UUID)
        logger.info(f"Stream stoped {self.client.address}")
        await self.client.disconnect()
        logger.info(f"Disconnected {self.client.address}")

    async def _find_device(self) -> BLEDevice:
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

    def _imu_payload(self, enable: bool) -> bytearray:
        """Refer to eSense BLE specifications.
        Helper function to build the required payload
        """
        cmd_head = 0x53
        data_size = 0x02
        data_enable = int(enable)
        checksum = (data_size + data_enable + self.sample_rate) & 0xFF

        return bytearray([cmd_head, checksum, data_size, data_enable, self.sample_rate])


class IMU_BNO055(Sensor):
    """Abstract API to read data from BNO055"""

    # I2C singleton interface
    i2c = I2C(SCL, SDA)
    tca = TCA9548A(i2c)

    def __init__(self, name: str, i2c_multiplexer_index: int):
        self.sensor = BNO055_I2C(self.tca[i2c_multiplexer_index])
        super().__init__(name=name, sample_rate_s=0.01, csv_headers=[
            'dt',
            'acceleration_x',
            'acceleration_y',
            'acceleration_z',
            'magnetic_x',
            'magnetic_y',
            'magnetic_z',
            'gyro_x',
            'gyro_y',
            'gyro_z',
            'euler_x',
            'euler_y',
            'euler_z',
            'quaternion_a',
            'quaternion_b',
            'quaternion_c',
            'quaternion_d',
            'linear_acceleration_x',
            'linear_acceleration_y',
            'linear_acceleration_z',
            'gravity_x',
            'gravity_y',
            'gravity_z'
        ])

    async def get_data(self):
        return {
            'dt': now_ms(),
            'acceleration_x': self.sensor.acceleration[0],
            'acceleration_y': self.sensor.acceleration[1],
            'acceleration_z': self.sensor.acceleration[2],
            'magnetic_x': self.sensor.magnetic[0],
            'magnetic_y': self.sensor.magnetic[1],
            'magnetic_z': self.sensor.magnetic[2],
            'gyro_x': self.sensor.gyro[0],
            'gyro_y': self.sensor.gyro[1],
            'gyro_z': self.sensor.gyro[2],
            'euler_x': self.sensor.euler[0],
            'euler_y': self.sensor.euler[1],
            'euler_z': self.sensor.euler[2],
            'quaternion_a': self.sensor.quaternion[0],
            'quaternion_b': self.sensor.quaternion[1],
            'quaternion_c': self.sensor.quaternion[2],
            'quaternion_d': self.sensor.quaternion[3],
            'linear_acceleration_x': self.sensor.linear_acceleration[0],
            'linear_acceleration_y': self.sensor.linear_acceleration[1],
            'linear_acceleration_z': self.sensor.linear_acceleration[2],
            'gravity_x': self.sensor.gravity[0],
            'gravity_y': self.sensor.gravity[1],
            'gravity_z': self.sensor.gravity[2]
        }


class GSR_Grovepi(Sensor):
    """Abstract API to read data from the Grove GSR"""

    # Maps port name to physical pin number
    PORT_TO_PIN = {
        "A0": 14
    }

    def __init__(self, name: str, port: str = "A0"):
        self.pin = self.PORT_TO_PIN[port]
        super().__init__(name=name, sample_rate_s=0.01, csv_headers=[
            'dt',
            'gsr'
        ])

    def _setup_read(self):
        """Sets the grovepi+ hat board to input mode"""

        pinMode(self.pin, "INPUT")

    def _gsr(self):
        """Reads the gsr value"""

        self._setup_read()
        return analogRead(self.pin)

    async def get_data(self):
        return {
            'dt': now_ms(),
            'gsr': self._gsr(),
        }


class EMG_Olimex_x4(Sensor):
    def __init__(self, name: str, baudrate: int = 115200):
        self.ser = serial.Serial('/dev/ttyACM0', baudrate=baudrate,
                                 parity=serial.PARITY_NONE,
                                 stopbits=serial.STOPBITS_ONE,
                                 bytesize=serial.EIGHTBITS, timeout=1)
        self.ser.reset_input_buffer()
        super().__init__(name=name, sample_rate_s=0, csv_headers=[
            'dt',
            'masseter_left',
            'masseter_right',
            'temporalis_left',
            'temporalis_right',
        ])

    async def get_data(self):
        data = self.ser.readline().decode('utf8').rstrip().split(',')
        return {
            'dt': now_ms(),
            'masseter_left': data[0],
            'masseter_right': data[1],
            'temporalis_left': data[2],
            'temporalis_right': data[3],
        }


# TODO: Audio recorder (adapt implementation from the test notebook)
