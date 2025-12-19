import serial
import logging
import time
from typing import Literal
from IPX_Config import IPXCommands
import numpy as np


import pandas as pd

import re # apparently good for handling text


logger = logging.getLogger(__name__)


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




"""------------------------------------------------------------------------------------------------------------------------------------------------------"""
#initialise custom IPX errors
# start with base class for IPX serial errors
""" FOLLOWIGN ERRORS ARE ALL COMMUNICATION ERRORS RELATED TO IPX DEVICES OVER SERIAL PORTS """

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
"""------------------------------------------------------------------------------------------------------------------------------------------------------"""


"""------------------------------------------------------------------------------------------------------------------------------------------------------"""
""" MAIN IPX SERIAL COMMUNICATOR CLASS FOR HANDLING SERIAL COMMUNICATION WITH IPX DEVICES """

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
            raise IPXSerialError("Not connected to any serial device.")
        # send command (add prints for debugging)

        # Clear input buffer to ensure we only read the response to *this* command
        self.connection.reset_input_buffer()
        self.connection.write(command.encode("UTF-8"))
        logging.debug(f"Sent command: {command.strip()}")

        # 1. block and wait for the first byte to arrive
        first_byte = self.connection.read(1)
        if not first_byte:
            logging.error("No response received from device.")
            raise IPXNoResponseError("No response received from device within the expected timeout.") # didnt recieve response within timeout
        

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
                        logging.debug(line)

                        # adding stop on string logic
                        if stop_on_string and stop_on_string in line:
                            logging.debug(f" Terminator string found. Finalising read")
                            stop_reading_now = True
            if stop_reading_now == True:
                break
            
            elif time.time() - start_time > listen_duration:
                # no new data received within listen_duration
                logging.debug("No new data received within listen duration, ending read.") # change to debug later
                break # break the while loop
            time.sleep(0.01)  # short delay to stop loop from hogging CPU (gemini)
        
        response = all_responses
        if response:
            logging.debug(f"Received response: {response}")
        else:
            logging.error("No response received from device.")
            raise IPXNoResponseError("No response received from device within the expected timeout.") # add this exception for error catching
        return response
    


    def _decode_string_and_check(self, response: bytes, expected_response:str = "", command:str = "") -> str:
        """For ensuring random/corrupted data is not recieved by IPX, added verification within this function"""
        try:
            response_str = response.decode("utf-8").strip()
        except UnicodeDecodeError: # catch decode errors, should be thrown when the ipx is sending jibberish, etc when gets disconnected and connected again
            logging.error("Corrupted data recieved: UTF-8 decode failed")
            raise IPXCorruptedDataError("Corrupted data could not decode UTF-8 bytes | Please check connection and try again")
        
        if self.verify and expected_response: # this is for verifying the response matches expected response
            logging.debug(f"Verifying response, expecting to find {expected_response}")
            if not response_str.lower().startswith(expected_response.lower()): # if the string doesnt start with expected response, raise an error
                error_message = (
                    f"verification failed for command: {command}" # add command for debugging
                    f"Expected response to start with {expected_response}, but got {response_str}"# detailed error message
                )
                logging.error(error_message)
                raise IPXVerificationError(error_message) # raise verification error
            else:
                logging.debug(f"response verified successfully for command: {command}")

        
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
    



    def calibrate(self, uid: int, data_type: Literal['dataframe', 'string'] = 'dataframe') -> list| str:
        """ Calibrates IPX device with given UID , and returns results as a parsed
        list of dictionaries
        
        Args:
        uid(int): UID of device to calibrate
        data_type (str) 'parsed to return structured data (default), or 'string'"""
        #1. validation check
        allowed_types = ['dataframe', 'string']
        if data_type not in allowed_types:
            raise ValueError(f"Invalid data_type '{data_type}'. Allowed types are: {allowed_types}")
        
        command = IPXCommands.Commands.calibrate.format(uid=str(uid)) # change uid to str for formatting

        response = self._send_and_receive_listen(command, 
                                                 listen_duration=self.DEFAULT_TIMEOUTS['calibrate'],
                                                 stop_on_string=IPXCommands.Responses.CALIBRATION_COMPLETE)
        response_str = self._decode_string_and_check(response)

        if data_type == 'string': # return this as string
            return(response_str)
        
        # New dictionary parsing logic using regex etc
        if data_type == 'dataframe':
            logging.debug("Passing calibration results into a dataframe...")
            # use regex to define the pattern to capture the 4 data groups
            pattern = re.compile(r"Sensor number (\d+) mean = (-?\d+), standard dev = (\d+) axis (\d+)") # extract sensor number, mean, std dev and axis number as seperate values
            matches = pattern.findall(response_str) # do this to response_str, should generate list of tuples, of format ('sensornum', "mean", "std dev ", "axis number")
            # logger.trace(f"Created matches tuple as follows: {matches} ")
            if not matches:
                logging.error(f"Match object was empty, received this as reponse: {response_str}")
                # raise Exception(f"Did not find any values for creation of DF: {response_str}") # gemini says raising an exception is too harsh

                # Return an empty DataFrame instead of raising an exception
                return pd.DataFrame(columns=["sensor_num", "mean", "std_dev", "axis"])

            # Create data frame directly from list of tuples
            columns = ["sensor_num", "mean", "std_dev", "axis"]
            cal_df = pd.DataFrame(matches, columns=columns)

            # Ensure to convert the columns to correct numeric types, all str right now, as regex captures everything as strings
            convert_dict = {
                "sensor_num": int,
                "mean" : int,
                "std_dev" : int,
                "axis": int
            }
            cal_df = cal_df.astype(convert_dict) # assign correct int to columns
            logging.debug(f"Successfully parsed {len(cal_df)} data points into a dataframe")
            return cal_df
            

        
    
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
            raise
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """ for use with 'with' block, will handle closing the serial connection """
        if exc_value or exc_type:
            logging.error(f"Error during communication exc value: {exc_value}")
            logging.error(f"Error during communication exc type: {exc_type}")

        if self.connection and self.connection.is_open:
            self.connection.close()
            logging.info("Serial port closed successfully.")





