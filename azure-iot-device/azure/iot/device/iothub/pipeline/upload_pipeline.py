# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import sys
from azure.iot.device.common.evented_callback import EventedCallback
from azure.iot.device.common.pipeline import (
    pipeline_stages_base,
    pipeline_ops_base,
    pipeline_stages_http,
)
from . import (
    constant,
    pipeline_stages_iothub,
    pipeline_ops_iothub,
    pipeline_ops_upload,
    pipeline_stages_upload_http,
)
from azure.iot.device.iothub.auth.x509_authentication_provider import X509AuthenticationProvider

logger = logging.getLogger(__name__)


class UploadPipeline(object):
    """Pipeline to communicate with Upload endpoint of IoT Hub.
    Uses HTTP.
    """

    def __init__(self, auth_provider, pipeline_configuration):

        # Event Handlers - Will be set by Client after instantiation of this object
        self.on_connected = None
        self.on_disconnected = None
        self.on_c2d_message_received = None
        self.on_input_message_received = None
        self.on_method_request_received = None
        self.on_twin_patch_received = None

        self._pipeline = (
            pipeline_stages_base.PipelineRootStage(pipeline_configuration=pipeline_configuration)
            .append_stage(pipeline_stages_iothub.UseAuthProviderStage())
            .append_stage(pipeline_stages_upload_http.UploadHTTPTranslationStage())
            .append_stage(pipeline_stages_http.HTTPTransportStage())
        )

        callback = EventedCallback()

        if isinstance(auth_provider, X509AuthenticationProvider):
            op = pipeline_ops_iothub.SetX509AuthProviderOperation(
                auth_provider=auth_provider, callback=callback
            )
        else:  # Currently everything else goes via this block.
            op = pipeline_ops_iothub.SetAuthProviderOperation(
                auth_provider=auth_provider, callback=callback
            )

        self._pipeline.run_op(op)
        callback.wait_for_completion()

    def get_storage_info(self, blob_name, callback):
        def on_complete(op, error):
            if error:
                callback(error=error, storage_info=None)
            else:
                callback(storage_info=op.storage_info)

        self._pipeline.run_op(
            pipeline_ops_upload.GetStorageInfoOperation(blob_name=blob_name, callback=on_complete)
        )
