# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from azure.iot.device.common.pipeline import pipeline_ops_base, PipelineStage
from . import pipeline_ops_iothub
from . import constant


class UseSkAuthProvider(PipelineStage):
    """
    PipelineStage which handles operations on a Shared Key Authentication Provider.

    Operations Handled:
    * SetAuthProvider

    Operations Produced:
    * SetAuthProviderArgs
    * SetSasToken

    This stage handles SetAuthProvider operations.  It parses the connection
    string into it's constituant parts and generates a sas token to pass down.  It
    uses SetAuthProviderArgs to pass the connection string args and the ca_cert
    from the Authentication Provider, and it uses SetSasToken to pass down the
    generated sas token.  After passing down the args and the sas token, this stage
    completes the SetAuthProvider operation.

    All other operations are passed down.
    """

    def _run_op(self, op):
        if isinstance(op, pipeline_ops_iothub.SetAuthProvider):

            def pipeline_ops_done(completed_op):
                op.error = completed_op.error
                op.callback(op)

            auth_provider = op.auth_provider
            self.run_ops_serial(
                pipeline_ops_iothub.SetAuthProviderArgs(
                    device_id=auth_provider.device_id,
                    module_id=getattr(auth_provider, "module_id", None),
                    hostname=auth_provider.hostname,
                    gateway_hostname=getattr(auth_provider, "gateway_hostname", None),
                    ca_cert=getattr(auth_provider, "ca_cert", None),
                ),
                pipeline_ops_base.SetSasToken(sas_token=auth_provider.get_current_sas_token()),
                callback=pipeline_ops_done,
            )
        else:
            self.continue_op(op)


class HandleTwinOperations(PipelineStage):
    """
    PipelineStage which handles twin operations. In particular, it converts twin GET and PATCH
    operations into SendIotRequestAndWaitForResponse operations.  This is done at the IotHub level because
    there is nothing transport-specific about this code.  The transport-specific implementation
    for twin requests and responses is handled inside IotHubMQTTConverter, when it converts
    the SendIotRequest to a transport-specific send operation and when it converts the
    transport-specific receive event into an IotResponseEvent event.
    """

    def _run_op(self, op):
        if isinstance(op, pipeline_ops_iothub.GetTwin):

            def on_twin_response(twin_op):
                if new_op.error:
                    op.error = new_op.error
                    self.complete_op(op)
                else:
                    # TODO: status code check here?
                    op.twin = twin_op.response_body
                    self.complete_op(op)

            new_op = pipeline_ops_base.SendIotRequestAndWaitForResponse(
                request_type=constant.twin,
                method="GET",
                resource_location="/",
                request_body=" ",
                callback=on_twin_response,
            )
            self.continue_op(new_op)

        elif isinstance(op, pipeline_ops_iothub.PatchTwinReportedProperties):
            # TODO: convert this into SendIotRequestAndWaitForResponse operation
            pass

        else:
            self.continue_op(op)
