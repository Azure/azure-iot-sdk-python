# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from azure.iot.device.common.pipeline import PipelineOperation


class GetStorageInfoOperation(PipelineOperation):
    """
    A PipleineOperation object which contains arguments used to get the storage information from IoT Hub.
    """

    def __init__(self, blob_name, callback):
        """
        Initializer for GetStorageInfo objects.

        :param callback: The function that gets called when this operation is complete or has failed.
         The callback function must accept a PipelineOperation object which indicates the specific operation has which
         has completed or failed.
        :type callback: Function/callable


        :ivar storage_info: Upon completion, this contains the storage information which was retrieved from the service.
        :type storage_info: Storage Info
        """
        super(GetStorageInfoOperation, self).__init__(callback=callback)
        self.blob_name = blob_name
        self.storage_info = None


class NotifyBlobUploadStatusOperation(PipelineOperation):
    """
    A PipleineOperation object which contains arguments used to get the storage information from IoT Hub.
    """

    def __init__(self, correlation_id, upload_response, status_code, status_description, callback):
        """
        Initializer for GetStorageInfo objects.

        :param callback: The function that gets called when this operation is complete or has failed.
         The callback function must accept a PipelineOperation object which indicates the specific operation has which
         has completed or failed.
        :type callback: Function/callable


        :ivar storage_info: Upon completion, this contains the storage information which was retrieved from the service.
        :type storage_info: Storage Info
        """
        super(NotifyBlobUploadStatusOperation, self).__init__(callback=callback)
        self.correlation_id = correlation_id
        self.upload_response = upload_response
        self.request_status_code = status_code
        self.status_description = status_description
        self.response_status_code = None
