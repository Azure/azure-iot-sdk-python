# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.

TRANSPORT_MQTT = "mqtt"
TRANSPORT_MQTT_WS = "mqttws"
TRANSPORT_CHOICES = [TRANSPORT_MQTT, TRANSPORT_MQTT_WS]

IDENTITY_DEVICE_CLIENT = "deviceclient"
IDENTITY_MODULE_CLIENT = "module_client"
IDENTITY_CHOICES = [IDENTITY_DEVICE_CLIENT, IDENTITY_MODULE_CLIENT]

AUTH_CONNECTION_STRING = "connection_string"
AUTH_X509 = "x509"
AUTH_CHOICES = [AUTH_CONNECTION_STRING, AUTH_X509]


class Config(object):
    def __init__(self):
        self.transport = TRANSPORT_MQTT
        self.identity = IDENTITY_DEVICE_CLIENT
        self.auth = AUTH_CONNECTION_STRING


config = Config()
