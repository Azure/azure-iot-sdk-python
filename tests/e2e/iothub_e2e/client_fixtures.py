# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import test_config


@pytest.fixture(scope="function")
def device_id(device_identity):
    return device_identity.device_id


@pytest.fixture(scope="function")
def module_id(device_identity):
    return None


@pytest.fixture(scope="function")
def connection_retry(request):
    # let tests use @pytest.mark.connection_retry(x) to set connection_retry
    marker = request.node.get_closest_marker("connection_retry")
    if marker:
        return marker.args[0]
    else:
        return True


@pytest.fixture(scope="function")
def auto_connect(request):
    # let tests use @pytest.mark.auto_connect(x) to set auto_connect
    marker = request.node.get_closest_marker("auto_connect")
    if marker:
        return marker.args[0]
    else:
        return True


@pytest.fixture(scope="function")
def websockets():
    return test_config.config.transport == test_config.TRANSPORT_MQTT_WS


@pytest.fixture(scope="function")
def keep_alive(request):
    # let tests use @pytest.mark.keep_alive(x) to set keep_alive
    marker = request.node.get_closest_marker("keep_alive")
    if marker:
        return marker.args[0]
    else:
        return None


@pytest.fixture(scope="function")
def sastoken_ttl(request):
    # let tests use @pytest.mark.sastoken_ttl(x) to set sas token ttl
    marker = request.node.get_closest_marker("sastoken_ttl")
    if marker:
        return marker.args[0]
    else:
        return None
    return None


@pytest.fixture(scope="function")
def client_kwargs(auto_connect, connection_retry, websockets, keep_alive, sastoken_ttl):
    kwargs = {}
    kwargs["auto_connect"] = auto_connect
    kwargs["connection_retry"] = connection_retry
    kwargs["websockets"] = websockets
    if keep_alive is not None:
        kwargs["keep_alive"] = keep_alive
    if sastoken_ttl is not None:
        kwargs["sastoken_ttl"] = sastoken_ttl
    return kwargs
