# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
import msrest
from azure.iot.hub import IoTHubDigitalTwinManager


iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")
device_id = os.getenv("IOTHUB_DEVICE_ID")
command_name = os.getenv("IOTHUB_COMMAND_NAME")  # for the thermostat you can try getMaxMinReport
payload = os.getenv("IOTHUB_COMMAND_PAYLOAD")  # it really doesn't matter, any string will do.

try:
    # Create IoTHubDigitalTwinManager
    iothub_digital_twin_manager = IoTHubDigitalTwinManager(iothub_connection_str)

    # Invoke command
    invoke_command_result = iothub_digital_twin_manager.invoke_command(
        device_id, command_name, payload
    )
    if invoke_command_result:
        print(invoke_command_result)
    else:
        print("No invoke_command_result found")

except msrest.exceptions.HttpOperationError as ex:
    print("HttpOperationError error {0}".format(ex.response.text))
except Exception as exc:
    print("Unexpected error {0}".format(exc))
except KeyboardInterrupt:
    print("Sample stopped")
