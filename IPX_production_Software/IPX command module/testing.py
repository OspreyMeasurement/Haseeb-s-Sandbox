from IPX import IPXSerialCommunicator
import time
import logging

# Initialise logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')

# software shoudl ask how many sensors we are expecting to configurate, sometimes for some reason, software does not pickup all sensors
with IPXSerialCommunicator(port='COM8', baudrate=9600, timeout=5, verify=True) as ipx_comm:
    print(ipx_comm.list_uids(data_type='string'))

    print(ipx_comm.set_alias(1020901966, '10'))

    # print(ipx_comm.get_status(1020901966, data_type='dict'))
    # print(ipx_comm.get_raw(1020901966, data_type='array'))

#     # print(ipx_comm.set_uid(1020901966, 1))
#     print(ipx_comm.set_baud(uid=1020901966, baud=9600))



# with IPXSerialCommunicator(port='COM8', baudrate=9600, timeout=5) as ipx_comm:
#     # print(ipx_comm.set_uid(current_uid=1, new_uid=1020901966))
    print(ipx_comm.set_gain(uid=1020901966, gain=2))
    print(ipx_comm.set_centroid_threshold( 1020901966 , 10))
    print(ipx_comm.set_centroid_res(1020901966, 10))
    print(ipx_comm.set_n_stds(1020901966, 10))
    print(ipx_comm.set_term(1020901966, 0))
    print(ipx_comm.set_alias(1020901966, 20))
