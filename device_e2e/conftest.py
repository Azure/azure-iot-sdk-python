# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import concurrent.futures
import test_config

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
    extra_client_kwargs,
    auto_connect,
    connection_retry,
    websockets,
    device_id,
    module_id,
    reported_props,
    watches_events,
    random_message,
)

logging.basicConfig(level=logging.WARNING)
logging.getLogger("e2e").setLevel(level=logging.DEBUG)
logging.getLogger("paho").setLevel(level=logging.DEBUG)
logging.getLogger("azure.iot").setLevel(level=logging.DEBUG)


@pytest.fixture(scope="module")
def transport():
    return test_config.config.transport


@pytest.fixture(scope="module")
def executor():
    return concurrent.futures.ThreadPoolExecutor()


def pytest_addoption(parser):
    parser.addoption(
        "--transport",
        help="Transport to use for tests",
        type=str,
        choices=test_config.TRANSPORT_CHOICES,
        default=test_config.TRANSPORT_MQTT,
    )
    parser.addoption(
        "--auth",
        help="Auth to use for tests",
        type=str,
        choices=test_config.AUTH_CHOICES,
        default=test_config.AUTH_CONNECTION_STRING,
    )
    parser.addoption(
        "--identity",
        help="Identity (client type) to use for tests",
        type=str,
        choices=test_config.IDENTITY_CHOICES,
        default=test_config.IDENTITY_DEVICE_CLIENT,
    )


def pytest_configure(config):
    test_config.config.transport = config.getoption("transport")
    test_config.config.auth = config.getoption("auth")
    test_config.config.identity = config.getoption("identity")
