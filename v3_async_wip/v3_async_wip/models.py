# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from typing import Optional


# TODO: how much of Message do we really need?
class Message:
    pass


class MethodResponse:
    def __init__(self, request_id: str, status: int, payload: Optional[str] = None):
        self.request_id = request_id
        self.status = status
        self.payload = payload  # TODO: is this really a str? or bytes? or what else?
