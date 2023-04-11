# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
""" NOTE: This module will not be necessary anymore once these tests are moved
to the main testing directory"""

import pytest


@pytest.fixture
def arbitrary_exception():
    class ArbitraryException(Exception):
        pass

    e = ArbitraryException("arbitrary description")
    return e
