import six.moves.urllib as urllib
import requests
import requests_unixsocket
import os
import base64
import json

requests_unixsocket.monkeypatch()


class IotEdgeHsm(object):
    @staticmethod
    def fix_socket_uri(old_uri):
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
        Constructor for instantiating a iot hsm object.  This is an object that can 
        communicate with the IoTEdge HSM from within an IoTEdge Module
        """
        # All of these environment variables are required.  If any are missing,
        # we want this to fail.
        self.module_id = os.environ["IOTEDGE_MODULEID"]
        self.api_version = os.environ["IOTEDGE_APIVERSION"]
        self.module_generation_id = os.environ["IOTEDGE_MODULEGENERATIONID"]
        self.workload_uri = IotEdgeHsm.fix_socket_uri(os.environ["IOTEDGE_WORKLOADURI"])

    def get_trust_bundle(self):
        """
        Return the trust bundle that can be used to validate the server-side SSL
        TLS connection that we use to talk to edgeHub.
        """
        r = requests.get(
            self.workload_uri + "trust-bundle", params={"api-version": self.api_version}
        )
        r.raise_for_status()
        return r.json()["certificate"]

    def sign(self, message):
        """
        Use the IoTEdge HSM to sign a message.  The signed value can be used a
        SAS token when communicating with IoTEdge

        :param message The string to sign

        returns The signature string.
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
            "data": base64.b64encode(message.encode()).decode(),
        }

        r = requests.post(
            path,
            params={"api-version": self.api_version},
            data=json.dumps(sign_request),
        )
        r.raise_for_status()
        return base64.b64decode(r.json()["digest"]).decode()
