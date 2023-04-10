# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import asyncio
import pytest
import uuid
from azure.iot.device.request_response import Request, Response, RequestLedger


fake_request_id = str(uuid.uuid4())
fake_status = 200
fake_body = "{'data' : 'value'}"


@pytest.mark.describe("Response")
class TestResponse:
    @pytest.mark.it(
        "Instantiates with the provided request_id, status, and body stored as attributes"
    )
    def test_attributes(self):
        r = Response(request_id=fake_request_id, status=fake_status, body=fake_body)
        assert r.request_id == fake_request_id
        assert r.status == fake_status
        assert r.body == fake_body


@pytest.mark.describe("Request")
class TestRequest:
    @pytest.mark.it(
        "Instantiates with a generated UUID (in string format) as the `request_id` attribute, if no `request_id` is provided"
    )
    async def test_request_id_attr_generated(self, mocker):
        uuid4_mock = mocker.patch.object(uuid, "uuid4")
        r = Request()
        assert uuid4_mock.call_count == 1
        assert r.request_id == str(uuid4_mock.return_value)

    @pytest.mark.it(
        "Instantiates with the `request_id` attribute set to the provided `request_id`, if it is provided"
    )
    async def test_request_id_provided(self, mocker):
        my_request_id = "3226c2f7-3d30-425c-b83b-0c34335f8220"
        r = Request(request_id=my_request_id)
        assert r.request_id == my_request_id

    @pytest.mark.it(
        "Instantiates with an incomplete async Future as the `response_future` attribute"
    )
    async def test_response_future_attr(self):
        r = Request()
        assert isinstance(r.response_future, asyncio.Future)
        assert not r.response_future.done()

    @pytest.mark.it(
        "Awaits and returns the result of the `response_future` when `.get_response()` is invoked"
    )
    async def test_get_response(self):
        req = Request()
        assert not req.response_future.done()

        # .get_response() doesn't return yet
        task = asyncio.create_task(req.get_response())
        await asyncio.sleep(0.1)
        assert not task.done()

        # Add a result to the future so the task will complete
        resp = Response(request_id=req.request_id, status=fake_status, body=fake_body)
        req.response_future.set_result(resp)
        result = await task
        assert result is resp


