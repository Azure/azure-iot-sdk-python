# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import os
import logging
from azure.iot.hub.devicesdk.module_client import ModuleClient
from azure.iot.hub.devicesdk.auth.authentication_provider_factory import from_connection_string

logging.basicConfig(level=logging.INFO)

# This is just a simple module on the simple device. Connection string is of the format
# HostName=<SomeHostName>;DeviceId=<SomeDeviceId>;ModuleId=<SomeModuleIdOnSomeDevice>;SharedAccessKey=<SomeSharedAccessKey>
conn_str = os.getenv("IOTHUB_MODULE_CONNECTION_STRING")
logging.info(conn_str)
auth_provider = from_connection_string(conn_str)
simple_module = ModuleClient.from_authentication_provider(auth_provider, "mqtt")


def connection_state_callback(status):
    print("connection status: " + status)
    if status == "connected":
        simple_module.send_event("payload from module")


simple_module.on_connection_state = connection_state_callback
simple_module.connect()

while True:
    continue
