import json
import datetime
import logging
import pandas as pd
import numpy as np
import os # for path and directory operations
import re # for cleaning filename

""" This file is for generating a json file to keep track of 
IPX device configurations and settings during production"""


class CustomJSONEncoder(json.JSONEncoder):
    """ Custom JSON encoder to help json libary handle special data type
     that it doesnt know how to save
      like pandas dataframes and numpy arrays
      - (Suggested by Gemini)"""
    def default(self, obj):
        if isinstance(obj, pd.DataFrame):
            # Convert DataFrame to JSON friendly dictionary
            return obj.to_dict(orient='records')
        
        if isinstance(obj, np.ndarray):
            # convert numpy array to list
            return obj.tolist()
        return super().default(obj)
    


class ReportGenerator:
    """ Creates and manages JSON "Digital Birth Certificate" for each IPX configuration session"""

    def __init__(self, port:str,
                 customer_order: str,
                 manufacturing_order: str,
                 string_description: str,
                 operator:str):
        self.start_time = datetime.datetime.now()



        # -------- FILESAVING LOGIC --------
        #1. Define base path and direcory for saving reports
        base_dir = "production_runs"

        #2. create nested directory path:
        self.target_dir = os.path.join(base_dir, customer_order, manufacturing_order)

        #3. create directories if they dont exist:
        # os.makedirs(self.target_dir, exist_ok=True), makes full nested path
        try:
            os.makedirs(self.target_dir, exist_ok=True) # exist_ok prevents error if dir already exists
        except OSError as e: # catch any OS errors
            logging.error(f"Faile to create report directory {self.target_dir}: {e}")
            # fall back to saving in current directory?
            self.target_dir = "."
        
        #4. clean string description to make it a valid filename (using re)
        #According to gemini, this will replace any characters like \/ : * ? with an underscore (not valid in filenames)
        sane_filename = re.sub(r'[^\w\-_.]', '_', string_description)

        #5. create full final filepath for saving full report:
        self.full_filepath = os.path.join(self.target_dir, f"{sane_filename}_config_report.json")
        #-------- END FILESAVING LOGIC --------





        # Create main dictonary structure, which hold all our data:
        self.report_data = {
            "metadata": {
                "CO number": customer_order,
                "MO number": manufacturing_order,
                "String Description": string_description,
                "Report ID": self.start_time.strftime("%Y%m%d_%H%M%S"),
                "Start Time": self.start_time.isoformat(),
                "Operator": operator,
                "COM Port": port,
                "Status": "In Progress",
        },
        "Sensors" : {} # All sensor specific data will go in here, keyed by UID
        }

        # Need unique filename based on the metadata
        self.filename = f"{string_description}_config_report.json"
    
    def set_detected_sensors(self, uids: list[str]):
        """ Adds list of detected UIDs to metadata section of report
        These will be the initial UIDs detected at start of configuration session"""
        self.report_data["metadata"]["Detected UIDs"] = uids

    def add_sensor_data(self, uid: int, data_key: str, data_value):
        """ Adds specific piece of data (like 'final status' or 'calibration data'
        to a specific sensor's section in the report
        
        Args: 
        uid (int): UID of the sensor to add data for
        data_key (str): Key/name of the data to add (e.g., 'final_status', 'calibration_data')
        data_value: The actual data value to store
        """

        uid_str = str(uid)  # Ensure UID is a string for JSON compatibility

        # create dictionary for this uid, if its the first time we've seen it
        if uid_str not in self.report_data["Sensors"]:
            self.report_data["Sensors"][uid_str] = {}

        self.report_data["Sensors"][uid_str][data_key] = data_value
        logging.debug(f"Added data for UID {uid_str}: {data_key} = {data_value}")

    def save_report(self, final_status: str):
        """ Finalizes and saves the report to a JSON file
        Completes metadata, such as duration, and saves entire dictionary to JSON file

        Args:
        final_status (str): Overall status of the configuration session ('Success', 'Partial Success', 'Failure')
        """

        self.report_data["metadata"]["status"] = final_status # set final status
        end_time = datetime.datetime.now() # final time
        duration = (end_time - self.start_time).total_seconds() # get duration of configuration

        self.report_data["metadata"]["End Time"] = end_time.isoformat()
        self.report_data["metadata"]["Duration (seconds)"] = duration # save parameters
        # Save to JSON file using the full filepath (includes CO/MO directory structure)
        try:
            with open(self.full_filepath, 'w') as json_file:
                json.dump(self.report_data, json_file, indent=4, cls=CustomJSONEncoder)# json.dump basically writes the data to file
            logging.info(f"Configuration report saved to {self.full_filepath}")
        except IOError as e:
            logging.error(f"Failed to save configuration report: {e}")
        except TypeError as e:
            logging.error(f"Failed to serialize report data to JSON. Check Data types: {e}")
