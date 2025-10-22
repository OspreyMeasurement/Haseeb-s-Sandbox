import serial
import logging
import time
from typing import Literal
from IPX_Config import IPXCommands
import numpy as np

# com port 5 for testing

# print(IPXConfig.Commands.list_uids)

""" This file is for handling all serial communication with the IPX devices

"""

# Initialise logging setup
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s')



class IPXSerialCommunicator:
    """ Class for handling serial communication with IPX devices """
    def __init__(self, port: str, baudrate: int, timeout: int=5):
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


    
    def _send_and_receive_listen(self, command:str, listen_duration: float = 0.5 ):
        """ purely for sending command to IPX device, and receiving response
        Sends command and listens until no new data is received, or 
        listen_duration is exceeded
        This should always return bytes, higher level functions can decode if needed"""
        if not self.connection:
            logging.error("ERROR: Not connected")
            return ""
        # send command (add prints for debugging)

        # Clear input buffer to ensure we only read the response to *this* command
        self.connection.reset_input_buffer()
        self.connection.write(command.encode("UTF-8"))
        logging.info(f"Sent command: {command.strip()}")

        # 1. block and wait for the first byte to arrive
        first_byte = self.connection.read(1)
        if not first_byte:
            logging.warning("No response received from device.")
            return "" # timed out waiting for a response
        

        #2. once we have first byte, read remaining data in the buffer
        all_responses = bytearray(first_byte)  # start with the first byte we already read

        start_time = time.time() # record start time before loop

        while True: # byte level timeout -> try this instead
            
            if self.connection.in_waiting > 0: # whilst stuff still waiting in buffer
                all_responses.extend(self.connection.read(self.connection.in_waiting)) # read bytes waiting and add to response byte array
                #reset the timer since we got new data
                start_time = time.time()
            elif time.time() - start_time > listen_duration:
                # no new data received within listen_duration
                logging.info("No new data received within listen duration, ending read.") # change to debug later
                break # break the while loop
            time.sleep(0.01)  # short delay to stop loop from hogging CPU (gemini)
        
        response = all_responses
        if response:
            logging.info(f"Received response: {response}")
        else:
            logging.warning("No response received from device.")
        return response
        

    def _send_and_receive(self, command:str) -> str:
        """ Sends command to IPX device, and receives response
        Simpler function more suited for reading responses from one device"""
        if not self.connection:
            logging.error("ERROR: Not connected")
            return ""
        # send command (add prints for debugging)
        self.connection.write(command.encode("UTF-8"))
        logging.info(f"Sent command: {command.strip()}")
        # 1. block and wait for the first byte to arrive            # dont think this function is needed anymore
        first_byte = self.connection.read(1)
        response = bytearray(first_byte)  # start with the first byte we already read
        while self.connection.in_waiting > 0:
            response.extend(self.connection.read(self.connection.in_waiting)) # read bytes waiting and add to response byte array
        response = response.decode("UTF-8").strip() # maybe move this to higher level functions?
        logging.debug(f"Received raw bytes response: {response}")
        return response





    
    def list_uids(self, data_type: Literal['list', 'string', 'bytes', 'array'] = 'string'):
        """ Lists all connected IPX device UIDs """
        #1 validation check
        allowed_types = ['list', 'string', 'bytes', 'array']
        if data_type not in allowed_types:
            raise ValueError(f"Invalid data_type '{data_type}'. Allowed types are: {allowed_types}")
        
        response = self._send_and_receive_listen(IPXCommands.Commands.list_uids) # simplified into one line for simplicity
        logging.debug("Moving to parsing response based on requested data type")
        try:
            response_str = response.decode("UTF-8").strip()
        except UnicodeDecodeError:
            logging.CRITICAL('Corrupted data received from sensors: Check wiring and sensors. Check inputs to ensure broadcasting is not being used etc')
            raise ValueError("Corrupted data: could not decode UTF-8 bytes")

        if data_type == 'string':
            logging.debug("Parsing response as string")
            return(response_str)
        
        elif data_type == 'list':
            logging.debug("Parsing response as list")
            uid_list = [int(line.split("uid:")[1]) for line in response_str.splitlines() if "uid:" in line]
            return(uid_list)
        
        elif data_type == 'array':
            logging.debug("Parsing response as numpy array")
            uid_array = np.array([int(line.split("uid:")[1]) for line in response_str.splitlines() if "uid:" in line])
            return(uid_array)
        
        elif data_type == 'bytes':
            logging.debug("Returning response as bytes")
            return(response)
    


    def get_status(self, uid: int, data_type: Literal['string', 'bytes', 'dict'] = 'dict'):
        """ Gets status of IPX device with given UID """
        # allowed data types check
        allowed_types = ['string', 'bytes', 'dict']
        if data_type not in allowed_types:
            raise ValueError(f"Invalid data_type '{data_type}'. Allowed types are: {allowed_types}")
        
        if uid == 0:
            logging.warning("UID 0 is reserved for broadcasting to all devices, please provide a valid device UID.")
            return ""
        else:
            response = self._send_and_receive_listen(IPXCommands.Commands.get_status.format(uid=str(uid)))

            try:
                response_str = response.decode("UTF-8").strip()
            except UnicodeDecodeError:
                logging.CRITICAL('Corrupted data received from sensors: Check wiring and sensors. Check inputs to ensure broadcasting is not being used etc') # added error catching within the function in case of jargon
                raise ValueError("Corrupted data: could not decode UTF-8 bytes")
            
            if data_type == 'string':
                return(response_str)
            
            elif data_type == 'bytes':
                return(response)
            
            elif data_type == 'dict':
               # start with decoding to string
                logging.debug(f"parsing response string to dictionary: {response_str}")
                status_dict = {} # initialise empty dict
                for line in response_str.splitlines()[1:]: # splits string into a list of lines, and iterates over them (skipping first line)
                    if ':' in line: # lines containing : are processed
                        logging.debug(f"Processing line: {line}")
                        key, value = line.split(':', 1) # split only on first colon
                        logging.debug(f"Key: {key.strip()}, Value: {value.strip()}")
                        status_dict[key.strip()] = value.strip() # strip removes and remaining leading/trailing whitespace and adds to dictionary
                        logging.debug(f"Added to dictionary: {key.strip()} : {value.strip()}")
                return(status_dict) # may want to manipulate further to convert the numeric values to int/float later



    def get_raw(self, uid: int, data_type: Literal['string', 'bytes', 'list', 'array'] = 'string') -> str:
        """ Gets raw data from IPX device with given UID """
        #1. validation check
        allowed_types = ['string', 'bytes', 'list', 'array']
        if data_type not in allowed_types:
            raise ValueError(f"Invalid data_type '{data_type}'. Allowed types are: {allowed_types}")
        if uid == 0:
            logging.warning("UID 0 is reserved for broadcasting to all devices, please provide a valid device UID.")
            return ""
        
        # get response
        response = self._send_and_receive_listen(IPXCommands.Commands.get_raw.format(uid=str(uid)))
   
        logging.debug('recieved response within get_raw functions and converted to response_str and raw_list')
        

        
        try:
            response_str = response.decode("UTF-8").strip()
        except UnicodeDecodeError:
            logging.CRITICAL('Corrupted data received from sensors: Check wiring and sensors. Check inputs to ensure broadcasting is not being used etc')
            raise ValueError("Corrupted data: could not decode UTF-8 bytes")
        raw_list = [int(x) for x in response_str.split(',')]

        if data_type == 'bytes':
            return(response)
        if data_type == 'string':
            return(response_str)
        
        elif data_type == 'list': # works as expected
            return(raw_list)
        
        elif data_type == 'array':
            return(np.array(raw_list))
    


    def calibrate(self, uid: int) -> str:
        """ Calibrates IPX device with given UID """
        command = IPXCommands.Commands.calibrate.format(uid=str(uid)) # change uid to str for formatting
        response = self._send_and_receive(command)
        return(response)
    
    def set_baud(self, uid: int, baud: int) -> str:
        """ Sets baud rate of IPX device with given UID """
        command = IPXCommands.Commands.set_baud.format(uid=str(uid), baud=str(baud))
        response = self._send_and_receive(command)
        return(response)
    
    def set_uid(self, current_uid: int, new_uid: int) -> str:
        """ Sets UID of IPX device with given current UID to new UID """
        command = IPXCommands.Commands.set_uid.format(current_uid=str(current_uid), new_uid=str(new_uid))
        response = self._send_and_receive(command)
        return(response)
    
    def set_axis(self, uid: int, axis: int) -> str:
        """ Sets axis of IPX device with given UID """
        command = IPXCommands.Commands.set_axis.format(uid=str(uid), axis=str(axis))
        response = self._send_and_receive(command)
        return(response)
    
    def set_gain(self, uid: int, gain: int) -> str:
        """ Sets gain of IPX device with given UID """
        command = IPXCommands.Commands.set_gain.format(uid=str(uid), gain=str(gain))
        response = self._send_and_receive(command)
        return(response)
    
    def set_centroid_threshold(self, uid: int, threshold: int) -> str:
        """ Sets centroid threshold of IPX device with given UID """
        command = IPXCommands.Commands.set_centroid_threshold.format(uid=str(uid), threshold=str(threshold))
        response = self._send_and_receive(command)
        return(response)
    
    def set_centroid_res(self, uid: int, resolution: int) -> str:
        """ Sets centroid resolution of IPX device with given UID """
        command = IPXCommands.Commands.set_centroid_res.format(uid=str(uid), resolution=str(resolution))
        response = self._send_and_receive(command)
        return(response)
    
    def set_n_stds(self, uid: int, n_stds: int) -> str:
        """ Sets number of standard deviations of IPX device with given UID """
        command = IPXCommands.Commands.set_n_stds.format(uid=str(uid), n_stds=str(n_stds))
        response = self._send_and_receive(command)
        return(response)
    
    def set_term(self, uid: int, termination: int) -> str:
        """ Sets termination of IPX device with given UID """
        command = IPXCommands.Commands.set_term.format(uid=str(uid), termination=str(termination))
        response = self._send_and_receive(command)
        return(response)
    
    def set_alias(self, uid: int, alias: str) -> str:
        """ Sets alias of IPX device with given UID """
        command = IPXCommands.Commands.set_alias.format(uid=str(uid), alias=str(alias))
        response = self._send_and_receive(command)
        return(response)






    # all for use with 'with' block
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



