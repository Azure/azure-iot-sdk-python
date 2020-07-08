# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.hub import IoTHubDigitalTwinManager


iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")
model_id = os.getenv("IOTHUB_MODEL_ID")

try:
    # Create IoTHubDigitalTwinManager
    iothub_digital_twin_manager = IoTHubDigitalTwinManager(iothub_connection_str)

    # Get model
    model = iothub_digital_twin_manager.get_model(model_id)
    if model:
        print(model)
    else:
        print("No model found")

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("Sample stopped")
