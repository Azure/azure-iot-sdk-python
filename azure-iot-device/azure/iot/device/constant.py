# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module defines constants for use across the azure-iot-device package
"""

VERSION = "2.12.0"
IOTHUB_IDENTIFIER = "azure-iot-device-iothub-py"
PROVISIONING_IDENTIFIER = "azure-iot-device-provisioning-py"
IOTHUB_API_VERSION = "2019-10-01"
PROVISIONING_API_VERSION = "2019-03-31"
SECURITY_MESSAGE_INTERFACE_ID = "urn:azureiot:Security:SecurityAgent:1"
TELEMETRY_MESSAGE_SIZE_LIMIT = 262144
# The max keep alive is determined by the load balancer currently.
MAX_KEEP_ALIVE_SECS = 1740
# Everything in digital twin is defined here
# as things are extremely dynamic and subject to sudden changes
DIGITAL_TWIN_PREFIX = "dtmi"
DIGITAL_TWIN_API_VERSION = "2020-09-30"
DIGITAL_TWIN_QUERY_HEADER = "model-id"
