# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import json
import base64
import ssl
import requests
import requests_unixsocket
from six.moves import urllib, http_client
from azure.iot.device.common.chainable_exception import ChainableException
from azure.iot.device.common.auth.signing_mechanism import SigningMechanism
from azure.iot.device import user_agent

requests_unixsocket.monkeypatch()
logger = logging.getLogger(__name__)


class IoTEdgeError(ChainableException):
    pass


class IoTEdgeHsm(SigningMechanism):
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

    def __init__(self, module_id, generation_id, workload_uri, api_version, hostname):
        """
        Constructor for instantiating a Azure IoT Edge HSM object

        :param str module_id: The module id
        :param str api_version: The API version
        :param str generation_id: The module generation id
        :param str workload_uri: The workload uri
        """
        self.module_id = urllib.parse.quote(module_id, safe="")
        self.api_version = api_version
        self.generation_id = generation_id
        self.workload_uri = workload_uri
        self.hostname = hostname
        # self.workload_uri = _format_socket_uri(workload_uri)

    def get_certificate(self):
        """
        Return the server verification certificate from the trust bundle that can be used to
        validate the server-side SSL TLS connection that we use to talk to Edge

        :return: The server verification certificate to use for connections to the Azure IoT Edge
        instance, as a PEM certificate in string form.

        :raises: IoTEdgeError if unable to retrieve the certificate.
        """
        # TODO remove this
        logger.debug("RETRIEVING CERT WITH HOSTNAME {}".format(self.hostname))
        ssl_context = ssl.create_default_context()
        connection = http_client.HTTPSConnection(self.hostname, context=ssl_context)
        connection.connect()

        # Derive the URL
        query_params = "api-version={api_version}".format(
            api_version=urllib.parse.quote_plus(user_agent.get_iothub_user_agent())
        )
        url = "{workload_uri}trust-bundle?{query_params}".format(
            workload_uri=self.workload_uri, query_params=query_params
        )

        # Derive the headers
        headers = {"User-Agent": urllib.parse.quote_plus(user_agent.get_iothub_user_agent())}

        # Make the request and get response
        connection.request("GET", url, headers=headers)
        response = connection.getresponse()
        # check status here?

        # TODO: REMOVE THIS
        logger.debug("EDGE RESPONSE:\n{}".format(response.read()))

        # Extract the certificate from response
        response = response.read().decode("utf-8")
        bundle = json.loads(response)

        # TODO: REMOVE THIS
        logger.debug("TRUST BUNDLE:\n{}".format(bundle))
        return bundle["certificate"]

        # r = requests.get(
        #     self.workload_uri + "trust-bundle",
        #     params={"api-version": self.api_version},
        #     headers={"User-Agent": urllib.parse.quote_plus(user_agent.get_iothub_user_agent())},
        # )
        # # Validate that the request was successful
        # try:
        #     r.raise_for_status()
        # except requests.exceptions.HTTPError as e:
        #     raise IoTEdgeError(message="Unable to get trust bundle from Edge", cause=e)
        # # Decode the trust bundle
        # try:
        #     bundle = r.json()
        # except ValueError as e:
        #     raise IoTEdgeError(message="Unable to decode trust bundle", cause=e)
        # # Retrieve the certificate
        # try:
        #     cert = bundle["certificate"]
        # except KeyError as e:
        #     raise IoTEdgeError(message="No certificate in trust bundle", cause=e)
        # return cert

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

        path = "{workload_uri}modules/{module_id}/genid/{gen_id}/sign".format(
            workload_uri=self.workload_uri, module_id=self.module_id, gen_id=self.generation_id
        )
        sign_request = {"keyId": "primary", "algo": "HMACSHA256", "data": encoded_data_str}

        r = requests.post(  # can we use json field instead of data?
            url=path,
            params={"api-version": self.api_version},
            headers={"User-Agent": urllib.parse.quote(user_agent.get_iothub_user_agent(), safe="")},
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

        return signed_data_str  # what format is this? string? bytes?


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
