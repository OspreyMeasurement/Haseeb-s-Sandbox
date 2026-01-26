"""Automates discovering ASP sensor UIDs via serial.

Workflow:
- Uses a relay on COM4 to power-cycle all ASP devices and an ASP bus on COM5.
- Opens the bus, sends `op bus 0 ls` to read the first responding UID, stores it,
  then issues a shutdown to every collected UID so only the next device replies
  after the subsequent power cycle.
- Repeats for a user-specified count, saving discovered UIDs to logs/asp_uids_*.json.

Dependencies and setup:
- Python 3 with `pyserial` installed.
- Hardware: relay controllable on COM4 that toggles ASP power, ASP bus reachable on COM5.
- Run directly (`python ASP_uids.py`) and enter the number of sensors to enumerate when prompted.
"""

import serial


import logging
import time
import json
import datetime
from pathlib import Path

""" This script should sequentially get the uids of all connected ASP devices, by
1. Turning all power_outs to 0, and then sending op bus 0 ls (first sensor always on, so will respond), and then power cycling (relay off on) so all devices can turn back on
2. Then the uids we have, we use shutdown command to turn them off ( so they dont respond), then power out again, so next sensor can respond to op bus 0 ls command, and then we repeat"""

relay_com_port = 'COM4'  # COM port for the relay
asp_com_port = 'COM5'    # COM port for the ASP devices




# set logging level to debug
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
# setup logging with time and level

# define communicator class (for handling serial communication) (this is taken straight from IPX.py with minor modifications to the exception handling):
class SerialCommunicator:
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

    def _send_and_receive_listen(self, command:str, listen_duration: float = 0.5, stop_on_string: str = None ):
        """ purely for sending command to IPX device, and receiving response
        Sends command and listens until no new data is received, or 
        listen_duration is exceeded
        This should always return bytes, higher level functions can decode if needed
        Can now stop early, if a specific terminator string is found in the response stream"""
        if not self.connection:
            logging.error("ERROR: Not connected")
            raise Exception("Not connected to any serial device.")
        # send command (add prints for debugging)

        # Clear input buffer to ensure we only read the response to *this* command
        self.connection.reset_input_buffer()
        self.connection.reset_output_buffer() # clear output buffer too, just in case
        self.connection.write(command.encode("UTF-8"))
        logging.debug(f"Sent command: {command.strip()}")

        # 1. block and wait for the first byte to arrive
        first_byte = self.connection.read(1)
        if not first_byte:
            logging.error("No response received from device.")
            raise Exception("No response received from device within the expected timeout.") # didnt recieve response within timeout
        

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
            raise Exception("No response received from device within the expected timeout.") # add this exception for error catching
        return response
    

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







# define function for saving the uids to a json file
def save_list_json(data, folder="logs", prefix="data"):
    Path(folder).mkdir(parents=True, exist_ok=True) # turns folder string into path object and makes the directory if it doesn't exist

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # 20260119_103012 example format, gets current datetime
    path = Path(folder) / f"{prefix}_{ts}.json" # creates full path for the file
    with path.open("w", encoding="utf-8") as f: # opens the file for writing
        json.dump(data, f, indent=2, ensure_ascii=False) # saves the data to the json file with indentation for readability
    return path # returns the path of the saved file



power_out_str = "op bus 0 power_out 0\n" # turns off all outputs on all devices
shutdown_str = "op bus {uid} shutdown 5000000\n" # shuts down device 5000000


# define functions for communication steps + power cycling relay::

def communicate_and_get_uid(communicator):
    """Sends the command to get the uid of the first device on the bus and returns it as an integer"""
    s = communicator._send_and_receive_listen(command = "op bus 0 ls\n", listen_duration = 0.25)
    s = s.decode('utf-8')
    uid = int(s.split(":", 1)[0].strip())
    return uid

def power_off_outputs(communicator):
    """Sends the command to turn off all power outputs on all devices"""
    communicator._send_and_receive_listen(command=power_out_str, listen_duration = 0.25)
    logging.debug("Sent power off command to all devices")

