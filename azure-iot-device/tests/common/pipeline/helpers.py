# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import inspect
import pytest
import functools
from threading import Event
from azure.iot.device.common import config
from azure.iot.device.common.pipeline import (
    pipeline_events_base,
    pipeline_ops_base,
    pipeline_stages_base,
    pipeline_events_mqtt,
    pipeline_ops_mqtt,
)

try:
    from inspect import getfullargspec as getargspec
except ImportError:
    from inspect import getargspec

all_common_ops = [
    pipeline_ops_base.ConnectOperation,
    pipeline_ops_base.ReconnectOperation,
    pipeline_ops_base.DisconnectOperation,
    pipeline_ops_base.EnableFeatureOperation,
    pipeline_ops_base.DisableFeatureOperation,
    pipeline_ops_base.UpdateSasTokenOperation,
    pipeline_ops_base.SendIotRequestAndWaitForResponseOperation,
    pipeline_ops_base.SendIotRequestOperation,
    pipeline_ops_mqtt.SetMQTTConnectionArgsOperation,
    pipeline_ops_mqtt.MQTTPublishOperation,
    pipeline_ops_mqtt.MQTTSubscribeOperation,
    pipeline_ops_mqtt.MQTTUnsubscribeOperation,
]

all_common_events = [pipeline_events_mqtt.IncomingMQTTMessageEvent]


def all_except(all_items, items_to_exclude):
    """
    helper function to return a new list with all ops that are in the first list
    and not in the second list.

    :param list all_items: list of all operations or events
    :param list items_to_exclude: ops or events to exclude
    """
    return [x for x in all_items if x not in items_to_exclude]


class StageTestBase(object):
    @pytest.fixture(autouse=True)
    def stage_base_configuration(self, stage, mocker):
        """
        This fixture configures the stage for testing.  This is automatically
        applied, so it will be called before your test runs, but it's not
        guaranteed to be called before any other fixtures run.  If you have
        a fixture that needs to rely on the stage being configured, then
        you have to add a manual dependency inside that fixture (like we do in
        next_stage_succeeds_all_ops below)
        """

        class NextStageForTest(pipeline_stages_base.PipelineStage):
            def _execute_op(self, op):
                pass

        next = NextStageForTest()
        root = (
            pipeline_stages_base.PipelineRootStage(config.BasePipelineConfig())
            .append_stage(stage)
            .append_stage(next)
        )

        mocker.spy(stage, "_execute_op")
        mocker.spy(stage, "run_op")

        mocker.spy(next, "_execute_op")
        mocker.spy(next, "run_op")

        return root

    @pytest.fixture
    def next_stage_succeeds(self, stage, stage_base_configuration, mocker):
        stage.next._execute_op = stage.complete_op
        mocker.spy(stage.next, "_execute_op")

    @pytest.fixture
    def next_stage_raises_arbitrary_exception(
        self, stage, stage_base_configuration, mocker, arbitrary_exception
    ):
        stage.next._execute_op = mocker.MagicMock(side_effect=arbitrary_exception)

    @pytest.fixture
    def next_stage_raises_arbitrary_base_exception(
        self, stage, stage_base_configuration, mocker, arbitrary_base_exception
    ):
        stage.next._execute_op = mocker.MagicMock(side_effect=arbitrary_base_exception)


def assert_callback_succeeded(op, callback=None):
    if not callback:
        callback = op.callback
    try:
        # if the callback has a __wrapped__ attribute, that means that the
        # pipeline added a wrapper around the callback, so we want to look
        # at the original function instead of the wrapped function.
        callback = callback.__wrapped__
    except AttributeError:
        pass
    assert callback.call_count == 1
    callback_op_arg = callback.call_args[0][0]
    assert callback_op_arg == op
    callback_error_arg = callback.call_args[1]["error"]
    assert callback_error_arg is None


def assert_callback_failed(op, callback=None, error=None):
    if not callback:
        callback = op.callback
    try:
        # if the callback has a __wrapped__ attribute, that means that the
        # pipeline added a wrapper around the callback, so we want to look
        # at the original function instead of the wrapped function.
        callback = callback.__wrapped__
    except AttributeError:
        pass
    assert callback.call_count == 1
    callback_op_arg = callback.call_args[0][0]
    assert callback_op_arg == op

    callback_error_arg = callback.call_args[1]["error"]
    if error:
        if isinstance(error, type):
            assert callback_error_arg.__class__ == error
        else:
            assert callback_error_arg is error
    else:
        assert callback_error_arg is not None


def get_arg_count(fn):
    """
    return the number of arguments (args) passed into a
    particular function.  Returned value does not include kwargs.
    """
    try:
        # if __wrapped__ is set, we're looking at a decorated function
        # Functools.wraps doesn't copy arg metadata, so we need to
        # get argument count from the wrapped function instead.
        return len(getargspec(fn.__wrapped__).args)
    except AttributeError:
        return len(getargspec(fn).args)


def make_mock_op_or_event(cls):
    args = [None for i in (range(get_arg_count(cls.__init__) - 1))]
    return cls(*args)


def add_mock_method_waiter(obj, method_name):
    """
    For mock methods, add "wait_for_xxx_to_be_called" and "wait_for_xxx_to_not_be_called"
    helper functions on the object.  This is very handy for methods that get called by
    another thread, when you want your test functions to wait until the other thread is
    able to call the method without using a sleep call.
    """
    method_called = Event()

    def signal_method_called(*args, **kwargs):
        method_called.set()

    def wait_for_method_to_be_called():
        method_called.wait(0.1)
        assert method_called.isSet()
        method_called.clear()

    def wait_for_method_to_not_be_called():
        method_called.wait(0.1)
        assert not method_called.isSet()

    getattr(obj, method_name).side_effect = signal_method_called
    setattr(obj, "wait_for_{}_to_be_called".format(method_name), wait_for_method_to_be_called)
    setattr(
        obj, "wait_for_{}_to_not_be_called".format(method_name), wait_for_method_to_not_be_called
    )
