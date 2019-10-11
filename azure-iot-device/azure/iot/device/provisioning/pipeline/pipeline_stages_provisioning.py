# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from azure.iot.device.common.pipeline import pipeline_ops_base, pipeline_thread
from azure.iot.device.common.pipeline.pipeline_stages_base import PipelineStage
from . import pipeline_ops_provisioning


class UseSecurityClientStage(PipelineStage):
    """
    PipelineStage which extracts relevant SecurityClient values for a new
    SetProvisioningClientConnectionArgsOperation.

    All other operations are passed down.
    """

    @pipeline_thread.runs_on_pipeline_thread
    def _execute_op(self, op):
        if isinstance(op, pipeline_ops_provisioning.SetSymmetricKeySecurityClientOperation):

            security_client = op.security_client
            self._send_worker_op_down(
                worker_op=pipeline_ops_provisioning.SetProvisioningClientConnectionArgsOperation(
                    provisioning_host=security_client.provisioning_host,
                    registration_id=security_client.registration_id,
                    id_scope=security_client.id_scope,
                    sas_token=security_client.get_current_sas_token(),
                    callback=op.callback,
                ),
                op=op,
            )

        elif isinstance(op, pipeline_ops_provisioning.SetX509SecurityClientOperation):
            security_client = op.security_client
            self._send_worker_op_down(
                worker_op=pipeline_ops_provisioning.SetProvisioningClientConnectionArgsOperation(
                    provisioning_host=security_client.provisioning_host,
                    registration_id=security_client.registration_id,
                    id_scope=security_client.id_scope,
                    client_cert=security_client.get_x509_certificate(),
                    callback=op.callback,
                ),
                op=op,
            )

        else:
            self._send_op_down(op)
