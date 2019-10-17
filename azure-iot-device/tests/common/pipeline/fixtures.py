# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import threading
from tests.common.pipeline import helpers
from azure.iot.device.common import handle_exceptions
from azure.iot.device.common.pipeline import (
    pipeline_events_base,
    pipeline_ops_base,
    pipeline_thread,
)


class FakeEvent(pipeline_events_base.PipelineEvent):
    def __init__(self):
        super(FakeEvent, self).__init__()


@pytest.fixture
def arbitrary_event():
    return FakeEvent()


class FakeOperation(pipeline_ops_base.PipelineOperation):
    def __init__(self, callback=None):
        super(FakeOperation, self).__init__(callback=callback)


@pytest.fixture
def arbitrary_op(mocker):
    op = FakeOperation(callback=mocker.MagicMock())
    op.name = "arbitrary_op"
    return op


@pytest.fixture
def fake_pipeline_thread():
    """
    This fixture mocks out the thread name so that the pipeline decorators
    use to assert that you are in a pipeline thread.
    """
    this_thread = threading.current_thread()
    old_name = this_thread.name

    this_thread.name = "pipeline"
    yield
    this_thread.name = old_name


@pytest.fixture
def fake_non_pipeline_thread():
    """
    This fixture sets thread name to something other than "pipeline" to force asserts
    """
    this_thread = threading.current_thread()
    old_name = this_thread.name

    this_thread.name = "not pipeline"
    yield
    this_thread.name = old_name


@pytest.fixture
def unhandled_error_handler(mocker):
    return mocker.patch.object(handle_exceptions, "handle_background_exception")
