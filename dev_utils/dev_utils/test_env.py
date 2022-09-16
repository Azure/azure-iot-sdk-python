# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.
import os

IOTHUB_CONNECTION_STRING = None
EVENTHUB_CONNECTION_STRING = None
IOTHUB_HOSTNAME = None
IOTHUB_NAME = None
EVENTHUB_CONSUMER_GROUP = None
DEVICE_CONNECTION_STRING = None


if "IOTHUB_E2E_IOTHUB_CONNECTION_STRING" in os.environ:
    IOTHUB_CONNECTION_STRING = os.environ["IOTHUB_E2E_IOTHUB_CONNECTION_STRING"]
    EVENTHUB_CONNECTION_STRING = os.environ["IOTHUB_E2E_EVENTHUB_CONNECTION_STRING"]
    EVENTHUB_CONSUMER_GROUP = os.getenv("IOTHUB_E2E_EVENTHUB_CONSUMER_GROUP", None)
else:
    IOTHUB_CONNECTION_STRING = os.environ["IOTHUB_CONNECTION_STRING"]
    EVENTHUB_CONNECTION_STRING = os.environ.get("EVENTHUB_CONNECTION_STRING")
    EVENTHUB_CONSUMER_GROUP = os.getenv("EVENTHUB_CONSUMER_GROUP", None)

DEVICE_CONNECTION_STRING = os.environ.get("IOTHUB_DEVICE_CONNECTION_STRING")

parts = {}
for key_and_value in IOTHUB_CONNECTION_STRING.split(";"):
    key, value = key_and_value.split("=", 1)
    parts[key] = value

IOTHUB_HOSTNAME = parts["HostName"]
IOTHUB_NAME = IOTHUB_HOSTNAME.split(".")[0]


if not EVENTHUB_CONSUMER_GROUP:
    EVENTHUB_CONSUMER_GROUP = "$default"
