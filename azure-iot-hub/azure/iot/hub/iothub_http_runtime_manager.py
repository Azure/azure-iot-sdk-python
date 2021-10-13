# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from .auth import ConnectionStringAuthentication, AzureIdentityCredentialAdapter
from .protocol.iot_hub_gateway_service_ap_is import IotHubGatewayServiceAPIs as protocol_client


class IoTHubHttpRuntimeManager(object):
    """A class to provide convenience APIs for IoTHub Http Runtime Manager operations,
    based on top of the auto generated IotHub REST APIs
    """

    def __init__(self, connection_string=None, host=None, auth=None):
        """Initializer for a Http Runtime Manager Service client.

        After a successful creation the class has been authenticated with IoTHub and
        it is ready to call the member APIs to communicate with IoTHub.

        :param str connection_string: The IoTHub connection string used to authenticate connection
            with IoTHub if we are using connection_str authentication. Default value: None
        :param str host: The Azure service url if we are using token credential authentication.
            Default value: None
        :param str auth: The Azure authentication object if we are using token credential authentication.
            Default value: None

        :returns: Instance of the IoTHubHttpRuntimeManager object.
        :rtype: :class:`azure.iot.hub.IoTHubHttpRuntimeManager`
        """
        if connection_string is not None:
            self.auth = ConnectionStringAuthentication(connection_string)
            self.protocol = protocol_client(self.auth, "https://" + self.auth["HostName"])
        else:
            self.auth = auth
            self.protocol = protocol_client(self.auth, "https://" + host)

    @classmethod
    def from_connection_string(cls, connection_string):
        """Classmethod initializer for a IoTHubHttpRuntimeManager Service client.
        Creates IoTHubHttpRuntimeManager class from connection string.

        After a successful creation the class has been authenticated with IoTHub and
        it is ready to call the member APIs to communicate with IoTHub.

        :param str connection_string: The IoTHub connection string used to authenticate connection
            with IoTHub.

        :rtype: :class:`azure.iot.hub.IoTHubHttpRuntimeManager`
        """
        return cls(connection_string=connection_string)

    @classmethod
    def from_token_credential(cls, url, token_credential):
        """Classmethod initializer for a IoTHubHttpRuntimeManager Service client.
        Creates IoTHubHttpRuntimeManager class from host name url and Azure token credential.

        After a successful creation the class has been authenticated with IoTHub and
        it is ready to call the member APIs to communicate with IoTHub.

        :param str url: The Azure service url (host name).
        :param token_credential: The Azure token credential object
        :type token_credential: :class:`azure.core.TokenCredential`

        :rtype: :class:`azure.iot.hub.IoTHubHttpRuntimeManager`
        """
        host = url
        auth = AzureIdentityCredentialAdapter(token_credential)
        return cls(host=host, auth=auth)

    def receive_feedback_notification(self):
        """This method is used to retrieve feedback of a cloud-to-device message.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: None.
        """
        return self.protocol.cloud_to_device_messages.receive_feedback_notification()

    def complete_feedback_notification(self, lock_token):
        """This method completes a feedback message.

        :param str lock_token: Lock token.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: None.
        """
        return self.protocol.cloud_to_device_messages.complete_feedback_notification(lock_token)

    def abandon_feedback_notification(self, lock_token):
        """This method abandons a feedback message.

        :param str lock_token: Lock token.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: None.
        """
        return self.protocol.cloud_to_device_messages.abandon_feedback_notification(lock_token)
