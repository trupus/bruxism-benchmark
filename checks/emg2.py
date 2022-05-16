import serial
import time

MAX_PAYLOAD_LEN = 10

if __name__ == '__main__':
    ser = serial.Serial('/dev/ttyUSB0', baudrate=500000,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS, timeout=1)
    ser.reset_input_buffer()

    line_buffer = []
    file_buffer = {}
    try:
        key = None
        last_packet = None
        while True:
            line = ser.readline().decode('utf8').rstrip()
            key = int(time.time())
            if key in file_buffer:
                file_buffer[key] = file_buffer[key] + 1
            else:
                file_buffer[key] = 1
            # print(line)
    except KeyboardInterrupt as e:
        values_list = list(file_buffer.values())
        values_list = values_list[3:-1]
        print(values_list)
        if len(values_list) > 0:
            print(f"Avg sample rate: {sum(values_list)/len(values_list)}Hz")
