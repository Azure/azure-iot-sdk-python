import six.moves.urllib as urllib
import requests
import os
import base64
import json

class IotEdgeHsm(object):

    def __init__(self):
        """
        Constructor for instantiating a iot hsm object.  This is an object that can 
        communicate with the IoTEdge HSM from within an IoTEdge Module
        """
        # All of these environment variables are required.  If any are missing,
        # we want this to fail.
        self.module_id = os.environ['IOTEDGE_MODULEID']
        self.api_version = os.environ['IOTEDGE_APIVERSION']
        self.module_generation_id = os.environ['IOTEDGE_MODULEGENERATIONID']
        self.workload_uri = os.environ['IOTEDGE_WORKLOADURI']

    def get_trust_bundle(self):
        """
        Return the trust bundle that can be used to validate the server-side SSL
        TLS connection that we use to talk to edgeHub.
        """
        r = requests.get(self.workload_uri + 'trust-bundle', params={'api-version': self.api_version})
        r.raise_for_status()
        return r.json()['certificate']

    def sign(self, message):
        """
        Use the IoTEdge HSM to sign a message.  The signed value can be used a
        SAS token when communicating with IoTEdge

        :param message The string to sign

        returns The signature string.
        """
        path = self.workload_uri + 'modules/' + urllib.parse.quote(self.module_id) + '/genid/' + self.module_generation_id + '/sign'
        sign_request = {
            'keyId': 'primary',
            'algo': 'HMACSHA256',
            'data': base64.b64encode(message.encode()).decode()
        }

        r = requests.post(path, params={'api-version': self.api_version}, data=json.dumps(sign_request))
        r.raise_for_status()
        return base64.b64decode(r.json()['digest']).decode()

