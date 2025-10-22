from IPX import IPXSerialCommunicator


with IPXSerialCommunicator(port='COM8', baudrate=9600, timeout=5) as ipx_comm:
    # print(ipx_comm.list_uids())
    print(ipx_comm.get_status(0))
    # print(ipx_comm.get_raw(1020901966))