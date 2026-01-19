"""File for doing some stupid shit"""
from IPX import IPXSerialCommunicator
from IPX import IPXConfigurator
import logging
from IPX_datalogger_tester import IPXGeosenseTester
from IPX_datalogger_tester import IPXModbusTester

#initialise logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',)

# with IPXSerialCommunicator(port="com5", baudrate=9600) as ipx:
#     configurator = IPXConfigurator(port="com5", initial_baudrate=9600)
#     uids_list = ipx.list_uids(data_type='list')
#     alias_and_uids_list = configurator.set_default_parameters(ipx, uids_list)
#     print(alias_and_uids_list)

# with IPXSerialCommunicator(port="com5", baudrate=9600) as ipx:
    # print(ipx.list_uids())
    # print(ipx.set_uid(current_uid=1020901182, new_uid=1040901186))
    # print(ipx.get_status(uid=1040901186))
    # ipx.set_alias(uid=1040901186, alias=1)

with IPXGeosenseTester(port="com5", baudrate=9600) as geosense_tester:
    print(geosense_tester.gxm_measure_test(1040901186))


# with IPXModbusTester(port="com5", baudrate=9600) as modbus_tester:
#     modbus_tester.run_full_test(uid=1040901186, alias=1)