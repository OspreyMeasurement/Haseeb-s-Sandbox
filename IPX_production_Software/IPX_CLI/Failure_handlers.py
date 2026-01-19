import logging
import time





# -----    CUSTOM ERRORS FOR USE IN THIS SCRIPT  -----
class UserAbortError(Exception):
    """ Custom exception to indicate user aborted operation """
    pass



def prompt_user_on_cal_failure(uid:int, error_message: str = "") -> str:
    """
    Handles user input when a calibration failure occurs
    """
    while True:
        try:
            choice = input(
                    f"\n CRITICAL: Calibration for UID {uid} failed: {error_message}\n"
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
        except KeyboardInterrupt:
            logging.info("Calibration failure prompt cancelled by user.")
            raise UserAbortError("User aborted configuration during calibration failure.")

def prompt_user_on_other_failure(error_message:str = "") -> str:
    """
    Handles user input when a non-calibration failure occurs
    """
    while True:
        try:
            choice = input(
                    f"\n ERROR: An error occurred: {error_message}\n"
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
        except KeyboardInterrupt:
            logging.info("Error handling prompt cancelled by user.")
            raise UserAbortError("User aborted operation during error handling.")


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
        

def retry_on_exception(operation_func, handled_exceptions=(Exception,), 
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

            choice = prompt_user_on_other_failure(error_message=str(e))

            if choice == "retry":
                logging.info(f"Retrying operation after {retry_delay}s...")
                time.sleep(retry_delay)
                continue
            elif choice == "skip":
                logging.warning("User chose to skip this operation., returning current result")
                return result
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
