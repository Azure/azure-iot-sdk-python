# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import os
import sys
import iothub_service_client
from iothub_service_client import IoTHubDeviceConfigurationManager, IoTHubDeviceConfiguration
from iothub_service_client import IoTHubDeviceStatus, IoTHubError
from iothub_service_client_args import get_iothub_opt_configuration_id, OptionError

# String containing Hostname, SharedAccessKeyName & SharedAccessKey in the format:
# "HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>"
CONNECTION_STRING = None
CONFIGURATION_ID = None
MODULE_CONTENT = '''{"sunny": {"properties.desired": {"temperature": 69,"humidity": 30}}, 
                                      "goolily": {"properties.desired": {"elevation": 45,"orientation": "NE"}}, 
                                      "$edgeAgent": {"properties.desired": {"schemaVersion": "1.0","runtime": {"type": "docker","settings": {"minDockerVersion": "1.5","loggingOptions": ""}},"systemModules": 
                                                {"edgeAgent": {"type": "docker","settings": {"image": "edgeAgent","createOptions": ""},"configuration": {"id": "configurationapplyedgeagentreportinge2etestcit-config-a9ed4811-1b57-48bf-8af2-02319a38de01"}}, 
                                                "edgeHub": {"type": "docker","status": "running","restartPolicy": "always","settings": {"image": "edgeHub","createOptions": ""},"configuration": {"id": "configurationapplyedgeagentreportinge2etestcit-config-a9ed4811-1b57-48bf-8af2-02319a38de01"}}}, 
                                                    "modules": {"sunny": {"version": "1.0","type": "docker","status": "running","restartPolicy": "on-failure","settings": {"image": "mongo","createOptions": ""},"configuration": {"id": "configurationapplyedgeagentreportinge2etestcit-config-a9ed4811-1b57-48bf-8af2-02319a38de01"}}, 
                                                    "goolily": {"version": "1.0","type": "docker","status": "running","restartPolicy": "on-failure","settings": {"image": "asa","createOptions": ""},"configuration": {"id": "configurationapplyedgeagentreportinge2etestcit-config-a9ed4811-1b57-48bf-8af2-02319a38de01"}}}}}, 
                                      "$edgeHub": {"properties.desired": {"schemaVersion": "1.0","routes": {"route1": "from * INTO $upstream"},"storeAndForwardConfiguration": {"timeToLiveSecs": 20}}}}'''


def print_config_info(title, iothub_deviceconfig):
    print ( title + ":" )
    print ( "iothub_deviceconfig.targetCondition                = {0}".format(iothub_deviceconfig.targetCondition) )
    print ( "iothub_deviceconfig.schemaVersion                  = {0}".format(iothub_deviceconfig.schemaVersion) )
    print ( "iothub_deviceconfig.configurationId                = {0}".format(iothub_deviceconfig.configurationId) )
    print ( "iothub_deviceconfig.eTag                           = {0}".format(iothub_deviceconfig.eTag) )
    print ( "iothub_deviceconfig.createdTimeUtc                 = {0}".format(iothub_deviceconfig.createdTimeUtc) )
    print ( "iothub_deviceconfig.priority                       = {0}".format(iothub_deviceconfig.priority) )
    print ( "iothub_deviceconfig.content.deviceContent          = {0}".format(iothub_deviceconfig.content.deviceContent) )
    print ( "iothub_deviceconfig.content.modulesContent         = {0}".format(iothub_deviceconfig.content.modulesContent) )
    print ( "" )

def run_deviceconfig():
    try:
        iothub_deviceconfiguration = IoTHubDeviceConfiguration()
        iothub_deviceconfiguration.targetCondition = "tags.UniqueTag='configurationapplyedgeagentreportinge2etestcita5b4e2b7f6464fe9988feea7d887584a' and tags.Environment='test'"
        iothub_deviceconfiguration.configurationId =  CONFIGURATION_ID
        iothub_deviceconfiguration.priority = 10
        iothub_deviceconfiguration.content.deviceContent = ""
        iothub_deviceconfiguration.content.modulesContent = MODULE_CONTENT
        iothub_deviceconfiguration.labels["label1"] = "value1"
        iothub_deviceconfiguration.labels["label2"] = "value2"

        # add_configuration
        iothub_deviceconfiguration_manager = IoTHubDeviceConfigurationManager(CONNECTION_STRING)

        print("Adding configuration <{0}>".format(iothub_deviceconfiguration.configurationId))
        iothub_deviceconfig_add = iothub_deviceconfiguration_manager.add_configuration(iothub_deviceconfiguration)
        print_config_info("Added object", iothub_deviceconfig_add)

        # get_configuration
        print("Getting configuration <{0}>".format(iothub_deviceconfiguration.configurationId))
        iothub_deviceconfig_get = iothub_deviceconfiguration_manager.get_configuration(CONFIGURATION_ID)
        print_config_info("GetConfiguration", iothub_deviceconfig_get)

        # update_configuration
        iothub_deviceconfig_add.targetCondition = "tags.UniqueTag='configurationapplyedgeagentreportinge2etestcita5b4e2b7f6464fe9988feea7d887584a' and tags.Environment='test'"
        iothub_deviceconfig_update = iothub_deviceconfiguration_manager.update_configuration(iothub_deviceconfig_add)
        print_config_info("Updated configuration", iothub_deviceconfig_update)

        # get_configuration_list
        print ( "get_configuration_list" )
        number_of_configurations = 10
        configuration_list = iothub_deviceconfiguration_manager.get_configuration_list(20)

        number_of_configurations = len(configuration_list)
        print ( "Number of configuration                       : {0}".format(number_of_configurations) )

        for configurationIndex in range(0, number_of_configurations):
            title = "Configuration " + str(configurationIndex)
            print_config_info(title, configuration_list[configurationIndex])
        print ( "" )

        print(" Deleting {0}".format(CONFIGURATION_ID))
        iothub_deviceconfiguration_manager.delete_configuration(CONFIGURATION_ID)
        print(" done ")

    except IoTHubError as iothub_error:
        print ( "Unexpected error {0}".format(iothub_error) )
        return
    except KeyboardInterrupt:
        print ( "IoTHubRegistryManager sample stopped" )


def usage():
    print ( "Usage: iothub_configuration_sample.py --connectionstring <connection_string> --configurationid <configuration_id>" )
    print ( "    connectionstring: <HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>>" )
    print ( "    configuration_id: <New configuration ID for CRUD operations>" )

if __name__ == '__main__':
    print ( "" )
    print ( "Python {0}".format(sys.version) )
    print ( "IoT Hub Service Client for Python" )
    print ( "" )

    try:
        (CONNECTION_STRING, CONFIGURATION_ID) = get_iothub_opt_configuration_id(sys.argv[1:], CONNECTION_STRING, CONFIGURATION_ID)
    except OptionError as option_error:
        print ( option_error )
        usage()
        sys.exit(1)

    print(CONNECTION_STRING)
    print(CONFIGURATION_ID)
    print("here")
    #run_deviceconfig()

