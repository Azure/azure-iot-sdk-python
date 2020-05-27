# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from azure.iot.device.common.pipeline import PipelineOperation


class SendD2CMessageOperation(PipelineOperation):
    """
    A PipelineOperation object which contains arguments used to send a telemetry message to an IoTHub or EdegHub server.

    This operation is in the group of IoTHub operations because it is very specific to the IoTHub client
    """

    def __init__(self, message, callback):
        """
        Initializer for SendD2CMessageOperation objects.

        :param Message message: The message that we're sending to the service
        :param Function callback: The function that gets called when this operation is complete or has failed.
         The callback function must accept A PipelineOperation object which indicates the specific operation which
         has completed or failed.
        """
        super(SendD2CMessageOperation, self).__init__(callback=callback)
        self.message = message


class SendOutputMessageOperation(PipelineOperation):
    """
    A PipelineOperation object which contains arguments used to send an output message to an EdgeHub server.

    This operation is in the group of IoTHub operations because it is very specific to the IoTHub client
    """

    def __init__(self, message, callback):
        """
        Initializer for SendOutputMessageOperation objects.

        :param Message message: The output message that we're sending to the service. The name of the output is
          expected to be stored in the output_name attribute of this object
        :param Function callback: The function that gets called when this operation is complete or has failed.
         The callback function must accept A PipelineOperation object which indicates the specific operation which
         has completed or failed.
        """
        super(SendOutputMessageOperation, self).__init__(callback=callback)
        self.message = message


class SendMethodResponseOperation(PipelineOperation):
    """
    A PipleineOperation object which contains arguments used to send a method response to an IoTHub or EdgeHub server.

    This operation is in the group of IoTHub operations because it is very specific to the IoTHub client.
    """

    def __init__(self, method_response, callback):
        """
        Initializer for SendMethodResponseOperation objects.

        :param method_response: The method response to be sent to IoTHub/EdgeHub
        :type method_response: MethodResponse
        :param callback: The function that gets called when this operation is complete or has failed.
         The callback function must accept a PipelineOperation object which indicates the specific operation has which
         has completed or failed.
        :type callback: Function/callable
        """
        super(SendMethodResponseOperation, self).__init__(callback=callback)
        self.method_response = method_response


class GetTwinOperation(PipelineOperation):
    """
    A PipelineOperation object which represents a request to get a device twin or a module twin from an Azure
    IoT Hub or Azure Iot Edge Hub service.

    :ivar twin: Upon completion, this contains the twin which was retrieved from the service.
    :type twin: Twin
    """

    def __init__(self, callback):
        """
        Initializer for GetTwinOperation objects.
        """
        super(GetTwinOperation, self).__init__(callback=callback)
        self.twin = None


class PatchTwinReportedPropertiesOperation(PipelineOperation):
    """
    A PipelineOperation object which contains arguments used to send a reported properties patch to the Azure
    IoT Hub or Azure IoT Edge Hub service.
    """

    def __init__(self, patch, callback):
        """
        Initializer for PatchTwinReportedPropertiesOperation object

        :param patch: The reported properties patch to send to the service.
        :type patch: dict, str, int, float, bool, or None (JSON compatible values)
        """
        super(PatchTwinReportedPropertiesOperation, self).__init__(callback=callback)
        self.patch = patch
