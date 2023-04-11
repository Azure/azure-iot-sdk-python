# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""Infrastructure for use implementing a high-level async request/response paradigm"""
import asyncio
import uuid
from typing import Dict, Optional


class Response:
    def __init__(
        self, request_id: str, status: int, body: str, properties: Optional[dict] = None
    ) -> None:
        self.request_id = request_id
        self.status = status
        self.body = body  # TODO: naming - "result"?
        self.properties = properties


class Request:
    def __init__(self, request_id: Optional[str] = None) -> None:
        if request_id:
            self.request_id = request_id
        else:
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

    async def create_request(self, request_id: Optional[str] = None) -> Request:
        request = Request(request_id=request_id)
        async with self.lock:
            if request.request_id not in self.pending:
                self.pending[request.request_id] = request.response_future
            else:
                raise ValueError("Provided request_id is a duplicate")
        return request

    async def delete_request(self, request_id) -> None:
        async with self.lock:
            del self.pending[request_id]

    async def match_response(self, response: Response) -> None:
        async with self.lock:
            self.pending[response.request_id].set_result(response)
            del self.pending[response.request_id]
