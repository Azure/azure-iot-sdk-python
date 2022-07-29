# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from .shared_client_fixtures import (  # noqa: F401
    mock_pipeline_init,
    provisioning_pipeline,
    registration_result,
    x509,
)


fake_status = "FakeStatus"
fake_sub_status = "FakeSubStatus"
fake_operation_id = "fake_operation_id"
fake_request_id = "request_1234"
fake_device_id = "MyDevice"
fake_assigned_hub = "MyIoTHub"
