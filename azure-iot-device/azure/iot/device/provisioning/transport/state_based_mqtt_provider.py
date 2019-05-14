# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
# TODO : This class is empty to later incorporate pipeline changes


class StateBasedMQTTProvider:
    def __init__(self, provisioning_host, security_client):
        pass

    def connect(self, callback=None):
        pass

    def disconnect(self, callback=None):
        pass

    def publish(self, topic, message, callback=None):
        pass

    def subscribe(self, topic, callback=None):
        pass

    def unsubscribe(self, topic, callback=None):
        pass
