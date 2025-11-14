import json
import datetime
import logging
import pandas as pd
import numpy as np
import os # for path and directory operations
import re # for cleaning filename

# graph stuff
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
    



# ------------------------------    THIS CLASS IS AI GENERATED FOR MANAGIN PLOTTING OF STD AND MEANS GRAPHS ------------------------------

class PlotManager:
    """ Manages plotting of cal_df graphs using plotly
    Means and std dev graph combined"""

    def create_calibration_plots(self, cal_df: pd.DataFrame, uid: int) -> tuple[go.Figure, go.Figure]:
        """ Creates and saves calibration plots for a given sensor's calibration dataframe
        Creates two plots: one for mean and one for std dev
        Args:
        cal_df (pd.DataFrame): DataFrame containing calibration data with 'Position', 'Mean', 'StdDev' columns
        uid (str): UID of the sensor for labeling the plot
        Returns:
        fig: Plotly figure object
        """
        try:
            # Create two separate figures, each with 3 subplots (one for each axis)
            fig_mean = make_subplots(
                rows=3, cols=1,
                subplot_titles=("X-Axis Mean", "Y-Axis Mean", "Z-Axis Mean"),
                vertical_spacing=0.1
            )
            
            fig_std = make_subplots(
                rows=3, cols=1,
                subplot_titles=("X-Axis Std Dev", "Y-Axis Std Dev", "Z-Axis Std Dev"),
                vertical_spacing=0.1
            )

            # Plot data for each axis
            for axis_num in range(3):
                # Filter the DataFrame for the current axis
                axis_data = cal_df[cal_df['axis'] == axis_num]
                
                # Plot means
                fig_mean.add_trace(
                    go.Scatter(
                        x=axis_data['sensor_num'],
                        y=axis_data['mean'],
                        name=f"Axis {axis_num}",
                        mode='lines+markers'
                    ),
                    row=axis_num + 1, col=1
                )

                # Plot standard deviations
                fig_std.add_trace(
                    go.Scatter(
                        x=axis_data['sensor_num'],
                        y=axis_data['std_dev'],
                        name=f"Axis {axis_num}",
                        mode='lines+markers'
                    ),
                    row=axis_num + 1, col=1
                )

            # Update layouts for both figures
            fig_mean.update_layout(
                title=f"Sensor {uid} - Calibration Means",
                height=900, showlegend=True, template="plotly_white"
            )
            fig_std.update_layout(
                title=f"Sensor {uid} - Calibration Standard Deviations",
                height=900, showlegend=True, template="plotly_white"
            )

            return fig_mean, fig_std

        except Exception as e:
            logging.error(f"Error creating plots for UID {uid}: {e}", exc_info=True)
            return None, None
        

    def save_plot(self, fig: go.Figure, filename: str, target_dir: str = None):
        """Saves a Plotly figure to an HTML file."""

        try:
            os.makedirs(target_dir, exist_ok=True) # save to same directory as json reports etc.
            filepath = os.path.join(target_dir, filename)
            fig.write_html(filepath)
            logging.info(f"Saved plot to {filepath}")
        except Exception as e:
            logging.error(f"Error saving plot {filename}: {e}", exc_info=True)




#--------------------------------- END OF PLOTTING CLASS ---------------------------------


