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

# import files for JSON report generation
from report_generator import ReportGenerator

# -----    CUSTOM ERRORS FOR USE IN THIS SCRIPT  -----
class UserAbortError(Exception):
    """ Custom exception to indicate user aborted operation """
    pass






baudrate = int(input("Enter baud rate (default 9600): ") or "9600")


# setup log level
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Function for getting order details from user:
def get_order_details():
    """Gets customer order details from user input."""
    customer_order = input("Enter Customer Order (CO) number: ").strip()
    manufacturing_order = input("Enter Manufacturing Order (MO) number: ").strip()
    string_description = input("Enter String Description: ").strip()
    operator = input("Enter Operator Name/ID: ").strip()
    return customer_order, manufacturing_order, string_description, operator



def get_initial_settings():
    """ Gets com port and number of sensors from user.
    Get initial settings from cmd arguments or use defaults."""
    try:
        # real app would list available ports
        com_port = input("Enter COM port (default COM8): ") or "COM8"
        num_sensors_int = int(input("Enter number of input sensors: "))
        return com_port, num_sensors_int
    except (ValueError, KeyboardInterrupt):
        logging.error("Invalid input or operation cancelled.")
        sys.exit(1)
        return None, None


def get_com_port():
    """Helper function to get COM port from user."""
    com_port = input("Enter COM port (default COM8): ") or "COM8"
    return com_port



def list_uids():
    """Helper function to list UIDs of connected sensors."""
    port = get_com_port()
    with IPXSerialCommunicator(port=port, baudrate=baudrate, verify=True) as ipx:
        uids = ipx.list_uids(data_type='list')
        logging.info(f"Connected sensor UIDs: {uids}")
        return uids


    

    

#
def prompt_user_on_cal_failure(uid:int) -> str:
    """
    Handles user input when a calibration failure occurs
    """
    while True:
        choice = input(
                f"\n CRITICAL: Calibration for UID {uid} failed.\n"
                "   Choose an option:\n"
                "   [1] Retry calibration for this sensor\n"
                "   [2] Skip this sensor and continue\n"
                "   [3] Abort the entire configuration\n"
                "   Enter your choice (1, 2, or 3): "
            ).strip()
        if choice == '1': return "retry"
        if choice == '2': return "skip"
        if choice == '3':
            # FOR ABORTING AND RETURNING TO MAIN MENU
            raise UserAbortError("User aborted configuration during calibration failure.")
        print("Invalid choice. Please enter 1, 2, or 3.")

def prompt_user_on_other_failure() -> str:
    """
    Handles user input when a non-calibration failure occurs
    """
    while True:
        choice = input(
                "\n ERROR: An error occurred.\n"
                "   Choose an option:\n"
                "   [1] Retry the operation\n"
                "   [2] Skip and continue\n"
                "   [3] Abort the entire operation\n"
                "   Enter your choice (1, 2, or 3): "
            ).strip()
        if choice == '1': return "retry"
        if choice == '2': return "skip"
        if choice == '3': 
            # FOR ABORTING AND RETURNING TO MAIN MENU
            raise UserAbortError("User aborted operation during error handling.")
        print("Invalid choice. Please enter 1, 2, or 3.")


def retry_on_failure(operation_func, prompt_func, success_message: str = None, *args, **kwargs):
    # This function doesnt handle exceptions, only checks for False/None return values, a bit simpler than retry_on_exception
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
                raise UserAbortError("Configuration aborted by user.")
        else:
            # Operation successful
            if success_message:
                logging.info(success_message)
            return result
        

