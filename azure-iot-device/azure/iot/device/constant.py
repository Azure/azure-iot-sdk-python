# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module defines constants for use across the azure-iot-device package
"""

VERSION = "3.0.0b2"
IOTHUB_IDENTIFIER = "azure-iot-device-iothub-py"
PROVISIONING_IDENTIFIER = "azure-iot-device-provisioning-py"
IOTHUB_API_VERSION = "2020-09-30"
PROVISIONING_API_VERSION = "2019-03-31"
SECURITY_MESSAGE_INTERFACE_ID = "urn:azureiot:Security:SecurityAgent:1"
PROVISIONING_GLOBAL_ENDPOINT = "global.azure-devices-provisioning.net"

# TODO: find somewhere else for this
TELEMETRY_MESSAGE_SIZE_LIMIT = 262144

# Everything in digital twin is defined here
# as things are extremely dynamic and subject to sudden changes
DIGITAL_TWIN_PREFIX = "dtmi"
DIGITAL_TWIN_QUERY_HEADER = "model-id"
