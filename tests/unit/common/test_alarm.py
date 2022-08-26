# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import logging
import time
from azure.iot.device.common.alarm import Alarm

logging.basicConfig(level=logging.DEBUG)

# NOTE: A fundamental aspect of the Alarm class that makes it different from Timer (beyond the
# input format) is that sleeping the system will not throw off the timekeeping. However, there
# isn't a great way to test that in unit tests, because to do so would involve a system sleep.
# So note well that these tests would pass the same if using a Timer implementation, because the
# thing that makes Alarms unique isn't tested here.


@pytest.mark.describe("Alarm")
class TestAlarm(object):
    @pytest.fixture
    def desired_function(self, mocker):
        return mocker.MagicMock()

    @pytest.mark.it(
        "Invokes the given function with the given args and kwargs at the given alarm time once started"
    )
    @pytest.mark.parametrize(
        "args", [pytest.param(["arg1", "arg2"], id="W/ args"), pytest.param([], id="No args")]
    )
    @pytest.mark.parametrize(
        "kwargs",
        [
            pytest.param({"kwarg1": "value1", "kwarg2": "value2"}, id="W/ kwargs"),
            pytest.param({}, id="No kwargs"),
        ],
    )
    def test_fn_called_w_args(self, mocker, desired_function, args, kwargs):
        alarm_time = time.time() + 2  # call fn in 2 seconds
        a = Alarm(alarm_time=alarm_time, function=desired_function, args=args, kwargs=kwargs)
        a.start()

        assert desired_function.call_count == 0
        time.sleep(1)  # hasn't been 2 seconds yet
        assert desired_function.call_count == 0
        time.sleep(1.1)  # it has now been just over 2 seconds, so the call HAS been made
        assert desired_function.call_count == 1
        assert desired_function.call_args == mocker.call(*args, **kwargs)

    @pytest.mark.it("Invokes the function with no args or kwargs by default if none are provided")
    def test_fn_called_no_args(self, mocker, desired_function):
        alarm_time = time.time() + 1  # call fn in 1 seconds
        a = Alarm(alarm_time=alarm_time, function=desired_function)
        a.start()

        assert desired_function.call_count == 0
        time.sleep(1.1)  # it has now been just over 1 second, so the call HAS been made
        assert desired_function.call_count == 1
        desired_function.call_args == mocker.call()

    @pytest.mark.it("Invokes the function immediately if the given alarm time is in the past")
    def test_alarm_already_expired(self, mocker, desired_function):
        alarm_time = time.time() - 1
        a = Alarm(alarm_time=alarm_time, function=desired_function)
        a.start()

        assert desired_function.call_count == 1

    @pytest.mark.it(
        "Does not invoke the given function at the given alarm time if the alarm was cancelled before the given alarm time"
    )
    def test_cancel_alarm(self, mocker, desired_function):
        alarm_time = time.time() + 2  # call fn in 2 seconds
        a = Alarm(alarm_time=alarm_time, function=desired_function)
        a.start()

        assert desired_function.call_count == 0
        time.sleep(1)  # hasn't been 2 seconds yet
        assert desired_function.call_count == 0
        a.cancel()  # cancel the alarm
        time.sleep(1.5)  # it has now been more than 2 seconds
        assert desired_function.call_count == 0  # still not called
