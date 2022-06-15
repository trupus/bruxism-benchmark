from sys import byteorder
import serial
import ast
import time

MAX_PAYLOAD_LEN = 10

if __name__ == '__main__':
    ser = serial.Serial('/dev/ttyACM0', baudrate=115200,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS, timeout=1)
    ser.reset_input_buffer()

    line_buffer = []
    file_buffer = {}
    reading_payload_sync1 = False
    reading_payload_sync2 = False
    try:
        key = None
        last_packet = None
        while True:
            if ser.in_waiting > 0:
                char = ser.read()
                char_hex = hex(int.from_bytes(char, byteorder="big"))
                char_hex = int(char_hex, 16)
                # print(line_buffer)

                if len(line_buffer) == 0:
                    if char_hex == 0xa5:
                        key = int(time.time())
                        reading_payload_sync1 = True
                        # print("1sync")
                        continue
                    if reading_payload_sync1 and char_hex == 0x5a:
                        # print("2sync")
                        reading_payload_sync2 = True
                        continue

                if reading_payload_sync1 and reading_payload_sync2 and len(line_buffer) < MAX_PAYLOAD_LEN:
                    # print("append")
                    line_buffer.append(char_hex)
                    continue

                if len(line_buffer) == MAX_PAYLOAD_LEN and char_hex == 0x01:
                    if key in file_buffer:
                        file_buffer[key] = file_buffer[key] + 1
                    else:
                        file_buffer[key] = 1
                    line_buffer = []
                    reading_payload_sync1 = False
                    reading_payload_sync2 = False
                else:
                    line_buffer = []
                    reading_payload_sync1 = False
                    reading_payload_sync2 = False
    except KeyboardInterrupt as e:
        values_list = list(file_buffer.values())
        values_list = values_list[3:-1]
        print(values_list)
        if len(values_list) > 0:
            print(f"Avg sample rate: {sum(values_list)/len(values_list)}Hz")

        # [pkt, ch1, ch2, ch3, ch4] =
        # print(f"{time.time() * 1000} {line}")
