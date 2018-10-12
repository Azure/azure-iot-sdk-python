# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------


class AMQPWrapper(object):
    def __init__(self, client_id, hostname):
        self._client_id = client_id
        self._hostname = hostname
