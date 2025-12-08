import time
import struct
from dataclasses import dataclass
from typing import Dict, List, Optional
import logging

from pymodbus.client import ModbusSerialClient
from pymodbus import FramerType
from pymodbus.exceptions import ModbusException


# logging.basicConfig(
#     level=logging.DEBUG,
#     format="%(asctime)s [%(levelname)s] %(message)s")



#--------------------------- Exception classes for modbus communication -------------------------
class IPXModbusError(Exception):
    """Base exception for IPX modbus error."""

class IPXModbusReadError(IPXModbusError):
    """Raised when modbus read fails"""

class IPXModbusWriteError(IPXModbusError):
    """Raised when a modbus write fails"""

#-----------------------------------------------------------------------------------------------------------


# ------------------------------ Class for production testing using modbus (instead of datalogger) -------------------------------
class IPXModbusTester:
    """
    High-level Modbus RTU client for IPX sensors on RS-485.
    In order to verify IPX sensor functionality

    Supports multiple sensors on one bus (each with its own Modbus address).
    Implements the sequence:
        - trigger measurement
        - wait for status == 0
        - read distance, temperature, voltage
    """
    # this is not referenced in the script, change in init if needed
    # DEFAULT REGISTER MAP (FOR IPX SENSORS):
    TRIGGER_REG = 0x0063 # starts measurement, then stores on ipx
    STATUS_REG = 0X0135 # read 1 reg, status == 1 means ok
    DISTANCE_REG = 0X0136 # Distance MSW / LSW (2 regs, float)
    TEMP_REG = 0X0139 # Temperature MSW / LSW (2 regs, float)
    VOLTAGE_REG = 0X013C # Voltage MSW / LSW (2 regs, float)



    def __init__(
            self, 
            port: str,
            baudrate: int = 9600,
            timeout: int = 1,):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.client = None

        self.TRIGGER_REG = 0x0063
        self.STATUS_REG = 0X0135
        self.DISTANCE_REG = 0X0136
        self.TEMP_REG = 0X0139
        self.VOLTAGE_REG = 0X013C
        
    
