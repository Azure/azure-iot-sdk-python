# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import asyncio
import concurrent.futures
import logging
import threading
from azure.iot.device.iothub.aio import loop_management
from tests.unit.helpers import BATCH_COMPLETION_TIMEOUT

logging.basicConfig(level=logging.DEBUG)


class SharedCustomLoopTests(object):
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        # Run cleanup both before and after tests so that the changes made here do not
        # impact other test modules when the tests are run as a complete suite
        loop_management._cleanup()
        yield
        loop_management._cleanup()

    @pytest.mark.it("Returns a new event loop the first time it is called")
    def test_new_loop(self, mocker, fn_under_test):
        new_event_loop_mock = mocker.patch.object(asyncio, "new_event_loop")
        loop = fn_under_test()
        assert loop is new_event_loop_mock.return_value

    @pytest.mark.it("Begins running the new event loop in a daemon Thread")
    def test_daemon_thread(self, mocker, fn_under_test):
        mock_new_event_loop = mocker.patch("asyncio.new_event_loop")
        mock_loop = mock_new_event_loop.return_value
        mock_thread_init = mocker.patch("threading.Thread")
        mock_thread = mock_thread_init.return_value
        fn_under_test()
        # Loop was created
        assert mock_new_event_loop.call_count == 1
        # Loop is running on the new Thread
        assert mock_thread_init.call_count == 1
        assert mock_thread_init.call_args == mocker.call(target=mock_loop.run_forever)
        assert mock_thread.start.call_count == 1
        # Thread is a daemon
        assert mock_thread.daemon is True

    @pytest.mark.it("Returns the same event loop each time it is called")
    def test_same_loop(self, fn_under_test):
        loop1 = fn_under_test()
        loop2 = fn_under_test()
        assert loop1 is loop2

    @pytest.mark.it("Creates only one event loop when first called concurrently")
    def test_threadsafe_first_call(self, mocker, fn_under_test):
        class CoordinatedLoopMap(dict):
            def __init__(self, loops):
                super().__init__(loops)
                self._read_barrier = threading.Barrier(2)
                self._read_lock = threading.Lock()
                self._reads_to_coordinate = 2

            def __getitem__(self, loop_name):
                loop = super().__getitem__(loop_name)
                with self._read_lock:
                    coordinate_read = self._reads_to_coordinate > 0
                    if coordinate_read:
                        self._reads_to_coordinate -= 1
                if coordinate_read:
                    self._read_barrier.wait(timeout=BATCH_COMPLETION_TIMEOUT)
                return loop

        def make_loop(loop_name):
            loop_management.loops[loop_name] = mocker.MagicMock()

        mocker.patch.object(loop_management, "loops", CoordinatedLoopMap(loop_management.loops))
        make_loop_mock = mocker.patch.object(
            loop_management, "_make_new_loop", side_effect=make_loop
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(fn_under_test) for _ in range(2)]
            returned_loops = [future.result(timeout=BATCH_COMPLETION_TIMEOUT) for future in futures]

        assert make_loop_mock.call_count == 1
        assert returned_loops[0] is returned_loops[1]


@pytest.mark.describe(".get_client_internal_loop()")
class TestGetClientInternalLoop(SharedCustomLoopTests):
    @pytest.fixture
    def fn_under_test(self):
        return loop_management.get_client_internal_loop


@pytest.mark.describe(".get_client_handler_runner_loop()")
class TestGetClientHandlerRunnerLoop(SharedCustomLoopTests):
    @pytest.fixture
    def fn_under_test(self):
        return loop_management.get_client_handler_runner_loop


@pytest.mark.describe(".get_client_handler_loop()")
class TestGetClientHandlerLoop(SharedCustomLoopTests):
    @pytest.fixture
    def fn_under_test(self):
        return loop_management.get_client_handler_loop
