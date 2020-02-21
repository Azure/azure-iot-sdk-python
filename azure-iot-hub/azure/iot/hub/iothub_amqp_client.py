# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import os
import sys
import base64
import time
import hashlib
import hmac
from uuid import uuid4
import six.moves.urllib as urllib

from urllib.parse import quote, quote_plus, urlencode

import uamqp

default_sas_expiry = 30


class IoTHubAmqpClient:
    def _generate_auth_token(self, uri, sas_name, sas_value):
        sas = base64.b64decode(sas_value)
        expiry = str(int(time.time() + default_sas_expiry))
        string_to_sign = (uri + "\n" + expiry).encode("utf-8")
        signed_hmac_sha256 = hmac.HMAC(sas, string_to_sign, hashlib.sha256)
        signature = urllib.parse.quote(base64.b64encode(signed_hmac_sha256.digest()))
        return "SharedAccessSignature sr={}&sig={}&se={}&skn={}".format(
            uri, signature, expiry, sas_name
        )

    def _build_amqp_endpoint(self, hostname, shared_access_key_name, shared_access_key):
        hub_name = hostname.split(".")[0]
        endpoint = "{}@sas.root.{}".format(shared_access_key_name, hub_name)
        endpoint = quote_plus(endpoint)
        sas_token = self._generate_auth_token(
            hostname, shared_access_key_name, shared_access_key + "="
        )
        endpoint = endpoint + ":{}@{}".format(quote_plus(sas_token), hostname)
        return endpoint

    def __init__(self, hostname, shared_access_key_name, shared_access_key):
        self.endpoint = self._build_amqp_endpoint(
            hostname, shared_access_key_name, shared_access_key
        )
        operation = "/messages/devicebound"
        target = "amqps://" + self.endpoint + operation
        self.amqp_client = uamqp.SendClient(target)

    def disconnect_sync(self):
        """
        Disconnect the Amqp client.
        """
        if self.amqp_client:
            self.amqp_client.close()
            self.amqp_client = None

    def send_message_to_device(self, device_id, message):
        """Send a message to the specified deivce.

        :param str device_id: The name (Id) of the device.
        :param str message: The message that is to be delivered to the device.

        :raises: Exception if the Send command is not able to send the message
        """
        msg_content = message
        app_properties = {}
        msg_props = uamqp.message.MessageProperties()
        msg_props.to = "/devices/{}/messages/devicebound".format(device_id)
        msg_props.message_id = str(uuid4())
        message = uamqp.Message(
            msg_content, properties=msg_props, application_properties=app_properties
        )
        self.amqp_client.queue_message(message)
        results = self.amqp_client.send_all_messages(close_on_done=False)
        if uamqp.constants.MessageState.SendFailed in results:
            raise Exception("C2D message sned failure")
