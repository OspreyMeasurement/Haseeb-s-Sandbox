# This will contain all the workflow functions for IPX Configuration software


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

# import files for JSON report generation
from report_generator import ReportGenerator


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
    


def initial_uid_update(com_port, baudrate):
    """ Function for renaming the UIDs of sensors initially. Automatically renames sensors to 
    sequential UIDs starting from 1 based on the number of sensors detected."""
    try:
        logging.info("--- Starting initial UID update session ---")
        if not com_port:
            logging.error("Invalid COM port")
            return
        while True:
            with IPXSerialCommunicator(port=com_port, baudrate=baudrate, verify=True) as ipx: # instantiate communicator
                uids_list = fh.retry_on_exception(operation_func=ipx.list_uids, data_type='list')# use retry on exception to get uuds as list 
                
                if uids_list is None: # just for catching errors, should already be integrated into ipx serial communicator class
                    logging.error("Sensor detection failed or was skipped. Exiting UID update.") # slight error catch
                    return
                logging.info(f"Detected {len(uids_list)} sensors. Proceeding to update UID of last detected sensor.")
                print(uids_list)
                last_uid = uids_list[-1] # get last element in uid list
                new_uid = len(uids_list)  # sequential UID starting from 1

                if last_uid == IPXCommands.Default_settings.Check_sensor_uid:
                    logging.error("Last detected sensor is a check sensor. Aborting UID update to prevent renaming check sensor.")
                    return
                
                try:
                    confirm = input(f"Press Enter to set UID of sensor with current UID {last_uid} to new UID {new_uid}... or abort (type 'abort'): or type 'retry' retry uid update ").strip().lower()
                except KeyboardInterrupt:
                    logging.info("UID update cancelled by user.")
                    raise fh.UserAbortError("UID update cancelled by user.")
                    
                if confirm == "": # proceed to next, and rename uid
                    ipx.set_uid(current_uid=last_uid, new_uid=new_uid) # set uid to new uid
                    logging.info(f"Successfully updated UID from {last_uid} to {new_uid}")
                    # should also do a get raw check to ensure this sensor is responding correctly before gluing
                    logging.info("Please ensure the raw data looks correct for this sensor: (BELOW)")
                    raw = ipx.get_raw(uid=new_uid, data_type='string')
                    logging.info(f"Raw data sample from newly updated UID {new_uid}: {raw}")



                elif confirm == "abort":
                    raise fh.UserAbortError("UID update aborted by user.") # need to change all system exits
                elif confirm == "retry" or confirm:
                    logging.info("Retrying UID update...")
                    continue

                logging.info("Proceeding to next UID update..., Please press enter when ready.")
                try:
                    confirm = input("Press Enter to continue updating the next sensor UID, or type 'exit' to finish: ").strip().lower()
                except KeyboardInterrupt:
                    logging.info("UID update cancelled by user.")
                    raise fh.UserAbortError("UID update cancelled by user.")
                    
                if confirm == "":
                    continue
                if confirm == "exit" or confirm:
                    logging.info("UID update session completed by user.")
                    break

            return
        
    except KeyboardInterrupt:
        logging.info("UID update session interrupted by user (Ctrl+C). Returning to main menu.")
        raise fh.UserAbortError("UID update session cancelled by user.")
    