def shutdown_device(communicator, uid):
    """Sends the shutdown command to the device with the given uid"""
    command = shutdown_str.format(uid=uid)
    communicator._send_and_receive_listen(command=command, listen_duration = 0.5)
    logging.debug(f"Sent shutdown command to device with UID: {uid}")

def power_cycle_relay(ser_relay, delay=0.5):
    """Turn relay off and back on after delay"""
    logging.info('Command started')
    ser_relay.write(b"AT+CH1=0") # turn relay off
    
    logging.info('relay switched off')

    time.sleep(delay)
    logging.info('relay switched on')
    ser_relay.write(b"AT+CH1=1") # turn relay back on after small delay




# instantiate an empty list to hold the uids
uids_list = [] 



def safe_list_uids(asp_com_port=asp_com_port, relay_com_port=relay_com_port):
    """Main function to get the uids of all connected ASP devices"""
    relay = None # initialise relay variable for finally block
    uids_list = [] 
    try:
        with SerialCommunicator(port=asp_com_port, baudrate=9600) as communicator:
            while not (s := input("Enter number of expected sensors: ").strip()).isdigit(): print("Not a number!")
            n = int(s)

            # instatntiate serial connection to the relay
            relay = serial.Serial(relay_com_port, baudrate=9600, timeout=1)
            # 1. Clear the Input Buffer (discard received data you haven't read)
            relay.reset_input_buffer()
            # 2. Clear the Output Buffer (abort sending data sitting in the queue)
            relay.reset_output_buffer()

            # relay.close() # open relay serial port
            # relay.open() # open relay serial port
            logging.debug("Relay serial port opened successfully.")

            # start with power cycling the relay/ asp device to ensure all are on
            power_cycle_relay(relay, delay=1.0)
            input(" Did the relay function correctly? Press Enter to continue... ")

            time.sleep(3) # wait for devices to power back on --> OTS issue
            # set all power outs to 0?

            for i in range(n):
                # first power off all outputs
                power_off_outputs(communicator)

                time.sleep(0.2) # increased to 0.4 from 0.2

                # get the uid of the first device on the bus, then append to list
                uid = communicate_and_get_uid(communicator)
                uid = str(uid) # ensure it is string
                uids_list.append(uid)
                logging.info(f"Found UID: {uid}")

                # then power cycle the relay

                power_cycle_relay(relay, delay=1.0)
                time.sleep(0.5)  # wait for devices to power back on

                time.sleep(2.5) # wait for devices to power back on --> OTS issue

                # then shutdown the devices we have uids for
                for uid in uids_list:
                    shutdown_device(communicator, uid)
                    # wait for device to shutdown before next iteration
                    # debug print to confirm shutdown

                    logging.debug(f"Device with UID {uid} should now be shut down.")
                time.sleep(0.5)

            if not uids_list:
                logging.error("No UIDs were found.")
                raise Exception("No UIDs were found.")

            elif len(uids_list) < n:
                logging.error(f"Expected {n} sensors, but only found {len(uids_list)}.")
                raise Exception(f"Expected {n} sensors, but only found {len(uids_list)}.")

            # final power cycle relay to reset ots devices


            else:
                power_cycle_relay(relay, delay=1.0)
                time.sleep(2.5)  # wait for devices to power back on



    except KeyboardInterrupt:
        logging.warning("Process interrupted by user.")

    finally:
        relay.close()
        logging.info("UIDS retrieval process completed")
        logging.info(f"Number of sensors found: {len(uids_list)}")
        logging.info(f"UIDs: {uids_list}")
        
        if uids_list:
            logging.info("Saving UIDs to JSON file...")
            print("UIDS list save to : ", save_list_json(uids_list, folder="logs", prefix="asp_uids") )
        return uids_list
    


if __name__ == "__main__":
    safe_list_uids(asp_com_port=asp_com_port, relay_com_port=relay_com_port)


 