# Enter/exit for context manager -----------------------------------------------------
    def __enter__(self):
        self._connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback): # contain error information for debugging
        self._disconnect()
        return self
    

    def _connect(self):
        """ Function for establishing modbus connection 
        called when entering context manager"""
        try:
            # instantiate client (for rtu over serial)
            self.client = ModbusSerialClient(
                port=self.port,
                baudrate=self.baudrate,
                parity="N",
                stopbits=1,
                bytesize=8,
                timeout=self.timeout,
                framer=FramerType.RTU
            )
            logging.debug(f"Attempting to connect to Modbus on {self.port}...")
            if not self.client.connect(): # if failed to connect raise error
                logging.error(f"Failed to connect to Modbus on {self.port}")
                raise IPXModbusError(f"Failed to connect to Modbus on {self.port}")
            logging.info(f"Connected to Modbus on {self.port}")
        except Exception as e: # catch all exceptions during connection
            logging.error(f"Error connecting to Modbus on {self.port}: {e}")
            raise IPXModbusError(f"Error connecting to Modbus: {e}")
        

    def _disconnect(self):
        """ Function for closing modbus connection
        called when exiting context manager"""
        # closes connection
        if self.client:
            self.client.close()
            logging.info(f"Disconnected from Modbus on {self.port}")

    def _regs_to_float(self, msw: int, lsw: int) -> float:
        """ Convert two 16-bit registers (Big Endian) (MSW, LSW) to a float32 value """
        raw = (msw << 16) | lsw
        return struct.unpack(">f", raw.to_bytes(4, "big"))[0] # big endian ( converts to bytes, then unpacks as python float)


    #------------------------------ High-level measurement sequence -------------------------------
    def datalogger_test(self, uid:int, alias:int) -> dict:
        """ Performs full measurement sequence for one IPX Sensor (same as datalogger):
        Reads Status, Distance, Temperature, Voltage
        Args:
            alias (int): Modbus address of the IPX sensor
            
        Returns:
            IPXMeasurement: dictionary with Status, distance (mm), temperature (C), voltage (V)"""
        

        logging.info(f"Starting measurement sequence for IPX sensor at address {alias}")

        try:

            #1. Trigger measurement (write to register 0x0063):
            write_result = self.client.write_register(
                address=self.TRIGGER_REG,
                value=0xFFFF,
                device_id=alias,
            )
            if write_result.isError(): # check if the write was successful
                logging.error(f"Trigger write failed for alias {alias}: {write_result}")
                raise IPXModbusWriteError(f"Trigger write failed for alias {alias}: {write_result}")
            logging.debug("Measurment sequence successfully triggered")
            #2. wait for measurement to complete (wait 1s):
            time.sleep(1.0)

            logging.debug("Moving on to reading results...")
            # add uid and alis to results dictionary

            result = {"uid": uid, "alias": alias}

            #3. read status:
            logging.debug("Reading status...")
            rr_status = self.client.read_holding_registers(
                address=self.STATUS_REG,
                count=1,
                device_id=alias,)
            if rr_status.isError():
                logging.error(f"Status read failed for alias {alias}: {rr_status}")
                raise IPXModbusReadError(f"Status read failed for alias {alias}: {rr_status}")
            else:
                result["Status"] = rr_status.registers[0]
            
            logging.debug(f"Status read successfully")   
            
            #4. read distance:
            logging.debug("Reading distance...")
            rr_distance = self.client.read_holding_registers(
                address=self.DISTANCE_REG,
                count=2,
                device_id=alias,)
            if rr_distance.isError():
                logging.error(f"Distance read failed for alias {alias}: {rr_distance}")
                raise IPXModbusReadError(f"Distance read failed for alias {alias}: {rr_distance}")
            else:
                distance = self._regs_to_float(rr_distance.registers[0], rr_distance.registers[1]) # convert from bytes to python float
                result["Distance_mm"] = distance
            
            logging.debug(f"Distance read successfully")

            #5. read temperature:
            logging.debug("Reading temperature...")
            rr_temp = self.client.read_holding_registers(
                address=self.TEMP_REG,
                count=2,
                device_id=alias,)
            if rr_temp.isError():
                logging.error(f"Temperature read failed for alias {alias}: {rr_temp}")
                raise IPXModbusReadError(f"Temperature read failed for alias {alias}: {rr_temp}")
            else:
                temperature = self._regs_to_float(rr_temp.registers[0], rr_temp.registers[1])
                result["Temperature"] = temperature
            logging.debug(f"Temperature read successfully")

            #6. read voltage:
            logging.debug("Reading voltage...")
            rr_voltage = self.client.read_holding_registers(
                address=self.VOLTAGE_REG,
                count=2,
                device_id=alias,)
            if rr_voltage.isError():
                logging.error(f"Voltage read failed for alias {alias}: {rr_voltage}")
                raise IPXModbusReadError(f"Voltage read failed for alias {alias}: {rr_voltage}")
            else:
                voltage = self._regs_to_float(rr_voltage.registers[0], rr_voltage.registers[1])
                result["Voltage"] = voltage
            logging.debug(f"Voltage read successfully")

            log_msg = (f" Datalogger test results for: \n"
                       "\n=============================== \n"
                         f"UID: {uid}, Alias: {alias} \n"
                         "=============================== \n"
                         f"Status: {result['Status']} \n" 
                         f"Distance: {result['Distance_mm']} mm \n"
                         f"Temperature: {result['Temperature']:.3g} \u00B0C \n"
                         f"Voltage: {result['Voltage']:.3g} V \n"
                         "=============================== \n")
            
            # logging.info(log_msg) # reduce verbosity by commenting out, should be printed in main script instead

            return result
        
        except Exception as e:
            logging.error(f"Exception during modbus datalogger test for Alias {alias}: {e}")
            raise e # maybe just raise the error instead?, should be caught in main script??
        

        
    def verify_results(self, results: dict) -> dict:
        """
        Returns per-metric pass/fail plus overall.
        {
            "overall": bool,
            "status": bool,
            "distance": bool,
            "temperature": bool,
            "voltage": bool,
            "failures": [messages...]
        }
        Args:
            results (dict): Results dictionary from datalogger_test()

        Returns:
            dict: Dictionary with pass/fail results per metric and overall.
        """
        logging.debug("Parsing results, and extracting")
        alias = results.get("alias")
        uid = results.get("uid")
        status = results.get("Status")
        distance = results.get("Distance_mm")
        temperature = results.get("Temperature")
        voltage = results.get("Voltage")

        checks = {
            "status": status == 1, # Explicit check for none to avoid typerrors
            "distance": distance is not None and distance == -99,
            "temperature": temperature is not None and 10 <= temperature <= 40,
            "voltage": voltage is not None and 11.2 <= voltage <= 12.8,
        }
        
        logging.debug(f"Checking results for UID {uid}, Alias {alias}:")

        failures = []
        if not checks["status"]:
            logging.warning(f"Status check failed: {status} (expected 1)")
            failures.append(f"Status {status} (expected 1)")

        if not checks["distance"]:
            logging.warning(f"Distance check failed: {distance} mm (expected -99 mm)")
            failures.append(f"Distance {distance} mm (expected -99 mm)")

        if not checks["temperature"]:
            logging.warning(f"Temperature check failed: {temperature} °C (expected 10–40 °C)")
            failures.append(f"Temperature {temperature} °C (expected 10–40 °C)")

        if not checks["voltage"]:
            logging.warning(f"Voltage check failed: {voltage} V (expected 11.2–12.8 V)")
            failures.append(f"Voltage {voltage} V (expected 11.2–12.8 V)")

        checks["overall"] = all(checks.values())

        if checks["overall"] == True:
            logging.info(f"All checks passed for uid {uid}, Alias {alias}.")

        checks["failures"] = failures
        return checks
    

    def run_full_test(self, uid: int, alias: int) -> dict:
        """
        Runs the test, verifies it, and returns a single FLATTENED dictionary
        ready for a pandas DataFrame.
        Args:
            uid (int): Unique identifier for the sensor
            alias (int): Modbus address of the sensor
        Returns:
            dict: Flattened dictionary with all results and pass/fail flags.
        """
        # 1. Run the measurement
        measurements = self.datalogger_test(uid=uid, alias=alias)
        
        # 2. Verify the results
        verification = self.verify_results(measurements)
        
        logging.debug("Merging measurement and verification results into flattened record")
        # 3. Merge/Flatten the data internally
        flat_record = {
            "UID": uid,
            "Alias": alias,
            "Overall_Pass": verification["overall"],
            
            # Value & Pass/Fail pairs
            "Status_Val": measurements.get("Status"),
            "Status_Pass": verification.get("status"),
            
            "Dist_mm": measurements.get("Distance_mm"),
            "Dist_Pass": verification.get("distance"),
            
            "Temp_C": measurements.get("Temperature"),
            "Temp_Pass": verification.get("temperature"),
            
            "Volt_V": measurements.get("Voltage"),
            "Volt_Pass": verification.get("voltage"),
            
            # Combine all failure messages into one string
            "Errors": "; ".join(verification.get("failures", []))
        }
        logging.debug(f"Flattened record created successfully: {flat_record}")
        return flat_record# flat dictionary is for easy logging int pandas dataframe, so we can save the results as a csv file easily.



#-----------------------------------------------------------------------------------------------------------


# with IPXModbusTester(port="COM5", baudrate=9600, timeout=1) as client:
#     # Example usage for alias 1
#     client.run_full_test(uid=12345, alias=1)