# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import six.moves.urllib as urllib

logger = logging.getLogger(__name__)

POS_STATUS_CODE_IN_TOPIC = 3
POS_URL_PORTION = 1
POS_QUERY_PARAM_PORTION = 2


class RequestResponseProvider(object):
    """
    Class that processes requests sent from device and responses received at device.
    """

    def __init__(self, state_based_provider):

        self._state_based_provider = state_based_provider

        self._state_based_provider.on_state_based_provider_message_received = self._receive_response

        self._pending_requests = {}

    def send_request(self, rid, topic, request, callback):
        self._pending_requests[rid] = callback
        self.publish(topic=topic, request=request)

    def connect(self, callback=None):
        if callback is None:
            callback = self._on_connection_state_change
        self._state_based_provider.connect(callback=callback)

    def disconnect(self, callback=None):
        if callback is None:
            callback = self._on_connection_state_change
        self._state_based_provider.disconnect(callback=callback)

    def publish(self, topic, request, callback=None):
        if callback is None:
            callback = self._on_publish_completed
        self._state_based_provider.publish(topic=topic, message=request, callback=callback)

    def subscribe(self, topic, callback=None):
        if callback is None:
            callback = self._on_subscribe_completed
        self._state_based_provider.subscribe(topic=topic, callback=callback)

    def unsubscribe(self, topic, callback=None):
        if callback is None:
            callback = self._on_unsubscribe_completed
        self._state_based_provider.unsubscribe(topic=topic, callback=callback)

    def _receive_response(self, topic, payload):
        """
        Handler that processes the response from the service.
        :param topic: The topic in bytes name on which the message arrived on.
        :param payload: Payload in bytes of the message received.
        """
        # """ Sample topic and payload
        # $dps/registrations/res/200/?$rid=28c32371-608c-4390-8da7-c712353c1c3b
        # {"operationId":"4.550cb20c3349a409.390d2957-7b58-4701-b4f9-7fe848348f4a","status":"assigning"}
        # """
        logger.info("Received payload:")
        logger.info(payload)
        # topic_str = topic.decode("utf-8")
        if payload is not None:  # In cases of empty erroneous response from service
            response = payload.decode("utf-8")

        # There may be no response when status code is >= 300
        logger.info("Received response:{} on topic:{}".format(response, topic))

        if topic.startswith("$dps/registrations/res/"):
            topic_parts = topic.split("$")
            key_value_dict = urllib.parse.parse_qs(topic_parts[POS_QUERY_PARAM_PORTION])
            rid = key_value_dict["rid"][0]
        # TODO Not DPS may have other ways to retrieve rid

        if rid in self._pending_requests:
            callback = self._pending_requests[rid]
            # Only send the status code and the portion of the topic containing query parameters
            callback(topic_parts[POS_URL_PORTION], key_value_dict, response)
            del self._pending_requests[rid]

    def _on_connection_state_change(self, new_state):
        """Handler to be called by the transport upon a connection state change."""
        logger.info("Connection State - {}".format(new_state))

    def _on_publish_completed(self):
        logger.info("publish completed for request response provider")

    def _on_subscribe_completed(self):
        logger.info("subscribe completed for request response provider")

    def _on_unsubscribe_completed(self):
        logger.info("on_unsubscribe_completed for request response provider")
