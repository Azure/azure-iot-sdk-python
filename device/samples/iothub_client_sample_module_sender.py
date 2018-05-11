#!/usr/bin/env python

# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import random
import time
import sys
import iothub_client
from iothub_client import IoTHubModuleClient, IoTHubClientError, IoTHubTransportProvider
from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError, DeviceMethodReturnValue
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
# The timeout period starts at IoTHubModuleClient.send_event_to_output.
# By default, messages do not expire.
MESSAGE_TIMEOUT = 10000

RECEIVE_CONTEXT = 0
AVG_WIND_SPEED = 10.0
MIN_TEMPERATURE = 20.0
MIN_HUMIDITY = 60.0
MESSAGE_COUNT = 5
RECEIVED_COUNT = 0
TWIN_CONTEXT = 0
METHOD_CONTEXT = 0

# global counters
SEND_CALLBACKS = 0

# Choose HTTP, AMQP or MQTT as transport protocol.  Currently only MQTT is supported.
PROTOCOL = IoTHubTransportProvider.MQTT

# String containing Hostname, Device Id & Device Key in the format:
# "HostName=<host_name>;DeviceId=<device_id>;SharedAccessKey=<device_key>;ModuleId=<module_id>;GatewayHostName=<gateway>"
CONNECTION_STRING = "[Device Connection String]"

MSG_TXT = "{\"deviceId\": \"myPythonDevice\",\"windSpeed\": %.2f,\"temperature\": %.2f,\"humidity\": %.2f}"


def send_confirmation_callback(message, result, user_context):
    global SEND_CALLBACKS
    print ( "Confirmation[%d] received for message with result = %s" % (user_context, result) )
    map_properties = message.properties()
    key_value_pair = map_properties.get_internals()
    print ( "    Properties: %s" % key_value_pair )
    SEND_CALLBACKS += 1
    print ( "    Total calls confirmed: %d" % SEND_CALLBACKS )


class HubManager(object):

    def __init__(
            self,
            connection_string,
            protocol=IoTHubTransportProvider.MQTT):
        self.client_protocol = protocol
        self.client = IoTHubModuleClient(connection_string, protocol)
        if protocol == IoTHubTransportProvider.HTTP:
            self.client.set_option("timeout", TIMEOUT)
            self.client.set_option("MinimumPollingTime", MINIMUM_POLLING_TIME)
        # set the time until a message times out
        self.client.set_option("messageTimeout", MESSAGE_TIMEOUT)
        # some embedded platforms need certificate information
        # self.set_certificates()

    def set_certificates(self):
        from iothub_client_cert import CERTIFICATES
        try:
            self.client.set_option("TrustedCerts", CERTIFICATES)
            print ( "set_option TrustedCerts successful" )
        except IoTHubClientError as iothub_client_error:
            print ( "set_option TrustedCerts failed (%s)" % iothub_client_error )

    # Sends a message to the queue with outputQueueName, "temperatureOutput" in the case of the sample.
    def send_event_to_output(self, outputQueueName, event, properties, send_context):
        if not isinstance(event, IoTHubMessage):
            event = IoTHubMessage(bytearray(event, 'utf8'))

        if len(properties) > 0:
            prop_map = event.properties()
            for key in properties:
                prop_map.add_or_update(key, properties[key])

        self.client.send_event_async(
            outputQueueName, event, send_confirmation_callback, send_context)


def main(connection_string, protocol):
    try:
        print ( "\nPython %s\n" % sys.version )
        print ( "IoT Hub Client for Python" )

        hub_manager = HubManager(connection_string, protocol)

        print ( "Starting the IoT Hub Python sample using protocol %s..." % hub_manager.client_protocol )

        content = "Hello World from Python Blob APi"

        while True:
            # send a few messages every minute
            print ( "IoTHubModuleClient sending %d messages" % MESSAGE_COUNT )

            for message_counter in range(0, MESSAGE_COUNT):
                temperature = MIN_TEMPERATURE + (random.random() * 10)
                humidity = MIN_HUMIDITY + (random.random() * 20)
                msg_txt_formatted = MSG_TXT % (
                    AVG_WIND_SPEED + (random.random() * 4 + 2),
                    temperature,
                    humidity)

                msg_properties = {
                    "temperatureAlert": 'true' if temperature > 28 else 'false'
                }
                hub_manager.send_event_to_output("temperatureOutput", msg_txt_formatted, msg_properties, message_counter)
                print ( "IoTHubModuleClient.send_event_to_output accepted message [%d] for transmission to IoT Hub." % message_counter )

            # Wait for Commands or exit
            print ( "IoTHubModuleClient waiting for commands, press Ctrl-C to exit." )

            status_counter = 0
            while status_counter < 6:
                status = hub_manager.client.get_send_status()
                print ( "Send status: %s" % status )
                time.sleep(10)
                status_counter += 1

    except IoTHubError as iothub_error:
        print ( "Unexpected error %s from IoTHub" % iothub_error )
        return
    except KeyboardInterrupt:
        print ( "IoTHubModuleClient sample stopped" )


def usage():
    print ( "Usage: iothub_client_sample_module_sender.py -p <protocol> -c <connectionstring>" )
    print ( "    protocol        : <amqp, http, mqtt>" )
    print ( "    connectionstring: <HostName=<host_name>;DeviceId=<device_id>;SharedAccessKey=<device_key>;ModuleId=<module_id>;GatewayHostName=<gateway>" )

if __name__ == '__main__':
    try:
        (CONNECTION_STRING, PROTOCOL) = get_iothub_opt(sys.argv[1:], CONNECTION_STRING)
    except OptionError as option_error:
        print ( option_error )
        usage()
        sys.exit(1)

    if PROTOCOL != IoTHubTransportProvider.MQTT:
        protocol("Only the MQTT protocol is currently supported")
        sys.exit(1)

    main(CONNECTION_STRING, PROTOCOL)
