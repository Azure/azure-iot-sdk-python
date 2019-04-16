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

requests_unixsocket.monkeypatch()


class IotEdgeHsm(object):
    """
    Constructor for instantiating a iot hsm object.  This is an object that
    communicates with the Azure IoT Edge HSM in order to get connection credentials
    for an Azure IoT Edge module.  The credentials that this object return come in
    two forms:

    1. The trust bundle, which is a certificate that can be used as a trusted cert
       to authenticate the SSL connection between the IoE Edge module and IoT Edge
    2. A signing function, which can be used to create the sig field for a
       SharedAccessSignature string which can be used to authenticate with Iot Edge

    Instantiating this object does not require any parameters.  All necessary parameters
    come from environment variables that are set inside the IoT Edge module container
    by the edgeAgent that creates the module.
    """

    @staticmethod
    def _fix_socket_uri(old_uri):
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

    def __init__(self):
        """
        Constructor for instantiating a Azure IoT Edge HSM object
        """
        # All of these environment variables are required.  If any are missing,
        # we want this to fail.
        self.module_id = os.environ["IOTEDGE_MODULEID"]
        self.api_version = os.environ["IOTEDGE_APIVERSION"]
        self.module_generation_id = os.environ["IOTEDGE_MODULEGENERATIONID"]
        self.workload_uri = IotEdgeHsm._fix_socket_uri(os.environ["IOTEDGE_WORKLOADURI"])

    def get_trust_bundle(self):
        """
        Return the trust bundle that can be used to validate the server-side SSL
        TLS connection that we use to talk to edgeHub.

        :return: The CA certificate to use for connections to the Azure IoT Edge
        instance, as a PEM certificate in string form.
        """
        r = requests.get(
            self.workload_uri + "trust-bundle", params={"api-version": self.api_version}
        )
        r.raise_for_status()
        return r.json()["certificate"]

    def sign(self, data):
        """
        Use the IoTEdge HSM to sign a piece of data.  The caller should then insert the
        returned value (the signature) into the 'sig' field of a SharedAccessSignature string.

        :param data: The string to sign

        :return: The signature, as a URI-encoded and base64-encoded value that is ready to
        directly insert into the SharedAccessSignature string.
        """
        path = (
            self.workload_uri
            + "modules/"
            + urllib.parse.quote(self.module_id)
            + "/genid/"
            + self.module_generation_id
            + "/sign"
        )
        sign_request = {
            "keyId": "primary",
            "algo": "HMACSHA256",
            "data": base64.b64encode(data.encode("utf-8")).decode(),
        }

        r = requests.post(
            path, params={"api-version": self.api_version}, data=json.dumps(sign_request)
        )
        r.raise_for_status()
        return urllib.parse.quote(r.json()["digest"])
