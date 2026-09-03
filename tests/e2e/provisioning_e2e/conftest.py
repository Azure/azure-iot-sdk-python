# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.

import pytest

import dev_utils.leak_tracker as leak_tracker_module


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call():
    """
    Check that DPS client objects are released after each registration test.

    Successful registration shuts down the provisioning pipeline before returning. The leak check
    runs after the test frame is released so test-local clients and results do not cause false
    positives.
    """
    # DPS clients are created after this baseline, so allowing a "replacement" object would hide
    # a real leak rather than suppress a false positive.
    tracker = leak_tracker_module.LeakTracker()
    tracker.track_module("azure.iot.device")
    tracker.track_module("paho")
    tracker.set_initial_object_list()

    result = yield

    tracker.check_for_leaks()
    return result
