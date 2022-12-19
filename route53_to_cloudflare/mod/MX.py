#!/usr/bin/env python3

def set_MX_value(records_value):
    setPV="" 
    setPV2=""
    setPV3=""
    setPV4=""
    setPV5=""
    # get priority and value
    if len(records_value) > 0:
        setPV = records_value[0]['Value'].split()
    if len(records_value) > 1:
        setPV2 = records_value[1]['Value'].split()  
    if len(records_value) > 2:
        setPV3 = records_value[2]['Value'].split() 
    if len(records_value) > 3:
        setPV4 = records_value[3]['Value'].split()
    if len(records_value) == 5:
        setPV5 = records_value[4]['Value'].split()

    return setPV, setPV2, setPV3, setPV4, setPV5
