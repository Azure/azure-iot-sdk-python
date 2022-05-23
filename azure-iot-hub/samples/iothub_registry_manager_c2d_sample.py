# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import msrest
from azure.iot.hub import IoTHubRegistryManager

connection_str = os.getenv("IOTHUB_CONNECTION_STRING")
device_id = os.getenv("IOTHUB_DEVICE_ID")

try:
    # Create IoTHubRegistryManager
    registry_manager = IoTHubRegistryManager.from_connection_string(connection_str)
    print("Conn String: {0}".format(connection_str))

    # Send Message To Device
    send_message = "Sending c2d message 1"
    registry_manager.send_c2d_message(device_id, send_message)

    # Send 2nd Message To Device with property
    send_message = b"{ 'message': 'this is message 2' }"
    registry_manager.send_c2d_message(
        device_id, send_message, {"contentType": "application/json", "prop1": "value1"}
    )

    # Send 2nd Message To Device with property
    send_message = "Sending c2d message 3"
    registry_manager.send_c2d_message(
        device_id, send_message, properties={"prop1": "value1", "correlationId": "1234"}
    )

    # Set registry manager object to `None` so all open files get closed
    iothub_registry_manager = None

except msrest.exceptions.HttpOperationError as ex:
    print("HttpOperationError error {0}".format(ex.response.text))
except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("{} stopped".format(__file__))
finally:
    print("{} finished".format(__file__))
