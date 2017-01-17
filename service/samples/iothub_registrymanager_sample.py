# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import random
import time
import sys
import iothub_service_client
from iothub_service_client import *
from iothub_service_client_args import *

# String containing Hostname, SharedAccessKeyName & SharedAccessKey in the format:
# "HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>"
connection_string = "[IoTHub Connection String]";
device_id = "[Device Id]";

def printDeviceInfo(title, iothubDevice):
    print(title + ":")
    print("iothubDevice.deviceId                    = {0}".format(iothubDevice.deviceId))
    print("iothubDevice.primaryKey                  = {0}".format(iothubDevice.primaryKey))
    print("iothubDevice.secondaryKey                = {0}".format(iothubDevice.secondaryKey))
    print("iothubDevice.generationId                = {0}".format(iothubDevice.generationId))
    print("iothubDevice.eTag                        = {0}".format(iothubDevice.eTag))
    print("iothubDevice.connectionState             = {0}".format(iothubDevice.connectionState))
    print("iothubDevice.connectionStateUpdatedTime  = {0}".format(iothubDevice.connectionStateUpdatedTime))
    print("iothubDevice.status                      = {0}".format(iothubDevice.status))
    print("iothubDevice.statusReason                = {0}".format(iothubDevice.statusReason))
    print("iothubDevice.statusUpdatedTime           = {0}".format(iothubDevice.statusUpdatedTime))
    print("iothubDevice.lastActivityTime            = {0}".format(iothubDevice.lastActivityTime))
    print("iothubDevice.cloudToDeviceMessageCount   = {0}".format(iothubDevice.cloudToDeviceMessageCount))
    print("iothubDevice.isManaged                   = {0}".format(iothubDevice.isManaged))
    print("iothubDevice.configuration               = {0}".format(iothubDevice.configuration))
    print("iothubDevice.deviceProperties            = {0}".format(iothubDevice.deviceProperties))
    print("iothubDevice.serviceProperties           = {0}".format(iothubDevice.serviceProperties))
    print("iothubDevice.authMethod                  = {0}".format(iothubDevice.authMethod))
    print("")

def iothub_registrymanager_sample_run():

    try:
        # RegistryManager
        iothubRegistryManager = IoTHubRegistryManager(connection_string)

        # CreateDevice
        primaryKey = "aaabbbcccdddeeefffggghhhiiijjjkkklllmmmnnnoo"
        secondaryKey = "111222333444555666777888999000aaabbbcccdddee"
        authMethod = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY;
        newDevice = iothubRegistryManager.create_device(device_id, primaryKey, secondaryKey, authMethod)
        printDeviceInfo("CreateDevice", newDevice)

        # GetDevice
        iothubDevice = iothubRegistryManager.get_device(device_id)
        printDeviceInfo("GetDevice", iothubDevice)

        # UpdateDevice
        primaryKey = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        secondaryKey = "yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
        status = IoTHubDeviceStatus.DISABLED
        authMethod = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY;
        iothubRegistryManager.update_device(device_id, primaryKey, secondaryKey, status, authMethod)
        updatedDevice = iothubRegistryManager.get_device(device_id)
        printDeviceInfo("UpdateDevice", updatedDevice)

        # DeleteDevice
        print("DeleteDevice")
        iothubRegistryManager.delete_device(device_id)
        print("")

        # GetDeviceList
        print("GetDeviceList")
        numberOfDevices = 3
        devList = iothubRegistryManager.get_device_list(numberOfDevices)

        numberOfDevices = len(devList)
        print("Number of devices                        : {0}".format(numberOfDevices))

        for x in range(0, numberOfDevices):
            title = "Device " + str(x)
            printDeviceInfo(title, devList[x])
        print("")

        # GetStatistics
        iothubRegistryStatistics = iothubRegistryManager.get_statistics()
        print("GetStatistics")
        print("Total device count                       : {0}".format(iothubRegistryStatistics.totalDeviceCount));
        print("Enabled device count                     : {0}".format(iothubRegistryStatistics.enabledDeviceCount));
        print("Disabled device count                    : {0}".format(iothubRegistryStatistics.disabledDeviceCount));
        print("")

    except IoTHubError as e:
        print("Unexpected error {0}".format(e))
        return
    except KeyboardInterrupt:
        print("IoTHubRegistryManager sample stopped")

def usage():
    print("Usage: iothub_registrymanager_sample.py -c <connectionstring> -d <deviceid>")
    print("    connectionstring: <HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>>")
    print("    deviceid        : <New device ID for CRUD operations>")

if __name__ == '__main__':
    print("")
    print("Python {0}".format(sys.version))
    print("IoT Hub Service Client for Python SDK Version: {0}".format(iothub_service_client.__version__))
    print("")

    try:
        (connection_string, device_id) = get_iothub_opt(sys.argv[1:], connection_string, device_id)
    except OptionError as o:
        print(o)
        usage()
        sys.exit(1)

    print("Starting the IoT Hub Service Client Registry Manager Python sample...")
    print("    Connection string = {0}".format(connection_string))
    print("    Device ID         = {0}".format(device_id))

    iothub_registrymanager_sample_run()
