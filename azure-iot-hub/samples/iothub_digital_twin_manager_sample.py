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
    iothub_digital_twin_manager.update_digital_twin(device_id, patch)

    # Get components
    components = iothub_digital_twin_manager.get_components(device_id)
    if digital_twin:
        print(components)
    else:
        print("No component found")

    # Get component
    component_name = "sensor"  # for the environmental sensor, try "environmentalSensor"
    component = iothub_digital_twin_manager.get_component(device_id, component_name)
    if digital_twin:
        print(component)
    else:
        print("Component did not found")

    # Invoke component command
    component_name = "sensor"  # for the environmental sensor, try "environmentalSensor"
    command_name = (
        "blink"
    )  # for the environmental sensor, you can try "blink", "turnOff" or "turnOn"
    payload = "hello"  # for the environmental sensor, it really doesn't matter. any string will do.
    invoke_component_command_result = iothub_digital_twin_manager.invoke_component_command(
        device_id, component_name, command_name, payload
    )
    if invoke_component_command_result:
        print(invoke_component_command_result)
    else:
        print("No digital_twin found")

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iothub_digital_twin_manager_sample stopped")
