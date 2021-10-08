# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.
import six
import os
import json

if six.PY2:
    FileNotFoundError = IOError

secrets = None

this_file_path = os.path.dirname(os.path.realpath(__file__))
test_path = this_file_path
while secrets is None:
    filename = os.path.join(test_path, "_e2e_settings.json")
    try:
        with open(filename, "r") as f:
            secrets = json.load(f)
        print("settings loaded from {}".format(filename))
    except FileNotFoundError:
        new_test_path = os.path.dirname(test_path)
        if new_test_path == test_path:
            raise Exception("_e2e_settings.json not found in {} or parent".format(this_file_path))
        test_path = new_test_path

# Device ID used when running tests
DEVICE_ID = secrets.get("deviceId", None)

# Connection string for the iothub instance
IOTHUB_CONNECTION_STRING = secrets.get("iothubConnectionString", None)

# Connection string for the eventhub instance
EVENTHUB_CONNECTION_STRING = secrets.get("eventhubConnectionString", None)

# Consumer group used when monitoring eventhub events
EVENTHUB_CONSUMER_GROUP = secrets.get("eventhubConsumerGroup", None)

# Name of iothub.  Probably DNS name for the hub without the azure-devices.net suffix
IOTHUB_NAME = secrets.get("iothubName", None)

# Connection string for device under test
DEVICE_CONNECTION_STRING = secrets.get("deviceConnectionString", None)

# Set default values
if not EVENTHUB_CONSUMER_GROUP:
    EVENTHUB_CONSUMER_GROUP = "$default"

del secrets
del this_file_path
del test_path
