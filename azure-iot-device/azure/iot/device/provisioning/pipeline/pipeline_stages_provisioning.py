# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from azure.iot.device.common.pipeline import pipeline_ops_base
from azure.iot.device.common.pipeline.pipeline_stages_base import PipelineStage
from . import pipeline_ops_provisioning


class UseSymmetricKeyOrX509SecurityClient(PipelineStage):
    """
    PipelineStage which handles operations on a Shared Key security client
    or a X509 certificate driven security client

    Operations Handled:
    * SetSymmetricKeySecurityClient
    * SetX509SecurityClient

    Operations Produced:
    * SetSecurityClientArgs
    * SetSasToken
    * SetClientAuthenticationCertificate

    This stage handles SetX509SecurityClient and SetSymmetricKeySecurityClient operations.
    For the SetX509SecurityClient it retrieves string into it's constituent parts and generates a sas token to pass down.
    It uses SetSecurityClientArgs to pass the connection string args and the ca_cert
    from the Security Client, and it uses SetSasToken to pass down the
    generated sas token.  After passing down the args and the sas token, this stage
    completes the SetSymmetricKeySecurityClient operation.

    For the SetX509SecurityClient it uses SetSecurityClientArgs to pass the connection string args and the ca_cert
    from the Security Client, and it uses SetClientAuthenticationCertificate to pass down the certificate. After passing
    down the args and the certificate token, this stage completes the SetX509SecurityClient operation.

    All other operations are passed down.
    """

    def _run_op(self, op):
        def pipeline_ops_done(completed_op):
            op.error = completed_op.error
            op.callback(op)

        if isinstance(op, pipeline_ops_provisioning.SetSymmetricKeySecurityClient):

            security_client = op.security_client
            self.run_ops_serial(
                pipeline_ops_provisioning.SetSecurityClientArgs(
                    provisioning_host=security_client.provisioning_host,
                    registration_id=security_client.registration_id,
                    id_scope=security_client.id_scope,
                ),
                pipeline_ops_base.SetSasToken(sas_token=security_client.get_current_sas_token()),
                callback=pipeline_ops_done,
            )
        elif isinstance(op, pipeline_ops_provisioning.SetX509SecurityClient):
            security_client = op.security_client
            self.run_ops_serial(
                pipeline_ops_provisioning.SetSecurityClientArgs(
                    provisioning_host=security_client.provisioning_host,
                    registration_id=security_client.registration_id,
                    id_scope=security_client.id_scope,
                ),
                pipeline_ops_base.SetClientAuthenticationCertificate(
                    certificate=security_client.get_x509_certificate()
                ),
                callback=pipeline_ops_done,
            )

        else:
            self.continue_op(op)
