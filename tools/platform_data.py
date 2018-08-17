#!/usr/bin/env python

# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import random
import time
import sys

import os, commands, platform, subprocess, re
import requests
import netifaces
import fcntl, socket, struct



# get interfaces
interface_list = netifaces.interfaces()

# get all mac address
def get_mac_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
    return ''.join(['%02x:' % ord(char) for char in info[18:24]])[:-1]


# ger vendor details by calling the api
def vendor_details():
        for iface_name in interface_list:
	    mac=get_mac_address(ifname=str(iface_name))
            print("vendor details for [%s] is as bellow:" %iface_name)
            print("%s\n" % requests.get("http://macvendors.co/api/"+mac).text)


# get all mac address
def display_all_macaddress():
        myvalue='['
        for iface_name in interface_list:
	    mac=get_mac_address(ifname=str(iface_name))
            myvalue+="%s-%s;" % (iface_name,mac)
        myvalue+="]"
	return myvalue


# get cpu info
def get_cpu_info(property):
    if platform.system() == "Linux":
        command = "cat /proc/cpuinfo"
        all_info = subprocess.check_output(command, shell=True).strip()
        for line in all_info.split("\n"):
            if property in line.lower():
		mykey = line.split(":")
		if mykey[0].rstrip().lower() == property:
		    return mykey[1]
    return ""


if __name__ == '__main__':
    print ( "Process started ..... %s" % time.strftime("%c"))
    print("All MAC Address: %s\n" % display_all_macaddress())
    vendor_details()
    print("Model Name: %s" % get_cpu_info("model name"))
    print("Serial Number: %s" % get_cpu_info("serial"))
    print("Hardware : %s" % get_cpu_info("hardware"))
    print("Revision : %s" % get_cpu_info("revision"))
    print ( "Process end ..... %s" % time.strftime("%c"))



