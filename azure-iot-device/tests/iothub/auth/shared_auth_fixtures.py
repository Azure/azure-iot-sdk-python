# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest


@pytest.fixture
def hostname():
    return "__FAKE_HOSTNAME__"


@pytest.fixture
def device_id():
    return "__FAKE_DEVICE_ID__"


@pytest.fixture
def module_id():
    return "__FAKE_MODULE__ID__"
