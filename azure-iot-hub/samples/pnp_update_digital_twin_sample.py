# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.hub import IoTHubDigitalTwinManager


iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")
device_id = os.getenv("IOTHUB_DEVICE_ID")

try:
    # Create IoTHubDigitalTwinManager
    iothub_digital_twin_manager = IoTHubDigitalTwinManager(iothub_connection_str)

    # Get digital twin
    digital_twin = iothub_digital_twin_manager.get_digital_twin(device_id)
    if digital_twin:
        print(digital_twin)
    else:
        print("No digital_twin found")

    # Update digital twin desired properties
    # jsonpatch example:
    # patch = [
    #     {'op': 'add', 'path': '/newThermostat', 'value': {'tempSetpoint': 100, '$metadata': {}}},
    #     {'op': 'remove', 'path': '/baz/1'},
    #     {'op': 'replace', 'path': '/baz/0', 'value': 42},
    # ])
    patch = [
        {"op": "add", "path": "/newThermostat1", "value": {"tempSetpoint": 100, "$metadata": {}}}
    ]
    response = iothub_digital_twin_manager.update_digital_twin(device_id, patch)
    if response:
        print(response)
    else:
        print("No response found")

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("Sample stopped")
