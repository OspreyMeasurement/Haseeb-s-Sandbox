from IPX import IPXSerialCommunicator

# software shoudl ask how many sensors we are expecting to configurate, sometimes for some reason, software does not pickup all sensors
with IPXSerialCommunicator(port='COM8', baudrate=9600, timeout=5) as ipx_comm:
    print(ipx_comm.list_uids(data_type='array'))
    print(ipx_comm.get_status(1020901966, data_type='dict'))
    print(ipx_comm.get_raw(1020901966, data_type='array'))