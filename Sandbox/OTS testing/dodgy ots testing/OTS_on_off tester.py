# import relevant modules
# initialise logging script:

import logging
import datetime
import serial
import time # for delays


delays = 2000 # ms to wait between toggling relay     




# initialise logging files etc
current_date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

console_handler = logging.StreamHandler()
file_handler = logging.FileHandler(f"ots_log_{current_date}.txt", mode="w")

# Set log levels
console_handler.setLevel(logging.INFO)
file_handler.setLevel(logging.INFO)

# Create a common format
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Get the root logger and attach both handlers
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)
logger.addHandler(file_handler)




# try loop
try:
    

    # instantiate serial port for relay
    relay = serial.Serial('COM9', baudrate=9600, timeout=2) # instantiate serial object for relay control
    # instnatiate seria port for OTS
    ots = serial.Serial('COM5', baudrate=9600, timeout=2) # instantiate serial object for OTS control

    # 1. Clear the Input Buffer (discard received data you haven't read)
    relay.reset_input_buffer()

    # 2. Clear the Output Buffer (abort sending data sitting in the queue)
    relay.reset_output_buffer()
    ots.reset_input_buffer()
    ots.reset_output_buffer() # discard all data

    relay.close() # close ports after openend
    ots.close() # close ports after openend

    relay.open() # open relay serial port
    logging.info("Relay serial port opened successfully.")
    ots.open()   # open OTS serial port
    logging.info("OTS serial port opened successfully.")

    # cycle relay on/off to make sure relay on
    relay.write(b"AT+CH1=0") # turn relay off
    # time.sleep(1) #wait for 20 ms
    relay.write(b"AT+CH1=1") # turn relay on
    time.sleep(2) # updated this so first read doesnt fail 


    while True:  # infinite loop
        for i in range(delays):

            # convert i from s to ms
            i = i / 1000
            
            
            ots.write(b'op bus 0 ls\n')
            logging.info("Sent 'op bus 0 ls' command to OTS.")
            

            line = ots.readline()

            # logging.info("Waiting 300 ms for OTS to stabilise after relay toggle.")



            
            if line:
                logging.info(f"Raw response from OTS: {line}")
                logging.info(f"Received from OTS: {line.decode('UTF-8').strip()}")
            else:
                logging.warning("No response from OTS. May have failed")


            # now for relay on/off loop

            relay.write(b"AT+CH1=0")
            time.sleep(0.5)
            relay.write(b"AT+CH1=1") # turn relay back on
            time.sleep(i) # short delay to ensure command is sent and to turn relay back on 20 ms delay

            relay.write(b"AT+CH1=0")
            time.sleep(0.5)
            relay.write(b"AT+CH1=1") # turn relay back on
            time.sleep(2) # short delay to ensure command is sent and to turn relay back on 20 ms delay


            logging.info(f"Relay toggled off and on. With delay of {i} seconds.")


            logging.info("----------------------------------------")

except KeyboardInterrupt:
    logging.info("Program interrupted by user. KeyboardInterrupt detected.")

except Exception as e:
    logging.error(f"An error occurred: {e}")

finally: # to ensure serial ports are closed if an error occurs or issue with program
    relay.close() # close relay serial port
    ots.close()   # close OTS serial port
    logging.info("Serial ports closed. Exiting program.")