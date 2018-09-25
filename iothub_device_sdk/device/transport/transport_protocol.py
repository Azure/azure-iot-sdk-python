# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from enum import Enum


class TransportProtocol(Enum):
    MQTT = 0
    AMQP = 1
    HTTPS = 2
    MQTT_WS = 3
    AMQP_WS = 4

