# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.
import six
import os
import json

if six.PY2:
    FileNotFoundError = IOError

IOTHUB_CONNECTION_STRING = None
EVENTHUB_CONNECTION_STRING = None
IOTHUB_HOSTNAME = None
IOTHUB_NAME = None


def get_secrets():
    global IOTHUB_CONNECTION_STRING, EVENTHUB_CONNECTION_STRING, IOTHUB_HOSTNAME, IOTHUB_NAME

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
                break
            test_path = new_test_path

    if secrets:
        IOTHUB_CONNECTION_STRING = secrets.get("iothubConnectionString", None)
        EVENTHUB_CONNECTION_STRING = secrets.get("eventhubConnectionString", None)
    else:
        IOTHUB_CONNECTION_STRING = os.environ["IOTHUB_E2E_CONNECTION_STRING"]
        EVENTHUB_CONNECTION_STRING = os.environ["IOTHUB_E2E_EVENTHUB_CONNECTION_STRING"]

    parts = {}
    for key_and_value in IOTHUB_CONNECTION_STRING.split(";"):
        key, value = key_and_value.split("=", 1)
        parts[key] = value

    IOTHUB_HOSTNAME = parts["HostName"]
    IOTHUB_NAME = IOTHUB_HOSTNAME.split(".")[0]


get_secrets()
EVENTHUB_CONSUMER_GROUP = "$default"
