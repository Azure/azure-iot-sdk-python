# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest

"""
NOTE: ALL (yes, ALL) tests that use some kind of arbitrary exception should use one of the
following fixtures. This is to ensure the tests operate correctly - many tests used to
raise Exception or BaseException direclty to test arbitrary exceptions, but the result was
that exception handling was hiding other errors (also caught by an "except: Exception" block).

The solution

. The following fixtures are known to work, so for
safety, please use them ALWAYS.

You may still use exceptions defined elsewhere for non-arbitrary exceptions
(e.g. testing specific exceptions)
"""


@pytest.fixture
def fake_exception():
    class FakeException(Exception):
        pass

    return FakeException()


# @pytest.fixture
# def fake_base_exception():
#     class FakeBaseException(BaseException):
#         pass

#     return FakeBaseException()
