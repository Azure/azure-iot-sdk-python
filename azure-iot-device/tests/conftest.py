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
def unexpected_exception():
    class UnexpectedException(Exception):
        pass

    return UnexpectedException()


@pytest.fixture
def unexpected_base_exception():
    class UnexpectedBaseException(BaseException):
        pass

    return UnexpectedBaseException()
