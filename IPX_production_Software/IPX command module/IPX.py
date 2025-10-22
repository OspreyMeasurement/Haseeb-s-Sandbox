import serial
import logging
import time
from IPX_Config import IPXCommands

# com port 5 for testing

# print(IPXConfig.Commands.list_uids)

""" This file is for handling all serial communication with the IPX devices

"""

# Initialise logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')



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
        self.connection = None # used for initialising the serial connection in __enter__, holds serial.Serial()


    
    def send_and_receive(self, command:str) -> str:
        """ purely for sending command to IPX device, and receiving response"""
        if not self.connection:
            logging.error("ERROR: Not connected")
            return ""
        # send command (add prints for debugging)
        self.connection.write(command.encode("UTF-8"))
        logging.info(f"Sent command: {command.strip()}")
        # receive response
        response = self.connection.readline()
        response = response.decode("UTF-8").strip()
        logging.info(f"Received response: {response}")
        return response
    
    def execute_and_verify(self, command:str, expected_response:str, **kwargs) -> bool:
        """ handles executing sending of commands and verifying the response to ensure command was successful """
        try:
            command = command.format(**kwargs)
        except KeyError as e:
            logging.error(f"Error formatting command: missing a required argument {e}")
            return False, None
        # uids not part of recieved response
        if command == IPXCommands.Commands.list_uids:
            response = self.send_and_receive(command)
            return True, response
        else:
            response = self.send_and_receive(command)
            if expected_response in response:
                logging.info(f"Command executed successfully: {command.strip()}")
                return True, response # return response as well for further processing (index 1 is response)
            else:
                logging.error(f"Command execution failed, expected: {expected_response}, got: {response}")
                return False, None


    
    def list_uids(self) -> list[str]:
        """ Lists all connected IPX device UIDs """
        boolean, response = self._execute_and_verify(command=IPXCommands.Commands.list_uids, expected_response="Skip")
        if boolean is False:
            logging.error("Failed to list UIDs, ref execute and verify")
        else: 
            # process response to extract UIDs
            response_list = []
            lines = response.splitlines()
            for line in lines:
                response_list.append(line)
        print (response_list)
    





    # all for use with with block
    def __enter__(self):
        """ for use witj 'with' block, will handle opening the serial connection """
        try:
            self.connection = serial.Serial( self.port, self.baudrate, timeout=self.timeout) # initial paramaters are used here
            logging.info(f"Serial port opened successfully on {self.port}.")

        except serial.SerialException as e:
            logging.error(f"Error opening serial port: {e}")
            self.connection = None
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """ for use with 'with' block, will handle closing the serial connection """
        if self.connection and self.connection.is_open:
            self.connection.close()
            logging.info("Serial port closed successfully.")


# Example usage
with IPXSerialCommunicator(port='COM8', baudrate=9600, timeout=5) as ipx_comm:
    ipx_comm.execute_and_verify(command=IPXCommands.Commands.list_uids, expected_response="skip")

