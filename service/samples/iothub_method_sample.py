# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import sys
import iothub_service_client
from iothub_service_client import IoTHubDeviceMethod, IoTHubError
from iothub_service_client_args import get_iothub_opt_with_module, OptionError

# String containing Hostname, SharedAccessKeyName & SharedAccessKey in the format:
# "HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>"
CONNECTION_STRING = "[IoTHub Connection String]"
DEVICE_ID = None
MODULE_ID = None

METHOD_NAME = "MethodName"
METHOD_PAYLOAD = "{\"method_number\":\"42\"}"
TIMEOUT = 60


def iothub_method_sample_run():
    try:
        iothub_device_method = IoTHubDeviceMethod(CONNECTION_STRING)

        if (MODULE_ID is None):
            response = iothub_device_method.invoke(DEVICE_ID, METHOD_NAME, METHOD_PAYLOAD, TIMEOUT)
        else:
            response = iothub_device_method.invoke(DEVICE_ID, MODULE_ID, METHOD_NAME, METHOD_PAYLOAD, TIMEOUT)

        print ( "" )
        print ( "Method called" )
        print ( "Method name       : {0}".format(METHOD_NAME) )
        print ( "Method payload    : {0}".format(METHOD_PAYLOAD) )
        print ( "" )
        print ( "Response status          : {0}".format(response.status) )
        print ( "Response payload         : {0}".format(response.payload) )

        try:
            # Try Python 2.xx first
            raw_input("Method successfully called.  Press Enter to continue...\n")
        except:
            pass
            # Use Python 3.xx in the case of exception
            input("Method successfully called.  Press Enter to continue...\n")

    except IoTHubError as iothub_error:
        print ( "" )
        print ( "Unexpected error {0}".format(iothub_error) )
        return
    except KeyboardInterrupt:
        print ( "" )
        print ( "IoTHubDeviceMethod sample stopped" )


def usage():
    print ( "Usage: iothub_devicemethod_sample.py -c <connectionstring> -d <device_id> [-m <module_id>]" )
    print ( "    connectionstring: <HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>>" )
    print ( "    deviceid        : <Existing device ID to call a method on>" )
    print ( "    moduleid        : <OPTIONAL> <Existing module ID to call a method on" )
    print ("                     : If moduleid is not set, sample will use device instead of module.")


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

    print ( "Starting the IoT Hub Service Client DeviceMethod Python sample..." )
    print ( "    Connection string = {0}".format(CONNECTION_STRING) )
    print ( "    Device ID         = {0}".format(DEVICE_ID) )
    if (MODULE_ID is not None):
        print ( "    Module ID         = {0}".format(MODULE_ID) )

    iothub_method_sample_run()
