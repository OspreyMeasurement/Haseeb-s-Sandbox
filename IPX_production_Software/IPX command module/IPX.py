import serial
import logging
import time
from typing import Literal
from IPX_Config import IPXCommands
import numpy as np

# com port 5 for testing

# print(IPXConfig.Commands.list_uids)
"""
IPX Serial Communication Module
--------------------------------

This module provides a robust Python interface for communicating with
IPX sensor devices over serial (COM) ports. It includes structured command
handling, real-time logging, and error management for reliable device interaction.

Main Features:
- Context-managed serial connections (`with` support)
- Command-specific timeouts (e.g. calibration vs. configuration)
- Incremental line-by-line response logging
- Custom exception classes for corrupted data and timeouts
- Configurable response data types (string, list, array, bytes)

Classes:
    IPXSerialCommunicator
        Main interface for sending commands and receiving responses.

    IPXSerialError (Exception)
        Base exception class for IPX serial errors.

    IPXCorruptedDataError (IPXSerialError)
        Raised when received data cannot be UTF-8 decoded.

    IPXNoResponseError (IPXSerialError)
        Raised when the IPX device fails to respond within the expected timeout.

Usage Example:
    with IPXSerialCommunicator("COM5", 115200) as ipx:
        uids = ipx.list_uids("list")
        print("Connected UIDs:", uids)
        status = ipx.get_status(uid=uids[0])
        print(status)

Dependencies:
    - pyserial
    - numpy
    - logging
    - time
    -IPX_Config.py

Author:
    Haseeb Mahmood
"""





#initialise custom IPX errors
# start with base class for IPX serial errors

class IPXSerialError(Exception):
    """Base class for all IPX-related serial communication errors"""
    pass

class IPXCorruptedDataError(IPXSerialError):
    """Raised when corrupted or non-decodable data is received from an IPX device"""
    pass

class IPXNoResponseError(IPXSerialError):
    """Raised when IPX does not respond within the expected timeout"""
    pass

class IPXVerificationError(IPXSerialError):
    """Raised when the device response does not match the expected success message"""
    pass


