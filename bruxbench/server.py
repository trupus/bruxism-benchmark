import asyncio
import json
import logging
import websockets
import os
import datetime
import glob
import numpy as np

logging.basicConfig()

CONNECTIONS = set()
DIR_TO_STREAM = None


def get_dirs():
    return json.dumps({"dirs": next(os.walk('./out'))[1]})


def start_stream(dir_to_stream):
    global DIR_TO_STREAM
    DIR_TO_STREAM = dir_to_stream

    list_of_files = glob.glob(f"./out/{DIR_TO_STREAM}/*")
    headers = {
        f"{file_path.split('/')[-1].split('.')[0]}": next(open(file_path, 'r')).replace('\n', '').split(',') for file_path in list_of_files
    }
    return json.dumps({"success": {"message": f"Starting streaming {dir_to_stream}", "headers": headers}})


def stop_stream():
    global DIR_TO_STREAM
    DIR_TO_STREAM = None
    return json.dumps({"success": {"message": "Stoping streaming"}})


def error_event(msg):
    return json.dumps({"error": {"message": msg}})


async def stream(limit):
    while True:
        if DIR_TO_STREAM != None:
            list_of_files = glob.glob(f"./out/{DIR_TO_STREAM}/*")

            with open(list_of_files[0], 'r') as f:
                lines = f.readlines()

            data = []
            if len(lines) < limit + 1:
                data = lines[1:]
            else:
                data = lines[-limit:]
            payload = {
                f"{file_path.split('/')[-1].split('.')[0]}": [d.replace('\n', '').split(',') for d in data] for file_path in list_of_files
            }

            message = json.dumps(payload)
            websockets.broadcast(CONNECTIONS, message)

        # 60Hz polling rate
        # await asyncio.sleep(0.0166)
        await asyncio.sleep(1)


async def counter(websocket):
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
    finally:
        # Unregister user
        CONNECTIONS.remove(websocket)


async def main():
    async with websockets.serve(counter, "0", 5678):
        await stream(1)  # run forever

if __name__ == "__main__":
    asyncio.run(main())
