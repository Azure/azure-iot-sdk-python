# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import sys
from azure.iot.device.common.pipeline import (
    pipeline_stages_base,
    pipeline_ops_base,
    pipeline_events_base,
    operation_flow,
)
from tests.common.pipeline.helpers import (
    make_mock_stage,
    assert_callback_failed,
    assert_callback_succeeded,
    UnhandledException,
    all_common_ops,
    all_common_events,
)
from tests.common.pipeline import pipeline_stage_test

logging.basicConfig(level=logging.INFO)

this_module = sys.modules[__name__]

pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_base.EnsureConnectionStage,
    module=this_module,
    all_ops=all_common_ops,
    handled_ops=[
        pipeline_ops_base.ConnectOperation,
        pipeline_ops_base.DisconnectOperation,
        pipeline_ops_base.EnableFeatureOperation,
        pipeline_ops_base.DisableFeatureOperation,
    ],
    all_events=all_common_events,
    handled_events=[],
)

pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_base.CoordinateRequestAndResponseStage,
    module=this_module,
    all_ops=all_common_ops,
    handled_ops=[pipeline_ops_base.SendIotRequestAndWaitForResponseOperation],
    all_events=all_common_events,
    handled_events=[pipeline_events_base.IotResponseEvent],
)
