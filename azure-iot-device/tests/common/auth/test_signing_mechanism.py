# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
import hmac
import hashlib
import base64
from azure.iot.device.common.auth import SymmetricKeySigningMechanism

logging.basicConfig(level=logging.DEBUG)


@pytest.mark.describe("SymmetricKeySigningMechanism - Instantiation")
class TestSymmetricKeySigningMechanismInstantiation(object):
    @pytest.mark.it(
        "Derives and stores the signing key from the provided symmetric key by base64 decoding it"
    )
    @pytest.mark.parametrize(
        "key, expected_signing_key",
        [
            pytest.param(
                "NMgJDvdKTxjLi+xBxxkDDEwDJxEvOE5u8BiT0mVgPeg=",
                b"4\xc8\t\x0e\xf7JO\x18\xcb\x8b\xecA\xc7\x19\x03\x0cL\x03'\x11/8Nn\xf0\x18\x93\xd2e`=\xe8",
                id="Example 1",
            ),
            pytest.param(
                "zqtyZCGuKg/UHvSzgYnNod/uHChWrzGGtHSgPi4cC2U=",
                b"\xce\xabrd!\xae*\x0f\xd4\x1e\xf4\xb3\x81\x89\xcd\xa1\xdf\xee\x1c(V\xaf1\x86\xb4t\xa0>.\x1c\x0be",
                id="Example 2",
            ),
        ],
    )
    def test_dervies_signing_key(self, key, expected_signing_key):
        sm = SymmetricKeySigningMechanism(key)
        assert sm._signing_key == expected_signing_key

    @pytest.mark.it("Supports symmetric keys in both string and byte formats")
    @pytest.mark.parametrize(
        "key, expected_signing_key",
        [
            pytest.param(
                "NMgJDvdKTxjLi+xBxxkDDEwDJxEvOE5u8BiT0mVgPeg=",
                b"4\xc8\t\x0e\xf7JO\x18\xcb\x8b\xecA\xc7\x19\x03\x0cL\x03'\x11/8Nn\xf0\x18\x93\xd2e`=\xe8",
                id="String",
            ),
            pytest.param(
                b"NMgJDvdKTxjLi+xBxxkDDEwDJxEvOE5u8BiT0mVgPeg=",
                b"4\xc8\t\x0e\xf7JO\x18\xcb\x8b\xecA\xc7\x19\x03\x0cL\x03'\x11/8Nn\xf0\x18\x93\xd2e`=\xe8",
                id="Bytes",
            ),
        ],
    )
    def test_supported_types(self, key, expected_signing_key):
        sm = SymmetricKeySigningMechanism(key)
        assert sm._signing_key == expected_signing_key

    @pytest.mark.it("Raises a ValueError if the provided symmetric key is invalid")
    @pytest.mark.parametrize(
        "key",
        [pytest.param("not a key", id="Not a key"), pytest.param("YWJjx", id="Incomplete key")],
    )
    def test_invalid_key(self, key):
        with pytest.raises(ValueError):
            SymmetricKeySigningMechanism(key)


@pytest.mark.describe("SymmetricKeySigningMechanism - .sign()")
class TestSymmetricKeySigningMechanismSign(object):
    @pytest.fixture
    def signing_mechanism(self):
        return SymmetricKeySigningMechanism("NMgJDvdKTxjLi+xBxxkDDEwDJxEvOE5u8BiT0mVgPeg=")

    @pytest.mark.it(
        "Generates an HMAC message digest from the signing key and provided data string, using the HMAC-SHA256 algorithm"
    )
    def test_hmac(self, mocker, signing_mechanism):
        hmac_mock = mocker.patch.object(hmac, "HMAC")
        hmac_digest_mock = hmac_mock.return_value.digest
        hmac_digest_mock.return_value = b"\xd2\x06\xf7\x12\xf1\xe9\x95$\x90\xfd\x12\x9a\xb1\xbe\xb4\xf8\xf3\xc4\x1ap\x8a\xab'\x8a.D\xfb\x84\x96\xca\xf3z"

        data_string = "sign this message"
        signing_mechanism.sign(data_string)

        assert hmac_mock.call_count == 1
        assert hmac_mock.call_args == mocker.call(
            key=signing_mechanism._signing_key,
            msg=data_string.encode("utf-8"),
            digestmod=hashlib.sha256,
        )
        assert hmac_digest_mock.call_count == 1

    @pytest.mark.it(
        "Returns the base64 encoded HMAC message digest (converted to string) as the signed data"
    )
    def test_b64encode(self, mocker, signing_mechanism):
        hmac_mock = mocker.patch.object(hmac, "HMAC")
        hmac_digest_mock = hmac_mock.return_value.digest
        hmac_digest_mock.return_value = b"\xd2\x06\xf7\x12\xf1\xe9\x95$\x90\xfd\x12\x9a\xb1\xbe\xb4\xf8\xf3\xc4\x1ap\x8a\xab'\x8a.D\xfb\x84\x96\xca\xf3z"

        data_string = "sign this message"
        signature = signing_mechanism.sign(data_string)

        assert signature == base64.b64encode(hmac_digest_mock.return_value).decode("utf-8")

    @pytest.mark.it("Supports data strings in both string and byte formats")
    @pytest.mark.parametrize(
        "data_string, expected_signature",
        [
            pytest.param(
                "sign this message", "8NJRMT83CcplGrAGaUVIUM/md5914KpWVNngSVoF9/M=", id="String"
            ),
            pytest.param(
                b"sign this message", "8NJRMT83CcplGrAGaUVIUM/md5914KpWVNngSVoF9/M=", id="Bytes"
            ),
        ],
    )
    def test_supported_types(self, signing_mechanism, data_string, expected_signature):
        assert signing_mechanism.sign(data_string) == expected_signature

    @pytest.mark.it("Raises a ValueError if unable to sign the provided data string")
    @pytest.mark.parametrize("data_string", [pytest.param(123, id="Integer input")])
    def test_bad_input(self, signing_mechanism, data_string):
        with pytest.raises(ValueError):
            signing_mechanism.sign(data_string)
