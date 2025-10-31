import serial
import time
import numpy as np
# try:
#     ser = serial.Serial(
#         port = 'COM8',
#         baudrate = 9600,
#         timeout = 5
#     )
#     print("Serial port opened successfully.")
#     command = "op ipx 0 list_uids\n"

#     ser.write(command.encode("UTF-8"))


#     # response = ser.readline()
#     # response = ser.readall()  # read all available data
#     # if response:
#     #     response = response.decode("UTF-8").strip()
#     #     print("Received response from device:", response)
#     # else:
#     #     print ("No response received from device.")



#     time.sleep(0.2)  # wait for 2 seconds to ensure all data is received
#     response = ser.read_all().decode("UTF-8").strip()  # read all available data # ask dan why this doesnt work
#     print(response)




#     ser.close()
#     print("Serial port closed successfully.")

# except serial.SerialException as e:
#     print(f"Error opening serial port: {e}")





#     # def send_and_receive(self, command:str) -> str:
#     #     """ Sends command to IPX device, and receives response"""
#     #     if not self.connection:
#     #         print("ERROR: Not connected")
#     #         return ""
#     #     # send command (add prints for debugging)
#     #     self.connection.write(command.encode("UTF-8"))
#     #     print(f"Sent command: {command.strip()}")
#     #     # receive response
#     #     response = self.connection.readline()
#     #     response = response.decode("UTF-8").strip()
#     #     print("Received response:", response)
#     #     return response
#     # original send and receive method


# def simpleaddition (a, b):
#     sum = a + b
#     multi = a * b
#     return sum, multi
    
# result = simpleaddition (2, 3)
# print (result)


# uids_list = [102, 103, 104, 105, 106]
# aliases = list(range(len(uids_list), 0, -1))

# print(aliases)


# combined_list = zip(range(len(uids_list), 0, -1), uids_list)
# print(combined_list)

# combined_list = list(combined_list)
# print(combined_list)
# # for index, uid in 



mylist = [(1, 5, 5, 7, 9), (2, 6, 6, 8, 10), (3, 7, 7, 9, 11), (4, 8, 8, 10, 12), (5, 9, 9, 11, 13)]
first = mylist[0]
print(first[])




