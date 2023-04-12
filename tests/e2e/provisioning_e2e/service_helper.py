# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import base64
import binascii
import hashlib
import hmac

from provisioning_e2e.iothubservice20180630.iot_hub_gateway_service_ap_is20180630 import (
    IotHubGatewayServiceAPIs20180630,
)

# import urllib
from msrest.exceptions import HttpOperationError
from azure.iot.device.connection_string import ConnectionString
import uuid
import time
import random
import urllib.parse


max_failure_count = 5

initial_backoff = 10

CS_DELIMITER = ";"
CS_VAL_SEPARATOR = "="

HOST_NAME = "HostName"
SHARED_ACCESS_KEY_NAME = "SharedAccessKeyName"
SHARED_ACCESS_KEY = "SharedAccessKey"
SHARED_ACCESS_SIGNATURE = "SharedAccessSignature"
DEVICE_ID = "DeviceId"
MODULE_ID = "ModuleId"
GATEWAY_HOST_NAME = "GatewayHostName"
X509 = "x509"

_valid_keys = [
    HOST_NAME,
    SHARED_ACCESS_KEY_NAME,
    SHARED_ACCESS_KEY,
    SHARED_ACCESS_SIGNATURE,
    DEVICE_ID,
    MODULE_ID,
    GATEWAY_HOST_NAME,
    X509,
]

_auth_rule_token_format = (
    "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}&skn={keyname}"
)
_simple_token_format = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}"


# class RenewableSasToken:
#     """Renewable Shared Access Signature Token used to authenticate a request.
#
#     This token is 'renewable', which means that it can be updated when necessary to
#     prevent expiry, by using the .refresh() method.
#
#     Data Attributes:
#     expiry_time (int): Time that token will expire (in UTC, since epoch)
#     ttl (int): Time to live for the token, in seconds
#     """
#
#     _auth_rule_token_format = (
#         "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}&skn={keyname}"
#     )
#     _simple_token_format = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}"
#
#     def __init__(self, uri, signing_mechanism, key_name=None, ttl=3600):
#         """
#         :param str uri: URI of the resource to be accessed
#         :param signing_mechanism: The signing mechanism to use in the SasToken
#         :type signing_mechanism: Child classes of :class:`azure.iot.common.SigningMechanism`
#         :param str key_name: Symmetric Key Name (optional)
#         :param int ttl: Time to live for the token, in seconds (default 3600)
#
#         :raises: SasTokenError if an error occurs building a SasToken
#         """
#         self._uri = uri
#         self._signing_mechanism = signing_mechanism
#         self._key_name = key_name
#         self._expiry_time = None  # This will be overwritten by the .refresh() call below
#         self._token = None  # This will be overwritten by the .refresh() call below
#
#         self.ttl = ttl
#         self.refresh()
#
#     def __str__(self):
#         return self._token
#
#     def refresh(self):
#         """
#         Refresh the SasToken lifespan, giving it a new expiry time, and generating a new token.
#         """
#         self._expiry_time = int(time.time() + self.ttl)
#         self._token = self._build_token()
#
#     def _build_token(self):
#         """Build SasToken representation
#
#         :returns: String representation of the token
#         """
#         url_encoded_uri = urllib.parse.quote(self._uri, safe="")
#         message = url_encoded_uri + "\n" + str(self.expiry_time)
#         try:
#             signature = self._signing_mechanism.sign(message)
#         except Exception as e:
#             # Because of variant signing mechanisms, we don't know what error might be raised.
#             # So we catch all of them.
#             raise ValueError("Unable to build SasToken from given values") from e
#         url_encoded_signature = urllib.parse.quote(signature, safe="")
#         if self._key_name:
#             token = self._auth_rule_token_format.format(
#                 resource=url_encoded_uri,
#                 signature=url_encoded_signature,
#                 expiry=str(self.expiry_time),
#                 keyname=self._key_name,
#             )
#         else:
#             token = self._simple_token_format.format(
#                 resource=url_encoded_uri,
#                 signature=url_encoded_signature,
#                 expiry=str(self.expiry_time),
#             )
#         return token
#
#     @property
#     def expiry_time(self):
#         """Expiry Time is READ ONLY"""
#         return self._expiry_time


