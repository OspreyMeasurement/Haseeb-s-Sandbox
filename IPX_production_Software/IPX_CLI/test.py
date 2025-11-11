"""File for doing some stupid shit"""
from IPX import IPXSerialCommunicator
from IPX import IPXConfigurator
import logging

#initialise logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',)

with IPXSerialCommunicator(port="com5", baudrate=9600) as ipx:
    configurator = IPXConfigurator(port="com5", initial_baudrate=9600)
    uids_list = ipx.list_uids(data_type='list')
    alias_and_uids_list = configurator.set_default_parameters(ipx, uids_list)
    print(alias_and_uids_list)