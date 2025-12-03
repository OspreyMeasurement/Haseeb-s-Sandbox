import time
import struct
from dataclasses import dataclass
from typing import Dict, List, Optional

from pymodbus.client import ModbusSerialClient
from pymodbus import FramerType
from pymodbus.exceptions import ModbusException


@dataclass
class IPXMeasurement:
    distance_mm: float
    temperature_c: float
    voltage_v: float



#--------------------------- Exception classes for modbus communication -------------------------
class IPXModbusError(Exception):
    """Base exception for IPX modbuss error."""

class IPXReadError(IPXModbusError):
    """Raised when modbus read fails"""

class IPXWriteError(IPXModbusError):
    """Raised when a modbus write fails"""

#-----------------------------------------------------------------------------------------------------------


# ------------------------------ Class for production testing using modbus (instead of datalogger) -------------------------------
class IPXModbusClient:
    """
    High-level Modbus RTU client for IPX sensors on RS-485.

    Supports multiple sensors on one bus (each with its own Modbus address).
    Implements the sequence:
        - trigger measurement
        - wait for status == 0
        - read distance, temperature, voltage
    """

# DEFAULT REGISTER MAP:
TRIGGER_REG = 0x0063 # starts measurement, then stores on ipx
STATUS_REG = 0X0135 # read 1 reg, status == 1 means ok
DISTANCE_REG = 0X0136 # Distance MSW / LSW (2 regs, float)
TEMP_REG = 0X0139 # Temperature MSW / LSW (2 regs, float)
VOLTAGE_REG = 0X013C # Voltage MSW / LSW (2 regs, float)

def __init__(
        self, 
        port: str,
        baudrate: int = 9600,
        num_sensors: int,
        

)