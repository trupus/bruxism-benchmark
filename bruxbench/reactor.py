import csv
import os
from asyncio import Queue, Event
from datetime import datetime


class Producer:
    def __init__(self):
        self.queue = Queue()
        self.finished_execution = Event()

    async def produce(self, data):
        self.queue.put_nowait(data)

    def stop_producer(self):
        self.finished_execution.set()


class Consumer:
    def __init__(self, filename: str, queue: Queue, finished_execution: Event, csv_headers: list):
        self.filename = filename
        self.queue = queue
        self.finished_execution = finished_execution
        self.csv_headers = csv_headers
        self.buffer = []

    async def consume(self):
        with open(f"{self.dir}/{self.filename}", 'a') as f:
            writer = csv.writer(f)
            while not self.finished_execution.is_set():
                # wait for an item from the producer
                item = await self.queue.get()
                # self.buffer.append(item.values())
                writer.writerow(item.values())
                self.queue.task_done()

        # with open(f"{self.dir}/{self.filename}", 'a') as f:
        #     writer = csv.writer(f)
        #     writer.writerows(self.buffer)

    def set_dir_name(self, dir):
        self.dir = f"out/{self._hash_dir_name(dir)}"
        self._init_out_file()

    def _init_out_file(self):
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        with open(f"{self.dir}/{self.filename}", 'a') as f:
            writer = csv.writer(f)
            # write the header
            writer.writerow(self.csv_headers)

    def _hash_dir_name(self, dir):
        return f"{dir}@{datetime.now().strftime('%Y_%m_%d__%H_%M_%S')}"
