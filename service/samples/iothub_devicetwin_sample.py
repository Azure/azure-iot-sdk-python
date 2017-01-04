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

updateJson = "{\"properties\":{\"desired\":{\"telemetryInterval\":120}}}";

def iothub_devicetwin_sample_run():

    try:
        iothubTwinMethod = IoTHubDeviceTwin(connection_string)
        twinInfo = iothubTwinMethod.get_twin(device_id);
        print("")
        print("Device Twin before update    :");
        print("{0}".format(twinInfo));

        twinInfo = iothubTwinMethod.update_twin(device_id, updateJson);
        print("")
        print("Device Twin after update     :");
        print("{0}".format(twinInfo));

    except IoTHubError as e:
        print("")
        print("Unexpected error {0}" % e)
        return
    except KeyboardInterrupt:
        print("")
        print("IoTHubDeviceTwin sample stopped")

def usage():
    print("Usage: iothub_devicetwin_sample.py -c <connectionstring>")
    print("    connectionstring: <HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>>")
    print("    deviceid        : <Existing device ID to get and update the TWIN>")

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

    print("Starting the IoT Hub Service Client DeviceTwin Python sample...")
    print("    Connection string = {0}".format(connection_string))
    print("    Device ID         = {0}".format(device_id))

    iothub_devicetwin_sample_run()
