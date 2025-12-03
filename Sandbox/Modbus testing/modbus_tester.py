from pymodbus.client import ModbusSerialClient
from pymodbus import FramerType
import time
import struct

# helper function
def regs_to_float(msw, lsw):
    raw = (msw << 16) | lsw
    return struct.unpack(">f", raw.to_bytes(4, "big"))[0] # big endian




client = ModbusSerialClient(
    port="COM5",            # your USB/RS485 adapter
    baudrate=9600,          # match the device
    parity="N",
    stopbits=1,
    bytesize=8,
    timeout=1,
    framer=FramerType.RTU   # RTU mode
)

client.connect() # connect to ipx



# write to register with initial command
# This essentially tells ipx to take measurement (1 sample)
wr = client.write_register(
    address=0x0063,       # 99
    value=0xFFFF,         # 65535
    device_id=1,          # or slave=1, depending on your pymodbus version
)

if wr.isError():
    print("Trigger write failed:", wr)

# then wait 1000 ms

time.sleep(1.0)
# now do the reading logic
# this is all for alias 1

# read ipx status code
rr = client.read_holding_registers(
    address=0x0135,     # 309
    count=1,
    device_id=1,
)
if rr.isError():
    print("Status read failed:", rr)
else:
    status = rr.registers[0]
    print("Status:", status)

# read ipx distance
rr = client.read_holding_registers(0x0136, count=2, device_id=1)

if rr.isError():
    print("Distance read failed:", rr)
else:
    dist = regs_to_float(rr.registers[0], rr.registers[1])
    print("Distance (mm):", dist)

# read temperature:
rr = client.read_holding_registers(
    address=0x0139,
    count = 2,
    device_id= 1
)

if rr.isError():
    print("Temperature read has failed", rr)

else:
    temp = regs_to_float(rr.registers[0], rr.registers[1])
    print("Temperature (deg C):", temp)

# read voltage:
rr = client.read_holding_registers(
    address = 0x013C,
    count = 2, 
    device_id = 1, 
)
    
if rr.isError():
    print("Voltage read has failed", rr)

else:
    voltage = regs_to_float(rr.registers[0], rr.registers[1])
    print("Voltage (V):", voltage)

    


client.close()


