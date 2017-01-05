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

methodName = "MethodName"
methodPayload = "MethodPayload"
timeout = 60

def iothub_devicemethod_sample_run():

    try:
        iothubDeviceMethod = IoTHubDeviceMethod(connection_string)

        response = iothubDeviceMethod.invoke(device_id, methodName, methodPayload, timeout)

        print("");
        print("Device Method called");
        print("Device Method name       : {0}".format(methodName));
        print("Device Method payload    : {0}".format(methodPayload));
        print("");
        print("Response status          : {0}".format(response.status));
        print("Response payload         : {0}".format(response.payload));

        raw_input("Press Enter to continue...\n")

    except IoTHubError as e:
        print("")
        print("Unexpected error {0}".format(e))
        return
    except KeyboardInterrupt:
        print("")
        print("IoTHubDeviceMethod sample stopped")

def usage():
    print("Usage: iothub_devicemethod_sample.py -c <connectionstring>")
    print("    connectionstring: <HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>>")
    print("    deviceid        : <Existing device ID to call a method on>")

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

    print("Starting the IoT Hub Service Client DeviceMethod Python sample...")
    print("    Connection string = {0}".format(connection_string))
    print("    Device ID         = {0}".format(device_id))

    iothub_devicemethod_sample_run()
