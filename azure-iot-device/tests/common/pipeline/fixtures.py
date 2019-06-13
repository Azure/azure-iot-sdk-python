# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from tests.common.pipeline import helpers
from azure.iot.device.common.pipeline import pipeline_events_base, pipeline_ops_base


@pytest.fixture
def callback(mocker):
    return mocker.Mock()


@pytest.fixture
def fake_exception():
    return Exception()


@pytest.fixture
def fake_base_exception():
    return helpers.UnhandledException()


class FakeEvent(pipeline_events_base.PipelineEvent):
    def __init__(self):
        super(FakeEvent, self).__init__()


@pytest.fixture
def event():
    return FakeEvent()


class FakeOperation(pipeline_ops_base.PipelineOperation):
    def __init__(self, callback=None):
        super(FakeOperation, self).__init__(callback=callback)


@pytest.fixture
def op():
    op = FakeOperation()
    op.name = "op"
    return op


@pytest.fixture
def op2():
    op = FakeOperation()
    op.name = "op2"
    return op


@pytest.fixture
def op3():
    op = FakeOperation()
    op.name = "op3"
    return op


@pytest.fixture
def finally_op():
    op = FakeOperation()
    op.name = "finally_op"
    return op


@pytest.fixture
def new_op():
    op = FakeOperation()
    op.name = "new_op"
    return op
