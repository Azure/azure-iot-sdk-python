# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.device.iothub.auth.sas_authentication_provider import (
    SharedAccessSignatureAuthenticationProvider,
)


sas_device_token_format = "SharedAccessSignature sr={}&sig={}&se={}"
sas_device_skn_token_format = "SharedAccessSignature sr={}&sig={}&se={}&skn={}"


shared_access_key_name = "alohomora"
hostname = "beauxbatons.academy-net"
device_id = "MyPensieve"
module_id = "Divination"

signature = "IsolemnlySwearThatIamuUptoNogood"
expiry = "1539043658"


def create_sas_token_string_device(is_module=False, is_key_name=False):
    uri = hostname + "/devices/" + device_id
    if is_module:
        uri = uri + "/modules/" + module_id
    if is_key_name:
        return sas_device_skn_token_format.format(uri, signature, expiry, shared_access_key_name)
    else:
        return sas_device_token_format.format(uri, signature, expiry)


def test_sas_auth_provider_is_created_from_device_sas_token_string():
    sas_string = create_sas_token_string_device()
    sas_auth_provider = SharedAccessSignatureAuthenticationProvider.parse(sas_string)
    assert sas_auth_provider.hostname == hostname
    assert sas_auth_provider.device_id == device_id
    assert hostname in sas_auth_provider.sas_token_str
    assert device_id in sas_auth_provider.sas_token_str


def test_sas_auth_provider_is_created_from_module_sas_token_string():
    sas_string = create_sas_token_string_device(True)
    sas_auth_provider = SharedAccessSignatureAuthenticationProvider.parse(sas_string)
    assert sas_auth_provider.hostname == hostname
    assert sas_auth_provider.device_id == device_id
    assert hostname in sas_auth_provider.sas_token_str
    assert device_id in sas_auth_provider.sas_token_str
    assert sas_auth_provider.module_id == module_id
    assert hostname in sas_auth_provider.sas_token_str
    assert device_id in sas_auth_provider.sas_token_str
    assert module_id in sas_auth_provider.sas_token_str


def test_sas_auth_provider_is_created_from_device_sas_token_string_with_keyname():
    sas_string = create_sas_token_string_device(False, True)
    sas_auth_provider = SharedAccessSignatureAuthenticationProvider.parse(sas_string)
    assert sas_auth_provider.hostname == hostname
    assert sas_auth_provider.device_id == device_id
    assert hostname in sas_auth_provider.sas_token_str
    assert device_id in sas_auth_provider.sas_token_str
    assert shared_access_key_name in sas_auth_provider.sas_token_str


def test_sas_auth_provider_is_created_from_device_sas_token_string_quoted():
    sas_string_quoted = "SharedAccessSignature sr=beauxbatons.academy-net%2Fdevices%2FMyPensieve&sig=IsolemnlySwearThatIamuUptoNogood&se=1539043658&skn=alohomora"
    sas_auth_provider = SharedAccessSignatureAuthenticationProvider.parse(sas_string_quoted)
    assert sas_auth_provider.hostname == hostname
    assert sas_auth_provider.device_id == device_id
    assert hostname in sas_auth_provider.sas_token_str
    assert device_id in sas_auth_provider.sas_token_str


def test_raises_when_auth_provider_created_from_empty_shared_access_signature_string():
    with pytest.raises(
        ValueError,
        match="The Shared Access Signature is required and should not be empty or blank and must be supplied as a string consisting of two parts in the format 'SharedAccessSignature sr=<resource_uri>&sig=<signature>&se=<expiry>' with an optional skn=<keyname>",
    ):
        SharedAccessSignatureAuthenticationProvider.parse("")


def test_raises_when_auth_provider_created_from_none_shared_access_signature_string():
    with pytest.raises(
        ValueError,
        match="The Shared Access Signature is required and should not be empty or blank and must be supplied as a string consisting of two parts in the format 'SharedAccessSignature sr=<resource_uri>&sig=<signature>&se=<expiry>' with an optional skn=<keyname>",
    ):
        SharedAccessSignatureAuthenticationProvider.parse(None)


def test_raises_when_auth_provider_created_from_blank_shared_access_signature_string():
    with pytest.raises(
        ValueError,
        match="The Shared Access Signature is required and should not be empty or blank and must be supplied as a string consisting of two parts in the format 'SharedAccessSignature sr=<resource_uri>&sig=<signature>&se=<expiry>' with an optional skn=<keyname>",
    ):
        SharedAccessSignatureAuthenticationProvider.parse("  ")


def test_raises_when_auth_provider_created_from_numeric_shared_access_signature_string():
    with pytest.raises(
        ValueError,
        match="The Shared Access Signature is required and should not be empty or blank and must be supplied as a string consisting of two parts in the format 'SharedAccessSignature sr=<resource_uri>&sig=<signature>&se=<expiry>' with an optional skn=<keyname>",
    ):
        SharedAccessSignatureAuthenticationProvider.parse(873915)


