# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest


@pytest.fixture(scope="session")
def pnp_model_id():
    return "dtmi:com:example:TemperatureController;2"


@pytest.fixture
def pnp_command_name():
    return "this_is_my_command_name"


@pytest.fixture
def pnp_component_name():
    return "this_is_my_component_name"


@pytest.fixture
def pnp_command_response_status():
    return 299


@pytest.fixture
def pnp_writable_property_name():
    return "writable_property_2"


@pytest.fixture
def pnp_read_only_property_name():
    return "read_only_property"


@pytest.fixture
def pnp_ack_code():
    return 266


@pytest.fixture
def pnp_ack_description():
    return "this is an ack description"
