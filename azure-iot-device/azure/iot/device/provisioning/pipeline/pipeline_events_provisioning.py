# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from azure.iot.device.common.pipeline.pipeline_events_base import PipelineEvent


class RegistrationResponseEvent(PipelineEvent):
    """
    A PipelineEvent object which represents an incoming RegistrationResponse event. This object is probably
    created by some converter stage based on a pipeline-specific event
    """

    def __init__(self, request_id, status_code, key_values, response_payload):
        """
        Initializer for RegistrationResponse objects.
        :param request_id : The id of the request to which the response arrived.
        :param status_code: The status code received in the topic.
        :param key_values: A dictionary containing key mapped to a list of values that were extarcted from the topic.
        :param response_payload: The response received from a registration process
        """
        super(RegistrationResponseEvent, self).__init__()
        self.request_id = request_id
        self.status_code = status_code
        self.key_values = key_values
        self.response_payload = response_payload
