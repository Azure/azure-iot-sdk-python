# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from azure.iot.device.common.pipeline.pipeline_ops_base import PipelineOperation


class RegisterOperation(PipelineOperation):
    """
    A PipelineOperation object which contains arguments used to send a registration request
    to an Device Provisioning Service.

    This operation is in the group of DPS operations because it is very specific to the DPS client.
    """

    def __init__(self, request_payload, registration_id, callback, registration_result=None):
        """
        Initializer for RegisterOperation objects.

        :param request_payload: The request that we are sending to the service
        :param registration_id: The registration ID is used to uniquely identify a device in the Device Provisioning Service.
        :param Function callback: The function that gets called when this operation is complete or has failed.
         The callback function must accept A PipelineOperation object which indicates the specific operation which
         has completed or failed.
        """
        super(RegisterOperation, self).__init__(callback=callback)
        self.request_payload = request_payload
        self.registration_id = registration_id
        self.registration_result = registration_result
        self.retry_after_timer = None
        self.polling_timer = None
        self.provisioning_timeout_timer = None


class PollStatusOperation(PipelineOperation):
    """
    A PipelineOperation object which contains arguments used to send a registration request
    to an Device Provisioning Service.

    This operation is in the group of DPS operations because it is very specific to the DPS client.
    """

    def __init__(self, operation_id, request_payload, callback, registration_result=None):
        """
        Initializer for PollStatusOperation objects.

        :param operation_id: The id of the existing operation for which the polling was started.
        :param request_payload: The request that we are sending to the service
        :param Function callback: The function that gets called when this operation is complete or has failed.
         The callback function must accept A PipelineOperation object which indicates the specific operation which
         has completed or failed.
        """
        super(PollStatusOperation, self).__init__(callback=callback)
        self.operation_id = operation_id
        self.request_payload = request_payload
        self.registration_result = registration_result
        self.retry_after_timer = None
        self.polling_timer = None
        self.provisioning_timeout_timer = None