class IPXSerialCommunicator:
    """ Class for handling serial communication with IPX devices """
    def __init__(self, port: str, baudrate: int, timeout: int=5, verify: bool = False):
        """ Initialize the serial communicator , with serial settings
        Arguments:
            port {str} -- COM port to use
            baudrate {int} -- Baud rate for serial communication
            timeout {int} -- Timeout for serial communication in seconds
        """
        self.port = port
        self.verify = verify # holds whether the response command is being verified or not
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None # used for initialising the serial connection in __enter__, holds serial.Serial()
    

    # This is called default timeouts but it is for adjusting the listen duration within the send_receive_listen method
    DEFAULT_TIMEOUTS = {
        "calibrate" : 20, # 10s for sensors to start calibrating
        "set_axis" : 0.25, # 10s
        "set_baud" : 0.25,
        "set_uid" : 0.25,
        "set_gain" : 0.25,
        "set_centroid_threshold" : 0.25,       # no need for any listening period, as waits for first byte
        "set_centroid_res" : 0.25,
        "set_n_stds" : 0.25,
        "set_term" : 0.25,
        "set_alias" : 0.25,

    }


    
    def _send_and_receive_listen(self, command:str, listen_duration: float = 0.5, stop_on_string: str = None ):
        """ purely for sending command to IPX device, and receiving response
        Sends command and listens until no new data is received, or 
        listen_duration is exceeded
        This should always return bytes, higher level functions can decode if needed
        Can now stop early, if a specific terminator string is found in the response stream"""
        if not self.connection:
            logging.error("ERROR: Not connected")
            return bytearray()
        # send command (add prints for debugging)

        # Clear input buffer to ensure we only read the response to *this* command
        self.connection.reset_input_buffer()
        self.connection.write(command.encode("UTF-8"))
        logging.info(f"Sent command: {command.strip()}")

        # 1. block and wait for the first byte to arrive
        first_byte = self.connection.read(1)
        if not first_byte:
            logging.warning("No response received from device.")
            return bytearray() # timed out waiting for a response
        

        #2. once we have first byte, read remaining data in the buffer
        all_responses = bytearray(first_byte)  # start with the first byte we already read

        start_time = time.time() # record start time before loop

        #add decode_buffer for incremental line logging:
        decode_buffer = bytearray(first_byte)

        while True: # byte level timeout -> try this instead
            # initialise flag at start of every loop to avoid error
            stop_reading_now = False

            if self.connection.in_waiting > 0: # whilst stuff still waiting in buffer
                chunk = self.connection.read(self.connection.in_waiting) # break the data up into 'chunks'
                all_responses.extend(chunk)
                decode_buffer += chunk
                #reset the timer since we got new data
                start_time = time.time()

                # try decoding the new bytes for logging stuff line by line
                try:
                    decoded_text = decode_buffer.decode('utf-8')
                except UnicodeDecodeError:
                    #incomplete byte sequence, so should wait for the next chunk
                    continue
                #split into complete lines
                lines = decoded_text.split("\n")
                # if unfinished lines present put back in buffer for next iteration
                if decoded_text.endswith("\n"):
                    decode_buffer = b""
                else:
                    #save partial line for next iteration
                    decode_buffer = lines.pop().encode("utf-8")
                #now onto logging each line straight away: # in the calibration function we should end it when we get the final line whi
                # -> calibration on all sensors complete, saving to memory
                for line in lines:
                    line = line.strip()
                    if line:
                        logging.info(line)

                        # adding stop on string logic
                        if stop_on_string and stop_on_string in line:
                            logging.info(f" Terminator string found. Finalising read")
                            stop_reading_now = True
            if stop_reading_now == True:
                break
            
            elif time.time() - start_time > listen_duration:
                # no new data received within listen_duration
                logging.info("No new data received within listen duration, ending read.") # change to debug later
                break # break the while loop
            time.sleep(0.01)  # short delay to stop loop from hogging CPU (gemini)
        
        response = all_responses
        if response:
            logging.debug(f"Received response: {response}")
        else:
            logging.warning("No response received from device.")
        return response
    


    def _decode_string_and_check(self, response: bytes, expected_response:str = "", command:str = "") -> str:
        """For ensuring random/corrupted data is not recieved by IPX, added verification within this function"""
        try:
            response_str = response.decode("utf-8").strip()
        except UnicodeDecodeError:
            logging.ERROR("Corrupted data recieved: UTF-8 decode failed")
            raise IPXCorruptedDataError("Corrupted data could not decode UTF-8 bytes")
        
        if self.verify and expected_response:
            logging.debug(f"Verifying response, expecting to find {expected_response}")
            if not response_str.lower().startswith(expected_response.lower()): # if the string doesnt start with expected response, raise an error
                error_message = (
                    f"verification failed for command: {command}",
                    f"Expected response to start with {expected_response}, but got {response_str}"
                )
                logging.error(error_message)
                raise IPXVerificationError(error_message)
            else:
                logging.info(f"response verified successfully for command: {command}")

        
        return response_str





    
    def list_uids(self, data_type: Literal['list', 'string', 'bytes', 'array'] = 'string'):
        """ Lists all connected IPX device UIDs """
        #1 validation check
        allowed_types = ['list', 'string', 'bytes', 'array']
        if data_type not in allowed_types:
            raise ValueError(f"Invalid data_type '{data_type}'. Allowed types are: {allowed_types}")
        
        response = self._send_and_receive_listen(IPXCommands.Commands.list_uids) # simplified into one line for simplicity
        logging.debug("Moving to parsing response based on requested data type")
        
        response_str = self._decode_string_and_check(response)

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
            response_str = self._decode_string_and_check(response) # use function for decoding and checkign instead
            
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
        

        response_str = self._decode_string_and_check(response)
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

        response = self._send_and_receive_listen(command, 
                                                 listen_duration=self.DEFAULT_TIMEOUTS['calibrate'],
                                                 stop_on_string=IPXCommands.Responses.CALIBRATION_COMPLETE)
        response = self._decode_string_and_check(response)
        return(response)
    
    def set_baud(self, uid: int, baud: int) -> str:
        """ Sets baud rate of IPX device with given UID """
        command = IPXCommands.Commands.set_baud.format(uid=str(uid), baud=str(baud))
        expected_response = IPXCommands.Responses.set_baud
        response = self._send_and_receive_listen(command, listen_duration= self.DEFAULT_TIMEOUTS['set_baud'])
        response = self._decode_string_and_check(response, expected_response=expected_response, command=command)
        return(response)
    
    def set_uid(self, current_uid: int, new_uid: int) -> str:
        """ Sets UID of IPX device with given current UID to new UID """
        command = IPXCommands.Commands.set_uid.format(current_uid=str(current_uid), new_uid=str(new_uid))
        expected_response = IPXCommands.Responses.set_uid
        response = self._send_and_receive_listen(command, listen_duration=self.DEFAULT_TIMEOUTS['set_uid'])
        response = self._decode_string_and_check(response, expected_response=expected_response, command=command)
        return(response)
    
    def set_axis(self, uid: int, axis: int) -> str:
        """ Sets axis of IPX device with given UID """
        command = IPXCommands.Commands.set_axis.format(uid=str(uid), axis=str(axis))
        expected_response = IPXCommands.Responses.set_axis
        response = self._send_and_receive_listen(command, listen_duration=self.DEFAULT_TIMEOUTS['set_axis'])
        response = self._decode_string_and_check(response, expected_response=expected_response, command=command)
        return(response)
    
    def set_gain(self, uid: int, gain: int) -> str:
        """ Sets gain of IPX device with given UID """
        command = IPXCommands.Commands.set_gain.format(uid=str(uid), gain=str(gain))
        expected_response = IPXCommands.Responses.set_gain
        response = self._send_and_receive_listen(command, listen_duration=self.DEFAULT_TIMEOUTS['set_gain'])
        response = self._decode_string_and_check(response, expected_response=expected_response, command=command)
        return(response)
    
    def set_centroid_threshold(self, uid: int, threshold: int) -> str:
        """ Sets centroid threshold of IPX device with given UID """
        command = IPXCommands.Commands.set_centroid_threshold.format(uid=str(uid), threshold=str(threshold))
        expected_response = IPXCommands.Responses.set_centroid_threshold
        response = self._send_and_receive_listen(command, listen_duration=self.DEFAULT_TIMEOUTS['set_centroid_threshold'])
        response = self._decode_string_and_check(response, expected_response=expected_response, command=command)
        return(response)
    
    def set_centroid_res(self, uid: int, resolution: int) -> str:
        """ Sets centroid resolution of IPX device with given UID """
        command = IPXCommands.Commands.set_centroid_res.format(uid=str(uid), resolution=str(resolution))
        expected_response = IPXCommands.Responses.set_centroid_res
        response = self._send_and_receive_listen(command, listen_duration=self.DEFAULT_TIMEOUTS["set_centroid_res"])
        response = self._decode_string_and_check(response, expected_response, command=command)
        return(response)
    
    def set_n_stds(self, uid: int, n_stds: int) -> str:
        """ Sets number of standard deviations of IPX device with given UID """
        command = IPXCommands.Commands.set_n_stds.format(uid=str(uid), n_stds=str(n_stds))
        expected_response = IPXCommands.Responses.set_n_stds
        response=self._send_and_receive_listen(command, listen_duration=self.DEFAULT_TIMEOUTS['set_n_stds'])
        response = self._decode_string_and_check(response, expected_response=expected_response, command=command)
        return(response)
    
    def set_term(self, uid: int, termination: int) -> str:
        """ Sets termination of IPX device with given UID """
        command = IPXCommands.Commands.set_term.format(uid=str(uid), termination=str(termination))
        expected_response = IPXCommands.Responses.set_term
        response = self._send_and_receive_listen(command, listen_duration= self.DEFAULT_TIMEOUTS['set_term'])
        response = self._decode_string_and_check(response, expected_response=expected_response, command=command)
        return(response)
    
    def set_alias(self, uid: int, alias: str) -> str:
        """ Sets alias of IPX device with given UID """
        command = IPXCommands.Commands.set_alias.format(uid=str(uid), alias=str(alias))
        expected_response = IPXCommands.Responses.set_alias
        response = self._send_and_receive_listen(command, listen_duration=self.DEFAULT_TIMEOUTS['set_alias'])
        response = self._decode_string_and_check(response, expected_response=expected_response, command=command)
        return(response)
    

    # maybe add a verify method to this class???
    # def verify_response(command, response):
        





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
        if exc_value or exc_type:
            logging.error(f"Error during communication exc value: {exc_value}")
            logging.error(f"Error during communication exc type: {exc_type}")

        if self.connection and self.connection.is_open:
            self.connection.close()
            logging.info("Serial port closed successfully.")




# create new IPX configurator class?

class IPXConfigurator:
    def __init__(self, port, max_retries: int=3, retry_delay: int=2):
        self.port = port
        self.max_retries = max_retries
        self.retry_delay = retry_delay



