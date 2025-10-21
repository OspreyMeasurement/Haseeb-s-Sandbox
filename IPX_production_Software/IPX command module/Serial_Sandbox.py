import serial

try:
    ser = serial.Serial(
        port = 'COM5',
        baudrate = 9600,
        timeout = 5
    )
    print("Serial port opened successfully.")
    command = "op ots 0 list_sn\n"

    ser.write(command.encode("UTF-8"))


    response = ser.readline()
    if response:
        response = response.decode("UTF-8").strip()
        print("Received response from device:", response)
    else:
        print ("No response received from device.")



    ser.close()
    print("Serial port closed successfully.")

except serial.SerialException as e:
    print(f"Error opening serial port: {e}")