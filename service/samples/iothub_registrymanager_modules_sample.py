# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import sys
import iothub_service_client
from iothub_service_client import IoTHubRegistryManager, IoTHubRegistryManagerAuthMethod
from iothub_service_client import IoTHubDeviceStatus, IoTHubError
from iothub_service_client_args import get_iothub_opt_with_module, OptionError

# The connection string can either be an IoT Hub's connection string in the format:
#   "HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>"
# Or the connection string can be for a device in the format:
#   "HostName=<host_name>;DeviceId=<device_id>;SharedAccessKey=<SharedAccessKey>"
# For most operations, you should use the device's connection string as this has more limited scope for security.
CONNECTION_STRING = "[IoTHub Connection String]"
DEVICE_ID = "[Existing Device Id]"
MODULE_ID = "[New Module Id]"


def print_module_info(title, iothub_module):
    print ( title + ":" )
    print ( "iothubModule.deviceId                    = {0}".format(iothub_module.deviceId) )
    print ( "iothubModule.moduleId                    = {0}".format(iothub_module.moduleId) )
    print ( "iothubModule.managedBy                   = {0}".format(iothub_module.managedBy) )
    print ( "iothubModule.primaryKey                  = {0}".format(iothub_module.primaryKey) )
    print ( "iothubModule.secondaryKey                = {0}".format(iothub_module.secondaryKey) )
    print ( "iothubModule.generationId                = {0}".format(iothub_module.generationId) )
    print ( "iothubModule.eTag                        = {0}".format(iothub_module.eTag) )
    print ( "iothubModule.connectionState             = {0}".format(iothub_module.connectionState) )
    print ( "iothubModule.connectionStateUpdatedTime  = {0}".format(iothub_module.connectionStateUpdatedTime) )
    print ( "iothubModule.lastActivityTime            = {0}".format(iothub_module.lastActivityTime) )
    print ( "iothubModule.cloudToDeviceMessageCount   = {0}".format(iothub_module.cloudToDeviceMessageCount) )
    print ( "iothubModule.authMethod                  = {0}".format(iothub_module.authMethod) )
    print ( "" )


def iothub_registrymanager_modules_sample_run():
    try:
        # RegistryManager
        iothub_registry_manager = IoTHubRegistryManager(CONNECTION_STRING)

        # CreateModule
        primary_key = "aaabbbcccdddeeefffggghhhiiijjjkkklllmmmnnnoo"
        secondary_key = "111222333444555666777888999000aaabbbcccdddee"
        auth_method = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY
        new_module = iothub_registry_manager.create_module(DEVICE_ID, primary_key, secondary_key, MODULE_ID, auth_method)
        print_module_info("CreateModule", new_module)

        # GetModule
        iothub_module = iothub_registry_manager.get_module(DEVICE_ID, MODULE_ID)
        print_module_info("GetModule", iothub_module)

        # UpdateModule
        primary_key = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        secondary_key = "yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
        auth_method = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY
        managedBy = "testManagedBy"
        iothub_registry_manager.update_module(DEVICE_ID, primary_key, secondary_key, MODULE_ID, auth_method, managedBy)
        updated_module = iothub_registry_manager.get_module(DEVICE_ID, MODULE_ID)
        print_module_info("UpdateModule", updated_module)

        # GetModuleList
        print ( "GetModuleList" )
        number_of_modules = 10
        modules_list = iothub_registry_manager.get_module_list(DEVICE_ID)

        number_of_modules = len(modules_list)
        print ( "Number of modules                        : {0}".format(number_of_modules) )

        for moduleIndex in range(0, number_of_modules):
            title = "Module " + str(moduleIndex)
            print_module_info(title, modules_list[moduleIndex])
        print ( "" )

        # DeleteModule
        print ( "DeleteModule" )
        iothub_registry_manager.delete_module(DEVICE_ID, MODULE_ID)
        print ( "" )

    except IoTHubError as iothub_error:
        print ( "Unexpected error {0}".format(iothub_error) )
        return
    except KeyboardInterrupt:
        print ( "IoTHubRegistryManager sample stopped" )


def usage():
    print ( "Usage: iothub_registrymanager_modules_sample.py -c <connection_string> -d <device_id> -m <module_id>" )
    print ( "    connectionString::                                                                                                  " )     
    print ( "    * When using the device's connection string (gives the application access to this device's modules                    " )
    print ( "        connectionstring: <HostName=<host_name>;DeviceId=<device_id>;SharedAccessKey=<SharedAccessKey>>                   " )
    print ( "    * When using the device's connection string (gives the application access to this device's modules                    " )    
    print ( "        connectionstring: <HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>>" )
    print ( "    deviceid        : <*EXISTING* device ID to perform module operations on>" )
    print ( "    moduleid        : <New module ID for CRUD operations>" )


if __name__ == '__main__':
    print ( "" )
    print ( "Python {0}".format(sys.version) )
    print ( "IoT Hub Service Client for Python" )
    print ( "" )

    try:
        (CONNECTION_STRING, DEVICE_ID, MODULE_ID) = get_iothub_opt_with_module(sys.argv[1:], CONNECTION_STRING, DEVICE_ID, MODULE_ID)
    except OptionError as option_error:
        print ( option_error )
        usage()
        sys.exit(1)

    print ( "Starting the IoT Hub Service Client Registry Manager Python sample..." )
    print ( "    Connection string = {0}".format(CONNECTION_STRING) )
    print ( "    Device ID         = {0}".format(DEVICE_ID) )
    print ( "    Module ID         = {0}".format(MODULE_ID) )

    iothub_registrymanager_modules_sample_run()
