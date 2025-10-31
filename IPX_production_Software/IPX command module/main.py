# main.py for command line interface 

import logging
import sys
from IPX import IPXSerialCommunicator
from IPX import IPXConfigurator

# setup log level
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_initial_settings():
    """Get initial settings from cmd arguments or use defaults."""
    try:
        # real app would list available ports
        com_port = input("Enter COM port (default COM8): ") or "COM8"
        num_sensors_int = int(input("Enter number of input sensors: "))
        return com_port, num_sensors_int
    except (ValueError, KeyboardInterrupt):
        logging.error("Invalid input or operation cancelled.")
        sys.exit(1)
        return None, None
    

#
def prompt_user_on_cal_failure(uid:int) -> str:
    """
    Handles user input when a calibration failure occurs
    """
    while True:
        choice = input(
                f"\n🛑 CRITICAL: Calibration for UID {uid} failed.\n"
                "   Choose an option:\n"
                "   [1] Retry calibration for this sensor\n"
                "   [2] Skip this sensor and continue\n"
                "   [3] Abort the entire configuration\n"
                "   Enter your choice (1, 2, or 3): "
            ).strip()
        if choice == '1': return "retry"
        if choice == '2': return "skip"
        if choice == '3': return "abort"
        print("Invalid choice. Please enter 1, 2, or 3.")

def prompt_user_on_other_failure() -> str:
    """
    Handles user input when a non-calibration failure occurs
    """
    while True:
        choice = input(
                "\n🛑 ERROR: An error occurred during configuration.\n"
                "   Choose an option:\n"
                "   [1] Retry the operation\n"
                "   [2] Skip this sensor and continue\n"
                "   [3] Abort the entire configuration\n"
                "   Enter your choice (1, 2, or 3): "
            ).strip()
        if choice == '1': return "retry"
        if choice == '2': return "skip"
        if choice == '3': return "abort"
        print("Invalid choice. Please enter 1, 2, or 3.")


# Main function for handling configuration with user inputs:
def run_configuraton_flow():
    com_port, num_sensors_int = get_initial_settings()
    configurator = IPXConfigurator(pot=com_port, initial_baudrate=115200, num_sensors=num_sensors_int)

    logging.info(f"--- Starting new external configuration session on {com_port} for {num_sensors_int} sensors ---")
    try:
        with IPXSerialCommunicator(port=com_port, baudrate=115200, verify=True) as ipx:
        # step 1 is to get the uids list
            uids_list = configurator._verify_sensor_count(ipx, num_sensors_int)
            if ui


