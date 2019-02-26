# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.hub.devicesdk.transport.abstract_transport import AbstractTransport


def test_raises_exception_on_init_of_abstract_transport(mocker):
    auth_provider = mocker.MagicMock
    with pytest.raises(TypeError):
        AbstractTransport(auth_provider)