def retry_on_exception(operation_func, prompt_func, handled_exceptions=(Exception,), 
                       success_message: str = None, retry_delay: float = 1.0, *args, **kwargs):
    # This function handles exceptions raised by operation_func, may be better to ensure that if there is a failure that it raises an exception whenever
    """
    Generic retry handler for operations that may raise exceptions.
    
    Args:
        operation_func: The function to execute (e.g., configurator._verify_sensor_count)
        prompt_func: Function or string to decide what to do on failure ('retry', 'skip', or 'abort')
        handled_exceptions: Tuple of exceptions to catch and handle (default: Exception)
        success_message: Optional message to log on success
        retry_delay: Seconds to wait before retrying
        *args, **kwargs: Arguments passed to operation_func
    
    Returns:
        The result from operation_func if successful, or None if skipped.
    """
    while True:
        try:
            result = operation_func(*args, **kwargs)
            if success_message:
                logging.info(success_message)
            return result  # ✅ success
        except handled_exceptions as e:
            logging.error(f"Operation failed with exception: {e}")

            choice = prompt_func() if callable(prompt_func) else prompt_func

            if choice == "retry":
                logging.info(f"Retrying operation after {retry_delay}s...")
                time.sleep(retry_delay)
                continue
            elif choice == "skip":
                logging.warning("User chose to skip this operation.")
                return None
            elif choice == "abort":
                logging.critical("User aborted operation.")
                raise UserAbortError("Configuration aborted by user.")
            else:
                logging.warning(f"Unknown choice '{choice}', aborting by default.")
                raise UserAbortError("Configuration aborted due to invalid user choice.")
        except Exception as e:
            # Catch any unexpected error not in handled_exceptions
            logging.critical(f"Unhandled error: {e}", exc_info=True)
            raise e


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
def run_configuraton_flow():
    """Handles full sensor configuration flow."""  
    # get all the initial settings from user
    com_port, num_sensors_int = get_initial_settings()
    co, mo, string_description, operator = get_order_details()
    # initialise the report generator
    report = ReportGenerator(
        port = com_port,
        customer_order = co,
        manufacturing_order = mo,
        string_description = string_description,
        operator = operator
    )



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
            
            # could add failure rerpot?
            if uids_list is None:
                logging.error("Sensor detection failed or was skipped. Exiting configuration.")
                return

            
            report.set_detected_sensors(uids_list) # NEW log detected UIDs to report:

            #2. apply default parameters to all sensors:

            configurator.set_default_parameters(ipx, uids_list)

            #3. run calibration with retry handling:
            for uid in uids_list:
                while True:
                    # use try loop to handle unexpected errors during calibration
                    try:
                        cal_df = ipx.calibrate(uid)
                        # validate cal_result
                        result_or_num_failed = configurator.validate_calibration_results(cal_df)
                        # unpack the  result_or_num_failed tuple of format ( bool, failed_sensor_nums| None)
                        sucess_bool , failed_sensor_nums = result_or_num_failed

                        if sucess_bool == True:
                            # ---- INITIAL CALIBRATION CHECK PASSED ----
                            # we should also do the abnormal high magnitude check here as well, if rawdatacheck is not called 
                            raw_data = ipx.get_raw(uid=uid, data_type='array')
                            if not configurator.abnormal_high_magnitude_check(uid, raw_values=raw_data): # if result is false run this loop
                                choice = prompt_user_on_cal_failure(uid)
                                if choice == "retry":
                                    logging.info(f"Retrying calibration for UID {uid} due to abnormal high magnitude...")
                                    continue
                                elif choice == "skip":
                                    logging.warning(f"User chose to skip retrying calibration for UID {uid}.")
                                    break  # exit while loop to skip
                                elif choice == "abort":
                                    logging.warning("User aborted configuration.")
                                    raise UserAbortError("Configuration aborted by user.") # maybe not system exit, return to main menu
                            logging.info(f"Abnormal high magnitude check passed for UID {uid}")
                            logging.info(f"Calibration successful for UID {uid}")
                            break  # exit while loop on success

                        # no need for raw data check if it didnt fail
                        # ------ INITIAL CALIBRATION CHECK FAILED (DUE TO ZERO MEAN/STD DEV) ------
                        else:
                            result2 = configurator.raw_data_check(ipx=ipx, uid=uid, sensor_index=failed_sensor_nums)
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
                                    raise UserAbortError("Configuration aborted by user.") # maybe not system exit, return to main menu
                                
                                # if we reach here, it means we need to handle error and give user option to retry/skip/abort


                        

                    except Exception as e: # if we get an error do we want to retry this calibration?
                        logging.error(f"An error occurred during calibration for UID {uid}: {e}", exc_info=True)
                        choice = prompt_user_on_cal_failure(uid)

                        if choice == "retry":
                            logging.info(f"Retrying calibration for UID {uid}...")
                            continue
                    
                        elif choice == "skip":
                            logging.warning(f"User chose to skip retrying calibration for UID {uid}, moving on to next sensor")
                            break  # exit while loop to skip

                        elif choice == "abort" or choice: # or choice incase user inputs something else, so will always abort
                            logging.warning("User aborted configuration.")
                            raise UserAbortError("Configuration aborted by user.")
            
            #4. now check for abnormal high magnitude raw data across all sensors (after configuration):
            # the only thing is that we are already doing a raw data check and then doing the abnomalous high magnitude check, we should integrate this into the raw data check function?
            # The abnormal high magnitude check should be integrated during the calibration loop, as we can choose to re-calibrate a function an abnormal mag is present
                    
            #5. set final baud rate to 9600 for all sensors:
            final_baud = IPXCommands.Default_settings.Baud_rate
            logging.info(f"Setting baud rate for all devices to {final_baud}")
            for uid in uids_list:
                ipx.set_baud(uid=uid, baud=final_baud)
            logging.info(f"Extensometer configuration successful")  
            
        
        with IPXSerialCommunicator(port=com_port, baudrate=final_baud, verify=True) as ipx:
            # Final get status to store in the report
            for uid in uids_list:
                final_status = ipx.get_status(uid=uid, data_type='dict')
                report.add_sensor_data(uid=uid, data_key='final_status', data_value=final_status)
                logging.debug(f"Successfully retrieved final status for UID {uid}, final status: {final_status}")
            
            # save final report:
            report.save_report(final_status="Success")

            
                # Try to catch any unexpected errrors
    except(IPXSerialError,RuntimeError) as e:
        logging.critical(f" CONFIGURATION FAILED: A critical error occurred: {e}")
        return False
        
    except Exception as e:
        # Catch any other unexpected errors
        logging.critical(f"CONFIGURATION FAILED: An unexpected error occurred: {e}", exc_info=True)
        return False
    

