# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest

TRANSPORT_MQTT = "mqtt"
TRANSPORT_MQTT_WS = "mqttws"
TRANSPORT_CHOICES = [TRANSPORT_MQTT, TRANSPORT_MQTT_WS]

IDENTITY_DEVICE = "device"
IDENTITY_MODULE = "module"
IDENTITY_EDGE_MODULE = "edge_module"
IDENTITY_EDGE_LEAF_DEVICE = "edge_leaf_device"
IDENTITY_CHOICES = [
    IDENTITY_DEVICE,
    IDENTITY_MODULE,
    IDENTITY_EDGE_MODULE,
    IDENTITY_EDGE_LEAF_DEVICE,
]

AUTH_CONNECTION_STRING = "connection_string"
AUTH_X509_SELF_SIGNED = "x509_self_signed"
AUTH_X509_CA_SIGNED = "x509_ca_signed"
AUTH_SYMMETRIC_KEY = "symmetric_key"
AUTH_SAS_TOKEN = "sas_token"
AUTH_EDGE_ENVIRONMENT = "edge_environment"
AUTH_CHOICES = [
    AUTH_CONNECTION_STRING,
    AUTH_X509_SELF_SIGNED,
    AUTH_X509_CA_SIGNED,
    AUTH_SYMMETRIC_KEY,
    AUTH_SAS_TOKEN,
    AUTH_EDGE_ENVIRONMENT,
]
AUTH_WITH_RENEWING_TOKEN = [
    AUTH_CONNECTION_STRING,
    AUTH_EDGE_ENVIRONMENT,
    AUTH_SYMMETRIC_KEY,
]


class Config(object):
    def __init__(self):
        self.transport = TRANSPORT_MQTT
        self.identity = IDENTITY_DEVICE
        self.auth = AUTH_CONNECTION_STRING
        self.fast_iteration = False


config = Config()

connection_retry_disabled_and_enabled = [
    "connection_retry",
    [
        pytest.param(True, id="connection_retry enabled"),
        pytest.param(
            False,
            id="connection_retry disabled",
            marks=pytest.mark.dont_run_this_if_you_want_your_tests_to_go_fast,
        ),
    ],
]

auto_connect_off_and_on = [
    "auto_connect",
    [
        pytest.param(True, id="auto_connect enabled"),
        pytest.param(
            False,
            id="auto_connect disabled",
            marks=pytest.mark.dont_run_this_if_you_want_your_tests_to_go_fast,
        ),
    ],
]
