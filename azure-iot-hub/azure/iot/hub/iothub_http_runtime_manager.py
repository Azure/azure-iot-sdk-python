# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from .auth import ConnectionStringAuthentication
from .protocol.iot_hub_gateway_service_ap_is import IotHubGatewayServiceAPIs as protocol_client


class IoTHubHttpRuntimeManager(object):
    """A class to provide convenience APIs for IoTHub Http Runtime Manager operations,
    based on top of the auto generated IotHub REST APIs
    """

    def __init__(self, connection_string):
        """Initializer for a Http Runtime Manager Service client.

        After a successful creation the class has been authenticated with IoTHub and
        it is ready to call the member APIs to communicate with IoTHub.

        :param str connection_string: The IoTHub connection string used to authenticate connection
            with IoTHub.

        :returns: Instance of the IoTHubHttpRuntimeManager object.
        :rtype: :class:`azure.iot.hub.IoTHubHttpRuntimeManager`
        """

        self.auth = ConnectionStringAuthentication(connection_string)
        self.protocol = protocol_client(self.auth, "https://" + self.auth["HostName"])

    def receive_feedback_notification(self):
        """This method is used to retrieve feedback of a cloud-to-device message.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: None.
        """
        return self.protocol.http_runtime.receive_feedback_notification()

    def complete_feedback_notification(self, lock_token):
        """This method completes a feedback message.

        :param str lock_token: Lock token.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: None.
        """
        return self.protocol.http_runtime.complete_feedback_notification(lock_token)

    def abandon_feedback_notification(self, lock_token):
        """This method abandons a feedback message.

        :param str lock_token: Lock token.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: None.
        """
        return self.protocol.http_runtime.abandon_feedback_notification(lock_token)
