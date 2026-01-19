# main.py for command line interface 

import logging
import sys
from IPX import IPXSerialCommunicator, IPXConfigurator, IPXSerialError

from IPX_datalogger_tester import IPXModbusTester, IPXGeosenseTester

import numpy as np
import pandas as pd
from IPX_Config import IPXCommands
import os
import time

import Failure_handlers as fh

import os
import platform

import IPX_workflows




# setup_logging(level=logging.INFO)  # Set default log level to INFO


# setup log level
# Default is INFO
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



# import files for JSON report generation
from report_generator import ReportGenerator

# -----    CUSTOM ERRORS FOR USE IN THIS SCRIPT  -----
class UserAbortError(Exception):
    """ Custom exception to indicate user aborted operation """
    pass






baudrate = int(input("Enter baud rate (default 115200): ") or "115200")
com_port = input("Enter COM port (default COM5): ") or "COM5"

def get_baudrate():
    """Get current baudrate value.""" # i think this function is redundant now??? not sure tho
    return baudrate

def set_com_port(new_port: str = None):
    """
    Function to change the global COM port setting.
    If new_port is not provided, prompts user for input.
    """
    global com_port
    
    if new_port is None:
        # Prompt user for new COM port
        try:
            print(f"Current COM port: {com_port}")
            user_input = input("Enter new COM port (COM1, COM5, COM8, etc.) or press Enter to keep current: ").strip()
            
            if user_input == "":
                logging.info(f"COM port unchanged: {com_port}")
                return com_port
            
            # Basic validation for COM port format
            if not user_input.upper().startswith('COM'):
                user_input = f"COM{user_input}"  # Add COM prefix if missing
            
            com_port = user_input.upper()
            logging.info(f"COM port updated to: {com_port}")
            return com_port
        
        except KeyboardInterrupt:
            logging.info("COM port change cancelled by user.")
            return com_port
    else:
        # Direct assignment when called programmatically
        com_port = new_port
        logging.info(f"COM port set to: {com_port}")
        return com_port
    


def set_baudrate(new_baudrate: int = None):
    """
    Function to change the global baudrate setting.
    If new_baudrate is not provided, prompts user for input.
    """
    global baudrate
    
    if new_baudrate is None:
        # Prompt user for new baudrate
        try:
            print(f"Current baud rate: {baudrate}")
            user_input = input("Enter new baud rate (9600, 115200, etc.) or press Enter to keep current: ").strip()
            
            if user_input == "":
                logging.info(f"Baud rate unchanged: {baudrate}")
                return baudrate
            
            new_baudrate = int(user_input)
            
            # Validate common baud rates
            valid_rates = [9600, 115200]
            if new_baudrate not in valid_rates:
                confirm = input(f"Warning: {new_baudrate} is not a standard baud rate. Continue? (y/n): ").strip().lower()
                if confirm != 'y':
                    logging.info("Baud rate change cancelled.")
                    return baudrate
            
            baudrate = new_baudrate
            logging.info(f"Baud rate updated to: {baudrate}")
            return baudrate
            
        except ValueError:
            logging.error("Invalid baud rate entered. Must be a number.")
            return baudrate
        except KeyboardInterrupt:
            logging.info("Baud rate change cancelled by user.")
            return baudrate
    else:
        # Direct assignment when called programmatically
        baudrate = new_baudrate
        logging.info(f"Baud rate set to: {baudrate}")
        return baudrate
    

def change_verbosity():
    print("\n----- Change Logging Verbosity ----")
    print(f"Current log level: {logging.getLevelName(logging.getLogger().level)}")
    print("[1] Info (Normal)")
    print("[2] Debug (Verbose)")
    while True:
        choice = input("Select log level (1 or 2): ").strip()
        if choice == '1':
            logging.getLogger().setLevel(logging.INFO)
            print("Log level set to INFO.")
            break
        elif choice == '2':
            logging.getLogger().setLevel(logging.DEBUG)
            print("Log level set to DEBUG.")
            print("Verbose mode enabled. Detailed logs will be shown.")
            break
        else:
            print("Invalid choice.")
            continue
    







        
def main_menu():
    while True:
        # Clear the terminal screen ('cls' for Windows, 'clear' for macOS/Linux)
        print("\n ----------------- Main Menu -----------------------------------")
        print("Software current settings:")
        print(f"Current COM Port: {com_port}")
        print(f"Current Baud Rate: {baudrate} \n")
        print("Select an option:")
        print("cls for clearing the terminal")
        print("1. Update Sensor UIDs via Barcode Scanner")
        print("2. Run Full Sensor Configuration")
        print("3. Initial UID Update (sequential UIDs starting from 1)")
        print("4. List uids of connected sensors")
        print("5. Switch all connected sensors to 115200 baud rate")
        print("6. Change Baud Rate")
        print("7. Change COM Port")
        print("8. Select verbosity level (DEBUG/INFO)")
        print("Ctrl+C to exit")
        choice = input("Enter your choice (1, 2, 3, 4, 5, 6, 7, 8):").strip()
    

        try:
            if choice == "cls":
                os.system('cls' if os.name == 'nt' else 'clear')
            elif choice == '1':
                IPX_workflows.run_uid_update_flow(com_port, baudrate)
            elif choice == '2':
                IPX_workflows.run_configuration_flow(com_port, baudrate)
            elif choice == '3':
                IPX_workflows.initial_uid_update(com_port, baudrate)
            elif choice == '4':
                IPX_workflows.list_uids(com_port, baudrate)
            elif choice == '5': IPX_workflows.switch_all_to_115200(com_port)  # switch all connected sensors to 115200 baud rate
            elif choice == '6': set_baudrate()  # prompt user to change baud rate
            elif choice == '7': set_com_port()  # prompt user to change COM port
            elif choice == '8': change_verbosity()  # change logging verbosity
            else:
                print("Invalid choice. Please enter 1, 2, 3, 4, 5, 6, 7, 8.")
            time.sleep(1) # brief pause before returning to main menu

        except UserAbortError as e:
            logging.warning(f"Operation aborted by user: {e}")
            time.sleep(2)  # brief pause before returning to main menu
            continue  # Return to main menu

        except Exception as e:
            logging.error(f"An error occurred: {e}", exc_info=True)
            time.sleep(2)  # brief pause before returning to main menu
            continue

        





            







if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        logging.info("Program terminated by user (Ctrl+C)")
    except Exception as e:
        logging.critical(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)



