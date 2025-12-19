import math


#to calculate cutting lengths, we need magnet target depth, and
# magnet target depth magnet above

ipx_board_length = 0.54 # meters
cable_scaling_factor = 1

def calculate_cutting_length(magnet_target_depth, magnet_depth_above, ipx_board_length, cable_slack):
    """ Calculates cutting length for the cables for all magnets other than top"""
    cutting_length = (magnet_target_depth - magnet_depth_above - ipx_board_length + (cable_slack / 1000))
    return cutting_length


def calculate_top_cable_length(magnet_target_depth, cable_top_bh, ipx_board_length, cable_scaling_factor):
    """ Calculates cutting length for the top cable """
    top_cable_length = ((magnet_target_depth - cable_top_bh - (ipx_board_length / 2) ) * cable_scaling_factor)
    return top_cable_length



# segment 


print(calculate_cutting_length(39.82, 18.82, ipx_board_length, 150))