# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
from azure.iot.device import IoTHubDeviceClient, MethodResponse

# The connection string for a device should never be stored in code. For the sake of simplicity we're using an environment variable here.
conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
# The client object is used to interact with your Azure IoT hub.
device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)


# connect the client.
device_client.connect()


# Define behavior for handling methods
def method_request_handler(method_request):
    # Determine how to respond to the method request based on the method name
    if method_request.name == "method1":
        payload = {"result": True, "data": "some data"}  # set response payload
        status = 200  # set return status code
        print("executed method1")
    elif method_request.name == "method2":
        payload = {"result": True, "data": 1234}  # set response payload
        status = 200  # set return status code
        print("executed method2")
    else:
        payload = {"result": False, "data": "unknown method"}  # set response payload
        status = 400  # set return status code
        print("executed unknown method: " + method_request.name)

    # Send the response
    method_response = MethodResponse.create_from_method_request(method_request, status, payload)
    device_client.send_method_response(method_response)


# Set the method request handler on the client
device_client.on_method_request_received = method_request_handler


# Wait for user to indicate they are done listening for messages
while True:
    selection = input("Press Q to quit\n")
    if selection == "Q" or selection == "q":
        print("Quitting...")
        break


# finally, shut down the client
device_client.shutdown()
