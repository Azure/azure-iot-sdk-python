# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from azure.iot.device.provisioning.pipeline import pipeline_ops_provisioning

all_provisioning_ops = [
    pipeline_ops_provisioning.SetSymmetricKeySecurityClientOperation,
    pipeline_ops_provisioning.SetX509SecurityClientOperation,
    pipeline_ops_provisioning.SetProvisioningClientConnectionArgsOperation,
    pipeline_ops_provisioning.RegisterOperation,
    pipeline_ops_provisioning.PollStatusOperation,
]

fake_key_values = {}
fake_key_values["request_id"] = ["request_1234", " "]
fake_key_values["retry-after"] = ["300", " "]
fake_key_values["name"] = ["hermione", " "]