"""------------------------------------------------------------------------------------------------------------------------------------------------------"""

#Move calibration errors to here, easier to reference

"""THESE ERRORS ARE FOR CALIBRATION AND CONFIGURATION ERRORS"""

class IPXConfigurationError(Exception):
    """Base class for all IPX calibration errors"""
    pass

class HIGH_MAG_VALUE_ERROR(IPXConfigurationError):
    """Raised when the calibration results show abnormally high magnitude values"""
    pass

class CALINBRATION_NO_CHANGE_ERROR(IPXConfigurationError):
    """Raised when calibration raw data shows no change across multiple readings"""
    pass

class CALIBRATION_CHECK_ERROR(IPXConfigurationError):
    """Raised when calibration results fail validation checks"""
    pass

"""------------------------------------------------------------------------------------------------------------------------------------------------------"""



"""IPX CONFIGURATOR CLASS FOR HIGH LEVEL CONFIGURATION OF EXTENSOMETERS"""
# This class should just be for performing the configuration tasks, not prompting the user for input etc

class IPXConfigurator:
    """ High level class to manage the configuration process for extensometer
    contains functions which perform various configuration tasks
    """
    def __init__(self, port: str, initial_baudrate: int = 115200, max_retries: int=3, retry_delay: int=2):
        """ Initialises configurator with connection settings

        Args:
        port(str): The com port to use
        baudrate (int): The initial baudrate for communication
        max_retries (int): Number of times to retry sensor detection
        retry_delay (int): Seconds to wait between retries
        """
        self.port = port
        self.initial_baudrate = initial_baudrate
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        logging.debug(f"IPX Configurator initialised for port {self.port}")


    def verify_sensor_count(self, ipx: IPXSerialCommunicator ,num_sensors:int) -> tuple[list, bool] | None:
        """Private helper to detect and verify the number of connected sensors
        Should return uid list
        Args:
            ipx (IPXSerialCommunicator): An instance of the IPXSerialCommunicator class
            num_sensors (int): Expected number of connected sensors
        Returns:
            (list, bool) | None: List of detected sensor UIDs if the expected number is met, check sensor found boolean\n
            or none if the expected number is not met after retries
             """
        logging.debug(f"Attempting to detect {num_sensors} sensors")
        # ADD logic for removing check senssor from this
        check_uid = int(IPXCommands.Default_settings.Check_sensor_uid) # get check sensor uid from config file (needs to be int)

        for attempt in range (1, self.max_retries + 1): # loop that retries so long as the right number of sensors are not detected, keeps retrying as long as doesnt exceed max_retries
            all_uids = ipx.list_uids(data_type='list') # get uids list
            # Filtering out check sensor logic:
            valid_uids = []
            check_sensor_found = False
            for uid in all_uids: # check if check sensor is present, and filter it out
                if uid == check_uid:
                    check_sensor_found = True
                    logging.debug("Check sensor detected and will be excluded from count")
                else:
                    valid_uids.append(uid) # add all other uids to valid uids list
            
            #verify count of valid sensors
            detected_sensors = len(valid_uids) # variable to hold the number of detected sensors
            if detected_sensors == num_sensors: # check then number of uids received is the number that is expected, if not retry
                if check_sensor_found:
                    logging.info(f"Check sensor with uid {check_uid} detected")
                logging.info("Number of expected sensors are connected")
                return valid_uids, check_sensor_found # return the valid uids list and check sensor found boolean
            else:
                logging.error(f"Incorrect number of sensors detected. Detected: {detected_sensors}, expected {num_sensors}")
                time.sleep(self.retry_delay)# retry delay
        else:
            logging.error("Failed to detect all sensors after multiple retries| Check inputted number of sensors") # log error
            return None # return false if failed to detect correct number of sensors after retries


    def set_default_parameters(self, ipx:IPXSerialCommunicator, uids_list: list, baud: int ,set_aliases: bool = True) -> list:
        """Private helper to loop through all uids and apply standard configurations + aliases
        Args:
            ipx (IPXSerialCommunicator): An instance of the IPXSerialCommunicator class
            uids_list (list): List of UIDs to configure
            set_aliases (bool): Whether to set aliases for the sensors  
            Returns:
            list: A list of tuples containing (alias, uid) if aliases are set, else a list of uids (for referecne later on)"""
        logging.debug ("Appling deafualt parameters to all detected sensors...")
        uids_list
        # if set alis = false, skip setting aliases

        if set_aliases is True:
            aliases_and_uids_list = list(zip(range(len(uids_list), 0, -1), uids_list)) # combine uids and list into a tuple in a list, of format (alias, uid)
            logging.debug(f"Aliases and uid list completed succesfully: {aliases_and_uids_list}")
            for alias_uid_tuple in aliases_and_uids_list:

                alias = str(alias_uid_tuple[0]) # extract alias
                uid = str(alias_uid_tuple[1]) # extract uid
                logging.info(f"Beginning setting process for sensor uid :{uid}")
                # now need to set all the paramaters, use all default config parameters in the IPXCommands section:
                
                ipx.set_baud(uid, baud) # set baud first to prevent any errors

                ipx.set_alias(uid, alias)
                

                ipx.set_gain(uid, gain=IPXCommands.Default_settings.Gain)

                ipx.set_centroid_threshold(uid, threshold=IPXCommands.Default_settings.Centroid_threshold)

                ipx.set_n_stds(uid=uid, n_stds=IPXCommands.Default_settings.N_stds)

                ipx.set_centroid_res(uid=uid, resolution=IPXCommands.Default_settings.Centroid_res)

                ipx.set_term(uid=uid, termination=IPXCommands.Default_settings.Termination)

                logging.info(f"Setting parameters complete for sensor with uid:{uid}")
            logging.info("All sensors have been set with default parameters")
            return aliases_and_uids_list # return this for reference later on (useful in main.py for generating a .txt file with uids and corresponding aliases)
            # alias and uid list is of format [(uid, alias), (uid, alias),.....] etc, with the last sensors uid being at the start of the list
            # so [(8, 1), (7,2), (6,3), (5,4), (4,5), (3,6), (2,7), (1,8)] for 8 sensors connected etc 

        else: # gxm inserts, so set all other paramaters except aliases:
            for uid in uids_list:
                logging.info(f"Beginning setting process for sensor uid :{uid}")
                # now need to set all the paramaters, use all default config parameters in the IPXCommands section:
                
                ipx.set_baud(uid, baud) # set baud first to prevent any errors

                ipx.set_gain(uid, gain=IPXCommands.Default_settings.Gain)

                ipx.set_centroid_threshold(uid, threshold=IPXCommands.Default_settings.Centroid_threshold)

                ipx.set_n_stds(uid=uid, n_stds=IPXCommands.Default_settings.N_stds)

                ipx.set_centroid_res(uid=uid, resolution=IPXCommands.Default_settings.Centroid_res)

                ipx.set_term(uid=uid, termination=IPXCommands.Default_settings.Termination)

                logging.info(f"Setting parameters complete for sensor with uid:{uid}")
            logging.info("All sensors have been set with default parameters")
            return uids_list # return this for reference later on


