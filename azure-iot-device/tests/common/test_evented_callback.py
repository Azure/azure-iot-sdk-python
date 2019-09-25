# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from time import sleep
from azure.iot.device.common.evented_callback import EventedCallback

logging.basicConfig(level=logging.INFO)


@pytest.mark.describe("EventedCallback")
class TestEventedCallback(object):
    @pytest.mark.it("Can be instantiated with no args")
    def test_instantiates_without_return_arg_name(self):
        callback = EventedCallback()
        assert isinstance(callback, EventedCallback)

    @pytest.mark.it("Can be instantiated with a return_arg_name")
    def test_instantiates_with_return_arg_name(self):
        callback = EventedCallback(return_arg_name="arg_name")
        assert isinstance(callback, EventedCallback)

    @pytest.mark.it("Raises a TypeError if return_arg_name is not a string")
    def test_value_error_on_bad_return_arg_name(self):
        with pytest.raises(TypeError):
            EventedCallback(return_arg_name=1)

    @pytest.mark.it(
        "Sets the instance completion Event when a call is invoked on the instance (without return_arg_name)"
    )
    def test_calling_object_sets_event(self):
        callback = EventedCallback()
        assert not callback.completion_event.isSet()
        callback()
        sleep(0.1)  # wait to give time to complete the callback
        assert callback.completion_event.isSet()
        assert not callback.exception
        callback.wait_for_completion()

    @pytest.mark.it(
        "Sets the instance completion Event when a call is invoked on the instance (with return_arg_name)"
    )
    def test_calling_object_sets_event_with_return_arg_name(self, fake_return_arg_value):
        callback = EventedCallback(return_arg_name="arg_name")
        assert not callback.completion_event.isSet()
        callback(arg_name=fake_return_arg_value)
        sleep(0.1)  # wait to give time to complete the callback
        assert callback.completion_event.isSet()
        assert not callback.exception
        assert callback.wait_for_completion() == fake_return_arg_value

    @pytest.mark.it(
        "Raises a TypeError when a call is invoked on the instance without the correct return argument (with return_arg_name)"
    )
    def test_calling_object_raises_exception_if_return_arg_is_missing(self, fake_return_arg_value):
        callback = EventedCallback(return_arg_name="arg_name")
        with pytest.raises(TypeError):
            callback()

    @pytest.mark.it(
        "Causes an error to be raised from the wait call when an error parameter is passed to the call (without return_arg_name)"
    )
    def test_raises_error_without_return_arg_name(self, fake_exception):
        callback = EventedCallback()
        assert not callback.completion_event.isSet()
        callback(error=fake_exception)
        sleep(0.1)  # wait to give time to complete the callback
        assert callback.completion_event.isSet()
        assert callback.exception == fake_exception
        with pytest.raises(fake_exception.__class__) as e_info:
            callback.wait_for_completion()
        assert e_info.value is fake_exception

    @pytest.mark.it(
        "Causes an error to be raised from the wait call when an error parameter is passed to the call (with return_arg_name)"
    )
    def test_raises_error_with_return_arg_name(self, fake_exception):
        callback = EventedCallback(return_arg_name="arg_name")
        assert not callback.completion_event.isSet()
        callback(error=fake_exception)
        sleep(0.1)  # wait to give time to complete the callback
        assert callback.completion_event.isSet()
        assert callback.exception == fake_exception
        with pytest.raises(fake_exception.__class__) as e_info:
            callback.wait_for_completion()
        assert e_info.value is fake_exception
