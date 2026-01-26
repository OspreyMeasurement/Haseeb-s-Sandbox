import argparse
import os
import csv
import json
from time import sleep, time
from serial import Serial
import struct
from safe_list_uids import safe_list_uids
import logging

def modbusCrc(msg): # bytearray, modbus crc calculation
    crc = 0xFFFF
    for n in range(len(msg)):
        crc ^= msg[n]
        for i in range(8):
            if crc & 1:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    #print(hex(crc>>8),hex(crc&0xff))
    return struct.pack("<H",crc)

def set_config(id):
    global list_uids, config
    flag=False
    for row in list_config:
        if id == row['uid']:
            #print(row)
            for key, val in row.items():
                #print(key,val)
                if key=="uid":
                    continue
                config[key]=val
            print("Updated conf.: ",config, "\n")
            flag=True
    return flag

def upload(uid, name):
    if name in ["main.py", "boot.py"]:
        print("You can't upload " + args[0] + ".")
        return False
    start=int(time())
    size=os.path.getsize(name)
    print("size", size)
    file_name=name.replace("\\","/").split("/")[-1]
    with open(name ,"rb") as f:
        data=f.read()
    #print("len", len(data))
    
    # trying to delete file brfore uploading

    ser.write("op bus {} delete {}\n".format(uid, file_name).encode())
    resp=ser.readline()
    print(resp)
    if len(resp)==0:
        return False
    
    ser.write("op bus {} upload {} {}\n".format(uid, file_name, size).encode())
    #print("send upload")
    while 1:
        resp=ser.readline()
        if len(resp)==0:
            return False
        print(resp)
        if resp.find("successfully".encode())>0:
            return True
        pos1=resp.find(b"CTS packet")
        if pos1>0:
            pos2=resp.find(b" ", pos1+11)
            pos3=resp.find(b"from ")
            pos4=resp.find(b"\n", pos1+11)
            try: # if packet number is not recognized
                pack_n=int(resp[pos1+11:pos2])
                pack_qty=int(resp[pos3+5:pos4])
                if pack_n<1 or pack_qty<1:
                    return False
                if pack_n==1:
                    if size%(1024*pack_qty)==0:
                        size_packet=(size//(1024*pack_qty))*1024
                    else:
                        size_packet=(size//(1024*pack_qty)+1)*1024
                    #print("size_packet", size_packet)
            except Exception as e:
                print(e)
                return False
            #print("pack_n",pack_n)
            packet=data[(pack_n-1)*size_packet:pack_n*size_packet]
            #print("packet",packet)
            crc=modbusCrc(packet)
            #print("crc",crc)
            ser.write(crc)
            ser.write(packet)
            ser.write(crc)
            #print("Output buffer", ser.out_waiting)
            while ser.out_waiting:
                pass
            resp=ser.readline()
            print(resp)
        else:
            return False 

def download(name_s, name_t): #name source and name target
    ser.write("op bus 0 download {}\n".format(name_s).encode())
    mode="wb"
    while 1:
        buff=bytearray()
        resp=ser.readline()
        #print(resp)
        if resp.find(b"Packet ")>=0:
            #print("Packet starts")
            start = int(time())
            while 1:
                if int(time())-start>10:
                    print("Download timeout.")
                    return False
                buff.extend(ser.read())
                #print("buff", buff1)
                if len(buff)>4 and buff[:2]==buff[-2:]:
                    #print("check",modbusCrc(buff[2:-2]),buff[:2],len(buff))
                    if modbusCrc(buff[2:-2]) == buff[:2]:
                        break
            data=buff[2:-2]
            with open(name_t,mode) as file:
                file.write(data)
            ser.write(("OK.\n").encode())
            mode="ab"
            print("Packet is OK.")
        else:
            # print(resp)
            ser.reset_input_buffer()
            return False
    return True

if __name__=='__main__':

    # set logging level
    logging.basicConfig(level=logging.DEBUG)

    list_uids=[]
    list_failed=[]
    list_config=[]
    config={}

    parser = argparse.ArgumentParser(description='OspreyBus Software Loader utility.')
    parser.add_argument('-n', metavar='name', type=str, nargs=1, help='name of product')
    parser.add_argument('-p', metavar='port', type=str, nargs=1, help='port') # added this argument for the realy com port
    parser.add_argument('-rp', metavar='relay_port', type=str, nargs=1, help='relay port')
    parser.add_argument('-u', metavar='uid', type=str, nargs= '+' , help='uid') # changed to + to accept multiple uids
    parser.add_argument('-e', metavar='expected_n_devices', type=int, nargs=1, help='expected number of devices')
    parser.add_argument('-f',  action='store_true', help='rewrite config file')
    args = parser.parse_args()
    
    if not args.n:
        print("Product not defined. Use -n <name>")
        exit()
    product=args.n[0]
    print("Product:", product)

    if not args.p:
        print("Port not defined. Use -p <port>")
        exit()
    port=args.p[0]
    print("Port:", port)
    
    if args.u:
        
        try:
            logging.debug(f"UIDS provided via command line raw format: {args.u}")
            # need to unpack uids from list of strings, and clean it:
            raw_string = " ".join(args.u)

            #2. clean string by turning syntax chars into spaces
            clean_string = raw_string.replace("[", " ").replace("]", " ").replace(",", " ") # replaces everything with spaces
            logging.debug(f"Cleaned UID string: {clean_string}")
            # now split based on whitespacaces to get uids
            list_uids = clean_string.split()
            logging.debug(f"Parsed UIDS: {list_uids}")
            #if uid_<1000000000:
             #   raise ValueError()

        except Exception as e:
           # print("Incorrect uid. Use -u <uid>")
            logging.error(f"Error passing uids:{e}")
            exit()

    if args.f:
        config_rewrite_flag=1
    else:
        config_rewrite_flag=0

    current_path=os.path.dirname(__file__)

    if os.name=="nt":
        path_delimiter="\\"
    else:
        path_delimiter="/"

    path_upload_folder=current_path+path_delimiter+"upload"+path_delimiter+product+path_delimiter+"flash"
    if not os.path.exists(path_upload_folder):
        print("No such folder as "+product+path_delimiter+"flash")
        exit()
    try:
        if product!="HUB":
            # filling list_uids if uid argument absent 
            if len(list_uids)==0:
                try:
                    list_uids = safe_list_uids(asp_com_port=args.p[0], relay_com_port=args.rp[0]) # call function to get uids safely
                except Exception as e:
                    print("Error getting uids:", e)
                    exit()

            # Check if the number of devices matches the expected number
            if args.e and len(list_uids) != args.e[0]:
                print(f"Error: Expected {args.e[0]} devices, but found {len(list_uids)}.")
                exit()

            sleep(0.5)
        else:
            list_uids=["0"]
            print("List_uids",list_uids, "\n")

        files=os.listdir(path_upload_folder)
        if "main.py" in files: 
            files.remove("main.py")
        if "boot.py" in files: 
            files.remove("boot.py")
        #    
        MAX_RETRIES = 3  # Maximum number of retry attempts
        n = 1
        for uid in list_uids:
            print("\nUpdating device {}.\n".format(uid))
            print("\nSensor {} in string.\n".format(n))
            n = n + 1

            with Serial(port=port, baudrate=9600, timeout=4) as ser:
                
                ser.write("op bus {} power_out 0\n".format(uid).encode())
                resp=ser.readline()
                if len(resp)>0:
                    print(resp)
                else:
                    list_failed.append(uid)
                    print(uid+": Error: No response for power_out 0")
                    continue
                
                # for deleting old config file
                if config_rewrite_flag:
                    config_name="w_"+product.lower()+"_config.json"
                    #print("config_name", config_name)
                    ser.write("op bus {} delete {}\n".format(uid, config_name).encode())
                    resp=ser.readline()
                    if len(resp)>0:
                        print(resp)
                    else:
                        list_failed.append(uid)
                        print(uid+": Error: No response for delete {}", config_name)
                        #continue
                
                ser.write("op bus {} set_baud 115200\n".format(uid).encode())
                resp=ser.readline()
                if len(resp)>0:
                    print(resp)
                else:
                    list_failed.append(uid)
                    print(uid+": Error: No response for set_baud 115200")
                    continue
            sleep(0.5) # important!
            with Serial(port=port, baudrate=115200, timeout=6) as ser: # previously timeout was a 12s 
                #download("123","none") ## I'm not sure why this call is needed, but without it the files are not uploaded
                # copying files to dev
                print("Upload folder path: ", path_upload_folder)
                print("Files: ", files)
                upload_failed = False
                for i in files:
                    retry_count = 0
                    while retry_count < MAX_RETRIES:
                        print(f"\nUploading {i} (Attempt {retry_count + 1})")
                        if upload(uid, path_upload_folder+path_delimiter+i):
                            print(f"File {i} uploaded successfully.")
                            break
                        else:
                            retry_count += 1
                            if retry_count < MAX_RETRIES:
                                print(f"{uid}: Error: Uploading {i} failed. Retrying...")
                            else:
                                print(f"{uid}: Error: Uploading {i} failed after {MAX_RETRIES} attempts.")
                                upload_failed = True
                                break
                    
                    if upload_failed:
                        break

                if upload_failed:
                    list_failed.append(uid)
                    print(f"{uid}: Error: Upload process failed.")
                    continue

                # supply power to the next device
                ser.write("op bus {} power_out 1\n".format(uid).encode())
                resp=ser.readline()
                if len(resp)>0:
                    print("\n"+str(resp))
                else:
                    list_failed.append(uid)
                    print(uid+": Error: No response for power_out 1")
                    continue
                sleep(2) #time for next sensor to boot
                
                ser.write("op bus {} shutdown\n".format(uid).encode())
                #ser.write("op bus {} set_baud 9600\n".format(uid).encode())
                resp=ser.readline()
                if len(resp)>0:
                    print(resp)
                else:
                    list_failed.append(uid)
                    print(uid+": Error: No response for shutdown")
                    continue
            print("\nDevice {} updated.".format(uid))
            sleep(2)
        if len(list_failed)>0:
            print("\nDevices that were not updated: ", list_failed)
        print("\nReset Bus after updating.")
    except Exception as e:
        print("Upload error.")
        print(e)