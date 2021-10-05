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
import const
from azure.iot.device.iothub import Message
from utils import get_random_message, get_random_dict
from azure.iot.device.iothub import IoTHubDeviceClient


@pytest.fixture(scope="class")
def client_kwargs():
    return {}


@pytest.fixture(scope="function")
def device_id(brand_new_client):
    # TODO: suggest adding device_id and module_id to client object
    return brand_new_client._mqtt_pipeline._pipeline.pipeline_configuration.device_id


@pytest.fixture(scope="function")
def module_id(brand_new_client):
    return brand_new_client._mqtt_pipeline._pipeline.pipeline_configuration.module_id


@pytest.fixture(scope="function")
def reported_props():
    return {const.TEST_CONTENT: get_random_dict()}


@pytest.fixture(scope="function")
def watches_events(service_helper, device_id, module_id):
    service_helper.start_watching(device_id, module_id)
    yield
    service_helper.stop_watching(device_id, module_id)


@pytest.fixture(scope="function")
def random_message():
    return get_random_message()


collect_ignore = []

# Ignore Async tests if below Python 3.5
if sys.version_info < (3, 5):
    collect_ignore.append("aio")
