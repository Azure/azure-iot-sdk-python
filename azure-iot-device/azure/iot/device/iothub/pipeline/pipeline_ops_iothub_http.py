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

    def __init__(self, target_device_id, target_module_id, method_params, callback):
        """
        Initializer for MethodInvokeOperation objects.

        :param str target_device_id: The device id of the target device/module
        :param str target_module_id: The module id of the target module
        :param method_params: The parameters used to invoke the method, as defined by the IoT Hub specification.
        :param callback: The function that gets called when this operation is complete or has failed.
            The callback function must accept a PipelineOperation object which indicates the specific operation has which
            has completed or failed.
        :type callback: Function/callable
        """
        super(MethodInvokeOperation, self).__init__(callback=callback)
        self.target_device_id = target_device_id
        self.target_module_id = target_module_id
        self.method_params = method_params
        self.method_response = None


class GetStorageInfoOperation(PipelineOperation):
    """
    A PipleineOperation object which contains arguments used to get the storage information from IoT Hub.
    """

    def __init__(self, blob_name, callback):
        """
        Initializer for GetStorageInfo objects.

        :param str blob_name: The name of the blob that will be created in Azure Storage
        :param callback: The function that gets called when this operation is complete or has failed.
            The callback function must accept a PipelineOperation object which indicates the specific operation has which
            has completed or failed.
        :type callback: Function/callable

        :ivar dict storage_info: Upon completion, this contains the storage information which was retrieved from the service.
        """
        super(GetStorageInfoOperation, self).__init__(callback=callback)
        self.blob_name = blob_name
        self.storage_info = None


class NotifyBlobUploadStatusOperation(PipelineOperation):
    """
    A PipleineOperation object which contains arguments used to get the storage information from IoT Hub.
    """

    def __init__(self, correlation_id, is_success, status_code, status_description, callback):
        """
        Initializer for GetStorageInfo objects.

        :param str correlation_id: Provided by IoT Hub on get_storage_info_for_blob request.
        :param bool is_success: A boolean that indicates whether the file was uploaded successfully.
        :param int request_status_code: A numeric status code that is the status for the upload of the fiel to storage.
        :param str status_description: A description that corresponds to the status_code.
        :param callback: The function that gets called when this operation is complete or has failed.
            The callback function must accept a PipelineOperation object which indicates the specific operation has which
            has completed or failed.
        :type callback: Function/callable
        """
        super(NotifyBlobUploadStatusOperation, self).__init__(callback=callback)
        self.correlation_id = correlation_id
        self.is_success = is_success
        self.request_status_code = status_code
        self.status_description = status_description
