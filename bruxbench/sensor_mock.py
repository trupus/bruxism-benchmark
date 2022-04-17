import asyncio
import time
import logging
import csv
import os

logger = logging.getLogger(__name__)

storage = []


def now():
    return int(time.time_ns()/1000000)


class Producer:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.finished_execution = asyncio.Event()

    def produce(self, data):
        self.queue.put_nowait(data)

    def stop_producer(self):
        self.finished_execution.set()


class Consumer:
    def __init__(self, dir: str, filename: str, queue: asyncio.Queue, finished_execution: asyncio.Event, csv_headers: list):
        self.dir = dir
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

        def async_write(item):
            writer.writerow(list(item.values()))

        while not self.finished_execution.is_set():
            # wait for an item from the producer
            item = await self.queue.get()

            # Print for debug
            print(item)
            # await loop.run_in_executor(None, async_write, item)
            storage.append(item)
            self.queue.task_done()

        f.close()


class Sensor:
    """Interface to ease the data collection"""

    def __init__(self, name: str):
        self.name = name
        self.producer = Producer()
        self.consumer = Consumer(dir="p1xyz", filename=f"{self.name}.csv", queue=self.producer.queue,
                                 finished_execution=self.producer.finished_execution, csv_headers=["dt"])

    async def read_data(self) -> dict:
        """Should return a dict maping sensor readings with their values:
            {
                ax: 42,
                ay: 42,
                az: 137,
                gx: 0.8
                ...
            }
        """
        while not self.producer.finished_execution.is_set():
            # Simulate N-Hz sample rate
            await asyncio.sleep(0.01)

            data = {
                "dt": now()
            }
            self.producer.produce(data=data)


async def time_bomb(time_s, producer: Producer):
    await asyncio.sleep(time_s)
    producer.stop_producer()


async def main():
    sensor1 = Sensor(name="sensor1")
    client_task = sensor1.read_data()
    consumer_task = sensor1.consumer.consume()
    time_bomb_task = time_bomb(3, sensor1.producer)
    await asyncio.gather(client_task, consumer_task, time_bomb_task)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
