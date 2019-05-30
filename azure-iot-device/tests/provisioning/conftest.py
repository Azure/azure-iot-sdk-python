# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import pytest

# These fixtures are shared between sync and async clients
from tests.common.pipeline_test_fixtures import callback, fake_error, event

collect_ignore = []
