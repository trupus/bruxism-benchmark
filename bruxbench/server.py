import asyncio
import json
import logging
import websockets
import os
import glob
import itertools
import io

logging.basicConfig()


class ReverseFile(io.IOBase):
    def __init__(self, filename, headers=1):
        self.fp = open(filename)
        self.headers = headers
        self.reverse = self.reversed_lines()
        self.end_position = -1
        self.current_position = -1

    def readline(self, size=-1):
        if self.headers > 0:
            self.headers -= 1
            raw = self.fp.readline(size)
            self.end_position = self.fp.tell()
            return raw

        raw = next(self.reverse)
        if self.current_position > self.end_position:
            return raw

        raise StopIteration

    def reversed_lines(self):
        """Generate the lines of file in reverse order.
        """
        part = ''
        for block in self.reversed_blocks():
            block = block + part
            block = block.split('\n')
            block.reverse()
            part = block.pop()
            if block[0] == '':
                block.pop(0)

            for line in block:
                yield line + '\n'

        if part:
            yield part

    def reversed_blocks(self, blocksize=0xFFFF):
        "Generate blocks of file's contents in reverse order."
        file = self.fp
        file.seek(0, os.SEEK_END)
        here = file.tell()
        while 0 < here:
            delta = min(blocksize, here)
            here -= delta
            file.seek(here, os.SEEK_SET)
            self.current_position = file.tell()
            yield file.read(delta)


CONNECTIONS = set()
DIR_TO_STREAM = None
HEADERS_MAP = {}
LINE_COLORS = [
    "#3366CC",
    "#DC3912",
    "#FF9900",
    "#109618",
    "#990099",
    "#3B3EAC",
    "#0099C6",
    "#DD4477",
    "#66AA00",
    "#B82E2E",
    "#316395",
    "#994499",
    "#22AA99",
    "#AAAA11",
    "#6633CC",
    "#E67300",
    "#8B0707",
    "#329262",
    "#5574A6",
    "#3B3EAC"
]
BACKGROUND_COLORS = [line_color + "99" for line_color in LINE_COLORS]


def get_dirs():
    return json.dumps({"type": "dirs", "dirs": next(os.walk('./out'))[1]})


def start_stream(dir_to_stream):
    global DIR_TO_STREAM
    global HEADERS_MAP
    DIR_TO_STREAM = dir_to_stream

    list_of_files = glob.glob(f"./out/{DIR_TO_STREAM}/*")
    HEADERS_MAP = {file_path.split('/')[-1].split('.')[0]: next(open(
        file_path, 'r')).replace('\n', '').split(',') for file_path in list_of_files}

    return json.dumps({"success": {"message": f"Starting streaming {dir_to_stream}"}})


def stop_stream():
    global DIR_TO_STREAM
    DIR_TO_STREAM = None
    return json.dumps({"success": {"message": "Stoping streaming"}})


def error_event(msg):
    return json.dumps({"error": {"message": msg}})


async def stream(limit, halt_event):
    while not halt_event.is_set():
        if DIR_TO_STREAM != None:
            list_of_files = glob.glob(f"./out/{DIR_TO_STREAM}/*")

            if len(list_of_files) > 0:
                payload = {}
                for sensor_file in list_of_files:
                    sensor_file_hash = sensor_file.split('/')[-1].split('.')[0]
                    chart_data = {
                        'labels': [],
                        'datasets': []
                    }

                    rev = ReverseFile(sensor_file)
                    lines = list(itertools.islice(rev, limit))[::-1]
                    if len(lines) == 0:
                        continue

                    rows = [row.rstrip('\n').split(',') for row in lines]
                    if 'dt' == rows[0][0]:
                        rows = rows[1:]

                    # X axis
                    chart_data['labels'] = [row[0] for row in rows]

                    # line data per column
                    try:
                        chart_data['datasets'] = [
                            {
                                'label': HEADERS_MAP[sensor_file_hash][col_i],
                                'data': [row[col_i] for row in rows],
                                'backgroundColor': BACKGROUND_COLORS[col_i - 1],
                                'borderColor': LINE_COLORS[col_i - 1]
                            } for col_i in range(1, len(HEADERS_MAP[sensor_file_hash]))
                        ]
                    except Exception as e:
                        logging.error(e)
                        chart_data['datasets'] = []

                    payload[sensor_file_hash] = chart_data

                message = json.dumps(
                    {"success": {"message": "Streaming.."}, "payload": payload, "type": "payload"})
                websockets.broadcast(CONNECTIONS, message)

            else:
                websockets.broadcast(CONNECTIONS, stop_stream())

        # 60Hz polling rate
        await asyncio.sleep(0.0166)
        # await asyncio.sleep(1)


async def event_listener(websocket):
    global CONNECTIONS
    try:
        # Register user
        CONNECTIONS.add(websocket)

        websockets.broadcast(CONNECTIONS, get_dirs())

        # Manage state changes
        async for message in websocket:
            event = json.loads(message)
            if event["action"] == "dirs":
                websockets.broadcast(CONNECTIONS, get_dirs())
            elif event["action"] == "stream":
                dir_to_stream = event["dir"]
                websockets.broadcast(CONNECTIONS, start_stream(dir_to_stream))
            elif event["action"] == "stop":
                websockets.broadcast(CONNECTIONS, stop_stream())
            else:
                error_msg = f"unsupported event: {event}"
                websockets.broadcast(CONNECTIONS, error_event(error_msg))
                logging.error(error_msg)

        await websocket.wait_closed()
    except Exception as e:
        logging.error(e)
    finally:
        # Unregister user
        CONNECTIONS.remove(websocket)


async def main(halt_event):
    async with websockets.serve(event_listener, "0", 1337):
        await stream(limit=100, halt_event=halt_event)

if __name__ == "__main__":
    halt_event = asyncio.Event()

    try:
        asyncio.run(main(halt_event=halt_event))
    except KeyboardInterrupt:
        logging.warning("Halt received! Shuting down..")
        halt_event.set()
