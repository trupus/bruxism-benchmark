import adafruit_bno055
import board
import grovepi
import collections
import asyncio
from bleak import BleakClient, BleakScanner
import datetime
import time


def now():
    return int(time.time_ns()/1000)


class Sensor:
    """Interface to ease the data collection"""

    def __init__(self, name: str, buffer: collections.deque):
        self.name = name
        self.buffer = buffer

    async def read_data(self) -> dict:
        """Should return a dict maping sensor readings with their values,
        with sensor name as prefix:
            {
                imu-left_ax: 42,
                imu-left_ay: 42,
                imu-left_az: 137,
                imu-left_gx: 0.8
                ...
            }
        """
        data = await self._read_data()
        # return data
        line = {f"{self.name}-{k}": v for k, v in data.items()}
        return line

    def buffer_data(self) -> dict:
        pass

    async def _read_data(self) -> dict:
        """Should return a dict maping sensor readings with their values:
            {
                ax: 42,
                ay: 42,
                az: 137,
                gx: 0.8
                ...
            }
        """
        pass


class IMU_BNO055(Sensor):
    """Abstract API to read data from BNO055"""

    # I2C singleton interface
    i2c = board.I2C()

    def __init__(self, name: str, address: hex = 0x28):
        self.sensor = adafruit_bno055.BNO055_I2C(self.i2c, address=address)
        super().__init__(name)

    async def _read_data(self):
        return {
            'temperature': self.sensor.temperature,
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
            'gravity_z': self.sensor.gravity[2],
            'dt': now()
        }


class GSR_Grovepi(Sensor):
    """Abstract API to read data from the Grove GSR"""

    # Maps port name to physical pin number
    PORT_TO_PIN = {
        "A0": 14
    }

    def __init__(self, name: str, port: str = "A0"):
        self.pin = self.PORT_TO_PIN[port]
        super().__init__(name)

    def gsr(self):
        """Reads the gsr value"""

        self._setup_read()
        return grovepi.analogRead(self.pin)

    def _setup_read(self):
        """Sets the grovepi+ hat board to input mode"""

        grovepi.pinMode(self.pin, "INPUT")

    async def _read_data(self):

        return {
            'gsr': self.gsr(),
            'dt': now()
        }


class BLE_eSense(Sensor):
    """Abstract API to read data from the eSense Earable"""
    DEVICE_NAME_UUID = "00002a00-0000-1000-8000-00805f9b34fb"
    IMU_ENABLE_UUID = "0000ff07-0000-1000-8000-00805f9b34fb"
    IMU_DATA_UUID = "0000ff08-0000-1000-8000-00805f9b34fb"

    def __init__(self, name: str, device_name: str, buffer: collections.deque, sample_rate: int = 50):
        self.device_name = device_name
        self.sample_rate = sample_rate
        self.raw_data = None
        super().__init__(name, buffer)

    async def _init(self):
        """Setup the eSense device. If connection was succesfull,
        it will listen for IMU notifications
        """
        self.device = await self._find_device()
        if (self.device):
            self.client = BleakClient(self.device)
            await self.client.connect()
            await self.client.write_gatt_char(
                self.IMU_ENABLE_UUID,
                self._enable_imu_payload()
            )
            await self._start_notifications()
        else:
            print(f"{self.device_name} not found!")

    async def _start_notifications(self):
        """Start listen to notifications"""
        await self.client.start_notify(self.IMU_DATA_UUID, self._update_raw_data)

    async def _find_device(self):
        """Find device by name in the list of discovered devices.
        If this part fails try fixes in the following order:
            1. Restart earable (long press until red, then nothing)
            2. Hard reset (put in the case, hold case button for 15-20s)
            3. Power cycle rpi (on very rare ocasions)
        """
        devices = await BleakScanner.discover()
        for device in devices:
            if device.name == self.device_name:
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

    def _update_raw_data(self, source, data):
        """IMU notifications handler"""
        self.raw_data = data

    async def _read_data(self):

        return {
            'raw_data': self.raw_data,
            'dt': now()
        }

    def buffer_data(self, source, data):
        self.buffer.appendleft(data)