# VALIDATION FUNCTIONS SHOULD ALWAYS RETURN A CONSISTENT TUPLE (SUCCESS BOOLEAN, DATA)


    def validate_calibration_results(self, cal_df: pd.DataFrame) -> tuple[bool, list| None]:
        """
        Checks calibration DataFrame for zero mean OR zero std dev across all axes.
        Args:
            cal_df (pd.DataFrame): DataFrame containing calibration results with columns 'sensor_num', 'mean', 'std_dev', and 'axis'.
        
        Returns:
            A tuple containing a list of unique failed sensor numbers, and a boolean for success.
        """
        if cal_df.empty:
            logging.error("Validation failed: The calibration DataFrame was empty.")
            return (False, None)
        
        # Use boolean indexing to find all rows that meet EITHER failure condition
        failed_df = cal_df[(cal_df['mean'] == 0) | (cal_df['std_dev'] == 0)]
        
        if not failed_df.empty:
            logging.warning("VALIDATION FAILED for the following sensors/axes:")
            for _, row in failed_df.iterrows(): # ite rows lets youy loop through a dataframe row by row, guives row index and row data as pandas series
                if row['mean'] == 0:
                    logging.warning(f"  - Sensor {row['sensor_num']}, Axis {row['axis']}: Mean is zero.")
                if row['std_dev'] == 0:
                    logging.warning(f"  - Sensor {row['sensor_num']}, Axis {row['axis']}: Std Dev is zero.")

            # Get the unique sensor numbers that had at least one failure
            failed_sensor_nums = list(np.unique(failed_df['sensor_num']))
            return (False, failed_sensor_nums)
                
        logging.info("Calibration results passed validation.")
        return (True, None) # keep it consistent and for this function to always return a tuple




    def abnormal_high_magnitude_check(self, uid, raw_values: np.ndarray, threshold=3.5, use_log=True) -> bool:
        """ small helper function for checking abnormally high magnitude values in raw data
        Should also be used in raw_data_check_function
        
        Detects outliers in raw_values using the Median Absolute Deviation (MAD) method.
            Args:
                raw_values (np.array): Array of raw sensor values.
                threshold (float): Modified z-score threshold to identify outliers.
                use_log (bool): Whether to apply logarithmic scaling to the raw values.
            Returns:
            True if no abnormally high magnitude values are detected, False otherwise. (boolean)"""
        logging.debug(f"Performing abnormally high magnitude check on UID:{uid}")

        # Detect outliers using modified z-score method:
        # firstly sort data
        sorted_values = np.sort(raw_values)

        if use_log:
            y = np.log1p(np.abs(sorted_values)) # log scale for wide-range data
        else:
            y = sorted_values.copy()
        
        median = np.median(y)
        mad_y = np.median(np.abs(y - median)) # median absolute deviation
        # Avoid division by zero if mad_y is zero (rare but safe) (only happens if all values are identical)
        if mad_y == 0:
            raise CALIBRATION_CHECK_ERROR(f"Calibration check failed for UID:{uid} due to zero MAD value, indicating no variation in raw data values | VERY UNLIKELY.")
        
        for values in y:
            if values == 0:
                continue # skip zero values to avoid false positives
            modified_z_scores = 0.6745 * (values - median) / mad_y
            if np.abs(modified_z_scores) > threshold:
                logging.warning(f" CONFIGURATION FAILED: Sensor UID:{uid} has abnormally high raw data values: {raw_values}, value trigger: {values} with modified z-score: {modified_z_scores}")
                return False
        logging.info(f"No abnormally high raw data values detected for UID:{uid}, check passed")
        return True

    
