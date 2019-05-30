# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from azure.iot.device.common.pipeline import pipeline_ops_base

fake_callback = "__fake_callback__"
fake_feature_name = "__fake_feature_name__"


def assert_all_base_defaults(obj, needs_connections):
    assert obj.name is obj.__class__.__name__
    assert obj.needs_connection is needs_connections
    assert obj.error is None


@pytest.mark.describe("PipelineOperation object")
class TestPipelineOperation(object):
    @pytest.mark.it("Sets name attribute on instantiation")
    @pytest.mark.it("Sets error attribute to None on instantiation")
    @pytest.mark.it("Sets needs_connection attribute to False on instantiation")
    @pytest.mark.it("Sets callback attribute to None if not provided on instantiation")
    def test_required_arguments(self):
        obj = pipeline_ops_base.PipelineOperation()
        assert_all_base_defaults(obj, False)
        assert obj.callback is None

    @pytest.mark.it("Sets callback attribute if provided on instantiation")
    def test_optional_arguments(self):
        obj = pipeline_ops_base.PipelineOperation(callback=fake_callback)
        assert obj.callback is fake_callback


@pytest.mark.describe("Connect object")
class TestConnect(object):
    @pytest.mark.it("Sets name attribute on instantiation")
    @pytest.mark.it("Sets error attribute to None on instantiation")
    @pytest.mark.it("Sets needs_connection attribute to False on instantiation")
    @pytest.mark.it("Sets callback attribute to None if not provided on instantiation")
    def test_required_arguments(self):
        obj = pipeline_ops_base.Connect()
        assert_all_base_defaults(obj, False)
        assert obj.callback is None

    @pytest.mark.it("Sets callback attribute if provided on instantiation")
    def test_optional_arguments(self):
        obj = pipeline_ops_base.Connect(callback=fake_callback)
        assert obj.callback is fake_callback


@pytest.mark.describe("Disconnect object")
class TestDisconnect(object):
    @pytest.mark.it("Sets name attribute on instantiation")
    @pytest.mark.it("Sets error attribute to None on instantiation")
    @pytest.mark.it("Sets needs_connection attribute to False on instantiation")
    @pytest.mark.it("Sets callback attribute to None if not provided on instantiation")
    def test_required_arguments(self):
        obj = pipeline_ops_base.Disconnect()
        assert_all_base_defaults(obj, False)
        assert obj.callback is None

    @pytest.mark.it("Sets callback attribute if provided on instantiation")
    def test_optional_arguments(self):
        obj = pipeline_ops_base.Disconnect(callback=fake_callback)
        assert obj.callback is fake_callback


@pytest.mark.describe("Reconnect object")
class TestReconnect(object):
    @pytest.mark.it("Sets name attribute on instantiation")
    @pytest.mark.it("Sets error attribute to None on instantiation")
    @pytest.mark.it("Sets needs_connection attribute to False on instantiation")
    @pytest.mark.it("Sets callback attribute to None if not provided on instantiation")
    def test_required_arguments(self):
        obj = pipeline_ops_base.Reconnect()
        assert_all_base_defaults(obj, False)
        assert obj.callback is None

    @pytest.mark.it("Sets callback attribute if provided on instantiation")
    def test_optional_arguments(self):
        obj = pipeline_ops_base.Reconnect(callback=fake_callback)
        assert obj.callback is fake_callback


@pytest.mark.describe("EnableFeature object")
class TestEnableFeature(object):
    @pytest.mark.it("Sets name attribute on instantiation")
    @pytest.mark.it("Sets error attribute to None on instantiation")
    @pytest.mark.it("Sets needs_connection attribute to False on instantiation")
    @pytest.mark.it("Sets feature_name attribute on instantiation")
    @pytest.mark.it("Sets callback attribute to None if not provided on instantiation")
    def test_required_arguments(self):
        obj = pipeline_ops_base.EnableFeature(feature_name=fake_feature_name)
        assert_all_base_defaults(obj, True)
        assert obj.callback is None
        assert obj.feature_name is fake_feature_name

    @pytest.mark.it("Sets callback attribute if provided on instantiation")
    def test_optional_arguments(self):
        obj = pipeline_ops_base.EnableFeature(
            feature_name=fake_feature_name, callback=fake_callback
        )
        assert obj.callback is fake_callback


@pytest.mark.describe("DisableFeature object")
class TestDisableFeature(object):
    @pytest.mark.it("Sets name attribute on instantiation")
    @pytest.mark.it("Sets error attribute to None on instantiation")
    @pytest.mark.it("Sets needs_connection attribute to False on instantiation")
    @pytest.mark.it("Sets feature_name attribute on instantiation")
    @pytest.mark.it("Sets callback attribute to None if not provided on instantiation")
    def test_required_arguments(self):
        obj = pipeline_ops_base.DisableFeature(feature_name=fake_feature_name)
        assert_all_base_defaults(obj, True)
        assert obj.callback is None
        assert obj.feature_name is fake_feature_name

    @pytest.mark.it("Sets callback attribute if provided on instantiation")
    def test_optional_arguments(self):
        obj = pipeline_ops_base.DisableFeature(
            feature_name=fake_feature_name, callback=fake_callback
        )
        assert obj.callback is fake_callback
