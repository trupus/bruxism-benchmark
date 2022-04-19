import asyncio
import logging
from typing import List
from sensor import Sensor

logger = logging.getLogger(__name__)


class Bruxi:
    def __init__(self, dir_name: str, sensors: List[Sensor], halt_event: asyncio.Event) -> None:
        self.sensors = []
        self.dir_name = dir_name
        self.halt_event = halt_event
        self.add_sensors(sensors)

    def add_sensor(self, sensor: Sensor):
        sensor.consumer.set_dir_name(self.dir_name)
        self.sensors.append(sensor)

    def add_sensors(self, sensors: List[Sensor]):
        for s in sensors:
            self.add_sensor(s)

    async def initialize_sensors(self) -> None:
        for s in self.sensors:
            await s._init()

    async def halt_event_listener(self) -> None:
        while True:
            if self.halt_event.is_set():
                logger.info("Halt received! Shuting down..")
                for s in self.sensors:
                    if not s.producer.finished_execution.is_set():
                        s.producer.stop_producer()
                break
            await asyncio.sleep(10)

    def spawn_coroutines(self) -> list:
        stream_futures = [s.start_stream() for s in self.sensors]
        consumer_futures = [s.consumer.consume() for s in self.sensors]
        event_listener_futures = [self.halt_event_listener()]

        futures = stream_futures + consumer_futures + event_listener_futures
        return futures
