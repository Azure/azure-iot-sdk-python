# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains user-facing asynchronous clients for the
Azure IoTHub Device SDK for Python.
"""

import logging
from azure.iot.common import async_adapter
from azure.iot.hub.devicesdk.sync_clients import GenericClient
from azure.iot.hub.devicesdk import Message
from azure.iot.hub.devicesdk.transport import constant
from azure.iot.hub.devicesdk.inbox_manager import InboxManager
from .async_inbox import AsyncClientInbox

logger = logging.getLogger(__name__)

__all__ = ["DeviceClient", "ModuleClient"]


class GenericClientAsync(GenericClient):
    """A super class representing a generic asynchronous client. This class needs to be extended for specific clients."""

    def __init__(self, transport):
        """Initializer for a generic asynchronous client.

        This initializer should not be called directly.
        Instead, the class method `from_authentication_provider` should be used to create a client object.

        :param transport: The transport that the client will use.
        """
        super().__init__(transport)
        self._inbox_manager = InboxManager(inbox_type=AsyncClientInbox)

    async def connect(self):
        """Connects the client to an Azure IoT Hub or Azure IoT Edge Hub instance.

        The destination is chosen based on the credentials passed via the auth_provider parameter
        that was provided when this object was initialized.
        """
        logger.info("Connecting to Hub...")
        connect_async = async_adapter.emulate_async(self._transport.connect)

        def sync_callback():
            logger.info("Successfully connected to Hub")

        callback = async_adapter.AwaitableCallback(sync_callback)

        await connect_async(callback=callback)
        await callback.completion()

    async def disconnect(self):
        """Disconnect the client from the Azure IoT Hub or Azure IoT Edge Hub instance.
        """
        logger.info("Disconnecting from Hub...")
        disconnect_async = async_adapter.emulate_async(self._transport.disconnect)

        def sync_callback():
            logger.info("Successfully disconnected from Hub")

        callback = async_adapter.AwaitableCallback(sync_callback)

        await disconnect_async(callback=callback)
        await callback.completion()

    async def send_event(self, message):
        """Sends a message to the default events endpoint on the Azure IoT Hub or Azure IoT Edge Hub instance.

        If the connection to the service has not previously been opened by a call to connect, this
        function will open the connection before sending the event.

        :param message: The actual message to send. Anything passed that is not an instance of the
        Message class will be converted to Message object.
        """
        if not isinstance(message, Message):
            message = Message(message)

        logger.info("Sending message to Hub...")
        send_event_async = async_adapter.emulate_async(self._transport.send_event)

        def sync_callback():
            logger.info("Successfully sent message to Hub")

        callback = async_adapter.AwaitableCallback(sync_callback)

        await send_event_async(message, callback=callback)
        await callback.completion()

    async def _enable_feature(self, feature_name):
        """Enable an Azure IoT Hub feature in the transport

        :param feature_name: The name of the feature to enable.
        See azure.iot.hub.devicesdk.transport.constant for possible values.
        """
        logger.info("Enabling feature:" + feature_name + "...")
        enable_feature_async = async_adapter.emulate_async(self._transport.enable_feature)

        def sync_callback():
            logger.info("Successfully enabled feature:" + feature_name)

        callback = async_adapter.AwaitableCallback(sync_callback)

        await enable_feature_async(feature_name, callback=callback)


class DeviceClient(GenericClientAsync):
    """An asynchronous device client that connects to an Azure IoT Hub instance.

    Intended for usage with Python 3.5.3+

    :ivar state: The current connection state
    """

    def __init__(self, transport):
        super().__init__(transport)
        self._transport.on_transport_c2d_message_received = self._inbox_manager.route_c2d_message

    async def receive_c2d_message(self):
        """Receive a C2D message that has been sent from the Azure IoT Hub.

        If no message is yet available, will wait until an item is available.

        :returns: Message that was sent from the Azure IoT Hub.
        """
        if not self._transport.feature_enabled[constant.C2D_MSG]:
            await self._enable_feature(constant.C2D_MSG)
        c2d_inbox = self._inbox_manager.get_c2d_message_inbox()

        logger.info("Waiting for C2D message...")
        message = await c2d_inbox.get()
        logger.info("C2D message received")
        return message


class ModuleClient(GenericClientAsync):
    """An asynchronous module client that connects to an Azure IoT Hub or Azure IoT Edge instance.

    Intended for usage with Python 3.5.3+

    :ivar state: The current connection state
    """

    def __init__(self, transport):
        super().__init__(transport)
        self._transport.on_transport_input_message_received = (
            self._inbox_manager.route_input_message
        )

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

        logger.info("Sending message to output:" + output_name + "...")
        send_output_event_async = async_adapter.emulate_async(self._transport.send_output_event)

        def sync_callback():
            logger.info("Successfully sent message to output: " + output_name)

        callback = async_adapter.AwaitableCallback(sync_callback)

        await send_output_event_async(message, callback)
        await callback.completion()

    async def receive_input_message(self, input_name):
        """Receive an input message that has been sent from another Module to a specific input.

        If no message is yet available, will wait until an item is available.

        :param str input_name: The input name to receive a message on.
        :returns: Message that was sent to the specified input.
        """
        if not self._transport.feature_enabled[constant.INPUT_MSG]:
            await self._enable_feature(constant.INPUT_MSG)
        inbox = self._inbox_manager.get_input_message_inbox(input_name)

        logger.info("Waiting for input message on: " + input_name + "...")
        message = await inbox.get()
        logger.info("Input message received on: " + input_name)
        return message
