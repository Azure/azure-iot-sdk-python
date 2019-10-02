# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest

"""
NOTE: ALL (yes, ALL) tests need some kind of non-specific, arbitrary exception should use
one of the following fixtures. This is to ensure the tests operate correctly - many tests used to
raise Exception or BaseException directly to test arbitrary exceptions, but the result was
that exception handling was hiding other errors (also caught by an "except: Exception" block).

The solution is to use a subclass of Exception or BaseException that is not defined anywhere else,
thus guaranteeing that it will be unexpected and unhandled except by broad all-encompassing
handling. Furthermore, because the exception in question is derived from either Exception or
BaseException, but is not itself an instance of either, tests checking that the exception in
question is raised will not spuriously pass due to different exceptions being raised.

For consistency, and to prevent confusion, please do this ONLY by using one of the follwing
fxitures.

You may (and should!) still use exceptions defined elsewhere for specific, non-arbitrary exceptions
(e.g. testing specific exceptions)
"""


@pytest.fixture
def unexpected_exception():
    class UnexpectedException(Exception):
        pass

    e = UnexpectedException()
    return e


@pytest.fixture
def unexpected_base_exception():
    class UnexpectedBaseException(BaseException):
        pass

    return UnexpectedBaseException()