# ------------------------------ REPORT GENERATOR CLASS FOR JSON REPORTS + SAVES CAL_DF AND CALLS PREVIOUS CLASS TO GENERATE GRAPHS ------------------------------
class ReportGenerator:
    """ Creates and manages JSON "Digital Birth Certificate" for each IPX configuration session"""

    def __init__(self, port:str,
                 customer_order: str,
                 manufacturing_order: str,
                 string_description: str,
                 operator:str):
        self.start_time = datetime.datetime.now()

        # ------------------------------------
        self.port = port.upper()
        self.customer_order = customer_order.upper()
        self.manufacturing_order = manufacturing_order.upper()
        self.string_description = (re.sub(r'[^\w\-_.]', '_', string_description)).upper()
        self.operator = operator.upper()
        
        # Ensure the strings are in a consistent format (e.g uppercase)

        # -------- FILESAVING LOGIC --------
        #1. Define base path and direcory for saving reports
        base_dir = "production_runs"

        #2. create nested directory path:
        self.target_dir = os.path.join(base_dir, self.customer_order, self.manufacturing_order, self.string_description) # this should create a subdirectory known as string description
        # this should also include checks to make sure that the string stays consistent, using upper lower etc.

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
        sane_filename = self.string_description

        #5. create full final filepath for saving full report:
        self.json_filepath = os.path.join(self.target_dir, f"{sane_filename}_config_report.json")
        self.txt_filepath = os.path.join(self.target_dir, f"{sane_filename}_alias_uid_list.txt")
        #-------- END FILESAVING LOGIC --------


        # Create an instance of PlotManager for saving plots
        self.plot_manager = PlotManager()





        # Create main dictonary structure, which hold all our data:
        self.report_data = {
            "metadata": {
                "CO number": self.customer_order,
                "MO number": self.manufacturing_order,
                "String Description": self.string_description,
                "Report ID": self.start_time.strftime("%Y%m%d_%H%M%S"),
                "Start Time": self.start_time.isoformat(),
                "Operator": self.operator,
                "COM Port": self.port,
                "Status": "In Progress",
        },
        "Sensors" : {} # All sensor specific data will go in here, keyed by UID
        }

        # Need unique filename based on the metadata
        self.filename = f"{self.string_description}_config_report.json"
    
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
            with open(self.json_filepath, 'w') as json_file:
                json.dump(self.report_data, json_file, indent=4, cls=CustomJSONEncoder)# json.dump basically writes the data to file
            logging.info(f"Configuration report saved to {self.json_filepath}")
        except IOError as e:
            logging.error(f"Failed to save configuration report: {e}")
        except TypeError as e:
            logging.error(f"Failed to serialize report data to JSON. Check Data types: {e}")


    # create a function to get the txt file ready, and then another function to save
    def create_txt_content(self, aliases_and_uids_list: list[tuple[str, str]]):
        """ New method to save a txt file with aliases and UIDs (would be good for UID requests)"""
        try:
            logging.debug("Generating txt file with aliases and UIDs")
            logging.debug(f"Received alias and UID list: {aliases_and_uids_list}")
            # Create a list to hold the lines of the txt file
            txt_lines = []
            meta = self.report_data["metadata"] # get all the metadata
            logging.debug(f"Retrieved metadata for txt file: {meta}")
            # now sort into header information
            txt_lines.append(f"Customer Order: {meta['CO number']}")
            txt_lines.append(f"Manufacturing Order: {meta['MO number']}")
            txt_lines.append(f"String Description: {meta['String Description']}")
            txt_lines.append("\n" + "-" * 40)
            
            for alias, uid in aliases_and_uids_list:
                txt_lines.append(f"\n Alias: {alias}")
                txt_lines.append(f" UID: {uid}")
                txt_lines.append("-" * 30)
            return "\n".join(txt_lines)  # Join all lines with newlines to get final string
        except Exception as e:
            logging.error(f"Error generating txt content: {e}")
            return "Error Could not generare txt content, check logs"
        
    def save_txt_file(self, txt_content: str):
        """ takes the generated txt content and saves it to a file in the same directory as the json report"""
        logging.debug(" Saving txt file with aliases and UIDs")
        content_to_save = txt_content # get the content to save
        try:
            with open(self.txt_filepath, 'w') as txt_file:
                txt_file.write(content_to_save)
                logging.debug(f"Alias and UID list saved to {self.txt_filepath}")
        except Exception as e:
            logging.error(f"Error saving txt file: {e}")



    def save_calibration_files(self, uid: int, cal_df: pd.DataFrame):
        """ Saves calibration df to csv, and generates the .html plot files"""
        if cal_df is None or cal_df.empty:
            logging.warning(f"No calibration data to save for UID {uid}")
            return
        
        #1. Save cal_df to CSV
        uid_str = str(uid)
        try:
            csv_filename = f"sensor_{uid_str}_calibration_data.csv"
            csv_filepath = os.path.join(self.target_dir, csv_filename)
            cal_df.to_csv(csv_filepath, index=False)
            logging.debug(f"Saved calibration data for UID {uid_str} to {csv_filepath}")
        except Exception as e:
            logging.error(f"Error saving calibration CSV for UID {uid_str}: {e}", exc_info=True)

        #2. Generate and save plots using plotmanager class
        fig_mean, fig_std = self.plot_manager.create_calibration_plots(cal_df, uid_str)

        self.plot_manager.save_plot(fig_mean, f"sensor_{uid_str}_calibration_means.html", self.target_dir)
        self.plot_manager.save_plot(fig_std, f"sensor_{uid_str}_calibration_stddevs.html", self.target_dir)



#--------------------------------- END OF REPORT GENERATOR CLASS ---------------------------------
        