def switch_all_to_115200(com_port):    
    """ Function to switch all connected sensors to 115200 baud rate."""
    # Firstly detect sensors on the given com port
    # instantiate configurato
    try:
        num_sensors_int = get_initial_settings()
        configurator = IPXConfigurator() # initialise IPX configurator without port or baudrate, as these will be set in the communicator context manager


        if not com_port or not num_sensors_int:
            logging.error("Invalid COM port or number of sensors.")
            return
        try:
            with IPXSerialCommunicator(port=com_port, baudrate=9600, verify=True) as ipx:
                # Step 1: Verify sensor count with automatic retry handling
                # should use verify sensor count function here
                initial_uids_list, _ = configurator.verify_sensor_count(ipx=ipx, num_sensors=num_sensors_int)
                if initial_uids_list is None:
                    logging.error("incorrect numnber of sensors detected")
                    return
                logging.info(f"Detected {len(initial_uids_list)} sensors: {initial_uids_list}")
                logging.info("Switching all sensors to 115200 baud rate...")


                # now set baud rate for all detected sensors to 115200
                for uid in initial_uids_list:
                    ipx.set_baud(uid=uid, baud=115200)
                    logging.info(f"Set baud rate to 115200 for UID {uid}")

        except Exception as e:
            logging.critical(f"An error occurred while switching baud rates: {e}", exc_info=True)
            raise e # exit function on error
        
        # now all baud rates are set to 115200, we can verify by reconnecting at 115200, and verifying number of sensors again
        try:
            with IPXSerialCommunicator(port=com_port, baudrate=115200, verify=True) as ipx:
                # Step 1: Verify sensor count with automatic retry handling
                # might as well use verify sensor count function
                new_uids_list, _ = configurator.verify_sensor_count(ipx=ipx, num_sensors=num_sensors_int)
                
                logging.info(f"Verifying baud rate change, detected {len(new_uids_list)} sensors: {new_uids_list}")

                if new_uids_list is None:
                    logging.error("Sensor detection failed or was skipped after baud rate change.")
                    return # this code is redundant due to retry on failure function, but just in case who knows

                if len(new_uids_list) != len(initial_uids_list):
                    logging.error("❌ FAILURE: Number of sensors detected after baud rate change does not match initial count.")
                    return # this is lowkey redundant as well
                
                logging.info("✅ SUCCESS: All sensors switched to 115200 baud rate successfully.")
        except Exception as e:
            logging.critical(f"An error occurred while verifying baud rate change: {e}", exc_info=True)
        return
    
    except KeyboardInterrupt:
        logging.info("Baud rate switching session interrupted by user (Ctrl+C). Returning to main menu.")
        raise fh.UserAbortError("Baud rate switching session cancelled by user.")
    



def get_initial_settings():
    """ Gets number of sensors from user.
    Get initial settings from cmd arguments or use defaults."""
    try:
        # COM port is now global, only need number of sensors
        num_sensors_int = int(input("Enter number of input sensors: "))
        return num_sensors_int
    except (ValueError, KeyboardInterrupt):
        logging.error("Invalid input or operation cancelled.")
        raise fh.UserAbortError("Initial settings input cancelled by user.")



