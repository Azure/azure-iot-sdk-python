# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import random
import time
import sys
import iothub_client
from iothub_client import IoTHubClient, IoTHubClientError, IoTHubTransportProvider, IoTHubClientResult
from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError
from iothub_client_args import get_iothub_opt, OptionError

# HTTP options
# Because it can poll "after 9 seconds" polls will happen effectively
# at ~10 seconds.
# Note that for scalabilty, the default value of minimumPollingTime
# is 25 minutes. For more information, see:
# https://azure.microsoft.com/documentation/articles/iot-hub-devguide/#messaging
TIMEOUT = 241000
MINIMUM_POLLING_TIME = 9

# messageTimeout - the maximum time in milliseconds until a message times out.
# The timeout period starts at IoTHubClient.send_event_async.
# By default, messages do not expire.
MESSAGE_TIMEOUT = 10000

RECEIVE_CONTEXT = 0
AVG_WIND_SPEED = 10.0
MESSAGE_COUNT = 5
RECEIVED_COUNT = 0

# global counters
RECEIVE_CALLBACKS = 0
SEND_CALLBACKS = 0

PROTOCOL = IoTHubTransportProvider.HTTP

# String containing Hostname, Device Id in the format:
# "HostName=<host_name>;DeviceId=<device_id>;x509=true"
CONNECTION_STRING = "[Device Connection String]"

MSG_TXT = "{\"deviceId\": \"myPythonDevice\",\"windSpeed\": %.2f}"

X509_CERTIFICATE = (
    "-----BEGIN CERTIFICATE-----"
    "MIICpDCCAYwCCQCfIjBnPxs5TzANBgkqhkiG9w0BAQsFADAUMRIwEAYDVQQDDAls"
    "b2NhbGhvc3QwHhcNMTYwNjIyMjM0MzI3WhcNMTYwNjIzMjM0MzI3WjAUMRIwEAYD"
    "..."
    "+s88wBF907s1dcY45vsG0ldE3f7Y6anGF60nUwYao/fN/eb5FT5EHANVMmnK8zZ2"
    "tjWUt5TFnAveFoQWIoIbtzlTbOxUFwMrQFzFXOrZoDJmHNWc2u6FmVAkowoOSHiE"
    "dkyVdoGPCXc="
    "-----END CERTIFICATE-----"
)

X509_PRIVATEKEY = (
    "-----BEGIN RSA PRIVATE KEY-----"
    "MIIEpQIBAAKCAQEA0zKK+Uu5I0nXq2V6+2gbdCsBXZ6j1uAgU/clsCohEAek1T8v"
    "qj2tR9Mz9iy9RtXPMHwzcQ7aXDaz7RbHdw7tYXqSw8iq0Mxq2s3p4mo6gd5vEOiN"
    "..."
    "EyePNmkCgYEAng+12qvs0de7OhkTjX9FLxluLWxfN2vbtQCWXslLCG+Es/ZzGlNF"
    "SaqVID4EAUgUqFDw0UO6SKLT+HyFjOr5qdHkfAmRzwE/0RBN69g2qLDN3Km1Px/k"
    "xyJyxc700uV1eKiCdRLRuCbUeecOSZreh8YRIQQXoG8uotO5IttdVRc="
    "-----END RSA PRIVATE KEY-----"
)

# some embedded platforms need certificate information


def receive_message_callback(message, counter):
    global RECEIVE_CALLBACKS
    message_buffer = message.get_bytearray()
    size = len(message_buffer)
    print "Received Message [%d]:" % counter
    print "    Data: <<<%s>>> & Size=%d" % (message_buffer[:size].decode('utf-8'), size)
    map_properties = message.properties()
    key_value_pair = map_properties.get_internals()
    print "    Properties: %s" % key_value_pair
    counter += 1
    RECEIVE_CALLBACKS += 1
    print "    Total calls received: %d" % RECEIVE_CALLBACKS
    return IoTHubMessageDispositionResult.ACCEPTED