def test_raises_when_auth_provider_created_from_object_shared_access_signature_string():
    with pytest.raises(
        ValueError,
        match="The Shared Access Signature is required and should not be empty or blank and must be supplied as a string consisting of two parts in the format 'SharedAccessSignature sr=<resource_uri>&sig=<signature>&se=<expiry>' with an optional skn=<keyname>",
    ):
        SharedAccessSignatureAuthenticationProvider.parse(object)


def test_raises_when_auth_provider_created_from_shared_access_signature_string_blank_second_part():
    with pytest.raises(
        ValueError,
        match="The Shared Access Signature is required and should not be empty or blank and must be supplied as a string consisting of two parts in the format 'SharedAccessSignature sr=<resource_uri>&sig=<signature>&se=<expiry>' with an optional skn=<keyname>",
    ):
        SharedAccessSignatureAuthenticationProvider.parse("SharedAccessSignature   ")


def test_raises_when_auth_provider_created_from_shared_access_signature_string_numeric_second_part():
    with pytest.raises(
        ValueError,
        match="The Shared Access Signature is required and should not be empty or blank and must be supplied as a string consisting of two parts in the format 'SharedAccessSignature sr=<resource_uri>&sig=<signature>&se=<expiry>' with an optional skn=<keyname>",
    ):
        SharedAccessSignatureAuthenticationProvider.parse("SharedAccessSignature 67998311999")


def test_raises_when_auth_provider_created_from_shared_access_signature_string_numeric_value_second_part():
    with pytest.raises(
        ValueError,
        match="One of the name value pair of the Shared Access Signature string should be a proper resource uri",
    ):
        SharedAccessSignatureAuthenticationProvider.parse(
            "SharedAccessSignature sr=67998311999&sig=24234234&se=1539043658&skn=25245245"
        )


def test_raises_when_auth_provider_created_from_shared_access_signature_string_with_incomplete_sr():
    with pytest.raises(
        ValueError,
        match="One of the name value pair of the Shared Access Signature string should be a proper resource uri",
    ):
        SharedAccessSignatureAuthenticationProvider.parse(
            "SharedAccessSignature sr=MyPensieve&sig=IsolemnlySwearThatIamuUptoNogood&se=1539043658&skn=alohomora"
        )


def test_raises_auth_provider_created_from_missing_part_shared_access_signature_string():
    with pytest.raises(
        ValueError,
        match="The Shared Access Signature is required and should not be empty or blank and must be supplied as a string consisting of two parts in the format 'SharedAccessSignature sr=<resource_uri>&sig=<signature>&se=<expiry>' with an optional skn=<keyname>",
    ):
        one_part_sas_str = "sr=beauxbatons.academy-net%2Fdevices%2FMyPensieve&sig=IsolemnlySwearThatIamuUptoNogood&se=1539043658&skn=alohomora"
        SharedAccessSignatureAuthenticationProvider.parse(one_part_sas_str)


def test_raises_auth_provider_created_from_more_parts_shared_access_signature_string():
    with pytest.raises(
        ValueError,
        match="The Shared Access Signature must be of the format 'SharedAccessSignature sr=<resource_uri>&sig=<signature>&se=<expiry>' or/and it can additionally contain an optional skn=<keyname> name=value pair.",
    ):
        more_part_sas_str = "SharedAccessSignature sr=beauxbatons.academy-net%2Fdevices%2FMyPensieve&sig=IsolemnlySwearThatIamuUptoNogood&se=1539043658&skn=alohomora SharedAccessSignature"
        SharedAccessSignatureAuthenticationProvider.parse(more_part_sas_str)


def test_raises_auth_provider_created_from_shared_access_signature_string_duplicate_keys():
    with pytest.raises(ValueError, match="Invalid Shared Access Signature - Unable to parse"):
        duplicate_sas_str = "SharedAccessSignature sr=beauxbatons.academy-net%2Fdevices%2FMyPensieve&sig=IsolemnlySwearThatIamuUptoNogood&se=1539043658&sr=alohomora"
        SharedAccessSignatureAuthenticationProvider.parse(duplicate_sas_str)


def test_raises_auth_provider_created_from_shared_access_signature_string_bad_keys():
    with pytest.raises(
        ValueError,
        match="Invalid keys in Shared Access Signature. The valid keys are sr, sig, se and an optional skn.",
    ):
        bad_key_sas_str = "SharedAccessSignature sr=beauxbatons.academy-net%2Fdevices%2FMyPensieve&signature=IsolemnlySwearThatIamuUptoNogood&se=1539043658&skn=alohomora"
        SharedAccessSignatureAuthenticationProvider.parse(bad_key_sas_str)


def test_raises_auth_provider_created_from_incomplete_shared_access_signature_string():
    with pytest.raises(
        ValueError,
        match="Invalid Shared Access Signature. It must be of the format 'SharedAccessSignature sr=<resource_uri>&sig=<signature>&se=<expiry>' or/and it can additionally contain an optional skn=<keyname> name=value pair.",
    ):
        incomplete_sas_str = "SharedAccessSignature sr=beauxbatons.academy-net%2Fdevices%2FMyPensieve&se=1539043658&skn=alohomora"
        SharedAccessSignatureAuthenticationProvider.parse(incomplete_sas_str)
