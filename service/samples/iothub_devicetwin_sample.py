# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import sys
import iothub_service_client
from iothub_service_client import IoTHubDeviceTwin, IoTHubError
from iothub_service_client_args import get_iothub_opt, OptionError

# String containing Hostname, SharedAccessKeyName & SharedAccessKey in the format:
# "HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>"
CONNECTION_STRING = "[IoTHub Connection String]"
DEVICE_ID = "[Device Id]"

UPDATE_JSON = "{\"properties\":{\"desired\":{\"telemetryInterval\":120}}}"


def iothub_devicetwin_sample_run():

    try:
        iothub_twin_method = IoTHubDeviceTwin(CONNECTION_STRING)
        twin_info = iothub_twin_method.get_twin(DEVICE_ID)
        print ( "" )
        print ( "Device Twin before update    :" )
        print ( "{0}".format(twin_info) )

        twin_info = iothub_twin_method.update_twin(DEVICE_ID, UPDATE_JSON)
        print ( "" )
        print ( "Device Twin after update     :" )
        print ( "{0}".format(twin_info) )

    except IoTHubError as iothub_error:
        print ( "" )
        print ( "Unexpected error {0}" % iothub_error )
        return
    except KeyboardInterrupt:
        print ( "" )
        print ( "IoTHubDeviceTwin sample stopped" )


def usage():
    print ( "Usage: iothub_devicetwin_sample.py -c <connectionstring> -d <device_id>" )
    print ( "    connectionstring: <HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>>" )
    print ( "    deviceid        : <Existing device ID to get and update the TWIN>" )


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

    print ( "Starting the IoT Hub Service Client DeviceTwin Python sample..." )
    print ( "    Connection string = {0}".format(CONNECTION_STRING) )
    print ( "    Device ID         = {0}".format(DEVICE_ID) )

    iothub_devicetwin_sample_run()