# CHECK FUNCTIONS SHOULD JUST RETURN BOOLEAN SUCCESS/FAILURE SUCCESS == TRUE, FAILURE == FALSE

    def raw_data_check(self, ipx: IPXSerialCommunicator, uid:int, sensor_index: list, num_readings: int = 5) -> tuple [bool, np.ndarray]:
        """Checks a sensors raw data ouptus, and ensures that the values are changing
        Secondary verification step after zero mean/ std dev are detected
        Should really be called stuck sensor and abnormal magnitude check
        Args:
            ipx (IPXSerialCommunicator): An instance of the IPXSerialCommunicator class.
            uid (int): The UID of the sensor to check.
            sensor_index (list): List of sensor indexes to monitor for changes.
            num_readings (int): Number of raw data readings to take for comparison.
        Returns:
            True if the raw data check passes, False otherwise."""
        num_no_changes_allowed = 3 # number of no change instances allowed before failing the check
        logging.info(f"Performing raw data check on UID:{uid}")
        raw_readings_list = []
        for i in range(num_readings):
            raw_readings_list.append(ipx.get_raw(uid=uid, data_type='array')) # get initial raw data
            time.sleep(0.5) # wait a bit before next measurment

        raw_values = raw_readings_list[0] # return the first set of raw values for reference later on

        # before comparing the readings, do an abnormally high magnitude check, just for the first tuple that is returned
        if not self.abnormal_high_magnitude_check(uid=uid, raw_values=raw_readings_list[0]):
            logging.error(f" Raw data check failed for UID:{uid} due to abnormally high magnitude values")
            return False, raw_values
        logging.info(f" Abnormally high magnitude check passed for UID:{uid}, proceeding to no change check")

        # then need to check the readings for changes by comparing indexes of all measurements
        first = raw_readings_list[0] # first tuple of raw measurments in the list
        pairs = list(zip(raw_readings_list[:-1], raw_readings_list[1:])) # create list of tuple pairs to compare so tuple 1,2 then 2,3 then 3,4 etc
        for pair in pairs:
            tuple_1, tuple_2 = pair # split data tuples into seperate tuples
            len_tuple = len(tuple_1)
            logging.debug(f"comparing tuples : {tuple_1} and {tuple_2}")

            num_no_change = 0 # reset counter for each pair comparison
            for i in sensor_index: # iterate over the tuple values and compare them by index, if same value detected, increment counter by 1
                if tuple_1[i] == tuple_2[i]:
                    num_no_change += 1

                    logging.debug(f"No change detected at index {i} between readings: {tuple_1} and {tuple_2}. Value was {tuple_1[i]}")
            if num_no_change > num_no_changes_allowed:
                logging.warning(f" Raw data check failed for UID:{uid}, {num_no_change} instances of no change detected between readings")
                return False, raw_values
        else:
            logging.info(f" Raw data check passed for UID:{uid}")
            return True, raw_values