@pytest.mark.describe("RequestLedger")
class TestRequestLedger:
    @pytest.fixture
    async def ledger(self):
        return RequestLedger()

    @pytest.mark.it("Instantiates with an empty dictionary of pending requests")
    async def test_initial_ledger(self):
        ledger = RequestLedger()
        assert isinstance(ledger.pending, dict)
        assert len(ledger.pending) == 0

    @pytest.mark.it(
        "Creates and returns a new Request, tracking it in the pending requests dictionary, for each invocation of .create_request()"
    )
    async def test_create_request(self, ledger):
        assert len(ledger.pending) == 0
        req1 = await ledger.create_request()
        assert len(ledger.pending) == 1
        req2 = await ledger.create_request()
        assert len(ledger.pending) == 2
        req3 = await ledger.create_request()
        assert len(ledger.pending) == 3

        assert ledger.pending[req1.request_id] == req1.response_future
        assert ledger.pending[req2.request_id] == req2.response_future
        assert ledger.pending[req3.request_id] == req3.response_future

    @pytest.mark.it(
        "New Requests can have their request_id provided when invoking .create_request()"
    )
    async def test_create_request_custom_id(self, ledger):
        assert len(ledger.pending) == 0
        request_id_1 = "3226c2f7-3d30-425c-b83b-0c34335f8220"
        req1 = await ledger.create_request(request_id=request_id_1)
        assert len(ledger.pending) == 1
        request_id_2 = "d9d7ce4d-3be9-498b-abde-913b81b880e5"
        req2 = await ledger.create_request(request_id=request_id_2)
        assert len(ledger.pending) == 2

        assert ledger.pending[req1.request_id] == req1.response_future
        assert ledger.pending[req2.request_id] == req2.response_future
        assert req1.request_id == request_id_1
        assert req2.request_id == request_id_2

    @pytest.mark.it(
        "Raises ValueError if the request id provided via an invocation of .create_request() is already being tracked"
    )
    async def test_create_duplicate_id(self, ledger):
        req_id = "3226c2f7-3d30-425c-b83b-0c34335f8220"
        req = await ledger.create_request(request_id=req_id)
        assert req.request_id in ledger.pending
        assert req.request_id == req_id

        with pytest.raises(ValueError):
            await ledger.create_request(request_id=req_id)

    @pytest.mark.it(
        "Removes a tracked Request from the ledger that matches the request id provided via an invocation of .delete_request()"
    )
    async def test_delete_request(self, ledger):
        req1 = await ledger.create_request()
        req2 = await ledger.create_request()
        assert req1.request_id in ledger.pending
        assert req2.request_id in ledger.pending

        await ledger.delete_request(req2.request_id)
        assert req2.request_id not in ledger.pending
        assert req1.request_id in ledger.pending
        await ledger.delete_request(req1.request_id)
        assert req1.request_id not in ledger.pending

    @pytest.mark.it(
        "Raises a KeyError if the request id provided to an invocation of .delete_request() does not match one in the ledger"
    )
    async def test_delete_request_bad_id(self, ledger):
        req1 = await ledger.create_request()
        assert req1.request_id in ledger.pending
        await ledger.delete_request(req1.request_id)
        assert req1.request_id not in ledger.pending

        with pytest.raises(KeyError):
            await ledger.delete_request(req1.request_id)

    @pytest.mark.it(
        "Completes a tracked Request and removes it from the Ledger when a Response that matches its request id is provided via an invocation of .match_response()"
    )
    async def test_match_response(self, ledger):
        assert len(ledger.pending) == 0
        req1 = await ledger.create_request()
        assert len(ledger.pending) == 1
        req2 = await ledger.create_request()
        assert len(ledger.pending) == 2
        req3 = await ledger.create_request()
        assert len(ledger.pending) == 3

        gr_task1 = asyncio.create_task(req1.get_response())
        gr_task2 = asyncio.create_task(req2.get_response())
        gr_task3 = asyncio.create_task(req3.get_response())
        await asyncio.sleep(0.1)
        assert not gr_task1.done()
        assert not gr_task2.done()
        assert not gr_task3.done()

        resp1 = Response(request_id=req1.request_id, status=fake_status, body=fake_body)
        resp2 = Response(request_id=req2.request_id, status=fake_status, body=fake_body)
        resp3 = Response(request_id=req3.request_id, status=fake_status, body=fake_body)

        await ledger.match_response(resp2)
        assert len(ledger.pending) == 2
        assert req2.request_id not in ledger.pending
        assert await gr_task2 is resp2

        await ledger.match_response(resp3)
        assert len(ledger.pending) == 1
        assert req3.request_id not in ledger.pending
        assert await gr_task3 is resp3

        await ledger.match_response(resp1)
        assert len(ledger.pending) == 0
        assert req1.request_id not in ledger.pending
        assert await gr_task1 is resp1

    @pytest.mark.it(
        "Raises a KeyError if the Response provided to an invocation of .match_response() does not have a request id that matches any tracked Request"
    )
    async def test_match_response_bad_id(self, ledger):
        req1 = await ledger.create_request()
        assert req1.request_id in ledger.pending
        await ledger.delete_request(req1.request_id)
        assert req1.request_id not in ledger.pending

        resp1 = Response(request_id=req1.request_id, status=fake_status, body=fake_body)

        with pytest.raises(KeyError):
            await ledger.match_response(resp1)

    @pytest.mark.it(
        "Implements support for len() by returning the number of pending items in the ledger"
    )
    async def test_len(self, ledger):
        assert len(ledger.pending) == 0
        assert len(ledger) == 0

        req1 = await ledger.create_request()
        assert len(ledger.pending) == len(ledger) == 1
        req2 = await ledger.create_request()
        assert len(ledger.pending) == len(ledger) == 2

        resp1 = Response(request_id=req1.request_id, status=fake_status, body=fake_body)
        await ledger.match_response(resp1)
        assert len(ledger.pending) == len(ledger) == 1
        resp2 = Response(request_id=req2.request_id, status=fake_status, body=fake_body)
        await ledger.match_response(resp2)
        assert len(ledger.pending) == len(ledger) == 0

    @pytest.mark.it("Implements support for identifying if a request_id is currently pending")
    async def test_contains(self, ledger):
        assert len(ledger) == 0

        req1 = await ledger.create_request()
        assert len(ledger) == 1
        assert req1.request_id in ledger
        req2 = await ledger.create_request()
        assert len(ledger) == 2
        assert req2.request_id in ledger

        # Remove req1 from ledger by matching
        resp = Response(request_id=req1.request_id, status=fake_status, body=fake_body)
        await ledger.match_response(resp)
        assert len(ledger) == 1
        assert req1.request_id not in ledger
        assert req2.request_id in ledger

        # Remove req2 from ledger by deletion
        await ledger.delete_request(req2.request_id)
        assert len(ledger) == 0
        assert req2.request_id not in ledger
