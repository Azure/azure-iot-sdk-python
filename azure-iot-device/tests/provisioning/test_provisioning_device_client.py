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

logging.basicConfig(level=logging.DEBUG)


class Wizard(object):
    def __init__(self, first_name, last_name, dict_of_stuff):
        self.first_name = first_name
        self.last_name = last_name
        self.props = dict_of_stuff


def test_raises_exception_on_init_of_abstract_client(mocker):
    fake_pipeline = mocker.MagicMock()
    with pytest.raises(TypeError):
        AbstractProvisioningDeviceClient(fake_pipeline)