def send_confirmation_callback(message, result, user_context):
    global SEND_CALLBACKS
    print "Confirmation[%d] received for message with result = %s" % (user_context, result)
    map_properties = message.properties()
    print "    message_id: %s" % message.message_id
    print "    correlation_id: %s" % message.correlation_id
    key_value_pair = map_properties.get_internals()
    print "    Properties: %s" % key_value_pair
    SEND_CALLBACKS += 1
    print "    Total calls confirmed: %d" % SEND_CALLBACKS


def iothub_client_init():
    # prepare iothub client
    client = IoTHubClient(CONNECTION_STRING, PROTOCOL)

    # HTTP specific settings
    if client.protocol == IoTHubTransportProvider.HTTP:
        client.set_option("timeout", TIMEOUT)
        client.set_option("MinimumPollingTime", MINIMUM_POLLING_TIME)

    # set the time until a message times out
    client.set_option("messageTimeout", MESSAGE_TIMEOUT)

    # this brings in x509 privateKey and certificate
    client.set_option("x509certificate", X509_CERTIFICATE)
    client.set_option("x509privatekey", X509_PRIVATEKEY)

    # to enable MQTT logging set to 1
    if client.protocol == IoTHubTransportProvider.MQTT:
        client.set_option("logtrace", 0)

    client.set_message_callback(
        receive_message_callback, RECEIVE_CONTEXT)
    return client


def print_last_message_time(client):
    try:
        last_message = client.get_last_message_receive_time()
        print "Last Message: %s" % time.asctime(time.localtime(last_message))
        print "Actual time : %s" % time.asctime()
    except IoTHubClientError as iothub_client_error:
        if iothub_client_error.args[0].result == IoTHubClientResult.INDEFINITE_TIME:
            print "No message received"
        else:
            print iothub_client_error


def iothub_client_sample_x509_run():

    try:

        client = iothub_client_init()

        while True:
            # send a few messages every minute
            print "IoTHubClient sending %d messages" % MESSAGE_COUNT

            for message_counter in range(0, MESSAGE_COUNT):
                msg_txt_formatted = MSG_TXT % (
                    AVG_WIND_SPEED + (random.random() * 4 + 2))
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
                prop_text = "PropMsg_%d" % message_counter
                prop_map.add("Property", prop_text)

                client.send_event_async(message, send_confirmation_callback, message_counter)
                print "IoTHubClient.send_event_async accepted message [%d] for transmission to IoT Hub." % message_counter

            # Wait for Commands or exit
            print "IoTHubClient waiting for commands, press Ctrl-C to exit"

            status_counter = 0
            while status_counter <= MESSAGE_COUNT:
                status = client.get_send_status()
                print "Send status: %s" % status
                time.sleep(10)
                status_counter += 1

    except IoTHubError as iothub_error:
        print "Unexpected error %s from IoTHub" % iothub_error
        return
    except KeyboardInterrupt:
        print "IoTHubClient sample stopped"

    print_last_message_time(client)


def usage():
    print "Usage: iothub_client_sample.py -p <protocol> -c <connectionstring>"
    print "    protocol        : <amqp, http, mqtt>"
    print "    connectionstring: <HostName=<host_name>;DeviceId=<device_id>;SharedAccessKey=<device_key>>"


if __name__ == '__main__':
    print "\nPython %s" % sys.version
    print "IoT Hub for Python SDK Version: %s" % iothub_client.__version__

    try:
        (CONNECTION_STRING, PROTOCOL) = get_iothub_opt(sys.argv[1:], CONNECTION_STRING, PROTOCOL)
    except OptionError as option_error:
        print option_error
        usage()
        sys.exit(1)

    print "Starting the IoT Hub Python sample..."
    print "    Protocol %s" % PROTOCOL
    print "    Connection string=%s" % CONNECTION_STRING

    iothub_client_sample_x509_run()
