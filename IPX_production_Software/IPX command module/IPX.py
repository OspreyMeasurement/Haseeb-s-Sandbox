import serial
import logging
import time
from IPX_Config import IPXCommands

# com port 5 for testing

# print(IPXConfig.Commands.list_uids)

""" This file is for handling all serial communication with the IPX devices

"""

class IPXSerialCommunicator:
    """ Class for handling serial communication with IPX devices """
    def __init__(self, port: str, baudrate: int, timeout: int):
        """ Initialize the serial communicator , with serial settings
        Arguments:
            port {str} -- COM port to use
            baudrate {int} -- Baud rate for serial communication
            timeout {int} -- Timeout for serial communication in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None

    def send_and_receive(self, command:str) -> str:
        """ Sends command to IPX device, and receives response"""
        if not self.connection:
            print("ERROR: Not connected")
            return ""
        # send command (add prints for debugging)
        self.connection.write(command.encode("UTF-8"))
        print(f"Sent command: {command.strip()}")
        # receive response
        response = self.connection.readline()
        response = response.decode("UTF-8").strip()
        print("Received response:", response)
        return response
    



    # all for use with with block
    def __enter__(self):
        """ for use witj 'with' block, will handle opening the serial connection """
        try:
            self.connection = serial.Serial( self.port, self.baudrate, timeout=self.timeout)
            print(f"Serial port opened successfully on {self.port}.")

        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            self.connection = None
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """ for use with 'with' block, will handle closing the serial connection """
        if self.connection and self.connection.is_open:
            self.connection.close()
            print("Serial port closed successfully.")


# Example usage
with IPXSerialCommunicator(port='COM8', baudrate=9600, timeout=5) as ipx_comm:
    ipx_comm.send_and_receive(IPXCommands.Commands.list_uids)

