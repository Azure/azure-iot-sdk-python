# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging

logger = logging.getLogger(__name__)

POS_STATUS_CODE_IN_TOPIC = 3
POS_URL_PORTION = 1
POS_QUERY_PARAM_PORTION = 2


class RequestResponseProvider(object):
    """
    Class that processes requests sent from device and responses received at device.
    """

    def __init__(self, provisioning_pipeline):

        self._provisioning_pipeline = provisioning_pipeline

        self._provisioning_pipeline.on_provisioning_pipeline_message_received = (
            self._receive_response
        )

        self._pending_requests = {}

    def send_request(
        self, request_id, request_payload, operation_id=None, callback_on_response=None
    ):
        """
        Sends a request
        :param request_id: Id of the request
        :param request_payload: The payload of the request.
        :param operation_id: A id of the operation in case it is an ongoing process.
        :param callback_on_response: callback which is called when response comes back for this request.
        """
        self._pending_requests[request_id] = callback_on_response
        self._provisioning_pipeline.send_request(
            request_id=request_id,
            request_payload=request_payload,
            operation_id=operation_id,
            callback=self._on_publish_completed,
        )

    def connect(self, callback=None):
        if callback is None:
            callback = self._on_connection_state_change
        self._provisioning_pipeline.connect(callback=callback)

    def disconnect(self, callback=None):
        if callback is None:
            callback = self._on_connection_state_change
        self._provisioning_pipeline.disconnect(callback=callback)

    def enable_responses(self, callback=None):
        if callback is None:
            callback = self._on_subscribe_completed
        self._provisioning_pipeline.enable_responses(callback=callback)

    def disable_responses(self, callback=None):
        if callback is None:
            callback = self._on_unsubscribe_completed
        self._provisioning_pipeline.disable_responses(callback=callback)

    def _receive_response(self, request_id, status_code, key_value_dict, response_payload):
        """
        Handler that processes the response from the service.
        :param request_id: The id of the request which is being responded to.
        :param status_code: The status code inside the response
        :param key_value_dict: A dictionary of keys mapped to a list of values extracted from the topic of the response.
        :param response_payload: String payload of the message received.
        :return:
        """
        # """ Sample topic and payload
        # $dps/registrations/res/200/?$rid=28c32371-608c-4390-8da7-c712353c1c3b
        # {"operationId":"4.550cb20c3349a409.390d2957-7b58-4701-b4f9-7fe848348f4a","status":"assigning"}
        # """
        logger.info("Received response {}:".format(response_payload))

        if request_id in self._pending_requests:
            callback = self._pending_requests[request_id]
            # Only send the status code and the extracted topic
            callback(request_id, status_code, key_value_dict, response_payload)
            del self._pending_requests[request_id]

        # TODO : What happens when request_id if not there ? trigger error ?

    def _on_connection_state_change(self, new_state):
        """Handler to be called by the pipeline upon a connection state change."""
        logger.info("Connection State - {}".format(new_state))

    def _on_publish_completed(self):
        logger.info("publish completed for request response provider")

    def _on_subscribe_completed(self):
        logger.info("subscribe completed for request response provider")

    def _on_unsubscribe_completed(self):
        logger.info("on_unsubscribe_completed for request response provider")
