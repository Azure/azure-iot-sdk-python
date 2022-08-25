# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.

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


config = Config()
