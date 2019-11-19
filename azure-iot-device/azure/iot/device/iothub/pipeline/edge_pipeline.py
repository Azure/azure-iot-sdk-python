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
    pipeline_ops_edgehub,
    pipeline_stages_edgehub_http,
)
from azure.iot.device.iothub.auth.x509_authentication_provider import X509AuthenticationProvider

logger = logging.getLogger(__name__)


class EdgePipeline(object):
    """Pipeline to communicate with Edge.
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
            .append_stage(pipeline_stages_edgehub_http.EdgeHubHTTPTranslationStage())
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

    def invoke_method(self, device_id, method_params, callback):
        """
        Send a method response to the service.
        """
        logger.debug("IoTHubPipeline invoke_method called")

        def on_complete(op, error):
            callback(error=error)

        self._pipeline.run_op(
            pipeline_ops_edgehub.MethodInvokeOperation(
                device_id=device_id,
                module_id=None,
                method_params=method_params,
                callback=on_complete,
            )
        )

    def invoke_method_module_to_module(self, device_id, module_id, method_params, callback):
        """
        Send a method response to the service.
        """
        logger.debug("IoTHubPipeline invoke_method called")

        def on_complete(op, error):
            callback(error=error)

        self._pipeline.run_op(
            pipeline_ops_edgehub.MethodInvokeOperation(
                device_id=device_id,
                module_id=module_id,
                method_params=method_params,
                callback=on_complete,
            )
        )
