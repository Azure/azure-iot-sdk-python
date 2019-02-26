# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from mock import MagicMock, patch
from threading import Timer
from azure.iot.hub.devicesdk.auth.base_renewable_token_authentication_provider import (
    BaseRenewableTokenAuthenticationProvider,
    DEFAULT_TOKEN_VALIDITY_PERIOD,
    DEFAULT_TOKEN_RENEWAL_MARGIN,
)

fake_signature = "__FAKE_SIGNATURE__"
fake_hostname = "__FAKE_HOSTNAME__"
fake_device_id = "__FAKE_DEVICE_ID__"
fake_module_id = "__FAKE_MODULE_ID__"
fake_current_time = 123456
fake_device_resource_uri = "{}%2Fdevices%2F{}".format(fake_hostname, fake_device_id)
fake_module_resource_uri = "{}%2Fdevices%2F{}%2Fmodules%2F{}".format(
    fake_hostname, fake_device_id, fake_module_id
)
fake_device_token_base = "SharedAccessSignature sr={}&sig={}&se=".format(
    fake_device_resource_uri, fake_signature
)
fake_module_token_base = "SharedAccessSignature sr={}&sig={}&se=".format(
    fake_module_resource_uri, fake_signature
)
new_token_validity_period = 8675
new_token_renewal_margin = 309


class FakeAuthProvider(BaseRenewableTokenAuthenticationProvider):
    def __init__(self, hostname, device_id, module_id):
        BaseRenewableTokenAuthenticationProvider.__init__(self, hostname, device_id, module_id)
        self._sign = MagicMock(return_value=fake_signature)

    def _sign(self, quoted_resource_uri, expiry):
        pass

    def parse(source):
        pass


@pytest.fixture(scope="function")
def device_auth_provider():
    auth_provider = FakeAuthProvider(fake_hostname, fake_device_id, None)
    yield auth_provider
    auth_provider.disconnect()


@pytest.fixture(scope="function")
def module_auth_provider():
    auth_provider = FakeAuthProvider(fake_hostname, fake_device_id, fake_module_id)
    yield auth_provider
    auth_provider.disconnect()


@pytest.fixture(scope="function")
def fake_get_current_time_function():
    with patch(
        "azure.iot.hub.devicesdk.auth.base_renewable_token_authentication_provider.time.time",
        MagicMock(return_value=fake_current_time),
    ):
        yield


@pytest.fixture(scope="function")
def fake_timer_object():
    with patch(
        "azure.iot.hub.devicesdk.auth.base_renewable_token_authentication_provider.Timer",
        MagicMock(spec=Timer),
    ) as PatchedTimer:
        yield PatchedTimer


def test_device_get_current_sas_token_generates_and_returns_new_sas_token(
    device_auth_provider, fake_get_current_time_function
):
    token = device_auth_provider.get_current_sas_token()
    assert device_auth_provider._sign.call_count == 1
    assert token == fake_device_token_base + str(fake_current_time + DEFAULT_TOKEN_VALIDITY_PERIOD)


def test_module_get_current_sas_token_generates_and_returns_new_sas_token(
    module_auth_provider, fake_get_current_time_function
):
    token = module_auth_provider.get_current_sas_token()
    assert module_auth_provider._sign.call_count == 1
    assert token == fake_module_token_base + str(fake_current_time + DEFAULT_TOKEN_VALIDITY_PERIOD)


def test_get_current_sas_token_returns_existing_sas_token(device_auth_provider):
    token1 = device_auth_provider.get_current_sas_token()
    token2 = device_auth_provider.get_current_sas_token()
    assert device_auth_provider._sign.call_count == 1
    assert token1 == token2


def test_generate_new_sas_token_calls_token_update_callback_when_sas_udpates(device_auth_provider):
    update_callback = MagicMock()
    device_auth_provider.token_update_callback = update_callback
    device_auth_provider.generate_new_sas_token()
    update_callback.assert_called_once_with()


def test_device_generate_new_sas_token_calls_sign_with_correct_default_args(
    device_auth_provider, fake_get_current_time_function
):
    device_auth_provider.generate_new_sas_token()
    resource_uri = device_auth_provider._sign.call_args[0][0]
    expiry = device_auth_provider._sign.call_args[0][1]
    assert resource_uri == fake_device_resource_uri
    assert expiry == fake_current_time + DEFAULT_TOKEN_VALIDITY_PERIOD


def test_module_generate_new_sas_token_calls_sign_with_correct_default_args(
    module_auth_provider, fake_get_current_time_function
):
    module_auth_provider.generate_new_sas_token()
    resource_uri = module_auth_provider._sign.call_args[0][0]
    expiry = module_auth_provider._sign.call_args[0][1]
    assert resource_uri == fake_module_resource_uri
    assert expiry == fake_current_time + DEFAULT_TOKEN_VALIDITY_PERIOD


def test_generate_new_sas_token_calls_sign_with_correct_modified_expiry(
    device_auth_provider, fake_get_current_time_function
):
    device_auth_provider.token_validity_period = new_token_validity_period
    device_auth_provider.token_renewal_margin = new_token_renewal_margin
    device_auth_provider.generate_new_sas_token()
    expiry = device_auth_provider._sign.call_args[0][1]
    assert expiry == fake_current_time + new_token_validity_period


def test_generate_new_sas_token_schedules_update_timer_with_correct_default_timeout(
    device_auth_provider, fake_timer_object
):
    device_auth_provider.generate_new_sas_token()
    assert (
        fake_timer_object.call_args[0][0]
        == DEFAULT_TOKEN_VALIDITY_PERIOD - DEFAULT_TOKEN_RENEWAL_MARGIN
    )


def test_generate_new_sas_token_cancels_and_reschedules_update_timer_with_correct_modified_timeout(
    device_auth_provider, fake_timer_object
):
    device_auth_provider.token_validity_period = new_token_validity_period
    device_auth_provider.token_renewal_margin = new_token_renewal_margin
    device_auth_provider.generate_new_sas_token()
    assert fake_timer_object.call_args[0][0] == new_token_validity_period - new_token_renewal_margin


def test_update_timer_generates_new_sas_token_and_calls_token_update_callback(
    device_auth_provider, fake_timer_object
):
    update_callback = MagicMock()
    device_auth_provider.generate_new_sas_token()
    device_auth_provider.token_update_callback = update_callback
    timer_callback = fake_timer_object.call_args[0][1]
    device_auth_provider._sign.reset_mock()
    timer_callback()
    update_callback.assert_called_once_with()
    assert device_auth_provider._sign.call_count == 1


def test_disconnect_cancels_update_timer(device_auth_provider, fake_timer_object):
    device_auth_provider.generate_new_sas_token()
    device_auth_provider.disconnect()
    fake_timer_object.return_value.cancel.assert_called_once_with()
