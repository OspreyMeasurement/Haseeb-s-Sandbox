# import relevant libraries
from IPX import IPXSerialCommunicator
from IPX_Config import IPXCommands
import logging
import time
import sys



console_handler = logging.StreamHandler()
file_handler = logging.FileHandler("ipx_log.txt", mode="w")

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

# way it should work is when someone calls IPX.configure, should ask how many senors, and then do all of the functions below
#add interruption to function, e.g cancel button in gui etc







port = 'COM8'
max_retries = 3
retry_delay = 2

num_sensors = int(input("How many sensors are connected?")) # input for num sensors

with IPXSerialCommunicator(port=port, baudrate=9600, verify=True) as ipx: # initialise serial com
    for attempt in range (1, max_retries + 1): # loop that retries so long as the right number of sensors are not detected, keeps retrying as long as doesnt exceed max_retries
        uids_list = ipx.list_uids(data_type='list') # get uids list
        detected_sensors = len(uids_list) # variable to hold the number of detected sensors
        if detected_sensors == num_sensors: # check then number of uids received is the number that is expected, if not retry
            logging.info("Number of expected sensors are connected")
            break
        else:
            logging.error(f"Incorrect number of sensors detected. Detected: {detected_sensors}, expected {num_sensors}")
            time.sleep(retry_delay)# retry delay

    else:
        logging.error("Failed to detect all sensors after multiple retries| Check inputted number of sensors") # log error
        sys.exit("Not enough sensors") # ensure code terminates if there is not enough sensors detected
        


    aliases_and_uids_list = list(zip(range(len(uids_list), 0, -1), uids_list)) # combine uids and list into a tuple in a list, of format (alias, uid)
    logging.debug(f"Aliases and uid list completed succesfully: {aliases_and_uids_list}")
    for alias_uid_tuple in aliases_and_uids_list:
        
        alias = str(alias_uid_tuple[0]) # extract alias
        uid = str(alias_uid_tuple[1]) # extract uid
        logging.info(f"Beginning setting process for sensor uid :{uid}")

        # now need to set all the paramaters, use all default config parameters in the IPXCommands section:
        ipx.set_alias(uid, alias)

        ipx.set_gain(uid, gain=IPXCommands.Default_settings.Gain)

        ipx.set_centroid_threshold(uid, threshold=IPXCommands.Default_settings.Centroid_threshold)

        ipx.set_n_stds(uid=uid, n_stds=IPXCommands.Default_settings.N_stds)

        ipx.set_centroid_res(uid=uid, resolution=IPXCommands.Default_settings.Centroid_res)

        ipx.set_centroid_threshold(uid=uid, threshold=IPXCommands.Default_settings.Centroid_threshold)

        ipx.set_term(uid=uid, termination=IPXCommands.Default_settings.Termination)

        logging.info(f"Setting parameters complete for sensor with uid:{uid}")
    
    logging.info("Setting parameters successful for all sensors")
    for uid in uids_list:
        ipx.calibrate(uid)

    
    for uid in uids_list:
        ipx.set_baud(uid=uid, baud=IPXCommands.Default_settings.Baud_rate)




    