def connection_string_to_sas_token(connection_string):
    """
    parse an IoTHub service connection string and return the host and a shared access
    signature that can be used to connect to the given hub
    """
    # conn_str_obj = ConnectionString(conn_str)
    try:
        cs_args = connection_string.split(CS_DELIMITER)
    except (AttributeError, TypeError):
        raise TypeError("Connection String must be of type str")
    try:
        conn_str_obj = dict(arg.split(CS_VAL_SEPARATOR, 1) for arg in cs_args)
    except ValueError:
        # This occurs in an extreme edge case where a dictionary cannot be formed because there
        # is only 1 token after the split (dict requires two in order to make a key/value pair)
        raise ValueError("Invalid Connection String - Unable to parse")
    if len(cs_args) != len(conn_str_obj):
        # various errors related to incorrect parsing - duplicate args, bad syntax, etc.
        raise ValueError("Invalid Connection String - Unable to parse")
    if not all(key in _valid_keys for key in conn_str_obj.keys()):
        raise ValueError("Invalid Connection String - Invalid Key")
    # _validate_keys(conn_str_obj)
    # return conn_str_obj
    # signing_mechanism = SymmetricKeySigningMechanism(conn_str_obj.get("SharedAccessKey"))
    # sas_token = RenewableSasToken(
    #     uri=conn_str_obj.get("HostName"),
    #     signing_mechanism=signing_mechanism,
    #     key_name=conn_str_obj.get("SharedAccessKeyName"),
    # )
    uri = conn_str_obj.get("HostName")
    key_name = conn_str_obj.get("SharedAccessKey")
    if isinstance(key_name, str):
        key_bytes = key_name.encode("utf-8")
    else:
        key_bytes = key_name

    # Derives the signing key
    try:
        signing_key = base64.b64decode(key_bytes)
    except (binascii.Error):
        raise ValueError("Invalid Symmetric Key")
    ttl = 3600
    expiry_time = int(time.time() + ttl)
    url_encoded_uri = urllib.parse.quote(uri, safe="")
    message = url_encoded_uri + "\n" + str(expiry_time)

    if isinstance(message, str):
        data_bytes = message.encode("utf-8")
    else:
        data_bytes = message

    # Derive signature via HMAC-SHA256 algorithm
    try:
        hmac_digest = hmac.HMAC(key=signing_key, msg=data_bytes, digestmod=hashlib.sha256).digest()
        signed_data = base64.b64encode(hmac_digest)
    except (TypeError):
        raise ValueError("Unable to sign string using the provided symmetric key")
    # Convert from bytes to string
    except Exception as e:
        # Because of variant signing mechanisms, we don't know what error might be raised.
        # So we catch all of them.
        raise ValueError("Unable to build SasToken from given values") from e
    url_encoded_signature = urllib.parse.quote(signed_data.decode("utf-8"), safe="")
    if key_name:
        token = _auth_rule_token_format.format(
            resource=url_encoded_uri,
            signature=url_encoded_signature,
            expiry=str(expiry_time),
            keyname=key_name,
        )
    else:
        token = _simple_token_format.format(
            resource=url_encoded_uri,
            signature=url_encoded_signature,
            expiry=str(expiry_time),
        )
    return {"host": conn_str_obj.get("HostName"), "sas": str(token)}


# def _validate_keys(d):
#     """Raise ValueError if incorrect combination of keys in dict d"""
#     host_name = d.get(HOST_NAME)
#     shared_access_key_name = d.get(SHARED_ACCESS_KEY_NAME)
#     shared_access_key = d.get(SHARED_ACCESS_KEY)
#     device_id = d.get(DEVICE_ID)
#     x509 = d.get(X509)
#
#     if shared_access_key and x509 and x509.lower() == "true":
#         raise ValueError("Invalid Connection String - Mixed authentication scheme")
#
#     # This logic could be expanded to return the category of ConnectionString
#     if host_name and device_id and (shared_access_key or x509):
#         pass
#     elif host_name and shared_access_key and shared_access_key_name:
#         pass
#     else:
#         raise ValueError("Invalid Connection String - Incomplete")


def connection_string_to_hostname(conn_str):
    """
    Retrieves only the hostname from connection string.
    This will eventually give us the Linked IoT Hub
    """
    conn_str_obj = ConnectionString(conn_str)
    return conn_str_obj.get("HostName")


def run_with_retry(fun, args, kwargs):
    failures_left = max_failure_count
    retry = True
    backoff = initial_backoff + random.randint(1, 10)

    while retry:
        try:
            return fun(*args, **kwargs)
        except HttpOperationError as e:
            resp = e.response.json()
            retry = False
            if "Message" in resp:
                if resp["Message"].startswith("ErrorCode:ThrottlingBacklogTimeout"):
                    retry = True
            if retry and failures_left:
                failures_left = failures_left - 1
                print("{} failures left before giving up".format(failures_left))
                print("sleeping for {} seconds".format(backoff))
                time.sleep(backoff)
                backoff = backoff * 2
            else:
                raise e


class Helper:
    def __init__(self, service_connection_string):
        self.cn = connection_string_to_sas_token(service_connection_string)
        self.service = IotHubGatewayServiceAPIs20180630("https://" + self.cn["host"]).service

    def headers(self):
        return {
            "Authorization": self.cn["sas"],
            "Request-Id": str(uuid.uuid4()),
            "User-Agent": "azure-iot-device-provisioning-e2e",
        }

    def get_device(self, device_id):
        device = run_with_retry(
            self.service.get_device, (device_id,), {"custom_headers": self.headers()}
        )
        return device

    def get_module(self, device_id, module_id):
        module = run_with_retry(
            self.service.get_module, (device_id, module_id), {"custom_headers": self.headers()}
        )
        return module

    def get_device_connection_string(self, device_id):
        device = run_with_retry(
            self.service.get_device, (device_id,), {"custom_headers": self.headers()}
        )

        primary_key = device.authentication.symmetric_key.primary_key
        return (
            "HostName="
            + self.cn["host"]
            + ";DeviceId="
            + device_id
            + ";SharedAccessKey="
            + primary_key
        )

    def get_module_connection_string(self, device_id, module_id):
        module = run_with_retry(
            self.service.get_module, (device_id, module_id), {"custom_headers": self.headers()}
        )

        primary_key = module.authentication.symmetric_key.primary_key
        return (
            "HostName="
            + self.cn["host"]
            + ";DeviceId="
            + device_id
            + ";ModuleId="
            + module_id
            + ";SharedAccessKey="
            + primary_key
        )

    def try_delete_device(self, device_id):
        try:
            run_with_retry(
                self.service.delete_device,
                (device_id,),
                {"if_match": "*", "custom_headers": self.headers()},
            )
            return True
        except HttpOperationError:
            return False

    def try_delete_module(self, device_id, module_id):
        try:
            run_with_retry(
                self.service.delete_module,
                (device_id, module_id),
                {"if_match": "*", "custom_headers": self.headers()},
            )
            return True
        except HttpOperationError:
            return False
