#!/usr/bin/env python

# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import random
import time
import sys
import iothub_client
from iothub_client import IoTHubClient, IoTHubClientError, IoTHubTransportProvider, IoTHubClientResult
from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError, DeviceMethodReturnValue
from iothub_client import IoTHubTransport, IoTHubConfig, IoTHubClientRetryPolicy
from iothub_client_args import get_iothub_opt, OptionError

# messageTimeout - the maximum time in milliseconds until a message times out.
# The timeout period starts at IoTHubClient.send_event_async.
# By default, messages do not expire.
MESSAGE_TIMEOUT = 10000

RECEIVE_CONTEXT = 0
AVG_WIND_SPEED = 10.0
MIN_TEMPERATURE = 20.0
MIN_HUMIDITY = 60.0
MESSAGE_COUNT = 10
CONNECTION_STATUS_CONTEXT = 0

# global counters
RECEIVE_CALLBACKS = 0
SEND_CALLBACKS = 0
CONNECTION_STATUS_CALLBACKS = 0
SEND_REPORTED_STATE_CALLBACKS = 0

# for trasnport sharing chose AMQP or AMQP_WS as transport protocol
PROTOCOL = IoTHubTransportProvider.AMQP_WS

# String containing Hostname, Device Id & Device Key in the format:
# "HostName=<host_name>;DeviceId=<device_id>;SharedAccessKey=<device_key>"
#CONNECTION_STRING = "HostName=z-test.azure-devices.net;DeviceId=z-001;SharedAccessKey=+oqBkTMhuaG9yew2pIZoRCIde6GKq88wSEXer2MV/Ic="
IOTHUBNAME = "[IoTHub Name]";
IOTHUBSUFFIX = "[IoTHub Suffix]";
DEVICE_NAME1 = "[Device Name 1]";
DEVICE_NAME2 = "[Device Name 2]";
DEVICE_KEY1 = "[Device Key 1]";
DEVICE_KEY2 = "[Device Key 2]";

# some embedded platforms need certificate information


def set_certificates(client):
    from iothub_client_cert import CERTIFICATES
    try:
        client.set_option("TrustedCerts", CERTIFICATES)
        print ( "set_option TrustedCerts successful" )
    except IoTHubClientError as iothub_client_error:
        print ( "set_option TrustedCerts failed (%s)" % iothub_client_error )

def receive_message_callback1(message, counter):
    global RECEIVE_CALLBACKS
    message_buffer = message.get_bytearray()
    size = len(message_buffer)
    print ( "Received Message [%d]:" % counter )
    print ( "    Data: <<<%s>>> & Size=%d" % (message_buffer[:size].decode('utf-8'), size) )
    map_properties = message.properties()
    key_value_pair = map_properties.get_internals()
    print ( "    Properties: %s" % key_value_pair )
    counter += 1
    RECEIVE_CALLBACKS += 1
    print ( "    Total calls received: %d" % RECEIVE_CALLBACKS )
    return IoTHubMessageDispositionResult.ACCEPTED

def receive_message_callback2(message, counter):
    global RECEIVE_CALLBACKS
    message_buffer = message.get_bytearray()
    size = len(message_buffer)
    print ( "Received Message [%d]:" % counter )
    print ( "    Data: <<<%s>>> & Size=%d" % (message_buffer[:size].decode('utf-8'), size) )
    map_properties = message.properties()
    key_value_pair = map_properties.get_internals()
    print ( "    Properties: %s" % key_value_pair )
    counter += 1
    RECEIVE_CALLBACKS += 1
    print ( "    Total calls received: %d" % RECEIVE_CALLBACKS )
    return IoTHubMessageDispositionResult.ACCEPTED

def send_confirmation_callback1(message, result, user_context):
    global SEND_CALLBACKS
    print ( "Client1 - Confirmation[%d] received for message with result = %s" % (user_context, result) )
    map_properties = message.properties()
    print ( "    message_id: %s" % message.message_id )
    print ( "    correlation_id: %s" % message.correlation_id )
    key_value_pair = map_properties.get_internals()
    print ( "    Properties: %s" % key_value_pair )
    SEND_CALLBACKS += 1
    print ( "    Total calls confirmed: %d" % SEND_CALLBACKS )

