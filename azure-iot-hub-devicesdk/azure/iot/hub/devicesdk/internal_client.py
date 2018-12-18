# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import logging
from threading import Event
from .transport.mqtt.mqtt_transport import MQTTTransport

logger = logging.getLogger(__name__)


class InternalClient(object):
    """
    A super class representing a generic client. This class needs to be extended for specific clients.
    """

    def __init__(self, auth_provider, transport):
        """
        Constructor for instantiating an internal client.  This initializer should not be called
        directly.  Instead, the static `from_authentication_provider` function should be used to
        create a client object.

        :param auth_provider: The authentication provider
        :param transport: The transport that the client will use.
        """
        self._auth_provider = auth_provider
        self._transport = transport
        self._transport.on_transport_connected = self._handle_transport_connected_state
        self._transport.on_transport_disconnected = self._handle_transport_connected_state

        self.state = "initial"

        self.on_connection_state = None
        self.on_event_sent = None

    def connect(self):
        """
        Connects the client to an Azure IoT Hub or Azure IoT Edge instance.  The destination is chosen
        based on the credentials passed via the auth_provider parameter that was provided when
        this object was initialized.

        This is a synchronous call, meaning that this function will not return until the connection
        to the service has been completely established.
        """
        logger.info("connecting to transport")

        connect_complete = Event()

        def callback():
            connect_complete.set()

        self._transport.connect(callback)
        connect_complete.wait()

    def disconnect(self):
        """
        Disconnect the client from the Azure IoT Hub or Azure IoT Edge instance.

        This is a synchronous call, meaning that this function will not return until the connection
        to the service has been completely closed.
        """
        logger.info("disconnecting from transport")

        disconnect_complete = Event()

        def callback():
            disconnect_complete.set()

        self._transport.disconnect(callback)
        disconnect_complete.wait()

    def send_event(self, message):
        """
        Sends a message to the default events endpoint on the Azure IoT Hub or Azure IoT Edge instance.
        This is a synchronous event, meaning that this function will not return until the event
        has been sent to the service and the service has acknowledged receipt of the event.

        If the connection to the service has not previously been opened by a call to connect, this
        function will open the connection before sending the event.

        :param message: The actual message to send.
        """

        send_complete = Event()

        def callback():
            send_complete.set()

        self._transport.send_event(message, callback)
        send_complete.wait()

    def _emit_connection_status(self):
        """
        The connection status is emitted whenever the client on the module gets connected or disconnected.
        """
        logger.info("emit_connection_status: {}".format(self.state))
        if self.on_connection_state:
            self.on_connection_state(self.state)
        else:
            logger.warn("No callback defined for sending state")

    def _handle_transport_connected_state(self, new_state):
        self.state = new_state
        self._emit_connection_status()

    def _handle_transport_event_sent(self):
        logger.info("_handle_transport_event_sent: " + str(self.on_event_sent))
        if self.on_event_sent:
            self.on_event_sent()

    @classmethod
    def from_authentication_provider(cls, authentication_provider, transport_name):
        """
        Creates a device client with the specified authentication provider and transport

        When creating the client, you need to pass in an authorization provider and a transport_name

        The authentication_provider parameter is an object created using the authentication_provider_factory
        module.  It knows where to connect (a network address), how to authenticate with the service
        (a set of credentials), and, if necessary, the protocol gateway to use when communicating
        with the service.

        The transport_name is a string which defines the name of the transport to use when connecting
        with the service or the protocol gateway.

        Currently "mqtt" is the only supported transport.

        :param authentication_provider: The authentication provider
        :param transport_name: The name of the transport that the client will use.
        """
        if transport_name == "mqtt":
            transport = MQTTTransport(authentication_provider)
        else:
            raise NotImplementedError(
                "No specific transport can be instantiated based on the choice."
            )
        return cls(authentication_provider, transport)


# This is where we add our _async functions to InternalClient.  We do this at runtime
# by adding them to the InternalClient prototype, using what the python community calls
# "monkeypatching".  If we're running on python 2.7, the import will throw a SyntaxError
# and we'll just carry on without the _async functions.
#
# Don't worry, adding them to InternalClient at runtime will also add them to DeviceClient
# and ModuleClient.  Python has a module cache like node, so the first time anyone imports
# internal_client.py (to use it for a base class, for instance), it will monkeypatch it here
# and use the patched class definition for anyone else who imports internal_client.py
try:
    from .async_internal_client import monkeypatch

    monkeypatch()
except SyntaxError:
    logger.info("python interpreter does not support async.  Not adding async methods.")
else:
    logger.info("Addded _async methods to client object")
