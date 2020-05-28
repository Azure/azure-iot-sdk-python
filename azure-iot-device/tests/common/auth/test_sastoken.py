# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import time
import re
import logging
import six.moves.urllib as urllib
from azure.iot.device.common.auth.sastoken import SasToken, SasTokenError

logging.basicConfig(level=logging.DEBUG)

fake_uri = "some/resource/location"
fake_signed_data = "ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI="
fake_key_name = "fakekeyname"


def token_parser(token_str):
    """helper function that parses a token string for indvidual values"""
    token_map = {}
    kv_string = token_str.split(" ")[1]
    kv_pairs = kv_string.split("&")
    for kv in kv_pairs:
        t = kv.split("=")
        token_map[t[0]] = t[1]
    return token_map


@pytest.fixture
def signing_mechanism(mocker):
    mechanism = mocker.MagicMock()
    mechanism.sign.return_value = fake_signed_data
    return mechanism


# TODO: Rename this. These are not "device" and "service" tokens, the distinction is more generic
@pytest.fixture(params=["Device Token", "Service Token"])
def sastoken(request, signing_mechanism):
    token_type = request.param
    if token_type == "Device Token":
        return SasToken(uri=fake_uri, signing_mechanism=signing_mechanism)
    elif token_type == "Service Token":
        return SasToken(uri=fake_uri, signing_mechanism=signing_mechanism, key_name=fake_key_name)


@pytest.mark.describe("SasToken")
class TestSasToken(object):
    @pytest.mark.it("Instantiates with a default TTL of 3600 seconds if no TTL is provided")
    def test_default_ttl(self, signing_mechanism):
        s = SasToken(fake_uri, signing_mechanism)
        assert s.ttl == 3600

    @pytest.mark.it("Instantiates with a custom TTL if provided")
    def test_custom_ttl(self, signing_mechanism):
        custom_ttl = 4747
        s = SasToken(fake_uri, signing_mechanism, ttl=custom_ttl)
        assert s.ttl == custom_ttl

    @pytest.mark.it("Instantiates with with no key name by default if no key name is provided")
    def test_default_key_name(self, signing_mechanism):
        s = SasToken(fake_uri, signing_mechanism)
        assert s._key_name is None

    @pytest.mark.it("Instantiates with the given key name if provided")
    def test_custom_key_name(self, signing_mechanism):
        s = SasToken(fake_uri, signing_mechanism, key_name=fake_key_name)
        assert s._key_name == fake_key_name

    @pytest.mark.it(
        "Instantiates with an expiry time TTL seconds in the future from the moment of instantiation"
    )
    def test_expiry_time(self, mocker, signing_mechanism):
        fake_current_time = 1000
        mocker.patch.object(time, "time", return_value=fake_current_time)

        s = SasToken(fake_uri, signing_mechanism)
        assert s.expiry_time == fake_current_time + s.ttl

    @pytest.mark.it("Calls .refresh() to build the SAS token string on instantiation")
    def test_refresh_on_instantiation(self, mocker, signing_mechanism):
        refresh_mock = mocker.spy(SasToken, "refresh")
        assert refresh_mock.call_count == 0
        SasToken(fake_uri, signing_mechanism)
        assert refresh_mock.call_count == 1

    @pytest.mark.it("Returns the SAS token string as the string representation of the object")
    def test_str_rep(self, sastoken):
        assert str(sastoken) == sastoken._token

    @pytest.mark.it(
        "Maintains the .expiry_time attribute as a read-only property (raises AttributeError upon attempt)"
    )
    def test_expiry_time_read_only(self, sastoken):
        with pytest.raises(AttributeError):
            sastoken.expiry_time = 12321312


@pytest.mark.describe("SasToken - .refresh()")
class TestSasTokenRefresh(object):
    @pytest.mark.it("Sets a new expiry time of TTL seconds in the future")
    def test_new_expiry(self, mocker, sastoken):
        fake_current_time = 1000
        mocker.patch.object(time, "time", return_value=fake_current_time)
        sastoken.refresh()
        assert sastoken.expiry_time == fake_current_time + sastoken.ttl

    # TODO: reflect url encoding here?
    @pytest.mark.it(
        "Uses the token's signing mechanism to create a signature by signing a concatenation of the (URL encoded) URI and updated expiry time"
    )
    def test_generate_new_token(self, mocker, signing_mechanism, sastoken):
        old_token_str = str(sastoken)
        fake_future_time = 1000
        mocker.patch.object(time, "time", return_value=fake_future_time)
        signing_mechanism.reset_mock()
        fake_signature = "new_fake_signature"
        signing_mechanism.sign.return_value = fake_signature

        sastoken.refresh()

        # The token string has been updated
        assert str(sastoken) != old_token_str
        # The signing mechanism was used to sign a string
        assert signing_mechanism.sign.call_count == 1
        # The string being signed was a concatenation of the URI and expiry time
        assert signing_mechanism.sign.call_args == mocker.call(
            urllib.parse.quote(sastoken._uri, safe="") + "\n" + str(sastoken.expiry_time)
        )
        # The token string has the resulting signed string included as the signature
        token_info = token_parser(str(sastoken))
        assert token_info["sig"] == fake_signature

    @pytest.mark.it(
        "Builds a new token string using the token's URI (URL encoded) and expiry time, along with the signature created by the signing mechanism (also URL encoded)"
    )
    def test_token_string(self, sastoken):
        token_str = sastoken._token

        # Verify that token string representation matches token format
        if not sastoken._key_name:
            pattern = re.compile(r"SharedAccessSignature sr=(.+)&sig=(.+)&se=(.+)")
        else:
            pattern = re.compile(r"SharedAccessSignature sr=(.+)&sig=(.+)&se=(.+)&skn=(.+)")
        assert pattern.match(token_str)

        # Verify that content in the string representation is correct
        token_info = token_parser(token_str)
        assert token_info["sr"] == urllib.parse.quote(sastoken._uri, safe="")
        assert token_info["sig"] == urllib.parse.quote(
            sastoken._signing_mechanism.sign.return_value, safe=""
        )
        assert token_info["se"] == str(sastoken.expiry_time)
        if sastoken._key_name:
            assert token_info["skn"] == sastoken._key_name

    @pytest.mark.it("Raises a SasTokenError if an exception is raised by the signing mechanism")
    def test_signing_mechanism_raises_value_error(
        self, mocker, signing_mechanism, sastoken, arbitrary_exception
    ):
        signing_mechanism.sign.side_effect = arbitrary_exception

        with pytest.raises(SasTokenError) as e_info:
            sastoken.refresh()
        assert e_info.value.__cause__ is arbitrary_exception
