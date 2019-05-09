# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from azure.iot.device.common.transport import pipeline_ops_base

fake_callback = "__fake_callback__"
fake_feature_name = "__fake_feature_name__"


def assert_all_base_defaults(obj):
    assert obj.name is obj.__class__.__name__
    assert obj.needs_connection is False
    assert obj.error is None


@pytest.mark.describe("PipelineOperation object")
class TestPipelineOperation(object):
    @pytest.mark.it("Sets required and default arguments correctly")
    def test_required_arguments(self):
        obj = pipeline_ops_base.PipelineOperation()
        assert_all_base_defaults(obj)
        assert obj.callback is None

    @pytest.mark.it("Sets optional arguments correctly")
    def test_optional_arguments(self):
        obj = pipeline_ops_base.PipelineOperation(callback=fake_callback)
        assert_all_base_defaults(obj)
        assert obj.callback is fake_callback


@pytest.mark.describe("Connect object")
class TestConnect(object):
    @pytest.mark.it("Sets required and default arguments correctly")
    def test_required_arguments(self):
        obj = pipeline_ops_base.Connect()
        assert_all_base_defaults(obj)
        assert obj.callback is None

    @pytest.mark.it("Sets optional arguments correctly")
    def test_optional_arguments(self):
        obj = pipeline_ops_base.Connect(callback=fake_callback)
        assert_all_base_defaults(obj)
        assert obj.callback is fake_callback


@pytest.mark.describe("Disconnect object")
class TestDisconnect(object):
    @pytest.mark.it("Sets required and default arguments correctly")
    def test_required_arguments(self):
        obj = pipeline_ops_base.Disconnect()
        assert_all_base_defaults(obj)
        assert obj.callback is None

    @pytest.mark.it("Sets optional arguments correctly")
    def test_optional_arguments(self):
        obj = pipeline_ops_base.Disconnect(callback=fake_callback)
        assert_all_base_defaults(obj)
        assert obj.callback is fake_callback


@pytest.mark.describe("Reconnect object")
class TestReconnect(object):
    @pytest.mark.it("Sets required and default arguments correctly")
    def test_required_arguments(self):
        obj = pipeline_ops_base.Reconnect()
        assert_all_base_defaults(obj)
        assert obj.callback is None

    @pytest.mark.it("Sets optional arguments correctly")
    def test_optional_arguments(self):
        obj = pipeline_ops_base.Reconnect(callback=fake_callback)
        assert_all_base_defaults(obj)
        assert obj.callback is fake_callback


@pytest.mark.describe("EnableFeature object")
class TestEnableFeature(object):
    @pytest.mark.it("Sets required and default arguments correctly")
    def test_required_arguments(self):
        obj = pipeline_ops_base.EnableFeature(feature_name=fake_feature_name)
        assert_all_base_defaults(obj)
        assert obj.callback is None
        assert obj.feature_name is fake_feature_name

    @pytest.mark.it("Sets optional arguments correctly")
    def test_optional_arguments(self):
        obj = pipeline_ops_base.EnableFeature(
            feature_name=fake_feature_name, callback=fake_callback
        )
        assert_all_base_defaults(obj)
        assert obj.callback is fake_callback


@pytest.mark.describe("DisableFeature object")
class TestDisableFeature(object):
    @pytest.mark.it("Sets required and default arguments correctly")
    def test_required_arguments(self):
        obj = pipeline_ops_base.DisableFeature(feature_name=fake_feature_name)
        assert_all_base_defaults(obj)
        assert obj.callback is None
        assert obj.feature_name is fake_feature_name

    @pytest.mark.it("Sets optional arguments correctly")
    def test_optional_arguments(self):
        obj = pipeline_ops_base.DisableFeature(
            feature_name=fake_feature_name, callback=fake_callback
        )
        assert_all_base_defaults(obj)
        assert obj.callback is fake_callback
