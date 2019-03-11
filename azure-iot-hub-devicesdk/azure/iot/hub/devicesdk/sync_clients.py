# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains user-facing synchronous clients for the
Azure IoTHub Device SDK for Python.
"""

import logging
import six
import weakref
from threading import Event
from .transport.mqtt import MQTTTransport
from .transport import constant
from .message import Message
from .inbox_manager import InboxManager
from .sync_inbox import SyncClientInbox

logger = logging.getLogger(__name__)

__all__ = ["DeviceClient", "ModuleClient"]


class GenericClient(object):
    """A superclass representing a generic client. This class needs to be extended for specific clients."""

    def __init__(self, transport):
        """Initializer for a generic client.

        :param transport: The transport that the client will use.
        """
        self._transport = transport
        self._transport.on_transport_connected = self._state_change
        self._transport.on_transport_disconnected = self._state_change
        self.state = "initial"

    def _state_change(self, new_state):
        """Handler to be called by the transport upon a connection state change."""
        self.state = new_state
        logger.info("Connection State - {}".format(self.state))

    @classmethod
    def from_authentication_provider(cls, authentication_provider, transport_name):
        """Creates a device client with the specified authentication provider and transport.

        When creating the client, you need to pass in an authorization provider and a transport_name.

        The authentication_provider parameter is an object created using the authentication_provider_factory
        module.  It knows where to connect (a network address), how to authenticate with the service
        (a set of credentials), and, if necessary, the protocol gateway to use when communicating
        with the service.

        The transport_name is a string which defines the name of the transport to use when connecting
        with the service or the protocol gateway.

        Currently "mqtt" is the only supported transport.

        :param authentication_provider: The authentication provider.
        :param transport_name: The name of the transport that the client will use.

        :returns: Instance of the client.

        :raises: ValueError if given an invalid transport_name.
        :raises: NotImplementedError if transport_name is "amqp" or "http".
        """
        transport_name = transport_name.lower()
        if transport_name == "mqtt":
            transport = MQTTTransport(authentication_provider)
        elif transport_name == "amqp" or transport_name == "http":
            raise NotImplementedError("This transport has not yet been implemented")
        else:
            raise ValueError("No specific transport can be instantiated based on the choice.")
        return cls(transport)


class GenericClientSync(GenericClient):
    """A superclass representing a generic synchronous client. This class needs to be extended for specific clients.
    """

    def __init__(self, transport):
        """Initializer for a generic synchronous client.

        This initializer should not be called directly.
        Instead, the class method `from_authentication_provider` should be used to create a client object.

        :param transport: The transport that the client will use.
        """
        super(GenericClientSync, self).__init__(transport)
        self._inbox_manager = InboxManager(inbox_type=SyncClientInbox)

    def connect(self):
        """Connects the client to an Azure IoT Hub or Azure IoT Edge Hub instance.

        The destination is chosen based on the credentials passed via the auth_provider parameter
        that was provided when this object was initialized.

        This is a synchronous call, meaning that this function will not return until the connection
        to the service has been completely established.
        """
        logger.info("Connecting to Hub...")

        connect_complete = Event()

        def callback():
            connect_complete.set()
            logger.info("Successfully connected to Hub")

        self._transport.connect(callback=callback)
        connect_complete.wait()

    def disconnect(self):
        """Disconnect the client from the Azure IoT Hub or Azure IoT Edge Hub instance.

        This is a synchronous call, meaning that this function will not return until the connection
        to the service has been completely closed.
        """
        logger.info("Disconnecting from Hub...")

        disconnect_complete = Event()

        def callback():
            disconnect_complete.set()
            logger.info("Successfully disconnected from Hub")

        self._transport.disconnect(callback=callback)
        disconnect_complete.wait()

    def send_event(self, message):
        """Sends a message to the default events endpoint on the Azure IoT Hub or Azure IoT Edge Hub instance.

        This is a synchronous event, meaning that this function will not return until the event
        has been sent to the service and the service has acknowledged receipt of the event.

        If the connection to the service has not previously been opened by a call to connect, this
        function will open the connection before sending the event.

        :param message: The actual message to send. Anything passed that is not an instance of the
        Message class will be converted to Message object.
        """
        if not isinstance(message, Message):
            message = Message(message)

        logger.info("Sending message to Hub...")
        send_complete = Event()

        def callback():
            send_complete.set()
            logger.info("Successfully sent message to Hub")

        self._transport.send_event(message, callback=callback)
        send_complete.wait()

    def _enable_feature(self, feature_name):
        """Enable an Azure IoT Hub feature in the transport.

        This is a synchronous call, meaning that this function will not return until the feature
        has been enabled.

        :param feature_name: The name of the feature to enable.
        See azure.iot.hub.devicesdk.transport.constant for possible values
        """
        logger.info("Enabling feature:" + feature_name + "...")
        enable_complete = Event()

        def callback():
            enable_complete.set()
            logger.info("Successfully enabled feature:" + feature_name)

        self._transport.enable_feature(feature_name, callback=callback)
        enable_complete.wait()


class DeviceClient(GenericClientSync):
    """A synchronous device client that connects to an Azure IoT Hub instance.

    Intended for usage with Python 2.7 or compatibility scenarios for Python 3.5.3+.

    :ivar state: The current connection state
    """

    def __init__(self, transport):
        """Initializer for a DeviceClient.

        This initializer should not be called directly.
        Instead, the class method `from_authentication_provider` should be used to create a client object.

        :param transport: The transport that the client will use.
        """
        super(DeviceClient, self).__init__(transport)
        self._transport.on_transport_c2d_message_received = self._inbox_manager.route_c2d_message

    def receive_c2d_message(self, block=True, timeout=None):
        """Receive a C2D message that has been sent from the Azure IoT Hub.

        :param bool block: Indicates if the operation should block until a message is received.
        Default True.
        :param int timeout: Optionally provide a number of seconds until blocking times out.

        :raises: InboxEmpty if timeout occurs on a blocking operation.
        :raises: InboxEmpty if no message is available on a non-blocking operation.

        :returns: Message that was sent from the Azure IoT Hub.
        """
        if not self._transport.feature_enabled[constant.C2D_MSG]:
            self._enable_feature(constant.C2D_MSG)
        c2d_inbox = self._inbox_manager.get_c2d_message_inbox()

        logger.info("Waiting for C2D message...")
        message = c2d_inbox.get(block=block, timeout=timeout)
        logger.info("C2D message received")
        return message


class ModuleClient(GenericClientSync):
    """A synchronous module client that connects to an Azure IoT Hub or Azure IoT Edge instance.

    Intended for usage with Python 2.7 or compatibility scenarios for Python 3.5.3+.

    :ivar state: The current connection state.
    """

    def __init__(self, transport):
        """Intializer for a ModuleClient.

        This initializer should not be called directly.
        Instead, the class method `from_authentication_provider` should be used to create a client object.

        :param transport: The transport that the client will use.
        """
        super(ModuleClient, self).__init__(transport)
        self._transport.on_transport_input_message_received = (
            self._inbox_manager.route_input_message
        )

    def send_to_output(self, message, output_name):
        """Sends an event/message to the given module output.

        These are outgoing events and are meant to be "output events".

        This is a synchronous event, meaning that this function will not return until the event
        has been sent to the service and the service has acknowledged receipt of the event.

        If the connection to the service has not previously been opened by a call to connect, this
        function will open the connection before sending the event.

        :param message: message to send to the given output. Anything passed that is not an instance of the
        Message class will be converted to Message object.
        :param output_name: Name of the output to send the event to.
        """
        if not isinstance(message, Message):
            message = Message(message)
        message.output_name = output_name

        logger.info("Sending message to output:" + output_name + "...")
        send_complete = Event()

        def callback():
            logger.info("Successfully sent message to output: " + output_name)
            send_complete.set()

        self._transport.send_output_event(message, callback)
        send_complete.wait()

    def receive_input_message(self, input_name, block=True, timeout=None):
        """Receive an input message that has been sent from another Module to a specific input.

        :param str input_name: The input name to receive a message on.
        :param bool block: Indicates if the operation should block until a message is received.
        Default True.
        :param int timeout: Optionally provide a number of seconds until blocking times out.

        :raises: InboxEmpty if timeout occurs on a blocking operation.
        :raises: InboxEmpty if no message is available on a non-blocking operation.

        :returns: Message that was sent to the specified input.
        """
        if not self._transport.feature_enabled[constant.INPUT_MSG]:
            self._enable_feature(constant.INPUT_MSG)
        input_inbox = self._inbox_manager.get_input_message_inbox(input_name)

        logger.info("Waiting for input message on: " + input_name + "...")
        message = input_inbox.get(block=block, timeout=timeout)
        logger.info("Input message received on: " + input_name)
        return message
