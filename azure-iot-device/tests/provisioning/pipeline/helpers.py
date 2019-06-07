# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from azure.iot.device.provisioning.pipeline import (
    pipeline_events_provisioning,
    pipeline_ops_provisioning,
)

all_provisioning_ops = [
    [pipeline_ops_provisioning.SetSymmetricKeySecurityClient, [None]],
    [
        pipeline_ops_provisioning.SetSymmetricKeySecurityClientArgs,
        ["hogwarts.com", "remembrall", "anyone_inside_hogwarts"],
    ],
    [
        pipeline_ops_provisioning.SendRegistrationRequest,
        ["fake_request_1234", "assemble the order of phoenix"],
    ],
    [
        pipeline_ops_provisioning.SendQueryRequest,
        ["fake_request_1234", "fake_operation_9876", "hello hogwarts"],
    ],
]

fake_key_values = {}
fake_key_values["request_id"] = ["request_1234", " "]
fake_key_values["retry-after"] = ["300", " "]
fake_key_values["name"] = ["hermione", " "]

all_provisioning_events = [
    [
        pipeline_events_provisioning.RegistrationResponseEvent,
        ["request_1234", "999", fake_key_values, "expecto patronum"],
    ]
]
