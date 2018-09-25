#!/usr/bin/env python

# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import sys
import time

from iothub_client import IoTHubClient, IoTHubTransportProvider, IoTHubMessage, IoTHubClientError

# 1) Obtain the connection string for your downstream device and to it
#    append this string GatewayHostName=<edge device hostname>;
# 2) The edge device hostname is the hostname set in the config.yaml of the Edge device
#    to which this sample will connect to.
#
# The resulting string should look like the following
# "HostName=<iothub_host_name>;DeviceId=<device_id>;SharedAccessKey=<device_key>;GatewayHostName=<edge device hostname>"
CONNECTION_STRING = "[Downstream device IoT Edge connection string]"

# Path to the Edge trusted root CA certificate
TRUSTED_ROOT_CA_CERTIFICATE_PATH = "[Path to Edge CA certificate]"

# Supported IoTHubTransportProvider protocols are: MQTT, MQTT_WS, AMQP, AMQP_WS and HTTP
PROTOCOL = IoTHubTransportProvider.MQTT

# Provide the Azure IoT device client the trusted certificate contents
# via set_option with the X509
# Edge root CA certificate that was used to setup the Edge runtime
def set_certificates(client):
    if len(TRUSTED_ROOT_CA_CERTIFICATE_PATH) > 0:
        cert_data = ''
        with open(TRUSTED_ROOT_CA_CERTIFICATE_PATH, 'rb') as cert_file:
            cert_data = cert_file.read()
        try:
            client.set_option("TrustedCerts", cert_data)
            print ( "set_option TrustedCerts successful" )
        except IoTHubClientError as iothub_client_error:
            print ( "set_option TrustedCerts failed (%s)" % iothub_client_error )
            sys.exit(1)

def send_confirmation_callback(message, result, user_context):
    print("Confirmation received for message with result = %s" % (result))

if __name__ == '__main__':
    client = IoTHubClient(CONNECTION_STRING, PROTOCOL)
    set_certificates(client)
    message = IoTHubMessage("test message")

    # send a message every two seconds
    while True:
        client.send_event_async(message, send_confirmation_callback, None)
        print("Message transmitted to IoT Edge")
        time.sleep(2)
