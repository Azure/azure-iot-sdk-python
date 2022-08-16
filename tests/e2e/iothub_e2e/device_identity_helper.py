# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import uuid
from dev_utils import test_env
import time
from azure.iot.hub import IoTHubRegistryManager
from base64 import b64encode, b64decode
from hashlib import sha256
from six.moves.urllib import parse
from hmac import HMAC


def generate_sas_token(uri, key, policy_name, expiry):
    sign_data = "%s\n%d" % ((parse.quote_plus(uri)), int(expiry))

    signature = b64encode(HMAC(b64decode(key), sign_data.encode("utf-8"), sha256).digest())

    rawtoken = {"sr": uri, "sig": signature, "se": str(int(expiry))}

    if policy_name is not None:
        rawtoken["skn"] = policy_name

    return "SharedAccessSignature " + parse.urlencode(rawtoken)


class IdentityDescription(object):
    def __init_(self):
        self.device_id = None
        self.authentication_description = None
        self.connection_string = None
        self.certificate = None
        self.client_key = None
        self.primary_key = None
        self.sas_token = None


# NOTE: This code should probably be wrapped in an object with a shutdown method.  This way
# we could create the IoTHubRegistryManager once and clean it up when we're done.  Making
# the IoTHubRegistryManager object a global is ugly because that would cause us to get warnings
# from uamqp as it cleans up.


def create_device_with_x509_self_signed_cert():
    desc = IdentityDescription()
    desc.authentication_description = "x509 certificate"
    desc.device_id = "00e2etest-delete-me-python-x509-" + str(uuid.uuid4())
    raise Exception("NOTIMPL")


def create_device_with_symmetric_key():
    desc = IdentityDescription()
    desc.authentication_description = "shared private key"
    desc.device_id = "00e2etest-delete-me-python-key-" + str(uuid.uuid4())

    registry_manager = IoTHubRegistryManager.from_connection_string(
        test_env.IOTHUB_CONNECTION_STRING
    )
    dev = registry_manager.create_device_with_sas(desc.device_id, None, None, "enabled")

    desc.primary_key = dev.authentication.symmetric_key.primary_key
    desc.connection_string = (
        "HostName="
        + test_env.IOTHUB_HOSTNAME
        + ";DeviceId="
        + desc.device_id
        + ";SharedAccessKey="
        + desc.primary_key
    )
    return desc


def create_device_with_sas():
    desc = IdentityDescription()
    desc.authentication_description = "application supplied SAS"
    desc.device_id = "00e2etest-delete-me-python-sas-" + str(uuid.uuid4())

    registry_manager = IoTHubRegistryManager.from_connection_string(
        test_env.IOTHUB_CONNECTION_STRING
    )
    dev = registry_manager.create_device_with_sas(desc.device_id, None, None, "enabled")

    desc.primary_key = dev.authentication.symmetric_key.primary_key

    uri = "{}/devices/{}".format(test_env.IOTHUB_HOSTNAME, desc.device_id)
    expiry = time.time() + 3600
    desc.sas_token = generate_sas_token(uri, desc.primary_key, None, expiry)

    print("token = {}".format(desc.sas_token))

    return desc


def create_device_with_x509_ca_signed_cert():
    desc = IdentityDescription()
    desc.authentication_description = "CA signed certificate"
    desc.device_id = "e2e-del-me-python-CACert-" + str(uuid.uuid4())
    raise Exception("NOTIMPL")


def delete_device(device_id):
    registry_manager = IoTHubRegistryManager.from_connection_string(
        test_env.IOTHUB_CONNECTION_STRING
    )
    registry_manager.delete_device(device_id)