def send_confirmation_callback2(message, result, user_context):
    global SEND_CALLBACKS
    print ( "Client2 - Confirmation[%d] received for message with result = %s" % (user_context, result) )
    map_properties = message.properties()
    print ( "    message_id: %s" % message.message_id )
    print ( "    correlation_id: %s" % message.correlation_id )
    key_value_pair = map_properties.get_internals()
    print ( "    Properties: %s" % key_value_pair )
    SEND_CALLBACKS += 1
    print ( "    Total calls confirmed: %d" % SEND_CALLBACKS )

def connection_status_callback(result, reason, user_context):
    global CONNECTION_STATUS_CALLBACKS
    print ( "Connection status changed[%d] with:" % (user_context) )
    print ( "    reason: %d" % reason )
    print ( "    result: %s" % result )
    CONNECTION_STATUS_CALLBACKS += 1
    print ( "    Total calls confirmed: %d" % CONNECTION_STATUS_CALLBACKS )


def iothub_client_init(transport, device_name, device_key):
    # prepare iothub client with transport
    config = IoTHubConfig(PROTOCOL, device_name, device_key, "", IOTHUBNAME, IOTHUBSUFFIX, "")
    client = IoTHubClient(transport, config)

    # set the time until a message times out
    client.set_option("messageTimeout", MESSAGE_TIMEOUT)

    client.set_connection_status_callback(connection_status_callback, CONNECTION_STATUS_CONTEXT)

    return client


def print_last_message_time(client):
    try:
        last_message = client.get_last_message_receive_time()
        print ( "Last Message: %s" % time.asctime(time.localtime(last_message)) )
        print ( "Actual time : %s" % time.asctime() )
    except IoTHubClientError as iothub_client_error:
        if iothub_client_error.args[0].result == IoTHubClientResult.INDEFINITE_TIME:
            print ( "No message received" )
        else:
            print ( iothub_client_error )


def iothub_client_shared_transport_sample_run():
    try:
        # create transport to share
        transport = IoTHubTransport(PROTOCOL, IOTHUBNAME, IOTHUBSUFFIX)

        client1 = iothub_client_init(transport, DEVICE_NAME1, DEVICE_KEY1)
        client1.set_message_callback(receive_message_callback1, RECEIVE_CONTEXT)

        client2 = iothub_client_init(transport, DEVICE_NAME2, DEVICE_KEY2)
        client2.set_message_callback(receive_message_callback2, RECEIVE_CONTEXT)

        print ( "IoTHubClient has been initialized" )

        while True:
            # send a few messages every minute
            print ( "IoTHubClient sending %d messages" % MESSAGE_COUNT )

            for message_counter in range(0, MESSAGE_COUNT):
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

                if (message_counter % 2) == 0:
                    client1.send_event_async(message, send_confirmation_callback1, message_counter)
                else:
                    client2.send_event_async(message, send_confirmation_callback2, message_counter)
                print ( "IoTHubClient.send_event_async accepted message [%d] for transmission to IoT Hub." % message_counter )

            # Wait for Commands or exit
            print ( "IoTHubClient waiting for commands, press Ctrl-C to exit" )

            status_counter = 0
            while status_counter < MESSAGE_COUNT:
                status1 = client1.get_send_status()
                print ( "Send status client1: %s" % status1 )
                status2 = client2.get_send_status()
                print ( "Send status client2: %s" % status2 )
                time.sleep(10)
                status_counter += 1

    except IoTHubError as iothub_error:
        print ( "Unexpected error %s from IoTHub" % iothub_error )
        return
    except KeyboardInterrupt:
        print ( "IoTHubClient sample stopped" )

    print_last_message_time(client1)
    print_last_message_time(client2)


if __name__ == '__main__':
    print ( "\nPython %s" % sys.version )
    print ( "IoT Hub Client for Python" )

    print ( "Starting the IoT Hub Shared Transport Python sample..." )

    iothub_client_shared_transport_sample_run()
