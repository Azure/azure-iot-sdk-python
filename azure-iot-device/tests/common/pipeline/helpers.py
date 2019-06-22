# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import inspect
import pytest
import functools
from azure.iot.device.common.pipeline import (
    pipeline_events_base,
    pipeline_ops_base,
    pipeline_stages_base,
    pipeline_events_mqtt,
    pipeline_ops_mqtt,
    operation_flow,
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
    pipeline_ops_base.SetSasTokenOperation,
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


def make_mock_stage(mocker, stage_to_make):
    """
    make a stage object that we can use in testing.  This stage object is popsulated
    by mocker spies, and it has a next stage that can receive events.  It does not,
    by detfault, have a previous stage or a pipeline root that can receive events
    coming back up.  The previous stage is added by the tests which which require it.
    """
    # because PipelineStage is abstract, we need something concrete
    class NextStageForTest(pipeline_stages_base.PipelineStage):
        def _run_op(self, op):
            operation_flow.pass_op_to_next_stage(self, op)

    def stage_run_op(self, op):
        if getattr(op, "action", None) is None or op.action == "pass":
            operation_flow.complete_op(self, op)
        elif op.action == "fail" or op.action == "exception":
            raise Exception()
        elif op.action == "base_exception":
            raise UnhandledException()
        elif op.action == "pend":
            pass
        else:
            assert False

    first_stage = stage_to_make()
    first_stage.unhandled_error_handler = mocker.Mock()
    mocker.spy(first_stage, "_run_op")
    mocker.spy(first_stage, "run_op")

    next_stage = NextStageForTest()
    next_stage._run_op = functools.partial(stage_run_op, next_stage)
    mocker.spy(next_stage, "_run_op")
    mocker.spy(next_stage, "run_op")

    first_stage.next = next_stage
    first_stage.pipeline_root = first_stage

    next_stage.previous = first_stage
    next_stage.pipeline_root = first_stage

    return first_stage


def assert_callback_succeeded(op, callback=None):
    if not callback:
        callback = op.callback
    assert callback.call_count == 1
    callback_arg = callback.call_args[0][0]
    assert callback_arg == op
    assert op.error is None


def assert_callback_failed(op, callback=None, error=None):
    if not callback:
        callback = op.callback
    assert callback.call_count == 1
    callback_arg = callback.call_args[0][0]
    assert callback_arg == op

    if error:
        assert op.error is error
    else:
        assert op.error is not None


class UnhandledException(BaseException):
    pass


def get_arg_count(fn):
    """
    return the number of arguments (args) passed into a
    particular function.  Returned value not include kwargs.
    """
    return len(getargspec(fn).args)


def make_mock_op_or_event(cls):
    args = [None for i in (range(get_arg_count(cls.__init__) - 1))]
    return cls(*args)
