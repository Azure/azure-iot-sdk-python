#!/usr/bin/env python

# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import random
import time
import sys
import iothub_client
from iothub_client import IoTHubClient, IoTHubClientError, IoTHubTransportProvider, IoTHubClientResult, IoTHubSecurityType
from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError, DeviceMethodReturnValue
from iothub_client import IoTHubClientRetryPolicy, GetRetryPolicyReturnValue
from iothub_client_prov_args import get_iothub_prov_opt, OptionError

# IoTHub uri where the device will be created
IOTHUB_URI = "[IoTHub Uri]"

# The device ID which will be created
DEVICE_ID = "[Device ID]"

# The security type used to authenticate the device
SECURITY_TYPE = IoTHubSecurityType.SAS

# chose HTTP, AMQP, AMQP_WS or MQTT as transport protocol
PROTOCOL = IoTHubTransportProvider.HTTP

MESSAGE_COUNT = 5
SEND_CALLBACKS = 0
MSG_TXT = "{\"deviceId\": \"myPythonDevice\",\"windSpeed\": %.2f,\"temperature\": %.2f,\"humidity\": %.2f}"


def send_confirmation_callback(message, result, user_context):
    global SEND_CALLBACKS
    print ( "Confirmation[%d] received for message with result = %s" % (user_context, result) )
    map_properties = message.properties()
    print ( "    message_id: %s" % message.message_id )
    print ( "    correlation_id: %s" % message.correlation_id )
    key_value_pair = map_properties.get_internals()
    print ( "    Properties: %s" % key_value_pair )
    SEND_CALLBACKS += 1
    print ( "    Total calls confirmed: %d" % SEND_CALLBACKS )


def create_message(message_counter):
    AVG_WIND_SPEED = 10.0
    MIN_TEMPERATURE = 20.0
    MIN_HUMIDITY = 60.0

    temperature = MIN_TEMPERATURE + (random.random() * 10)
    humidity = MIN_HUMIDITY + (random.random() * 20)
    msg_txt_formatted = MSG_TXT % (
        AVG_WIND_SPEED + (random.random() * 4 + 2),
        temperature,
        humidity)

    # messages can be encoded as string or bytearray
    if (message_counter & 1) == 1:
        message = IoTHubMessage(bytearray(msg_txt_formatted, 'utf8'))
    else:
        message = IoTHubMessage(msg_txt_formatted)

    # optional: assign ids
    message.message_id = "message_%d" % message_counter
    message.correlation_id = "correlation_%d" % message_counter
    # optional: assign properties
    prop_map = message.properties()
    prop_map.add("temperatureAlert", 'true' if temperature > 28 else 'false')

    return message


def usage():
    print ( "Usage: iothub_client_prov_hsm_sample.py -u <iothub_uri> -d <device_id> -s <security_type> -p <protocol>" )
    print ( "    iothub_uri: <IoTHub Uri>" )
    print ( "    device_id: <Device ID>" )
    print ( "    security_type: <Security Type>" )
    print ( "    protocol        : <amqp, amqp_ws, http, mqtt, mqtt_ws>" )


def iothub_client_prov_hsm_sample_run():
    client = IoTHubClient(IOTHUB_URI, DEVICE_ID, SECURITY_TYPE, PROTOCOL)

    print ( "IoTHubClient sending %d messages" % MESSAGE_COUNT )

    for message_counter in range(0, MESSAGE_COUNT):
        message = create_message(message_counter)

        client.send_event_async(message, send_confirmation_callback, message_counter)
        print ( "IoTHubClient.send_event_async accepted message [%d] for transmission to IoT Hub." % message_counter )

    # Wait for Commands or exit
    print ( "IoTHubClient waiting for commands, press Ctrl-C to exit" )

    status_counter = 0
    while status_counter <= MESSAGE_COUNT:
        status = client.get_send_status()
        print ( "Send status: %s" % status )
        time.sleep(10)
        status_counter += 1


if __name__ == '__main__':
    print ( "\nPython %s" % sys.version )
    print ( "IoT Hub Client for Python" )

    try:
        (IOTHUB_URI, DEVICE_ID, SECURITY_TYPE, PROTOCOL) = get_iothub_prov_opt(sys.argv[1:], IOTHUB_URI, DEVICE_ID, SECURITY_TYPE, PROTOCOL)
    except OptionError as option_error:
        print ( option_error )
        usage()
        sys.exit(1)

    print ( "Starting the IoT Hub Python sample..." )
    print ( "    IoTHub Uri=%s" % IOTHUB_URI )
    print ( "    Device ID=%s" % DEVICE_ID )
    print ( "    Security Type=%s" % SECURITY_TYPE )
    print ( "    Protocol %s" % PROTOCOL )

    iothub_client_prov_hsm_sample_run()
