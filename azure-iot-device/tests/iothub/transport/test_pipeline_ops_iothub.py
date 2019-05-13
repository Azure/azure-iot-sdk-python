# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from azure.iot.device.iothub.transport import pipeline_ops_iothub

fake_callback = "__fake_callback__"
fake_auth_provider = "__fake_auth_provider__"
fake_device_id = "__fake_device_id__"
fake_hostname = "__fake_hostname__"
fake_module_id = "__fake_module_id__"
fake_gateway_hostname = "__fake_gateway_hostname__"
fake_ca_cert = "__fake_ca_cert__"
fake_message = "__fake_message__"


def assert_all_base_defaults(obj, needs_connection=False):
    assert obj.name is obj.__class__.__name__
    assert obj.needs_connection is needs_connection
    assert obj.error is None


@pytest.mark.describe("SetAuthProvider object")
class TestSetAuthProvider(object):
    @pytest.mark.it("Sets name attribute on instantiation")
    @pytest.mark.it("Sets error attribute to None on instantiation")
    @pytest.mark.it("Sets needs_connection attribute to False on instantiation")
    @pytest.mark.it("Sets auth_provider attribute on instantiation")
    @pytest.mark.it("Sets callback attribute to None if not provided on instantiation")
    def test_required_arguments(self):
        obj = pipeline_ops_iothub.SetAuthProvider(auth_provider=fake_auth_provider)
        assert_all_base_defaults(obj)
        assert obj.auth_provider is fake_auth_provider
        assert obj.callback is None

    @pytest.mark.it("Sets callback attribute if provided on instantiation")
    def test_optional_arguments(self):
        obj = pipeline_ops_iothub.SetAuthProvider(
            auth_provider=fake_auth_provider, callback=fake_callback
        )
        assert obj.callback is fake_callback


@pytest.mark.describe("SetAuthProviderArgs object")
class TestSetAuthProviderArgs(object):
    @pytest.mark.it("Sets name attribute on instantiation")
    @pytest.mark.it("Sets error attribute to None on instantiation")
    @pytest.mark.it("Sets needs_connection attribute to False on instantiation")
    @pytest.mark.it("Sets device_id attribute on instantiation")
    @pytest.mark.it("Sets hostname attribute on instantiation")
    @pytest.mark.it("Sets module_id attribute to None if not provided on instantiation")
    @pytest.mark.it("Sets gateway_hostname attribute to None if not provided on instantiation")
    @pytest.mark.it("Sets ca_cert attribute to None if not provided on instantiation")
    @pytest.mark.it("Sets callback attribute to None if not provided on instantiation")
    def test_required_arguments(self):
        obj = pipeline_ops_iothub.SetAuthProviderArgs(
            device_id=fake_device_id, hostname=fake_hostname
        )
        assert_all_base_defaults(obj)
        assert obj.device_id is fake_device_id
        assert obj.hostname is fake_hostname
        assert obj.callback is None

    @pytest.mark.it("Sets module_id attribute if provided on instantiation")
    @pytest.mark.it("Sets gateway_hostname attribute if provided on instantiation")
    @pytest.mark.it("Sets fake_ca_cert attribute if provided on instantiation")
    @pytest.mark.it("Sets callback attribute if provided on instantiation")
    def test_optional_arguments(self):
        obj = pipeline_ops_iothub.SetAuthProviderArgs(
            device_id=fake_device_id,
            hostname=fake_hostname,
            module_id=fake_module_id,
            gateway_hostname=fake_gateway_hostname,
            ca_cert=fake_ca_cert,
            callback=fake_callback,
        )
        assert obj.module_id is fake_module_id
        assert obj.gateway_hostname is fake_gateway_hostname
        assert obj.ca_cert is fake_ca_cert
        assert obj.callback is fake_callback


@pytest.mark.describe("SendTelemetry object")
class TestSendTelemetry(object):
    @pytest.mark.it("Sets name attribute on instantiation")
    @pytest.mark.it("Sets error attribute to None on instantiation")
    @pytest.mark.it("Sets needs_connection to True attribute on instantiation")
    @pytest.mark.it("Sets message attribute on instantiation")
    @pytest.mark.it("Sets callback attribute to None if not provided on instantiation")
    def test_required_arguments(self):
        obj = pipeline_ops_iothub.SendTelemetry(message=fake_message)
        assert_all_base_defaults(obj, needs_connection=True)
        assert obj.message is fake_message
        assert obj.callback is None

    @pytest.mark.it("Sets callback attribute if provided on instantiation")
    def test_optional_arguments(self):
        obj = pipeline_ops_iothub.SendTelemetry(message=fake_message, callback=fake_callback)
        assert obj.callback is fake_callback


@pytest.mark.describe("SendOutputEvent object")
class TestSendOutputEvent(object):
    @pytest.mark.it("Sets name attribute on instantiation")
    @pytest.mark.it("Sets error attribute on to None instantiation")
    @pytest.mark.it("Sets needs_connection attribute to True on instantiation")
    @pytest.mark.it("Sets message attribute on instantiation")
    @pytest.mark.it("Sets callback attribute to None if not provided on instantiation")
    def test_required_arguments(self):
        obj = pipeline_ops_iothub.SendOutputEvent(message=fake_message)
        assert_all_base_defaults(obj, needs_connection=True)
        assert obj.message is fake_message
        assert obj.callback is None

    @pytest.mark.it("Sets callback attribute if provided on instantiation")
    def test_optional_arguments(self):
        obj = pipeline_ops_iothub.SendOutputEvent(message=fake_message, callback=fake_callback)
        assert obj.callback is fake_callback
