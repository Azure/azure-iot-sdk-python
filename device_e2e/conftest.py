# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import concurrent.futures

# noqa: F401 defined in .flake8 file in root of repo

from drop_fixtures import dropper
from pnp_fixtures import (
    pnp_model_id,
    pnp_command_name,
    pnp_component_name,
    pnp_command_response_status,
    pnp_writable_property_name,
    pnp_read_only_property_name,
    pnp_ack_code,
    pnp_ack_description,
)
from client_fixtures import (
    client_kwargs,
    device_id,
    module_id,
    reported_props,
    watches_events,
    test_message,
)

logging.basicConfig(level=logging.WARNING)
logging.getLogger("e2e").setLevel(level=logging.DEBUG)
logging.getLogger("paho").setLevel(level=logging.DEBUG)
logging.getLogger("azure.iot").setLevel(level=logging.INFO)


@pytest.fixture(scope="module")
def transport():
    return "mqtt"


@pytest.fixture(scope="module")
def executor():
    return concurrent.futures.ThreadPoolExecutor()
