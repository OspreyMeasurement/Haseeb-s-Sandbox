# 🧩 IPX Serial Communication Module

A Python library for communicating with **IPX sensor devices** over serial (COM) interfaces.  
This module provides a clean, object-oriented API to send commands, read responses, and manage device configurations — with robust error handling, logging, and flexible data output formats.

---

## 📂 Project Structure

```
IPX/
├── IPX.py              # Core communication logic and command implementations
└── IPX_Config.py       # Command and response string definitions for IPX protocol
```

---

## 🚀 Features

- ✅ Clean class-based interface (`IPXSerialCommunicator`)
- ✅ Real-time logging of device responses as they arrive
- ✅ Custom exception classes for robust error handling
- ✅ Automatic UTF-8 corruption detection
- ✅ Multiple response formats (`string`, `bytes`, `list`, or `numpy array`)
- ✅ Command-specific timeouts for long operations like calibration
- ✅ Context manager support (`with` block auto-opens and closes serial ports)

---

## ⚙️ Installation

Install dependencies:

```bash
pip install pyserial numpy
```

Then include both `IPX.py` and `IPX_Config.py` in your project.

---

## 🧠 Example Usage

```python
from IPX import IPXSerialCommunicator

with IPXSerialCommunicator(port="COM5", baudrate=115200) as ipx:
    # List connected IPX devices
    uids = ipx.list_uids(data_type="list")
    print("Connected UIDs:", uids)

    # Get device status
    status = ipx.get_status(uid=uids[0])
    print(status)

    # Start calibration
    print("Starting calibration...")
    result = ipx.calibrate(uid=uids[0])
    print(result)
```

---

## 🧩 Class Overview

### **`IPXSerialCommunicator`**

Main class for all IPX serial operations.

#### **Initialization**

```python
IPXSerialCommunicator(port: str, baudrate: int, timeout: int = 5)
```

| Parameter | Description |
|------------|--------------|
| `port` | COM port name (e.g. `"COM5"` or `"/dev/ttyUSB0"`) |
| `baudrate` | Serial baud rate (e.g. 9600 or 115200) |
| `timeout` | Read timeout in seconds |

---

### **Context Manager**

Automatically handles connection setup and teardown:

```python
with IPXSerialCommunicator("COM5", 115200) as ipx:
    ipx.list_uids()
```

---

### **Available Methods**

| Method | Description | Returns |
|--------|--------------|----------|
| `list_uids(data_type='string')` | Lists connected IPX device UIDs | `str`, `list[int]`, `np.ndarray`, `bytes` |
| `get_status(uid, data_type='dict')` | Reads detailed device status | `dict`, `str`, `bytes` |
| `get_raw(uid, data_type='list')` | Reads raw sensor data | `list[int]`, `np.ndarray`, `str`, `bytes` |
| `calibrate(uid)` | Starts calibration and streams progress logs | `str` |
| `set_baud(uid, baud)` | Changes device baud rate | `str` |
| `set_uid(current_uid, new_uid)` | Updates device UID | `str` |
| `set_axis(uid, axis)` | Sets measurement axis | `str` |
| `set_gain(uid, gain)` | Adjusts gain value | `str` |
| `set_centroid_threshold(uid, threshold)` | Sets centroid threshold | `str` |
| `set_centroid_res(uid, resolution)` | Sets centroid resolution | `str` |
| `set_n_stds(uid, n_stds)` | Sets number of standard deviations | `str` |
| `set_term(uid, termination)` | Enables/disables termination resistor | `str` |
| `set_alias(uid, alias)` | Assigns a human-readable alias | `str` |

---

## 🧱 Error Handling

Custom exception hierarchy for clean error management:

| Exception | Description |
|------------|--------------|
| `IPXSerialError` | Base class for all IPX serial errors |
| `IPXCorruptedDataError` | Raised when UTF-8 decoding fails (corrupted data) |
| `IPXNoResponseError` | Raised when no response is received within timeout |

Example:
```python
from IPX import IPXCorruptedDataError, IPXNoResponseError

try:
    with IPXSerialCommunicator("COM5", 115200) as ipx:
        ipx.get_raw(1001)
except IPXNoResponseError:
    print("⚠️ No response from device.")
except IPXCorruptedDataError:
    print("⚠️ Corrupted data detected — check wiring or interference.")
```

---

## 🕓 Command-Specific Timeouts

Some commands take longer (like calibration).  
Timeouts are defined in `DEFAULT_TIMEOUTS`:

```python
DEFAULT_TIMEOUTS = {
    "calibrate": 20,
    "set_axis": 5,
    "set_baud": 1,
    "set_uid": 1,
    "set_gain": 0.5,
    "set_centroid_threshold": 0.5,
    "set_centroid_res": 0.5,
    "set_n_stds": 0.5,
    "set_term": 0.5,
    "set_alias": 0.5,
}
```

Each high-level method automatically applies the correct timeout.

---

## 🔍 Real-Time Logging

Device responses are streamed live as they are received, providing immediate feedback during long operations.

Example output during calibration:
```
INFO - Sent command: op ipx 100 calibrate
INFO - CMD_EXEC_Calibrate: Starting calibration procedure.
INFO - CMD_EXEC_Calibrate: Sensor 0 mean = 462, standard dev = 16 axis 0.
...
INFO - CMD_EXEC_Calibrate: Calibration complete, saving to memory.
```

---

## 📜 Example: Status Parsing

```python
status = ipx.get_status(123456)
print(status)
```

**Output:**
```python
{
  "CMD_EXEC_Get_Status": "Device is active",
  "Axis": "1",
  "Gain": "3",
  "Centroid_Threshold": "800",
  "Baud": "115200"
}
```

---

## ⚠️ Best Practices

- UID `0` is reserved for broadcast commands.  
- Always use `with` to auto-close ports.  
- For persistent corruption issues, check:
  - Cable shielding and grounding
  - Baud rate settings
  - Line interference
- To debug:
  ```python
  logging.getLogger().setLevel(logging.DEBUG)
  ```

---

## 🧩 File: `IPX_Config.py`

Defines command and response templates for the IPX communication protocol.

Example:
```python
class IPXCommands:
    class Commands:
        list_uids = "op ipx 0 list_uids\n"
        get_status = "op ipx {uid} get_status\n"
        calibrate = "op ipx {uid} calibrate\n"
``

---

## 🧰 Future Improvements

- [ ] Retry mechanism for transient communication drops  
- [ ] CRC or checksum validation  
- [ ] Async I/O support for non-blocking reads  
- [ ] Structured calibration data parsing  
- [ ] CLI utility for quick device setup  

---

## ✨ Author

**Haseeb Mahmood**  
📧 *Haseeb@ospreymeasurement.com*  
🛠️ Designed for reliable and debuggable IPX sensor communication.
