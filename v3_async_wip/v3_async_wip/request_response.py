# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""Infrastructure for use implementing a high-level async request/response paradigm"""
import asyncio
import uuid
from typing import Dict


class Response:
    def __init__(self, request_id: str, status: int, body: str) -> None:
        self.request_id = request_id
        self.status = status
        self.body = body  # TODO: naming - "result"?


class Request:
    def __init__(self) -> None:
        self.request_id = str(uuid.uuid4())
        self.response_future: asyncio.Future[Response] = asyncio.Future()

    async def get_response(self) -> Response:
        return await self.response_future


class RequestLedger:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.pending: Dict[str, asyncio.Future[Response]] = {}

    def __len__(self) -> int:
        return len(self.pending)

    def __contains__(self, request_id):
        return request_id in self.pending

    async def create_request(self) -> Request:
        request = Request()
        async with self.lock:
            self.pending[request.request_id] = request.response_future
        return request

    async def delete_request(self, request_id) -> None:
        async with self.lock:
            del self.pending[request_id]

    async def match_response(self, response: Response) -> None:
        async with self.lock:
            self.pending[response.request_id].set_result(response)
            del self.pending[response.request_id]
