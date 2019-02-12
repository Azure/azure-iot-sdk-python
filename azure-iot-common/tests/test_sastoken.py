# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import pytest
import time
import base64
import hmac
import hashlib
import copy
import six.moves.urllib as urllib
from azure.iot.common.sastoken import SasToken, SasTokenError

uri = "my.host.name"
key = "Zm9vYmFy"
key_name = "mykeyname"
device_token_kwargs = {"uri": uri, "key": key}
service_token_kwargs = {"uri": uri, "key": key, "key_name": key_name}


def generate_signature(uri, key, expiry_time):
    message = (uri + "\n" + str(expiry_time)).encode("utf-8")
    signing_key = base64.b64decode(key.encode("utf-8"))
    signed_hmac = hmac.HMAC(signing_key, message, hashlib.sha256)
    signature = urllib.parse.quote(base64.b64encode(signed_hmac.digest()))
    return signature


@pytest.fixture(params=["Device Token", "Service Token"])
def sastoken(request):
    token_type = request.param
    if token_type == "Device Token":
        return SasToken(uri, key)
    elif token_type == "Service Token":
        return SasToken(uri, key, key_name)


class TestSasToken(object):
    @pytest.mark.parametrize(
        "kwargs",
        [
            pytest.param(device_token_kwargs, id="Device Token"),
            pytest.param(service_token_kwargs, id="Service Token"),
        ],
    )
    def test_instantiates_with_default_ttl_3600(self, kwargs):
        s = SasToken(**kwargs)
        assert s._uri == kwargs.get("uri")
        assert s._key == kwargs.get("key")
        assert s._key_name == kwargs.get("key_name")
        assert s.ttl == 3600

    @pytest.mark.parametrize(
        "kwargs",
        [
            pytest.param(device_token_kwargs, id="Device Token"),
            pytest.param(service_token_kwargs, id="Service Token"),
        ],
    )
    def test_instantiates_with_custom_ttl(self, kwargs):
        kwargs = copy.copy(kwargs)
        kwargs["ttl"] = 9000
        s = SasToken(**kwargs)
        assert s._uri == kwargs.get("uri")
        assert s._key == kwargs.get("key")
        assert s._key_name == kwargs.get("key_name")
        assert s.ttl == 9000

    def test_url_encodes_utf8_characters_in_uri(self):
        utf8_uri = "my châteu.host.name"
        s = SasToken(utf8_uri, key)

        expected_uri = "my+ch%C3%A2teu.host.name"
        assert s._uri == expected_uri

    def test_raises_sastoken_error_if_key_is_not_base64(self):
        non_b64_key = "this is not base64"
        with pytest.raises(SasTokenError):
            SasToken(uri, non_b64_key)

    @pytest.mark.parametrize(
        "sastoken,token_pattern",
        [
            pytest.param(
                "Device Token", "SharedAccessSignature sr={}&sig={}&se={}", id="Device Token"
            ),
            pytest.param(
                "Service Token",
                "SharedAccessSignature sr={}&sig={}&se={}&skn={}",
                id="Service Token",
            ),
        ],
        indirect=["sastoken"],
    )
    def test_string_conversion_returns_expected_sastoken_string(self, sastoken, token_pattern):
        signature = generate_signature(sastoken._uri, sastoken._key, sastoken.expiry_time)
        if sastoken._key_name:
            expected_string = token_pattern.format(
                sastoken._uri, signature, sastoken.expiry_time, sastoken._key_name
            )
        else:
            expected_string = token_pattern.format(sastoken._uri, signature, sastoken.expiry_time)
        strrep = str(sastoken)
        assert strrep == expected_string

    def test_refreshing_token_extends_expiry_time(self, sastoken):
        old_expiry = sastoken.expiry_time
        time.sleep(1)
        sastoken.refresh()
        new_expiry = sastoken.expiry_time
        assert new_expiry > old_expiry

    def test_refreshing_token_sets_expiry_time_to_be_ttl_seconds_in_the_future(
        self, mocker, sastoken
    ):
        current_time = 1000
        mocker.patch.object(time, "time", return_value=current_time)
        sastoken.refresh()
        assert sastoken.expiry_time == current_time + sastoken.ttl

    def test_refreshing_token_changes_string_representation(self, sastoken):
        # This should happen because refreshing updates expiry time
        old_token_string = str(sastoken)
        time.sleep(1)
        sastoken.refresh()
        new_token_string = str(sastoken)
        assert old_token_string != new_token_string


pytest.main()
