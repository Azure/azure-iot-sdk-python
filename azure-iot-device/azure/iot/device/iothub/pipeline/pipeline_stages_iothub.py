# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from azure.iot.device.common.pipeline import pipeline_ops_base, PipelineStage, operation_flow
from . import pipeline_ops_iothub
from . import constant


class UseSkAuthProviderStage(PipelineStage):
    """
    PipelineStage which handles operations on a Shared Key Authentication Provider.

    This stage handles SetAuthProviderOperation operations.  It parses the connection
    string into it's constituant parts and generates a sas token to pass down.  It
    uses SetAuthProviderArgsOperation to pass the connection string args and the ca_cert
    from the Authentication Provider, and it uses SetSasToken to pass down the
    generated sas token.  After passing down the args and the sas token, this stage
    completes the SetAuthProviderOperation operation.

    All other operations are passed down.
    """

    def _run_op(self, op):
        if isinstance(op, pipeline_ops_iothub.SetAuthProviderOperation):

            def pipeline_ops_done(completed_op):
                op.error = completed_op.error
                op.callback(op)

            auth_provider = op.auth_provider
            operation_flow.run_ops_in_serial(
                self,
                pipeline_ops_iothub.SetAuthProviderArgsOperation(
                    device_id=auth_provider.device_id,
                    module_id=getattr(auth_provider, "module_id", None),
                    hostname=auth_provider.hostname,
                    gateway_hostname=getattr(auth_provider, "gateway_hostname", None),
                    ca_cert=getattr(auth_provider, "ca_cert", None),
                ),
                pipeline_ops_base.SetSasTokenOperation(
                    sas_token=auth_provider.get_current_sas_token()
                ),
                callback=pipeline_ops_done,
            )
        else:
            operation_flow.pass_op_to_next_stage(self, op)


class HandleTwinOperationsStage(PipelineStage):
    """
    PipelineStage which handles twin operations. In particular, it converts twin GET and PATCH
    operations into SendIotRequestAndWaitForResponse operations.  This is done at the IoTHub level because
    there is nothing protocol-specific about this code.  The protocol-specific implementation
    for twin requests and responses is handled inside IoTHubMQTTConverterStage, when it converts
    the SendIotRequest to a protocol-specific send operation and when it converts the
    protocol-specific receive event into an IotResponseEvent event.
    """

    def _run_op(self, op):
        if isinstance(op, pipeline_ops_iothub.GetTwinOperation):

            def on_twin_response(twin_op):
                if new_op.error:
                    op.error = new_op.error
                    operation_flow.complete_op(self, op)
                else:
                    # TODO: status code check here?
                    op.twin = twin_op.response_body
                    operation_flow.complete_op(self, op)

            new_op = pipeline_ops_base.SendIotRequestAndWaitForResponseOperation(
                request_type=constant.twin,
                method="GET",
                resource_location="/",
                request_body=" ",
                callback=on_twin_response,
            )
            operation_flow.pass_op_to_next_stage(self, new_op)

        elif isinstance(op, pipeline_ops_iothub.PatchTwinReportedPropertiesOperation):
            # TODO: convert this into SendIotRequestAndWaitForResponse operation
            pass

        else:
            operation_flow.pass_op_to_next_stage(self, op)
