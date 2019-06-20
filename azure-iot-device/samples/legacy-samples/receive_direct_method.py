# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import logging
import threading
from six.moves import input
from azure.iot.device import IoTHubDeviceClient, MethodResponse
from azure.iot.device import auth

logging.basicConfig(level=logging.ERROR)


# The connection string for a device should never be stored in code. For the sake of simplicity we're using an environment variable here.
conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
# The client object is used to interact with your Azure IoT hub.
device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)


# connect the client.
device_client.connect()


# define behavior for handling methods
def method1_listener(device_client):
    while True:
        method_request = device_client.receive_method_request("method1")  # Wait for method1 calls
        payload = {"result": True, "data": "some data"}  # set response payload
        status = 200  # set return status code
        print("executed method1")
        method_response = MethodResponse.create_from_method_request(method_request, status, payload)
        device_client.send_method_response(method_response)  # send response


def method2_listener(device_client):
    while True:
        method_request = device_client.receive_method_request("method2")  # Wait for method2 calls
        payload = {"result": True, "data": 1234}  # set response payload
        status = 200  # set return status code
        print("executed method2")
        method_response = MethodResponse.create_from_method_request(method_request, status, payload)
        device_client.send_method_response(method_response)  # send response


def generic_method_listener(device_client):
    while True:
        method_request = device_client.receive_method_request()  # Wait for unknown method calls
        payload = {"result": False, "data": "unknown method"}  # set response payload
        status = 400  # set return status code
        print("executed unknown method: " + method_request.name)
        method_response = MethodResponse.create_from_method_request(method_request, status, payload)
        device_client.send_method_response(method_response)  # send response


# Run method listener threads in the background
method1_thread = threading.Thread(target=method1_listener, args=(device_client,))
method1_thread.daemon = True
method1_thread.start()


method2_thread = threading.Thread(target=method2_listener, args=(device_client,))
method2_thread.daemon = True
method2_thread.start()


generic_method_thread = threading.Thread(target=generic_method_listener, args=(device_client,))
generic_method_thread.daemon = True
generic_method_thread.start()


# Wait for user to indicate they are done listening for messages
while True:
    selection = input("Press Q to quit\n")
    if selection == "Q" or selection == "q":
        print("Quitting...")
        break


# finally, disconnect
device_client.disconnect()
