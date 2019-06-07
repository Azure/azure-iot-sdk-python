# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from tests.common.pipeline import helpers
from azure.iot.device.common.pipeline import pipeline_events_base


@pytest.fixture
def callback(mocker):
    return mocker.Mock()


@pytest.fixture
def fake_exception():
    return Exception()


@pytest.fixture
def fake_base_exception():
    return helpers.UnhandledException()


@pytest.fixture
def event():
    ev = pipeline_events_base.PipelineEvent()
    ev.name = "test event"
    return ev
