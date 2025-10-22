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


    
    def _send_and_receive_listen(self, command:str, listen_duration: float = 0.5, ) -> str:
        """ purely for sending command to IPX device, and receiving response
        Sends command and listens until no new data is received, or 
        listen_duration is exceeded"""
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

        response = all_responses.decode("UTF-8").strip()
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
        # 1. block and wait for the first byte to arrive
        first_byte = self.connection.read(1)
        response = bytearray(first_byte)  # start with the first byte we already read
        while self.connection.in_waiting > 0:
            response.extend(self.connection.read(self.connection.in_waiting)) # read bytes waiting and add to response byte array
        response = response.decode("UTF-8").strip()
        logging.info(f"Received response: {response}")
        return response





    
    def list_uids(self) -> str:
        """ Lists all connected IPX device UIDs """
        command = IPXCommands.Commands.list_uids
        response = self._send_and_receive_listen(command)
        # parse response to extract UIDs
        return(response)
    

    def get_status(self, uid: int) -> str:
        """ Gets status of IPX device with given UID """
        command = IPXCommands.Commands.get_status.format(uid=str(uid)) # change uid to str for formatting
        response = self._send_and_receive_listen(command)
        return(response)

    def get_raw(self, uid: int) -> str:
        """ Gets raw data from IPX device with given UID """
        command = IPXCommands.Commands.get_raw.format(uid=str(uid)) # change uid to str for formatting
        response = self._send_and_receive_listen(command)
        return(response)
    
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



