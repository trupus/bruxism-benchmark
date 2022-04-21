import serial
import ast
import time

MAX_PAYLOAD_LEN = 10

if __name__ == '__main__':
    ser = serial.Serial('/dev/ttyACM0', baudrate=57600,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS, timeout=1)
    ser.reset_input_buffer()

    line_buffer = []
    reading_payload_sync1 = False
    reading_payload_sync2 = False
    while True:
        if ser.in_waiting > 0:
            char = ser.read()
            char_hex = hex(int.from_bytes(char, byteorder='little'))

            # print(line_buffer)

            if len(line_buffer) == 0:
                if char_hex == hex(0xa5):
                    reading_payload_sync1 = True
                    # print("1sync")
                    continue
                if reading_payload_sync1 and char_hex == hex(0x5a):
                    # print("2sync")
                    reading_payload_sync2 = True
                    continue

            if reading_payload_sync1 and reading_payload_sync2 and len(line_buffer) < MAX_PAYLOAD_LEN:
                # print("append")
                line_buffer.append(char_hex)
                continue

            if len(line_buffer) == MAX_PAYLOAD_LEN and char_hex == hex(0x01):
                with open("sample.txt", "a") as f:
                    f.write(f"{time.time()}\n")
                line_buffer = []
                reading_payload_sync1 = False
                reading_payload_sync2 = False
            else:
                line_buffer = []
                reading_payload_sync1 = False
                reading_payload_sync2 = False

        # [pkt, ch1, ch2, ch3, ch4] =
        # print(f"{time.time() * 1000} {line}")
