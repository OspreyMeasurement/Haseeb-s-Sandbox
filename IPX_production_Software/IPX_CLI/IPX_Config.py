""" This file is for holding all configuration settings for the IPX devices and all the commands, such as
list_uids, configurate etc"""

class IPXCommands:
    """ Configuration holder for IPX settings, configurations and paths"""

    # Just namespace so make the class instantiable, to prevent accidental instantiation
    def __init__(self):
        raise RuntimeError("IPXConfig is a static class and cannot be instantiated")
    
    # Defaul IPX settings (Baud rate of 9600 is once configurated)
    class Default_settings:
        Axis: int = 1
        Gain: int = 3
        Centroid_threshold: int = 800
        Centroid_res: int = 10
        Termination: int = 0 # or use false? Termination = False? (depends on how its used in terminal)
        Check_sensor_uid: str = "1111111111"
        Baud_rate: int = 9600
        N_stds: int = 10


    # # Serial communication settings
    # class Serial_settings:
    #     Baud_rates: list[int] = [9600, 115200]
    #     Timeout: int = 5  # seconds
    #     Retry_attempts: int = 3 # add this variable for attempting to retry failed config? etc
    #     Retry_delay: int = 2  # seconds ( and delay as well)
    #     Default_baud = 115200

    class Commands:
        # Status/ listing strings:
        list_uids: str = "op ipx 0 list_uids\n" 
        get_status: str = "op ipx {uid} get_status\n"
        get_raw: str = "op ipx {uid} get_raw\n"

        # calibration string:
        calibrate: str = "op ipx {uid} calibrate\n"

        # set function strings:
        set_baud: str = "op ipx {uid} set_baud {baud}\n"
        set_uid: str = "op ipx {current_uid} set_uid 567892 {new_uid}\n"# play around with the formatting
                                                                        # using uids and old_uids might get confusing, maybe rename to current_uid and new_uid?
        set_axis: str = "op ipx {uid} set_axis {axis}\n"
        set_gain: str = "op ipx {uid} set_gain {gain}\n"
        set_centroid_threshold: str = "op ipx {uid} set_centroid_threshold {threshold}\n"
        set_centroid_res: str = "op ipx {uid} set_centroid_res {resolution}\n"
        set_n_stds: str = "op ipx {uid} set_n_stds {n_stds}\n"
        set_term: str = "op ipx {uid} set_term {termination}\n"
        set_alias: str = "op ipx {uid} set_alias {alias}\n"

        # geosense command string/s
        get_GXM_measurement: str = "@@{uid} SR\r" # Geosense command to get measurement from IPX insert


    class Responses:
        """ Expected response strings from IPX devices """
        set_axis: str = "CMD_EXEC_Set_Axis: Axis set to"
        set_gain: str = "CMD_EXEC_Set_Gain: Gain set to"
        set_centroid_threshold: str = "CMD_EXEC_Set_Centroid_Threshold: Centroiding threshold is set to"
        set_n_stds: str = "CMD_EXEC_Set_N_STDDevs: Number of standard deviations set to"
        set_centroid_res: str = "CMD_EXEC_Set_Centroid_Res: Centroiding resolution set to"
        set_term: str = "CMD_EXEC_Enable_120R: 120ohm termination"
        set_uid: str = "CMD_EXEC_Set_UID: UID set to"
        set_baud: str = "CMD_EXEC_Set_Baud: Baudrate set to"
        set_alias: str = "CMD_EXEC_Set_Alias: Alias set to"
        CALIBRATION_COMPLETE: str = "CMD_EXEC_Calibrate: Calibration on all sensors complete, saving to memory."
        get_gxm_measurement: str = "SR"  # Response prefix for Geosense measurement command








        
