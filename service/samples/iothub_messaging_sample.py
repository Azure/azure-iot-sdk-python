# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import random
import time
import sys
import iothub_service_client
from iothub_service_client import *
from iothub_service_client_args import *

open_context = 0
feedback_context = 1

message_count = 10

# String containing Hostname, SharedAccessKeyName & SharedAccessKey in the format:
# "HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>"
connection_string = "[IoTHub Connection String]";
device_id = "[Device Id]";

avg_wind_speed = 10.0
msg_txt0 = "{\"service client sent a message\"}"
msg_txt = "{\"service client sent a message\": %.2f}"

def open_complete_callback(
        context
        ):
    print('open_complete_callback called with context: {0}'.format(context));

def send_complete_callback(
        context,
        messagingResult
        ):
    context = 0
    print('send_complete_callback called with context : {0}'.format(context));
    print('messagingResult : {0}'.format(messagingResult));

def feedback_received_callback(
        context,
        batchUserId,
        batchLockToken,
        feedbackRecords
        ):
    print('feedback_received_callback called with context: {0}'.format(context));
    print('Batch userId                 : {0}'.format(batchUserId));
    print('Batch lockToken              : {0}'.format(batchLockToken));

    if feedbackRecords:
        numberOfFeedbackRecords = len(feedbackRecords)
        print('Number of feedback records   : {0}'.format(numberOfFeedbackRecords))

        for x in range(0, numberOfFeedbackRecords):
            print('Feedback record {0}'.format(x));
            print('    statusCode               : {0}'.format(feedbackRecords[x]["statusCode"]));
            print('    description              : {0}'.format(feedbackRecords[x]["description"]));
            print('    deviceId                 : {0}'.format(feedbackRecords[x]["deviceId"]));
            print('    generationId             : {0}'.format(feedbackRecords[x]["generationId"]));
            print('    correlationId            : {0}'.format(feedbackRecords[x]["correlationId"]));
            print('    enqueuedTimeUtc          : {0}'.format(feedbackRecords[x]["enqueuedTimeUtc"]));
            print('    originalMessageId        : {0}'.format(feedbackRecords[x]["originalMessageId"]));

def iothub_messaging_sample_run():
    try:
        iothubMessaging = IoTHubMessaging(connection_string)
        iothubMessaging.set_feedback_message_callback(feedback_received_callback, feedback_context)

        iothubMessaging.open(open_complete_callback, open_context)

        for i in range(0, message_count):
            print('Sending message: {0}'.format(i))
            msg_txt_formatted = msg_txt % (
                avg_wind_speed + (random.random() * 4 + 2))
            message = IoTHubMessage(bytearray(msg_txt_formatted, 'utf8'))
            message = IoTHubMessage(bytearray(msg_txt0, 'utf8'))

            # optional: assign ids
            message.message_id = "message_%d" % i
            message.correlation_id = "correlation_%d" % i
            # optional: assign properties
            prop_map = message.properties()
            prop_text = "PropMsg_%d" % i
            prop_map.add("Property", prop_text)

            iothubMessaging.send_async(device_id, message, send_complete_callback, i)

        raw_input("Press Enter to continue...\n")

        iothubMessaging.close()

    except IoTHubError as e:
        print("Unexpected error {0}" % e)
        return
    except KeyboardInterrupt:
        print("IoTHubMessaging sample stopped")

def usage():
    print("Usage: iothub_messaging_sample.py -c <connectionstring>")
    print("    connectionstring: <HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>>")
    print("    deviceid        : <Existing device ID to to send a message to>")

if __name__ == '__main__':
    print("")
    print("Python {0}".format(sys.version))
    print("IoT Hub Service Client for Python SDK Version: {0}".format(iothub_service_client.__version__))
    print("")

    try:
        (connection_string, device_id) = get_iothub_opt(sys.argv[1:], connection_string, device_id)
    except OptionError as o:
        print(o)
        usage()
        sys.exit(1)

    print("Starting the IoT Hub Service Client Messaging Python sample...")
    print("    Connection string = {0}".format(connection_string))
    print("    Device ID         = {0}".format(device_id))

    iothub_messaging_sample_run()
