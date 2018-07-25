#!/usr/bin/env python

# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import random
import time
import sys
import os
import iothub_client
from iothub_client import IoTHubModuleClient, IoTHubClientError, IoTHubTransportProvider
from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError, DeviceMethodReturnValue

RECEIVE_CONTEXT = 0

PROTOCOL = IoTHubTransportProvider.MQTT

def invoke_method_callback(response, user_context):
    print ("invoke_method_callback called:")
    print ("  result = %d" % response.result)
    print ("  responseStatus = %d" % response.responseStatus)
    print ("  responsePayload = %d" % response.responsePayload)

TARGET_MODULE="testFilter"
TARGET_METHOD_NAME="getCarVin"
TARGET_METHOD_PAYLOAD="{sample-Json}"
TIMEOUT=60

class HubManager(object):
    def __init__(
            self,
            protocol):
        self.client_protocol = protocol
        self.client = IoTHubModuleClient()
        self.client.create_from_environment(protocol)
        # set to increase logging level
        # self.client.set_option("logtrace", 1)


    # Invokes a method on a module running on same device.
    def invoke_module(self):
        # Edge indicates its deviceId by setting the environment variable IOTEDGE_DEVICEID in its container.
        deviceId = os.environ['IOTEDGE_DEVICEID']
        self.client.invoke_method_async(
            deviceId, TARGET_MODULE, TARGET_METHOD_NAME, TARGET_METHOD_PAYLOAD, TIMEOUT, invoke_method_callback, RECEIVE_CONTEXT)

def main(protocol):
    try:
        print ( "\nPython %s\n" % sys.version )
        print ( "IoT Hub Client for Python" )

        hub_manager = HubManager(protocol)

        print ( "Starting the IoT Hub Python sample for module invocation..."  )
        print ( "NOTE: This sample will only run when running from inside an Edge container")

        hub_manager.invoke_module()

    except IoTHubError as iothub_error:
        print ( "Unexpected error %s from IoTHub" % iothub_error )
        return
    except KeyboardInterrupt:
        print ( "IoTHubModuleClient sample stopped" )

if __name__ == '__main__':
    main(PROTOCOL)

