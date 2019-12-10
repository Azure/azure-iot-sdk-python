# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import json
import logging
from azure.iot.device.common.pipeline import pipeline_ops_base, PipelineStage, pipeline_thread
from azure.iot.device import exceptions
from azure.iot.device.common import handle_exceptions
from azure.iot.device.common.callable_weak_method import CallableWeakMethod
from . import pipeline_ops_iothub
from . import constant

logger = logging.getLogger(__name__)


class UseAuthProviderStage(PipelineStage):
    def __init__(self):
        super(UseAuthProviderStage, self).__init__()
        self.auth_provider = None

    """
    PipelineStage which extracts relevant AuthenticationProvider values for a new
    SetIoTHubConnectionArgsOperation.

    All other operations are passed down.
    """

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        if isinstance(op, pipeline_ops_iothub.SetAuthProviderOperation):
            self.auth_provider = op.auth_provider
            self.auth_provider.on_sas_token_updated_handler = CallableWeakMethod(
                self, "on_sas_token_updated"
            )
            worker_op = op.spawn_worker_op(
                worker_op_type=pipeline_ops_iothub.SetIoTHubConnectionArgsOperation,
                device_id=self.auth_provider.device_id,
                module_id=getattr(self.auth_provider, "module_id", None),
                hostname=self.auth_provider.hostname,
                gateway_hostname=getattr(self.auth_provider, "gateway_hostname", None),
                ca_cert=getattr(self.auth_provider, "ca_cert", None),
                sas_token=self.auth_provider.get_current_sas_token(),
            )
            self.send_op_down(worker_op)

        elif isinstance(op, pipeline_ops_iothub.SetX509AuthProviderOperation):
            self.auth_provider = op.auth_provider
            worker_op = op.spawn_worker_op(
                worker_op_type=pipeline_ops_iothub.SetIoTHubConnectionArgsOperation,
                device_id=self.auth_provider.device_id,
                module_id=getattr(self.auth_provider, "module_id", None),
                hostname=self.auth_provider.hostname,
                gateway_hostname=getattr(self.auth_provider, "gateway_hostname", None),
                ca_cert=getattr(self.auth_provider, "ca_cert", None),
                client_cert=self.auth_provider.get_x509_certificate(),
            )
            self.send_op_down(worker_op)
        else:
            super(UseAuthProviderStage, self)._run_op(op)

    @pipeline_thread.invoke_on_pipeline_thread_nowait
    def on_sas_token_updated(self):
        logger.info(
            "{}: New sas token received.  Passing down UpdateSasTokenOperation.".format(self.name)
        )

        @pipeline_thread.runs_on_pipeline_thread
        def on_token_update_complete(op, error):
            if error:
                logger.error(
                    "{}({}): token update operation failed.  Error={}".format(
                        self.name, op.name, error
                    )
                )
                handle_exceptions.handle_background_exception(error)
            else:
                logger.debug(
                    "{}({}): token update operation is complete".format(self.name, op.name)
                )

        self.send_op_down(
            op=pipeline_ops_base.UpdateSasTokenOperation(
                sas_token=self.auth_provider.get_current_sas_token(),
                callback=on_token_update_complete,
            )
        )


class TwinRequestResponseStage(PipelineStage):
    """
    PipelineStage which handles twin operations. In particular, it converts twin GET and PATCH
    operations into RequestAndResponseOperation operations.  This is done at the IoTHub level because
    there is nothing protocol-specific about this code.  The protocol-specific implementation
    for twin requests and responses is handled inside IoTHubMQTTTranslationStage, when it converts
    the RequestOperation to a protocol-specific send operation and when it converts the
    protocol-specific receive event into an ResponseEvent event.
    """

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        def map_twin_error(error, twin_op):
            if error:
                return error
            elif twin_op.status_code >= 300:
                # TODO map error codes to correct exceptions
                logger.error("Error {} received from twin operation".format(twin_op.status_code))
                logger.error("response body: {}".format(twin_op.response_body))
                return exceptions.ServiceError(
                    "twin operation returned status {}".format(twin_op.status_code)
                )

        if isinstance(op, pipeline_ops_iothub.GetTwinOperation):

            # Alias to avoid overload within the callback below
            # CT-TODO: remove the need for this with better callback semantics
            op_waiting_for_response = op

            def on_twin_response(op, error):
                logger.debug("{}({}): Got response for GetTwinOperation".format(self.name, op.name))
                error = map_twin_error(error=error, twin_op=op)
                if not error:
                    op_waiting_for_response.twin = json.loads(op.response_body.decode("utf-8"))
                op_waiting_for_response.complete(error=error)

            self.send_op_down(
                pipeline_ops_base.RequestAndResponseOperation(
                    request_type=constant.TWIN,
                    method="GET",
                    resource_location="/",
                    request_body=" ",
                    callback=on_twin_response,
                )
            )

        elif isinstance(op, pipeline_ops_iothub.PatchTwinReportedPropertiesOperation):

            # Alias to avoid overload within the callback below
            # CT-TODO: remove the need for this with better callback semantics
            op_waiting_for_response = op

            def on_twin_response(op, error):
                logger.debug(
                    "{}({}): Got response for PatchTwinReportedPropertiesOperation operation".format(
                        self.name, op.name
                    )
                )
                error = map_twin_error(error=error, twin_op=op)
                op_waiting_for_response.complete(error=error)

            logger.debug(
                "{}({}): Sending reported properties patch: {}".format(self.name, op.name, op.patch)
            )

            self.send_op_down(
                pipeline_ops_base.RequestAndResponseOperation(
                    request_type=constant.TWIN,
                    method="PATCH",
                    resource_location="/properties/reported/",
                    request_body=json.dumps(op.patch),
                    callback=on_twin_response,
                )
            )

        else:
            super(TwinRequestResponseStage, self)._run_op(op)
