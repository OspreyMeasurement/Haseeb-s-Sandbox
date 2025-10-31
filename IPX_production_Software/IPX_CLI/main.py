# main.py for command line interface 

import logging
import sys
from IPX import IPXSerialCommunicator
from IPX import IPXConfigurator
from IPX import IPXSerialError
import numpy as np
from IPX_Config import IPXCommands
import os
import time



baudrate = int(input("Enter baud rate (default 9600): ") or "9600")


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


def retry_on_failure(operation_func, prompt_func, success_message: str = None, *args, **kwargs):
    """
    Generic retry handler for operations that may fail.
    
    Args:
        operation_func: The function to execute (e.g., configurator._verify_sensor_count)
        prompt_func: The function to call on failure (e.g., prompt_user_on_other_failure)
        success_message: Optional message to log on success
        *args, **kwargs: Arguments to pass to operation_func
    
    Returns:
        The result from operation_func if successful, or None if aborted/skipped
    """
    while True:
        result = operation_func(*args, **kwargs)
        
        if result is False or result is None:
            choice = prompt_func() if callable(prompt_func) else prompt_func
            
            if choice == "retry":
                logging.info("Retrying operation...")
                continue
            elif choice == "skip":
                logging.warning("User chose to skip this operation.")
                return None
            elif choice == "abort":
                logging.warning("User aborted configuration.")
                raise SystemExit("Configuration aborted by user.")
        else:
            # Operation successful
            if success_message:
                logging.info(success_message)
            return result
        

#Helper function for displaying UIDs:
def display_uid_table(mappings, all_uids):
    """Clears the terminal and displays the current UID mapping table."""
    # Clear the terminal screen ('cls' for Windows, 'clear' for macOS/Linux)
    os.system('cls' if os.name == 'nt' else 'clear') 
    
    print("--- UID Update In Progress ---")
    print(f"{'Old UID':<15} -> {'New UID':<10}")
    print(f"{'-------':<15}    {'-------':<10}")

    # Display mappings that have already been entered
    for item in mappings:
        print(f"{item['old']:<15} -> {item['new']:<10}")

    # Display remaining UIDs that haven't been mapped yet
    mapped_uids = [item['old'] for item in mappings]
    remaining_uids = [uid for uid in all_uids if uid not in mapped_uids]
    for uid in remaining_uids:
        print(f"{uid:<15} -> {'(pending scan)':<10}")
    print("-" * 30)




# function for updating sensor UIDs via barcode scanner
def run_uid_update_flow():
    """Handles UID updating via barcode scanner input."""
    logging.info("--- Starting UID update session via barcode scanner ---")
    com_port, num_sensors_int = get_initial_settings() # _ as we only need com_port here
    if not com_port or not num_sensors_int:
        logging.error("Invalid COM port or number of sensors.")
        return
    configurator = IPXConfigurator(port=com_port, initial_baudrate=baudrate)
    try:
        with IPXSerialCommunicator(port=com_port, baudrate=baudrate, verify=True) as ipx:
            # UID updating logic here
            logging.info("Discovering connected sensors...")
            # Step 1: Verify sensor count with automatic retry handling
            uids_list = retry_on_failure(
                operation_func=configurator.verify_sensor_count,
                prompt_func=prompt_user_on_other_failure,
                success_message=f"Successfully detected {num_sensors_int} sensors",
                ipx=ipx,
                num_sensors=num_sensors_int
            )

            uid_mappings = [] # list will store our proposed uid changes

            if uids_list is None: # small check to ensure we have uids
                logging.error("Sensor detection failed or was skipped. Exiting UID update.")
                return
            
            for old_uids in uids_list:
                display_uid_table(uid_mappings, uids_list) # display the uid table before each scan

                new_uid_str = input(f"Scan new UID for sensor with Old UID (Top to bottom): {old_uids}: ")
                
                try:
                    new_uid = int(new_uid_str) # convert to int to
                    # add to mapping list
                    uid_mappings.append({'old': old_uids, 'new': new_uid})
                    logging.info(f"Mapped Old UID {old_uids} to New UID {new_uid}")
                except ValueError:
                    logging.error(f"Invalid UID scanned: {new_uid_str}. Please try again.")
                    continue
            # After collecting all mappings, apply them, show the final table

            display_uid_table(uid_mappings, uids_list) # final display

            confirm = input("Confirm applying these UID changes? (y/n): ").strip().lower()
            if confirm != 'y':
                logging.warning("UID update cancelled by user.")
                return
            
            logging.info("Applying UID changes to sensors...")
            for mapping in uid_mappings:
                ipx.set_uid(current_uid=mapping['old'], new_uid=mapping['new'])
                
                logging.debug(f"Set UID from {mapping['old']} to {mapping['new']}")
                time.sleep(0.5)  # small delay to ensure command is processed
                
            # Final verification
            logging.info("Verifying updated UIDs...")
            final_uids = ipx.list_uids(data_type='list')

            expected_uids = [m['new'] for m in uid_mappings]
            if all(uid in final_uids for uid in expected_uids):
                logging.info("✅ SUCCESS: All UIDs were updated successfully.")
            else:
                logging.error("❌ FAILURE: Some UIDs were not updated. Please check the device.")

    except (IPXSerialError, SystemExit) as e:
        logging.critical(f"An error occurred during the UID update process: {e}")





