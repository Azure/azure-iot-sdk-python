# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import sys

collect_ignore = []

# Ignore Async tests if below Python 3.5.3
if sys.version_info < (3, 5, 3):
    collect_ignore.append("test_async_adapter.py")
    collect_ignore.append("test_asyncio_compat.py")


@pytest.fixture
def fake_return_arg_value():
    return "__fake_return_arg_value__"
