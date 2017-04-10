# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import sys
import iothub_service_client
from iothub_service_client import IoTHubRegistryManager, IoTHubRegistryManagerAuthMethod
from iothub_service_client import IoTHubDeviceStatus, IoTHubError
from iothub_service_client_args import get_iothub_opt, OptionError

# String containing Hostname, SharedAccessKeyName & SharedAccessKey in the format:
# "HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>"
CONNECTION_STRING = "[IoTHub Connection String]"
DEVICE_ID = "[New Device Id]"


def print_device_info(title, iothub_device):
    print ( title + ":" )
    print ( "iothubDevice.deviceId                    = {0}".format(iothub_device.deviceId) )
    print ( "iothubDevice.primaryKey                  = {0}".format(iothub_device.primaryKey) )
    print ( "iothubDevice.secondaryKey                = {0}".format(iothub_device.secondaryKey) )
    print ( "iothubDevice.generationId                = {0}".format(iothub_device.generationId) )
    print ( "iothubDevice.eTag                        = {0}".format(iothub_device.eTag) )
    print ( "iothubDevice.connectionState             = {0}".format(iothub_device.connectionState) )
    print ( "iothubDevice.connectionStateUpdatedTime  = {0}".format(iothub_device.connectionStateUpdatedTime) )
    print ( "iothubDevice.status                      = {0}".format(iothub_device.status) )
    print ( "iothubDevice.statusReason                = {0}".format(iothub_device.statusReason) )
    print ( "iothubDevice.statusUpdatedTime           = {0}".format(iothub_device.statusUpdatedTime) )
    print ( "iothubDevice.lastActivityTime            = {0}".format(iothub_device.lastActivityTime) )
    print ( "iothubDevice.cloudToDeviceMessageCount   = {0}".format(iothub_device.cloudToDeviceMessageCount) )
    print ( "iothubDevice.isManaged                   = {0}".format(iothub_device.isManaged) )
    print ( "iothubDevice.configuration               = {0}".format(iothub_device.configuration) )
    print ( "iothubDevice.deviceProperties            = {0}".format(iothub_device.deviceProperties) )
    print ( "iothubDevice.serviceProperties           = {0}".format(iothub_device.serviceProperties) )
    print ( "iothubDevice.authMethod                  = {0}".format(iothub_device.authMethod) )
    print ( "" )


def iothub_registrymanager_sample_run():
    try:
        # RegistryManager
        iothub_registry_manager = IoTHubRegistryManager(CONNECTION_STRING)

        # CreateDevice
        primary_key = "aaabbbcccdddeeefffggghhhiiijjjkkklllmmmnnnoo"
        secondary_key = "111222333444555666777888999000aaabbbcccdddee"
        auth_method = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY
        new_device = iothub_registry_manager.create_device(DEVICE_ID, primary_key, secondary_key, auth_method)
        print_device_info("CreateDevice", new_device)

        # GetDevice
        iothub_device = iothub_registry_manager.get_device(DEVICE_ID)
        print_device_info("GetDevice", iothub_device)

        # UpdateDevice
        primary_key = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        secondary_key = "yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
        status = IoTHubDeviceStatus.DISABLED
        auth_method = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY
        iothub_registry_manager.update_device(DEVICE_ID, primary_key, secondary_key, status, auth_method)
        updated_device = iothub_registry_manager.get_device(DEVICE_ID)
        print_device_info("UpdateDevice", updated_device)

        # DeleteDevice
        print ( "DeleteDevice" )
        iothub_registry_manager.delete_device(DEVICE_ID)
        print ( "" )

        # GetDeviceList
        print ( "GetDeviceList" )
        number_of_devices = 3
        dev_list = iothub_registry_manager.get_device_list(number_of_devices)

        number_of_devices = len(dev_list)
        print ( "Number of devices                        : {0}".format(number_of_devices) )

        for device in range(0, number_of_devices):
            title = "Device " + str(device)
            print_device_info(title, dev_list[device])
        print ( "" )

        # GetStatistics
        iothub_registry_statistics = iothub_registry_manager.get_statistics()
        print ( "GetStatistics" )
        print ( "Total device count                       : {0}".format(iothub_registry_statistics.totalDeviceCount) )
        print ( "Enabled device count                     : {0}".format(iothub_registry_statistics.enabledDeviceCount) )
        print ( "Disabled device count                    : {0}".format(iothub_registry_statistics.disabledDeviceCount) )
        print ( "" )

    except IoTHubError as iothub_error:
        print ( "Unexpected error {0}".format(iothub_error) )
        return
    except KeyboardInterrupt:
        print ( "IoTHubRegistryManager sample stopped" )


def usage():
    print ( "Usage: iothub_registrymanager_sample.py -c <connection_string> -d <device_id>" )
    print ( "  connectionstring: <HostName=<host_name>;SharedAccessKeyName=<shared_access_key_name>;" \
          "SharedAccessKey=<shared_access_key>> " )
    print ( "  deviceid        : <New device ID for CRUD operations>" )


if __name__ == '__main__':
    print ( "" )
    print ( "Python {0}".format(sys.version) )
    print ( "IoT Hub Service Client for Python" )
    print ( "" )

    try:
        (CONNECTION_STRING, DEVICE_ID) = get_iothub_opt(sys.argv[1:], CONNECTION_STRING, DEVICE_ID)
    except OptionError as option_error:
        print ( option_error )
        usage()
        sys.exit(1)

    print ( "Starting the IoT Hub Service Client Registry Manager Python sample..." )
    print ( "    Connection string = {0}".format(CONNECTION_STRING) )
    print ( "    Device ID         = {0}".format(DEVICE_ID) )

    iothub_registrymanager_sample_run()
