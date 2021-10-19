# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import copy
import collections
import json
import functools
import time
import sys
import test_config


@pytest.fixture(scope="function")
def device_id(device_identity):
    return device_identity.device_id


@pytest.fixture(scope="function")
def module_id(device_identity):
    return None


@pytest.fixture(scope="function")
def connection_retry():
    return True


@pytest.fixture(scope="function")
def auto_connect():
    return True


@pytest.fixture(scope="function")
def websockets():
    return test_config.config.transport == test_config.TRANSPORT_MQTT_WS


@pytest.fixture(scope="function")
def extra_client_kwargs():
    return {}


@pytest.fixture(scope="function")
def client_kwargs(extra_client_kwargs, auto_connect, connection_retry, websockets):
    kwargs = {}
    kwargs["auto_connect"] = auto_connect
    kwargs["connection_retry"] = connection_retry
    kwargs["websockets"] = websockets
    for key, value in extra_client_kwargs.items():
        kwargs[key] = value
    return kwargs


collect_ignore = []

# Ignore Async tests if below Python 3.5
if sys.version_info < (3, 5):
    collect_ignore.append("aio")
