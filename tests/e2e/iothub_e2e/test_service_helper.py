# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import concurrent.futures
import threading

import pytest

from dev_utils.service_helper_sync import ServiceHelperSync


@pytest.fixture
def service_helper():
    helper = object.__new__(ServiceHelperSync)
    helper._eventhub_ready = threading.Event()
    helper._eventhub_future = concurrent.futures.Future()
    helper._eventhub_start_position = "eventhub-start-position"
    return helper


@pytest.mark.describe("ServiceHelperSync - .wait_until_ready()")
class TestWaitUntilReady(object):
    @pytest.mark.it("Returns when the Event Hub consumer is ready")
    def test_returns_when_ready(self, service_helper):
        service_helper._eventhub_ready.set()

        service_helper.wait_until_ready(timeout=0.1)

    @pytest.mark.it("Raises TimeoutError if the Event Hub consumer does not become ready")
    def test_times_out(self, service_helper):
        with pytest.raises(TimeoutError):
            service_helper.wait_until_ready(timeout=0.01)

    @pytest.mark.it("Raises the Event Hub consumer error if it exits during initialization")
    def test_raises_consumer_error(self, service_helper):
        arbitrary_exception = RuntimeError("arbitrary Event Hub failure")
        service_helper._eventhub_future.set_exception(arbitrary_exception)
        service_helper._eventhub_ready.set()

        with pytest.raises(arbitrary_exception.__class__) as e_info:
            service_helper.wait_until_ready(timeout=0.1)

        assert e_info.value is arbitrary_exception

    @pytest.mark.it("Raises RuntimeError if the Event Hub consumer exits without an error")
    def test_raises_if_consumer_exits(self, service_helper):
        service_helper._eventhub_future.set_result(None)
        service_helper._eventhub_ready.set()

        with pytest.raises(RuntimeError):
            service_helper.wait_until_ready(timeout=0.1)


@pytest.mark.describe("ServiceHelperSync - Event Hub consumer")
class TestEventHubConsumer(object):
    @pytest.mark.it("Runs on a daemon thread and exposes its result")
    def test_runs_on_daemon_thread(self, mocker, service_helper):
        eventhub_thread = mocker.patch.object(service_helper, "_eventhub_thread", return_value=None)

        future = service_helper._start_eventhub_thread()

        assert future.result(timeout=0.1) is None
        assert service_helper._eventhub_worker.daemon
        assert eventhub_thread.call_count == 1

    @pytest.mark.it("Exposes errors raised on the daemon thread")
    def test_exposes_error(self, mocker, service_helper):
        arbitrary_exception = RuntimeError("arbitrary Event Hub failure")
        mocker.patch.object(service_helper, "_eventhub_thread", side_effect=arbitrary_exception)

        future = service_helper._start_eventhub_thread()

        with pytest.raises(arbitrary_exception.__class__) as e_info:
            future.result(timeout=0.1)

        assert e_info.value is arbitrary_exception

    @pytest.mark.it("Becomes ready after the first receive cycle")
    def test_ready_after_receive(self, mocker, service_helper):
        eventhub_client = mocker.MagicMock()
        eventhub_client.__enter__.return_value = eventhub_client
        service_helper._eventhub_consumer_client = eventhub_client

        def receive_batch(**kwargs):
            kwargs["on_partition_initialize"](mocker.MagicMock())
            assert not service_helper._eventhub_ready.is_set()
            kwargs["on_event_batch"](mocker.MagicMock(), [])

        eventhub_client.receive_batch.side_effect = receive_batch

        service_helper._eventhub_thread()

        assert service_helper._eventhub_ready.is_set()
        assert (
            eventhub_client.receive_batch.call_args.kwargs["starting_position"]
            == service_helper._eventhub_start_position
        )


@pytest.mark.describe("ServiceHelperSync - .shutdown()")
class TestShutdown(object):
    @pytest.mark.it("Returns if the Event Hub receiver does not exit before the timeout")
    def test_receiver_timeout(self, mocker, service_helper):
        service_helper._eventhub_consumer_client = mocker.MagicMock()
        service_helper._eventhub_future = mocker.MagicMock()
        service_helper._eventhub_future.result.side_effect = concurrent.futures.TimeoutError()

        service_helper.shutdown()

        assert service_helper._eventhub_consumer_client.close.call_count == 1
        assert service_helper._eventhub_future.result.call_args == mocker.call(timeout=30)
