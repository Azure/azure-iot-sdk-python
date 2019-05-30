# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from azure.iot.device.provisioning.pipeline import pipeline_ops_provisioning

fake_registration_id = "registered_remembrall"
fake_provisioning_host = "hogwarts.com"
fake_id_scope = "weasley_wizard_wheezes"
fake_security_client = "secure_via_muffliato"
fake_request_id = "fake_request_1234"
fake_payload = "hello hogwarts"
fake_operation_id = "fake_operation_9876"


@pytest.fixture
def mock_callback(mocker):
    return mocker.Mock()


def assert_all_base_defaults(obj, needs_connection=False):
    assert obj.name is obj.__class__.__name__
    assert obj.needs_connection is needs_connection
    assert obj.error is None


@pytest.mark.describe("SetSymmetricKeySecurityClient")
class TestSetSymmetricKeySecurityClient(object):
    @pytest.mark.it(
        "Sets name , error, needs_connection, security_client, callback on instantiation"
    )
    def test_required_arguments(self):
        obj = pipeline_ops_provisioning.SetSymmetricKeySecurityClient(
            security_client=fake_security_client
        )
        assert_all_base_defaults(obj)
        assert obj.security_client is fake_security_client
        assert obj.callback is None

    @pytest.mark.it("Sets callback attribute if provided on instantiation")
    def test_optional_arguments(self):
        obj = pipeline_ops_provisioning.SetSymmetricKeySecurityClient(
            security_client=fake_security_client, callback=mock_callback
        )
        assert obj.callback is mock_callback


@pytest.mark.describe("SetSymmetricKeySecurityClientArgs")
class TestSetSymmetricKeySecurityClientArgs(object):
    @pytest.mark.it(
        "Sets name , error, needs_connection, provisioning_host, "
        "registration_id, id_scope, callback on instantiation"
    )
    def test_required_arguments(self):
        obj = pipeline_ops_provisioning.SetSymmetricKeySecurityClientArgs(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
        )
        assert_all_base_defaults(obj)
        assert obj.provisioning_host is fake_provisioning_host
        assert obj.registration_id is fake_registration_id
        assert obj.id_scope is fake_id_scope
        assert obj.callback is None

    @pytest.mark.it("Sets callback attribute if provided on instantiation")
    def test_optional_arguments(self):
        obj = pipeline_ops_provisioning.SetSymmetricKeySecurityClientArgs(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
            callback=mock_callback,
        )
        assert obj.callback is mock_callback


@pytest.mark.describe("SendRegistrationRequest")
class TestSendRegistrationRequest(object):
    @pytest.mark.it(
        "Sets name , error, needs_connection, rid, " "request_payload callback on instantiation"
    )
    def test_required_arguments(self):
        obj = pipeline_ops_provisioning.SendRegistrationRequest(
            rid=fake_request_id, request_payload=fake_payload
        )
        assert_all_base_defaults(obj, True)
        assert obj.rid is fake_request_id
        assert obj.request_payload is fake_payload
        assert obj.callback is None

    @pytest.mark.it("Sets callback attribute if provided on instantiation")
    def test_optional_arguments(self):
        obj = pipeline_ops_provisioning.SendRegistrationRequest(
            rid=fake_request_id, request_payload=fake_payload, callback=mock_callback
        )
        assert obj.callback is mock_callback


@pytest.mark.describe("SendQueryRequest")
class TestSendQueryRequest(object):
    @pytest.mark.it(
        "Sets name , error, needs_connection, rid, operation_id "
        "request_payload callback on instantiation"
    )
    def test_required_arguments(self):
        obj = pipeline_ops_provisioning.SendQueryRequest(
            rid=fake_request_id, operation_id=fake_operation_id, request_payload=fake_payload
        )
        assert_all_base_defaults(obj, True)
        assert obj.rid is fake_request_id
        assert obj.request_payload is fake_payload
        assert obj.operation_id is fake_operation_id
        assert obj.callback is None

    @pytest.mark.it("Sets callback attribute if provided on instantiation")
    def test_optional_arguments(self):
        obj = pipeline_ops_provisioning.SendQueryRequest(
            rid=fake_request_id,
            operation_id=fake_operation_id,
            request_payload=fake_payload,
            callback=mock_callback,
        )
        assert obj.callback is mock_callback
