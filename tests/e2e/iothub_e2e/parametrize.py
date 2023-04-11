# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest

all_method_payload_options = [
    "include_request_payload, include_response_payload",
    [
        pytest.param(
            True,
            True,
            id="with request and response payload",
            marks=pytest.mark.quicktest_suite,
        ),
        pytest.param(True, False, id="with request payload and no response payload"),
        pytest.param(False, True, id="with response payload and no request payload "),
        pytest.param(False, False, id="with no request payload and no response payload"),
    ],
]
