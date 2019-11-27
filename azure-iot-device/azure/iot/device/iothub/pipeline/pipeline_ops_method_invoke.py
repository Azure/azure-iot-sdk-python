# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from azure.iot.device.common.pipeline import PipelineOperation


class MethodInvokeOperation(PipelineOperation):
    """
    A PipleineOperation object which contains arguments used to send a method invoke to an IoTHub or EdgeHub server.

    This operation is in the group of EdgeHub operations because it is very specific to the EdgeHub client.
    """

    def __init__(self, device_id, module_id, method_params, callback):
        """
        Initializer for MethodInvokeOperation objects.

        :param method_response: The method response to be sent to IoTHub/EdgeHub
        :type method_response: MethodResponse
        :param callback: The function that gets called when this operation is complete or has failed.
         The callback function must accept a PipelineOperation object which indicates the specific operation has which
         has completed or failed.
        :type callback: Function/callable
        """
        super(MethodInvokeOperation, self).__init__(callback=callback)
        self.device_id = device_id
        self.module_id = module_id
        self.method_params = method_params
        self.method_response = None
