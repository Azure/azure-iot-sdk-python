# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from tests.common.pipeline.fixtures import (
    fake_pipeline_thread,
    fake_non_pipeline_thread,
    unhandled_error_handler,
    arbitrary_op,
    arbitrary_event,
)

from azure.iot.device.iothub.pipeline import constant

# Update this list with features as they are added to the SDK
# NOTE: should this be refactored into a fixture so it doesn't have to be imported?
# Is this used anywhere that DOESN'T just turn it into a fixture?
all_features = [
    constant.C2D_MSG,
    constant.INPUT_MSG,
    constant.METHODS,
    constant.TWIN,
    constant.TWIN_PATCHES,
]


@pytest.fixture(params=all_features)
def iothub_pipeline_feature(request):
    return request.param
