# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import random
import sys
import iothub_service_client
from iothub_service_client import IoTHubMessaging, IoTHubMessage, IoTHubError
from iothub_service_client_args import get_iothub_opt, OptionError

OPEN_CONTEXT = 0
FEEDBACK_CONTEXT = 1

MESSAGE_COUNT = 10

# String containing Hostname, SharedAccessKeyName & SharedAccessKey in the format:
# "HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>"
CONNECTION_STRING = "[IoTHub Connection String]"
DEVICE_ID = "[Device Id]"


AVG_WIND_SPEED = 10.0
MSG_TXT = "{\"service client sent a message\": %.2f}"


def open_complete_callback(context):
    print ( 'open_complete_callback called with context: {0}'.format(context) )


def send_complete_callback(context, messaging_result):
    context = 0
    print ( 'send_complete_callback called with context : {0}'.format(context) )
    print ( 'messagingResult : {0}'.format(messaging_result) )


def feedback_received_callback(context, batch_user_id, batch_lock_token, feedback_records):
    print ( 'feedback_received_callback called with context: {0}'.format(context) )
    print ( 'Batch userId                 : {0}'.format(batch_user_id) )
    print ( 'Batch lockToken              : {0}'.format(batch_lock_token) )

    if feedback_records:
        number_of_feedback_records = len(feedback_records)
        print ( 'Number of feedback records   : {0}'.format(number_of_feedback_records) )

        for feedback_index in range(0, number_of_feedback_records):
            print ( 'Feedback record {0}'.format(feedback_index) )
            print ( '    statusCode               : {0}'.format(feedback_records[feedback_index]["statusCode"]) )
            print ( '    description              : {0}'.format(feedback_records[feedback_index]["description"]) )
            print ( '    deviceId                 : {0}'.format(feedback_records[feedback_index]["deviceId"]) )
            print ( '    generationId             : {0}'.format(feedback_records[feedback_index]["generationId"]) )
            print ( '    correlationId            : {0}'.format(feedback_records[feedback_index]["correlationId"]) )
            print ( '    enqueuedTimeUtc          : {0}'.format(feedback_records[feedback_index]["enqueuedTimeUtc"]) )
            print ( '    originalMessageId        : {0}'.format(feedback_records[feedback_index]["originalMessageId"]) )


def iothub_messaging_sample_run():
    try:
        iothub_messaging = IoTHubMessaging(CONNECTION_STRING)
        iothub_messaging.set_feedback_message_callback(feedback_received_callback, FEEDBACK_CONTEXT)

        iothub_messaging.open(open_complete_callback, OPEN_CONTEXT)

        for i in range(0, MESSAGE_COUNT):
            print ( 'Sending message: {0}'.format(i) )
            msg_txt_formatted = MSG_TXT % (
                AVG_WIND_SPEED + (random.random() * 4 + 2))
            message = IoTHubMessage(bytearray(msg_txt_formatted, 'utf8'))

            # optional: assign ids
            message.message_id = "message_%d" % i
            message.correlation_id = "correlation_%d" % i
            # optional: assign properties
            prop_map = message.properties()
            prop_text = "PropMsg_%d" % i
            prop_map.add("Property", prop_text)

            iothub_messaging.send_async(DEVICE_ID, message, send_complete_callback, i)

        try:
            # Try Python 2.xx first
            raw_input("Press Enter to continue...\n")
        except:
            pass
            # Use Python 3.xx in the case of exception
            input("Press Enter to continue...\n")

        iothub_messaging.close()

    except IoTHubError as iothub_error:
        print ( "Unexpected error {0}" % iothub_error )
        return
    except KeyboardInterrupt:
        print ( "IoTHubMessaging sample stopped" )


def usage():
    print ( "Usage: iothub_messaging_sample.py -c <connectionstring>" )
    print ( "    connectionstring: <HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>>" )
    print ( "    deviceid        : <Existing device ID to to send a message to>" )


if __name__ == '__main__':
    print ( "" )
    print ( "Python {0}".format(sys.version) )
    print ( "IoT Hub Service Client for Python" )
    print ( "" )

    try:
        (CONNECTION_STRING, DEVICE_ID) = get_iothub_opt(sys.argv[1:], CONNECTION_STRING, DEVICE_ID)
    except OptionError as option_error:
        print ( option_error )
        usage()
        sys.exit(1)

    print ( "Starting the IoT Hub Service Client Messaging Python sample..." )
    print ( "    Connection string = {0}".format(CONNECTION_STRING) )
    print ( "    Device ID         = {0}".format(DEVICE_ID) )

    iothub_messaging_sample_run()
