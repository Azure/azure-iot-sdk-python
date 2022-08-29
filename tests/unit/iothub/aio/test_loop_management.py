# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import asyncio
import logging
from azure.iot.device.iothub.aio import loop_management

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