# debating whether i want the magnitude check function to do a get raw or not.





    # def abnormal_high_magnitude_check(self, ipx: IPXSerialCommunicator, uid:int , max_raw_value:500) -> bool:
    #     """ Small helper function for checking abnormally high magnitude values in raw data
    #     Changed to just check on one sensor rather than loop through all uids"""


    #     logging.debug(f"Performing abnormally high magnitude check on UID:{uid}")
    #     raw_values = ipx.get_raw(uid=uid, data_type='array')
        
    #     if np.any(np.abs(raw_values) > max_raw_value):
    #         logging.error(f" CONFIGURATION FAILED: Sensor UID:{uid} has abnormally high raw data values: {raw_values}")
    #         return False
    #     else:
    #         logging.debug(f"No abnormally high raw data values detected for UID:{uid}")
    #         return True

# need to clear up logic, i think they should return the uids of the failed sensors and a boolean for success/failure
# I also think i should add the .configurate command back but only to reconfigurate a specific sensor if needed (in case of a failed sensor during initial configuration)       

"""------------------------------------------------------------------------------------------------------------------------------------------------------"""

""" The general structure for configuration is:
1. First of all get UIDS
2. Then set all default parameters for each sensor
3. Then calibrate each sensor one by one, validating the results after each calibration
4. Do abnormal raw data check to ensure no abnormally high magnitude values present
5. Finally set baud rate to 9600 for all sensors

""" 


