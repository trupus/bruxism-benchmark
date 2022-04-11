import asyncio
from sensor import BLE_eSense
import collections  # for the buffer
import time  # to ease polling
import gevent
from gevent.event import Event
import gevent.monkey
gevent.monkey.patch_all()


def write_to_file(path, buffer, terminate_signal):
    with open(path, 'a') as out_file:  # close file automatically on exit
        while not terminate_signal.is_set() or buffer:  # go on until end is signaled
            try:
                data = buffer.pop()  # pop from RIGHT end of buffer
            except IndexError:
                time.sleep(0.5)  # wait for new data
            finally:
                out_file.write(data)  # write a chunk


def buffer_sensor_data(sensor):
    while True:
        sensor.buffer_data()


def time_bomb(seconds, terminate_signal):
    time.sleep(seconds)
    terminate_signal.set()


buffer = collections.deque()  # buffer for reading/writing
terminate_signal = Event()  # shared signal

left_esense = BLE_eSense("left_esense", "eSense-0091", buffer)
loop = asyncio.get_event_loop()
coroutine = left_esense._init()
loop.run_until_complete(coroutine)
# left_esense_init = asyncio_gevent.async_to_sync(left_esense._init())
# left_esense_init()

gevent.joinall([
    gevent.spawn(buffer_sensor_data, left_esense),
    gevent.spawn(
        write_to_file, f"{left_esense.name}.txt", buffer, terminate_signal),
    gevent.spawn(time_bomb, 10, terminate_signal),
])
