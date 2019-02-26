# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains user-facing asynchronous clients for the
Azure IoTHub Device SDK for Python.
"""

import logging
from azure.iot.hub.devicesdk.transport.mqtt import MQTTTransportAsync
from azure.iot.hub.devicesdk.sync_clients import GenericClient
from azure.iot.hub.devicesdk import Message

logger = logging.getLogger(__name__)

__all__ = ["DeviceClient", "ModuleClient"]


class GenericClientAsync(GenericClient):
    """A super class representing a generic asynchronous client. This class needs to be extended for specific clients."""

    @classmethod
    async def from_authentication_provider(cls, authentication_provider, transport_name):
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
        """
        transport_name = transport_name.lower()
        if transport_name == "mqtt":
            transport = MQTTTransportAsync(authentication_provider)
        elif transport_name == "amqp" or transport_name == "http":
            raise NotImplementedError("This transport has not yet been implemented")
        else:
            raise ValueError("No specific transport can be instantiated based on the choice.")
        return cls(transport)

    async def connect(self):
        """Connects the client to an Azure IoT Hub or Azure IoT Edge instance.

        The destination is chosen based on the credentials passed via the auth_provider parameter
        that was provided when this object was initialized.
        """
        await self._transport.connect()

    async def disconnect(self):
        """Disconnect the client from the Azure IoT Hub or Azure IoT Edge instance.
        """
        await self._transport.disconnect()

    async def send_event(self, message):
        """Sends a message to the default events endpoint on the Azure IoT Hub or Azure IoT Edge instance.

        If the connection to the service has not previously been opened by a call to connect, this
        function will open the connection before sending the event.

        :param message: The actual message to send. Anything passed that is not an instance of the
        Message class will be converted to Message object.
        """
        if not isinstance(message, Message):
            message = Message(message)
        await self._transport.send_event(message)


class DeviceClient(GenericClientAsync):
    """An asynchronous device client that connects to an Azure IoT Hub instance.

    Intended for usage with Python 3.5.3+

    :ivar state: The current connection state
    """

    pass


class ModuleClient(GenericClientAsync):
    """An asynchronous module client that connects to an Azure IoT Hub or Azure IoT Edge instance.

    Intended for usage with Python 3.5.3+

    :ivar state: The current connection state
    """

    async def send_to_output(self, message, output_name):
        """Sends an event/message to the given module output.

        These are outgoing events and are meant to be "output events"

        If the connection to the service has not previously been opened by a call to connect, this
        function will open the connection before sending the event.

        :param message: message to send to the given output. Anything passed that is not an instance of the
        Message class will be converted to Message object.
        :param output_name: Name of the output to send the event to.
        """
        if not isinstance(message, Message):
            message = Message(message)
        message.output_name = output_name
        await self._transport.send_output_event(message)
