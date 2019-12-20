# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import base64
import json
import six.moves.urllib as urllib
import requests
import requests_unixsocket
import logging
from .base_renewable_token_authentication_provider import BaseRenewableTokenAuthenticationProvider
from azure.iot.device import constant
from azure.iot.device.common.chainable_exception import ChainableException

requests_unixsocket.monkeypatch()

logger = logging.getLogger(__name__)


class IoTEdgeError(ChainableException):
    pass


class IoTEdgeAuthenticationProvider(BaseRenewableTokenAuthenticationProvider):
    """An Azure IoT Edge Authentication Provider.

    This provider creates the Shared Access Signature that would be needed to connenct to the IoT Edge runtime
    """

    def __init__(
        self,
        hostname,
        device_id,
        module_id,
        gateway_hostname,
        module_generation_id,
        workload_uri,
        api_version,
    ):
        """
        Constructor for IoT Edge Authentication Provider
        """

        logger.info("Using IoTEdge authentication for {%s, %s, %s}", hostname, device_id, module_id)

        super(IoTEdgeAuthenticationProvider, self).__init__(
            hostname=hostname, device_id=device_id, module_id=module_id
        )

        self.hsm = IoTEdgeHsm(
            module_id=module_id,
            api_version=api_version,
            module_generation_id=module_generation_id,
            workload_uri=workload_uri,
        )
        self.gateway_hostname = gateway_hostname
        self.server_verification_cert = self.hsm.get_trust_bundle()

    # TODO: reconsider this design when refactoring the BaseRenewableToken auth parent
    # TODO: Consider handling the quoting within this function, and renaming quoted_resource_uri to resource_uri
    def _sign(self, quoted_resource_uri, expiry):
        """
        Creates the signature to be inserted in the SAS token
        :param resource_uri: the resource URI to encode into the token
        :param expiry: an integer value representing the number of seconds since the epoch 00:00:00 UTC on 1 January 1970 at which the token will expire.
        :return: The signature portion of the Sas Token.

        :raises: IoTEdgeError if data cannot be signed
        """
        string_to_sign = quoted_resource_uri + "\n" + str(expiry)
        return self.hsm.sign(string_to_sign)


class IoTEdgeHsm(object):
    """
    Constructor for instantiating a iot hsm object.  This is an object that
    communicates with the Azure IoT Edge HSM in order to get connection credentials
    for an Azure IoT Edge module.  The credentials that this object return come in
    two forms:

    1. The trust bundle, which is a certificate that can be used as a trusted cert
       to authenticate the SSL connection between the IoE Edge module and IoT Edge
    2. A signing function, which can be used to create the sig field for a
       SharedAccessSignature string which can be used to authenticate with Iot Edge
    """

    def __init__(self, module_id, module_generation_id, workload_uri, api_version):
        """
        Constructor for instantiating a Azure IoT Edge HSM object

        :param str module_id: The module id
        :param str api_version: The API version
        :param str module_generation_id: The module generation id
        :param str workload_uri: The workload uri
        """
        self.module_id = urllib.parse.quote(module_id)
        self.api_version = api_version
        self.module_generation_id = module_generation_id
        self.workload_uri = _format_socket_uri(workload_uri)

    # TODO: Is this really the right name? It returns a certificate FROM the trust bundle,
    # not the trust bundle itself
    def get_trust_bundle(self):
        """
        Return the trust bundle that can be used to validate the server-side SSL
        TLS connection that we use to talk to edgeHub.

        :return: The server verification certificate to use for connections to the Azure IoT Edge
        instance, as a PEM certificate in string form.

        :raises: IoTEdgeError if unable to retrieve the certificate.
        """
        r = requests.get(
            self.workload_uri + "trust-bundle",
            params={"api-version": self.api_version},
            headers={"User-Agent": urllib.parse.quote_plus(constant.USER_AGENT)},
        )
        # Validate that the request was successful
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise IoTEdgeError(message="Unable to get trust bundle from EdgeHub", cause=e)
        # Decode the trust bundle
        try:
            bundle = r.json()
        except ValueError as e:
            raise IoTEdgeError(message="Unable to decode trust bundle", cause=e)
        # Retrieve the certificate
        try:
            cert = bundle["certificate"]
        except KeyError as e:
            raise IoTEdgeError(message="No certificate in trust bundle", cause=e)
        return cert

    def sign(self, data_str):
        """
        Use the IoTEdge HSM to sign a piece of string data.  The caller should then insert the
        returned value (the signature) into the 'sig' field of a SharedAccessSignature string.

        :param str data_str: The data string to sign

        :return: The signature, as a URI-encoded and base64-encoded value that is ready to
        directly insert into the SharedAccessSignature string.

        :raises: IoTEdgeError if unable to sign the data.
        """
        encoded_data_str = base64.b64encode(data_str.encode("utf-8")).decode()

        path = (
            self.workload_uri
            + "modules/"
            + self.module_id
            + "/genid/"
            + self.module_generation_id
            + "/sign"
        )
        sign_request = {"keyId": "primary", "algo": "HMACSHA256", "data": encoded_data_str}

        r = requests.post(  # TODO: can we use json field instead of data?
            url=path,
            params={"api-version": self.api_version},
            headers={"User-Agent": urllib.parse.quote_plus(constant.USER_AGENT)},
            data=json.dumps(sign_request),
        )
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise IoTEdgeError(message="Unable to sign data", cause=e)
        try:
            sign_response = r.json()
        except ValueError as e:
            raise IoTEdgeError(message="Unable to decode signed data", cause=e)
        try:
            signed_data_str = sign_response["digest"]
        except KeyError as e:
            raise IoTEdgeError(message="No signed data received", cause=e)

        return urllib.parse.quote(signed_data_str)


def _format_socket_uri(old_uri):
    """
    This function takes a socket URI in one form and converts it into another form.

    The source form is based on what we receive inside the IOTEDGE_WORKLOADURI
    environment variable, and it looks like this:
    "unix:///var/run/iotedge/workload.sock"

    The destination form is based on what the requests_unixsocket library expects
    and it looks like this:
    "http+unix://%2Fvar%2Frun%2Fiotedge%2Fworkload.sock/"

    The function changes the prefix, uri-encodes the path, and adds a slash
    at the end.

    If the socket URI does not start with unix:// this function only adds
    a slash at the end.

    :param old_uri: The URI in IOTEDGE_WORKLOADURI form

    :return: The URI in requests_unixsocket form
    """
    old_prefix = "unix://"
    new_prefix = "http+unix://"

    if old_uri.startswith(old_prefix):
        stripped_uri = old_uri[len(old_prefix) :]
        if stripped_uri.endswith("/"):
            stripped_uri = stripped_uri[:-1]
        new_uri = new_prefix + urllib.parse.quote(stripped_uri, safe="")
    else:
        new_uri = old_uri

    if not new_uri.endswith("/"):
        new_uri += "/"

    return new_uri
