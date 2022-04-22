# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import msrest
from azure.iot.hub import DigitalTwinClient


iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")
device_id = os.getenv("IOTHUB_DEVICE_ID")
command_name = os.getenv("IOTHUB_COMMAND_NAME")  # for the thermostat you can try getMaxMinReport
payload = os.getenv("IOTHUB_COMMAND_PAYLOAD")  # it really doesn't matter, any string will do.
# Optional parameters
connect_timeout_in_seconds = 3
response_timeout_in_seconds = 7  # Must be within 5-300

try:
    # Create DigitalTwinClient
    digital_twin_client = DigitalTwinClient.from_connection_string(iothub_connection_str)

    # Invoke command
    invoke_command_result = digital_twin_client.invoke_command(
        device_id, command_name, payload, connect_timeout_in_seconds, response_timeout_in_seconds
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
    print("{} stopped".format(__file__))
finally:
    print("{} finished".format(__file__))
