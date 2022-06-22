# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import threading
from azure.iot.device.common.pipeline import (
    pipeline_events_base,
    pipeline_ops_base,
    pipeline_nucleus,
)


class ArbitraryEvent(pipeline_events_base.PipelineEvent):
    def __init__(self):
        super().__init__()


@pytest.fixture
def arbitrary_event():
    return ArbitraryEvent()


class ArbitraryOperation(pipeline_ops_base.PipelineOperation):
    def __init__(self, callback=None):
        super().__init__(callback=callback)


@pytest.fixture
def arbitrary_op(mocker):
    op = ArbitraryOperation(callback=mocker.MagicMock())
    mocker.spy(op, "complete")
    return op


@pytest.fixture
def pipeline_connected_mock(mocker):
    """This mock can have it's return value altered by any test to indicate whether or not the
    pipeline is connected (boolean).

    Because this fixture is used by the nucleus fixture, and the nucleus is the single source of
    truth for connection, changing this fixture's return value will change the connection state
    of any other aspect of the pipeline (assuming it is using the nucleus fixture).

    This has to be it's own fixture, because due to how PropertyMocks work, you can't access them
    on an instance of an object like you can, say, the mocked settings on a PipelineConfiguration
    """
    p = mocker.PropertyMock()
    return p


@pytest.fixture
def nucleus(mocker, pipeline_connected_mock):
    """This fixture can be used to configure stages. Connection status can be mocked
    via the above pipeline_connected_mock, but by default .connected will return a real value.
    This nucleus will also come configured with a mocked pipeline configuration, which can be
    overridden if necessary
    """
    # Need to use a mock for pipeline config because we don't know
    # what type of config is being used since these are common
    nucleus = pipeline_nucleus.PipelineNucleus(pipeline_configuration=mocker.MagicMock())

    # By default, set the connected mock to return the real connected value
    # (this can be overridden by changing the return value of pipeline_connected_mock)
    def dynamic_return():
        if not isinstance(pipeline_connected_mock.return_value, mocker.Mock):
            return pipeline_connected_mock.return_value
        return nucleus.connection_state is pipeline_nucleus.ConnectionState.CONNECTED

    pipeline_connected_mock.side_effect = dynamic_return
    type(nucleus).connected = pipeline_connected_mock

    return nucleus


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
