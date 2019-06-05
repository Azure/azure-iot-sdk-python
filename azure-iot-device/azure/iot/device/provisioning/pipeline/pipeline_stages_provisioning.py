# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
from azure.iot.device.common.pipeline import pipeline_ops_base
from azure.iot.device.common.pipeline.pipeline_stages_base import PipelineStage
from . import pipeline_ops_provisioning


class UseSymmetricKeySecurityClient(PipelineStage):
    """
    PipelineStage which handles operations on a Shared Key Authentication Provider.

    Operations Handled:
    * SetSymmetricKeySecurityClient

    Operations Produced:
    * SetSymmetricKeySecurityClientArgs
    * SetSasToken

    This stage handles SetSymmetricKeySecurityClient operations. It retrieves
    string into it's constituent parts and generates a sas token to pass down.  It
    uses SetAuthProviderArgs to pass the connection string args and the ca_cert
    from the Authentication Provider, and it uses SetSasToken to pass down the
    generated sas token.  After passing down the args and the sas token, this stage
    completes the SetAuthProvider operation.

    All other operations are passed down.
    """

    def _run_op(self, op):
        if isinstance(op, pipeline_ops_provisioning.SetSymmetricKeySecurityClient):

            def pipeline_ops_done(completed_op):
                op.error = completed_op.error
                op.callback(op)

            security_client = op.security_client
            self.run_ops_serial(
                pipeline_ops_provisioning.SetSymmetricKeySecurityClientArgs(
                    provisioning_host=security_client.provisioning_host,
                    registration_id=security_client.registration_id,
                    id_scope=security_client.id_scope,
                ),
                pipeline_ops_base.SetSasToken(sas_token=security_client.get_current_sas_token()),
                callback=pipeline_ops_done,
            )
        else:
            self.continue_op(op)