# Main function for handling configuration with user inputs:
def run_configuraton_flow(baudrate, max_raw_value: int = 1000):
    com_port, num_sensors_int = get_initial_settings()
    configurator = IPXConfigurator(port=com_port, initial_baudrate=baudrate)

    logging.info(f"--- Starting new external configuration session on {com_port} for {num_sensors_int} sensors ---")
    try:
        with IPXSerialCommunicator(port=com_port, baudrate=baudrate, verify=True) as ipx:
            # Step 1: Verify sensor count with automatic retry handling
            uids_list = retry_on_failure(
                operation_func=configurator.verify_sensor_count,
                prompt_func=prompt_user_on_other_failure,
                success_message=f"Successfully detected {num_sensors_int} sensors",
                ipx=ipx,
                num_sensors=num_sensors_int
            )
            
            if uids_list is None:
                logging.error("Sensor detection failed or was skipped. Exiting configuration.")
                return
            
            #2. apply default parameters to all sensors:

            configurator.set_default_parameters(ipx, uids_list)

            #3. run calibration with retry handling:
            for uid in uids_list:
                while True:
                    cal_df = ipx.calibrate(uid)
                    # validate cal_result
                    result_or_num_failed = configurator._validate_calibration_results(cal_df)
                    if result_or_num_failed == True:
                        logging.info(f"Calibration successful for UID {uid}")
                        break  # exit while loop on success
                    else:
                        result2 = configurator.raw_data_check(ipx=ipx, uid=uid, sensor_index=result_or_num_failed)
                        if result2 == True:
                            logging.info(f"Calibration successful for UID {uid} after raw data check")
                            break  # exit while loop on success
                        else:
                            choice = prompt_user_on_cal_failure(uid)
                            if choice == "retry":
                                logging.info(f"Retrying calibration for UID {uid}...")
                                continue
                            elif choice == "skip":
                                logging.warning(f"User chose to skip retrying calibration for UID {uid}.")
                                break  # exit while loop to skip
                            elif choice == "abort":
                                logging.warning("User aborted configuration.")
                                raise SystemExit("Configuration aborted by user.")
            
            #4. now check for abnormal high magnitude raw data across all sensors:
            for uid in uids_list:
                raw_values = ipx.get_raw(uid=uid, data_type='array')
                
                if np.any(np.abs(raw_values) > max_raw_value):
                    logging.critical("\n")
                    logging.critical(f" CONFIGURATION FAILED: Sensor UID:{uid} has abnormally high raw data values: {raw_values}")
                    logging.critical("Please run the configuration again or contact support.")
                    logging.critical("\n")
                    
            #5. set final baud rate to 9600 for all sensors:
            final_baud = IPXCommands.Default_settings.Baud_rate
            logging.info(f"Setting baud rate for all devices to {final_baud}")
            for uid in uids_list:
                ipx.set_baud(uid=uid, baud=final_baud)
            logging.info(f"Extensometer configuration successful")  
            return True
            
                # Try to catch any unexpected errrors
    except(IPXSerialError,RuntimeError) as e:
        logging.critical(f" CONFIGURATION FAILED: A critical error occurred: {e}")
        return False
        
    except Exception as e:
        # Catch any other unexpected errors
        logging.critical(f"CONFIGURATION FAILED: An unexpected error occurred: {e}", exc_info=True)
        return False
        
def main_menu():
    print("Select an option:")
    print("1. Update Sensor UIDs via Barcode Scanner")
    print("2. Run Full Sensor Configuration")
    choice = input("Enter your choice (1 or 2): ").strip()
    
    if choice == '1':
        run_uid_update_flow()
    elif choice == '2':
        run_configuraton_flow(baudrate=baudrate)
    else:
        print("Invalid choice. Please enter 1 or 2.")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        logging.info("Program terminated by user.")



