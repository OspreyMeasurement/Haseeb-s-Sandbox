
import logging
from IPX import IPXSerialCommunicator
import time




# setup logging basi
logging.basicConfig(level=logging.DEBUG)


with IPXSerialCommunicator(port='COM5', baudrate=9600) as communicator:
    s = communicator._send_and_receive_listen(command = "op bus 0 power_out 0\n")

    time.sleep(10)
    communicator._send_and_receive_listen(command = "op bus 3733287496 ls\n")
    communicator._send_and_receive_listen(command = "op bus 6212786302 ls\n")
    communicator._send_and_receive_listen(command = "op bus 1460633827 ls\n")
    # s = s.decode('utf-8')
    # uid = int(s.split(":", 1)[0].strip())
    time.sleep(8)

# print(uid)


