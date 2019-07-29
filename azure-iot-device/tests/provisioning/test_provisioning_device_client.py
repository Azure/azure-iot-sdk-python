# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from azure.iot.device.provisioning.abstract_provisioning_device_client import (
    AbstractProvisioningDeviceClient,
)

logging.basicConfig(level=logging.INFO)


def test_raises_exception_on_init_of_abstract_client(mocker):
    fake_pipeline = mocker.MagicMock()
    with pytest.raises(TypeError):
        AbstractProvisioningDeviceClient(fake_pipeline)