def initial_uid_update():
    """ Function for renaming the UIDs of sensors initially. Automatically renames sensors to 
    sequential UIDs starting from 1 based on the number of sensors detected."""
    logging.info("--- Starting initial UID update session ---")
    com_port = get_com_port() # _ as we only need com_port here
    if not com_port:
        logging.error("Invalid COM port")
        return
    while True:
        with IPXSerialCommunicator(port=com_port, baudrate=baudrate, verify=True) as ipx: # instantiate communicator
            uids_list = retry_on_exception(operation_func=ipx.list_uids, prompt_func=prompt_user_on_other_failure, data_type='list')# use retry on exception to get uuds as list 
            
            if uids_list is None: # just for catching errors, should already be integrated into ipx serial communicator class
                logging.error("Sensor detection failed or was skipped. Exiting UID update.") # slight error catch
                return
            logging.info(f"Detected {len(uids_list)} sensors. Proceeding to update UID of last detected sensor.")
            print(uids_list)
            last_uid = uids_list[-1] # get last element in uid list
            new_uid = len(uids_list)  # sequential UID starting from 1
            confirm = input(f"Press Enter to set UID of sensor with current UID {last_uid} to new UID {new_uid}... or abort (type 'abort'): or type 'retry' retry uid update ").strip().lower()
            if confirm == "": # proceed to next, and rename uid
                ipx.set_uid(current_uid=last_uid, new_uid=new_uid) # set uid to new uid
                logging.info(f"Successfully updated UID from {last_uid} to {new_uid}")

            elif confirm == "abort":
                raise UserAbortError("UID update aborted by user.") # need to change all system exits
            elif confirm == "retry" or confirm:
                logging.info("Retrying UID update...")
                continue

            logging.info("Proceeding to next UID update..., Please press enter when ready.")
            confirm = input("Press Enter to continue updating the next sensor UID, or type 'exit' to finish: ").strip().lower()
            if confirm == "":
                continue
            if confirm == "exit" or confirm:
                logging.info("UID update session completed by user.")
                break

        return

            


            


            






        
def main_menu():
    while True:
        # Clear the terminal screen ('cls' for Windows, 'clear' for macOS/Linux)

        print("Select an option:")
        print("cls for clearing the terminal")
        print("1. Update Sensor UIDs via Barcode Scanner")
        print("2. Run Full Sensor Configuration")
        print("3. Initial UID Update (sequential UIDs starting from 1)")
        print("4. List uids of connected sensors")

        choice = input("Enter your choice (1, 2, 3, 4): ").strip()
    

        try:
            if choice == "cls":
                os.system('cls' if os.name == 'nt' else 'clear')
            elif choice == '1':
                run_uid_update_flow()
            elif choice == '2':
                run_configuraton_flow()
            elif choice == '3':
                initial_uid_update()
            elif choice == '4':
                list_uids()
            else:
                print("Invalid choice. Please enter 1,2,3,4.")
            time.sleep(3) # brief pause before returning to main menu

        except Exception as e:
            logging.error(f"An error occurred: {e}", exc_info=True)
            time.sleep(5)  # brief pause before returning to main menu
            continue

        
        except UserAbortError as e:
            logging.warning(f"Operation aborted by user: {e}")
            time.sleep(5)  # brief pause before returning to main menu
            continue  # Return to main menu




            






if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        logging.info("Program terminated by user (Ctrl+C)")
    except Exception as e:
        logging.critical(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)