def list_uids(com_port, baudrate):
    """Helper function to list UIDs of connected sensors."""
    with IPXSerialCommunicator(port=com_port, baudrate=baudrate, verify=True) as ipx:
        uids = ipx.list_uids(data_type='list')
        logging.info(f"Connected sensor UIDs: {uids}")
        return uids



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
def run_uid_update_flow(com_port, baudrate):
    """Handles UID updating via barcode scanner input."""
    try:
        logging.info("--- Starting UID update session via barcode scanner ---")
        num_sensors_int = get_initial_settings() # _ as we only need com_port here, need verify sensor count as well
        if not com_port or not num_sensors_int:
            logging.error("Invalid COM port or number of sensors.")
            return
        configurator = IPXConfigurator()
        try:
            with IPXSerialCommunicator(port=com_port, baudrate=baudrate, verify=True) as ipx:
                # UID updating logic here
                logging.info("Discovering connected sensors...")
                # Step 1: Verify sensor count with automatic retry handling
                uids_list, _ = fh.retry_on_failure(# _ as we dont need the check_sensor_present value here
                    operation_func=configurator.verify_sensor_count,
                    prompt_func=fh.prompt_user_on_other_failure,
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

                    try:
                        new_uid_str = input(f"Scan new UID for sensor with Old UID (Top to bottom): {old_uids}: ")
                    except KeyboardInterrupt:
                        logging.info("UID scanning cancelled by user.")
                        raise fh.UserAbortError("UID update cancelled by user.")
                    
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

                try:
                    confirm = input("Confirm applying these UID changes? (y/n): ").strip().lower()
                except KeyboardInterrupt:
                    logging.info("UID update confirmation cancelled by user.")
                    raise fh.UserAbortError("UID update cancelled by user.")
                    
                if confirm != 'y':
                    logging.warning("UID update cancelled by user.")
                    return
                
                logging.info("Applying UID changes to sensors...")
                for mapping in uid_mappings:
                    ipx.set_uid(current_uid=mapping['old'], new_uid=mapping['new'])
                    
                    logging.debug(f"Set UID from {mapping['old']} to {mapping['new']}")
                    time.sleep(0.5)  # small delay to ensure command is processed
                    
                # Final verification ( should this just not use verify_sensor_count again? )
                logging.info("Verifying updated UIDs...")
                # reverify after uid update
                final_uids, _ = configurator.verify_sensor_count(ipx=ipx, num_sensors=num_sensors_int)

                expected_uids = [m['new'] for m in uid_mappings]
                if all(uid in final_uids for uid in expected_uids):
                    logging.info("✅ SUCCESS: All UIDs were updated successfully.")
                else:
                    logging.error("❌ FAILURE: Some UIDs were not updated. Please check the device.")

        except (IPXSerialError, SystemExit) as e:
            logging.critical(f"An error occurred during the UID update process: {e}")

    except KeyboardInterrupt:
        logging.info("UID update process cancelled by user. (Ctrl+C), returning to main menu")
        raise fh.UserAbortError("UID update process cancelled by user.")




# ----------------------------- HELPER FUNCTIONS FOR BREAKING UP RUN CONFIGURATION FLOW -----------------------------
# functions for breaking up the run configuration flow, as the function is getting too long ( approx 400 lines rn)

# change calibration loop into a function:
def _run_calibration_loop(uids_list, ipx: IPXSerialCommunicator, configurator: IPXConfigurator, report: ReportGenerator):
    """Iterates through all uids, and attempts to calibrate all ipxs.
    
    Handles retries, failures and any raw data checks.
    
    Args:
        uids_list: List of UIDs to calibrate
        ipx: IPXSerialCommunicator instance
        configurator: IPXConfigurator instance
        report: ReportGenerator instance for logging results
    
    Returns:
        True if all calibrations completed, False if critical error occurred
    """
    for uid in uids_list:
                    
        counter = 0 # initialize a counter for calibration attempts, once we get to 3 cal attempts we can prompt user to skip/abort/retry the configuration for that specific sensor
        logging.info(f"Starting calibration for UID {uid}...")
        while True:
            # use try loop to handle unexpected errors during calibration
            
            counter += 1
            try:
                cal_df = ipx.calibrate(uid)
                # validate cal_result
                # after getting calibration data, save it straight away?

                report.save_calibration_files(uid=uid, cal_df=cal_df) # save calibration data to file
        
                result_or_num_failed = configurator.validate_calibration_results(cal_df)
                # unpack the  result_or_num_failed tuple of format ( bool, failed_sensor_nums| None)
                sucess_bool , failed_sensor_nums = result_or_num_failed

                if sucess_bool == True:
                    # ---- INITIAL CALIBRATION CHECK PASSED ----
                    # we should also do the abnormal high magnitude check here as well, if rawdatacheck is not called 

                    # this is all due to abnormal magnitude
                    #1. if we've failed < 3 times, auto retry
                    raw_data = ipx.get_raw(uid=uid, data_type='array')
                    raw_log = str(raw_data.tolist()) # convert to string for json serialization
                    # save raw data value to report
                    report.add_sensor_data(uid=uid, data_key='raw_data_sample', data_value=raw_log)
                    if not configurator.abnormal_high_magnitude_check(uid, raw_values=raw_data): # if result is false run this loop
                        if counter < 3:
                            logging.warning(f"Calibration for UID {uid} has failed abnormal high magnitude check {counter} times, retrying automatically.")
                            continue # retry calibration automatically
                        # if we've failed > 3 times, then prompt user for action
                        else:
                            logging.warning(f"Calibration for UID {uid} has failed abnormal high magnitude check {counter} times., prompting user for action.")
                            choice = fh.prompt_user_on_cal_failure(uid, error_message=f"Abnormal high magnitude detected in raw data after successful calibration, for uid {uid} with raw values: {raw_data}." )

                            if choice == "retry":
                                logging.info(f"Retrying calibration for UID {uid} due to abnormal high magnitude...")
                                logging.debug("Resetting counter to 0 for retry attempts.")
                                counter = 0  # reset counter for retries
                                continue
                            elif choice == "skip":
                                logging.warning(f"User chose to skip retrying calibration for UID {uid}.")
                                break  # exit while loop to skip
                            elif choice == "abort":
                                logging.warning("User aborted configuration.")
                                raise fh.UserAbortError("Configuration aborted by user.") # maybe not system exit, return to main menu
                        logging.info(f"Abnormal high magnitude check passed for UID {uid}")
                        logging.info(f"Calibration successful for UID {uid}")
                    
                    # if magnitude check passed:
                    logging.info(f"Calibration successful for UID {uid}")
                    break  # exit while loop on success

                # no need for raw data check if it didnt fail
                # ------ INITIAL CALIBRATION CHECK FAILED (DUE TO ZERO MEAN/STD DEV) ------
                else:
                    result2, raw_values = configurator.raw_data_check(ipx=ipx, uid=uid, sensor_index=failed_sensor_nums)
                    raw_log = str(raw_values.tolist()) # convert to string for json serialization
                    # save sensor data
                    report.add_sensor_data(uid=uid, data_key='raw_data_sample', data_value=raw_log)
                    if result2 == True:
                        logging.info(f"Calibration successful for UID {uid} after raw data check")
                        break  # exit while loop on success

                    #if fails, retry calibration automatically, or give user option
                    else:
                        if counter < 3:
                            logging.warning(f"Calibration for UID {uid} has failed stuck sensor/raw data check {counter} times, retrying automatically.")
                            continue # retry calibration automatically
                        else:
                            logging.warning(f"Calibration for UID {uid} has failed stuck sensor/raw data check {counter} times., prompting user for action.")
                            choice = fh.prompt_user_on_cal_failure(uid, error_message= f"Calibration validation failed after stuck sensor check, due to either\n"
                            f"Stuck sensor, or Abnormal high magnitude in raw data, for uid {uid}.\n")
                            if choice == "retry":
                                logging.info(f"Retrying calibration for UID {uid}...")
                                continue
                            elif choice == "skip":
                                logging.warning(f"User chose to skip retrying calibration for UID {uid}.")
                                break  # exit while loop to skip
                            elif choice == "abort":
                                logging.warning("User aborted configuration.")
                                raise fh.UserAbortError("Configuration aborted by user.") # maybe not system exit, return to main menu
                        
                        # if we reach here, it means we need to handle error and give user option to retry/skip/abort


                

            except Exception as e: # if we get an error do we want to retry this calibration?
                logging.error(f"An error occurred during calibration for UID {uid}: {e}", exc_info=True)
                choice = fh.prompt_user_on_cal_failure(uid, error_message=f" An unexpected error occurred during calibration: {e}")

                if choice == "retry":
                    logging.info(f"Retrying calibration for UID {uid}...")
                    continue
            
                elif choice == "skip":
                    logging.warning(f"User chose to skip retrying calibration for UID {uid}, moving on to next sensor")
                    break  # exit while loop to skip

                elif choice == "abort":
                    logging.warning("User aborted configuration.")
                    raise fh.UserAbortError("Configuration aborted by user.")
    
    #4. now check for abnormal high magnitude raw data across all sensors (after configuration):
    # the only thing is that we are already doing a raw data check and then doing the abnomalous high magnitude check, we should integrate this into the raw data check function?
    # The abnormal high magnitude check should be integrated during the calibration loop, as we can choose to re-calibrate a function an abnormal mag is present
    return True



def _run_modbus_verification(alias_and_uids_list, report, txt_content, com_port):
    """ Runs modbus verification tests on configured sensors. (mimics datalogger)

    Args:
        alias_and_uids_list: List of tuples of (alias, uid) for all configured sensors
        report: ReportGenerator instance for logging results
        com_port: COM port to use for Modbus communication
    
    Returns:
        True: if all tests completed
        False: if critical error occurred
    """
    logging.info("Starting Modbus communication test for all sensors...")
    modbus_record = [] # list to store all modbus test results:
    # i should mimic how the datalogger would test, it would get all of the results and then we would manually check them after
    # so mimic that process, but instead of manually checking them, we automate the checking process
    try:
        with IPXModbusTester(port=com_port, baudrate=9600) as modbus_tester:
            for tuple in alias_and_uids_list:
                alias = tuple[0]
                uid = tuple[1]
                
                logging.debug(f"Starting Modbus test for UID {uid} (Alias: {alias})")
                test_result = fh.retry_on_exception(lambda: modbus_tester.run_full_test(uid=uid, alias=alias))
                # retry incase a modbus read fails due to timeout or other comms error


                # log only certain test results, such as overall pass/fail, temperature, voltage, distance
                test_results_to_keep = ["Overall_Pass", "Dist_mm", "Temp_C", "Volt_V", "Status_Val"]
                test_result_for_report = {key: test_result[key] for key in test_results_to_keep}
                report.add_sensor_data(uid=uid, data_key='modbus_test_result', data_value=test_result_for_report) # log modbus test result to report
                
                # log immediate status just for info:
                if test_result["Overall_Pass"]:
                    logging.info(f"Modbus test PASSED for UID {uid} (Alias: {alias})")
                else:
                    logging.warning(f"Modbus test FAILED for UID {uid} (Alias: {alias})")
                
                modbus_record.append(test_result) # add result dict to record list ( so list of dicts )
    
    except Exception as e:
        logging.critical(f"An error occurred during Modbus testing: {e}", exc_info=True)
        report.save_report(final_status="Modbus Test Failed") # save normal json report
        report.save_txt_file(txt_content=txt_content) # save normal txt file of alias / uid mappings
        log_msg = ("=" * 50 + "\n"
                "Configuration was succesful but Modbus testing failed due to an unexpected error.\n"
                "=" * 50 + "\n")
        return False

    # Analysis + Reporting:
    datalogger_df = pd.DataFrame(modbus_record)
    # check for failures:
    failed_sensors = datalogger_df[datalogger_df["Overall_Pass"] == False]

    # Reporting to user:
    logging.info("\n" + "="*40)
    logging.info("      MODBUS VERIFICATION SUMMARY      ")
    logging.info("="*40)

    # -------- Report to user --------
    # print all modbus test results to user:
    logging.info("\nDetailed Test Results:\n")
    for index, row in datalogger_df.iterrows():
        log_msg = (f"Datalogger test results for: \n"
                f"\n=============================== \n"
                f"UID: {row['UID']}, Alias: {row['Alias']} \n"
                f"=============================== \n"
                f"Status: {row['Status_Val']} \n" 
                f"Distance: {row['Dist_mm']} mm \n"
                f"Temperature: {row['Temp_C']:.3g} °C \n"
                f"Voltage: {row['Volt_V']:.3g} V \n"
                f"Overall Result: {'✅ PASS' if row['Overall_Pass'] else '❌ FAIL'} \n"
                f"=============================== \n")
        logging.debug(log_msg) # this is for debug log, for when i start saving the logs with every configuration run
        print(log_msg) # this will look cleaner in the terminal

    if failed_sensors.empty:
        logging.info(f"✅ ALL {len(datalogger_df)} SENSORS PASSED.")
        logging.info("="*40 + "\n")
        final_run_status = "SUCCESS"
        logging.info("Modbus verification complete. All sensors passed.")
    else:
        logging.info(f"❌ {len(failed_sensors)} OUT OF {len(datalogger_df)} SENSORS FAILED MODBUS TESTING:")
        for index, row in failed_sensors.iterrows():
            logging.info(f"   - UID {row['UID']} (Alias: {row['Alias']}) failed.")
        logging.info("="*40 + "\n")
        final_run_status = "Configuration completed , but modbust testing has failures"
        logging.warning(f"Modbus verification complete. {len(failed_sensors)} sensors failed.")

    # pause so user sees summary:
    input("Press Enter to acknowledge results and save reports...")
    return True, datalogger_df, final_run_status


def _run_geosense_verification(uids_list, report, txt_content, com_port):
    """
    Runs Geosense (datalogger) verification tests on configured sensors.
    Hardcoded to 9600 baud, should never be anything different for geosense.
    Args:
        uids_list: List of UIDs for all configured sensors
        report: ReportGenerator instance for logging results
        com_port: COM port to use for Geosense communication
        txt_content: Content for the .txt report file
    Returns:
        True: if all tests completed
        False: if critical error occurred
    """

    logging.info("Starting Geosense measurement procedure for all inserts....")
    # instantiate geosensemeasurer
    # hardcoded to 9600, should never be anything different
    try:
        with IPXGeosenseTester(port=com_port, baudrate=9600) as geosense_tester:
            measurement_record = [] # list to store all measurement results, (list of dicts)
            for uid in uids_list: 
                logging.debug(f"Starting Geosense measurement for UID {uid}")
                measurement_result = fh.retry_on_exception(
                    operation_func=lambda: geosense_tester.gxm_measure_test(uid=uid)
                )
                # log measurement result to report
                report.add_sensor_data(uid=uid, data_key='geosense_measurement', data_value=measurement_result)

                logging.info(f"Geosense measurement completed for UID {uid} with results: {measurement_result}")
                measurement_record.append(measurement_result) # add result dict to record list

    except Exception as e:
        logging.critical(f"A critical error occurred during Geosense measurement: {e}", exc_info=True)
        report.save_report(final_status="Geosense Measurement Failed") # save normal json report
        report.save_txt_file(txt_content=txt_content) # save normal txt file of uids
        log_msg = ("=" * 50 + "\n"
                "Configuration was succesful but Geosense measurement failed due to an unexpected error.\n"
                "=" * 50 + "\n")
        logging.critical(log_msg)
        return False

    # Analysis + Reporting:
    datalogger_df = pd.DataFrame(measurement_record)
    # check for failures:
    failed_sensors = datalogger_df[datalogger_df["pass"] == False]

    # Reporting to user:
    logging.info("="*40)
    logging.info("      GEOSENSE VERIFICATION SUMMARY      ")
    logging.info("="*40)

    # -------- Report to user --------
    # print all modbus test results to user:
    logging.info("\nDetailed Test Results:\n")
    for index, row in datalogger_df.iterrows():
        log_msg = (
                f"\n=============================== \n"
                f"UID: {row['uid']},\n"
                f"=============================== \n"
                f"Axis A: {row['axis_a']} \n" 
                f"Temperature: {row['temperature']} °C \n"
                f"Overall Result: {'✅ PASS' if row['pass'] else '❌ FAIL'} \n"
                f"=============================== \n")
        logging.debug(log_msg) # this is for debug log, for when i start saving the logs with every configuration run
        print(log_msg) # this will look cleaner in the terminal

    if failed_sensors.empty:
        logging.info(f"✅ ALL {len(datalogger_df)} SENSORS PASSED.")
        logging.info("="*40 + "\n")
        final_run_status = "SUCCESS"
        logging.info("Geosense datalogger verification complete. All sensors passed.")
    else:
        logging.info(f"❌ {len(failed_sensors)} OUT OF {len(datalogger_df)} SENSORS FAILED GEOSENSE TESTING:")
        for index, row in failed_sensors.iterrows():
            logging.info(f"   - UID {row['uid']}  failed.")
        logging.info("="*40 + "\n")
        final_run_status = "Configuration completed , but geosense testing has failures"
        logging.warning(f"Geosense verification complete. {len(failed_sensors)} sensors failed.")

    # pause so user sees summary:
    input("Press Enter to acknowledge results and save reports...")
    return True, datalogger_df, final_run_status
    
# Function for getting order details from user:
def get_order_details():
    """Gets manufacturing order details from user input."""
    try:
        manufacturing_order = input("Enter Manufacturing Order (MO) number: ").strip()
        string_description = input("Enter String Description: ").strip()
        operator = input("Enter Operator Name/ID: ").strip()
        return manufacturing_order, string_description, operator
    except KeyboardInterrupt:
        logging.info("Order details input cancelled by user.")
        raise fh.UserAbortError("Order details input cancelled by user.")


# Main function for handling configuration with user inputs:
def run_configuration_flow(com_port, baudrate):
    """Handles full sensor configuration flow.""" 

    # ------------------------- get initial settings, plus instantiate classes -------------------------------------- 
    try:
        # get all the initial settings from user
        num_sensors_int = get_initial_settings()
        mo, string_description, operator = get_order_details()


        # initialise the report generator
        report = ReportGenerator(
            port = com_port,
            manufacturing_order = mo,
            string_description = string_description,
            operator = operator
        )



        configurator = IPXConfigurator() # initialise IPX configurator without port or baudrate, as these will be set in the communicator context manager

        # --------------------------- End of intial setup, ipx communicator is used in with loop -------------------------------

        logging.info(f"--- Starting new external configuration session on {com_port} for {num_sensors_int} sensors ---")
        try:
            with IPXSerialCommunicator(port=com_port, baudrate=baudrate, verify=True) as ipx:
                # Step 1: Verify sensor count with automatic retry handling
                uids_list, check_sensor_present = fh.retry_on_failure(
                    operation_func=configurator.verify_sensor_count,
                    prompt_func=fh.prompt_user_on_other_failure,
                    success_message=f"Successfully detected {num_sensors_int} sensors",
                    ipx=ipx,
                    num_sensors=num_sensors_int
                )
                
                # could add failure rerpot?
                if uids_list is None:
                    logging.error("Sensor detection failed or was skipped. Exiting configuration.")
                    return


                
                report.set_detected_sensors(uids_list) # NEW log detected UIDs to report:

                inserts = False # initialise this flag for whether inserts are connected or not
                #2. check whether inserts or normal extensometers are connected, and set default parameters accordingly:

                if all(str(uid).startswith("104") for uid in uids_list): # this are the inserts, skip assigning aliases to them
                    inserts = True # set the inserts flag to true
                    logging.info("Inserts detected, skipping alias assigning process")
                    if check_sensor_present is False:
                        logging.warning("Bottom check sensors has not been detected")
                        user_response = input("Bottom check sensors not detected. Do you want to continue? (y/n): ").strip().lower()
                        if user_response != 'y':
                            logging.info("Configuration aborted by user due to missing bottom check sensors.")
                            raise fh.UserAbortError("Configuration aborted by user due to missing bottom check sensors.")
                        
                    # now log paramaters etc
                    fh.retry_on_exception(lambda: configurator.set_default_parameters(ipx, uids_list, baud=baudrate, set_aliases=False,))
                    txt_content = report.create_txt_content(aliases_and_uids_list=uids_list, inserts=True) # create the .txt content for the report generator



                # add a check in case there are some 104s connected and this should abort process
                elif any(str(uid).startswith("104") for uid in uids_list): # little error catch for mixed sensor types
                    logging.critical("Mixed sensor types detected (inserts and extensometers). Aborting configuration.")
                    raise fh.UserAbortError("Configuration aborted due to mixed sensor types (inserts and normal extensometers).")


                # else will be normal extensometers    
                else:
                    logging.info("Normal extensometers detected, proceeding with full configuration (including alias assignment) ")
                    inserts = False # ensure inserts flag is false
                    alias_and_uids_list = fh.retry_on_exception(operation_func=lambda:configurator.set_default_parameters(ipx, uids_list, baud=baudrate))
                    # alias_and_uids_list is a list of tuples of format [(alias, uid), (alias, uid), etc....]
                    txt_content = report.create_txt_content(aliases_and_uids_list=alias_and_uids_list) # create the .txt content for the report generator
                
                logging.debug(f"UIDS_list before parsing into cal loop: {uids_list}")

                #3. --------------------------------- run calibration with retry handling: ---------------------------------
                _run_calibration_loop(uids_list=uids_list, ipx=ipx, configurator=configurator, report=report)
                
                
                        
                #5. set final baud rate to 9600 for all sensors:
                final_baud = IPXCommands.Default_settings.Baud_rate
                logging.info(f"Setting baud rate for all devices to {final_baud}")
                for uid in uids_list:
                    fh.retry_on_exception(operation_func=lambda:ipx.set_baud(uid=uid, baud=final_baud))
                
                
            
            with IPXSerialCommunicator(port=com_port, baudrate=final_baud, verify=True) as ipx:
                # Final get status to store in the report
                for uid in uids_list:
                    #put this into a try catch, while retry loop, as have had issues where a sensor hasnt responded in time
                    fh.retry_on_exception(
                        operation_func=lambda: report.add_sensor_data(uid=uid, data_key='final_status', data_value=ipx.get_status(uid=uid, data_type='dict'))
                    )
                    logging.debug(f"Successfully retrieved final status for UID {uid}")



                #------------------------- Modbus testing time! -------------------------
            if inserts == False: # only run modbus testing for normal extensometers
                _, datalogger_df, final_run_status = _run_modbus_verification(alias_and_uids_list=alias_and_uids_list, report=report, txt_content=txt_content, com_port=com_port)
                
# ------------------------------------------- Geosense measurement procedure --------------------------------------------------------
            # debating whether to chane modbus_df to just datalogger_df, that way can keep saving seperate
            # insert measurements should be in df as well
            elif inserts == True:
                _, datalogger_df, final_run_status = _run_geosense_verification(uids_list=uids_list, report=report, txt_content=txt_content, com_port=com_port)  



                
# Now onto saving the reports:
            
            # save final json report and uid + alias text file:
            report.save_datalogger_results(datalogger_df=datalogger_df) # moved saving modbus results to here, as we do not need to save it for inserts
            report.save_report(final_status=final_run_status) # should be consistent with the final_run_status variable
            report.save_txt_file(txt_content=txt_content)
            

            logging.debug("Report generation completed successfully.")
            logging.info("-----------------------------------------------")
            logging.info(str(final_run_status).upper())  
            logging.info("-----------------------------------------------")
            
            # Open json file automatically when done:
            try:
                file_path = report.json_filepath
                logging.info(f"Automatically opening report file: {file_path}")
                if platform.system() == 'Windows':
                    os.startfile(file_path)
                else:
                    logging.warning("Automatic opening of report file is only supported on Windows.")
            except Exception as e:
                logging.warning(f"Could not automatically open report file: {e}")

            return True

                    # Try to catch any unexpected errrors
        except fh.UserAbortError:
            # Re-raise UserAbortError so it's handled by main menu
            logging.info("Configuration aborted by user.")
            raise

        except(IPXSerialError,RuntimeError) as e:
            logging.critical(f" CONFIGURATION FAILED: A critical error occurred: {e}")
            return False
            
        except Exception as e:
            # Catch any other unexpected errors
            logging.critical(f"CONFIGURATION FAILED: An unexpected error occurred: {e}", exc_info=True)
            return False

    except KeyboardInterrupt:
        logging.info("Configuration flow interrupted by user (Ctrl+C). Returning to main menu.")
        raise fh.UserAbortError("Configuration flow cancelled by user.")
    















    