# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains user-facing synchronous clients for the
Azure IoTHub Device SDK for Python.
"""

import logging
from threading import Event
from .abstract_clients import (
    AbstractIoTHubClient,
    AbstractIoTHubDeviceClient,
    AbstractIoTHubModuleClient,
)
from .models import Message
from .inbox_manager import InboxManager
from .sync_inbox import SyncClientInbox
from azure.iot.device.common.transport import constant

logger = logging.getLogger(__name__)


class GenericIoTHubClient(AbstractIoTHubClient):
    """A superclass representing a generic synchronous client.
    This class needs to be extended for specific clients.
    """

    def __init__(self, transport):
        """Initializer for a generic synchronous client.

        This initializer should not be called directly.
        Instead, the class method `from_authentication_provider` should be used to create a client object.

        :param transport: The transport that the client will use.
        """
        super(GenericIoTHubClient, self).__init__(transport)
        self._inbox_manager = InboxManager(inbox_type=SyncClientInbox)
        self._transport.on_transport_connected = self._on_state_change
        self._transport.on_transport_disconnected = self._on_state_change
        self._transport.on_transport_method_request_received = (
            self._inbox_manager.route_method_request
        )

    def _on_state_change(self, new_state):
        """Handler to be called by the transport upon a connection state change."""
        logger.info("Connection State - {}".format(new_state))

        if new_state == "disconnected":
            self._on_disconnected()

    def _on_disconnected(self):
        """Helper handler that is called upon a a transport disconnect"""
        self._inbox_manager.clear_all_method_requests()
        logger.info("Cleared all pending method requests due to disconnect")

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

    def receive_method_request(self, method_name=None, block=True, timeout=None):
        """Receive a method request via the Azure IoT Hub or Azure IoT Edge Hub.

        :param str method_name: Optionally provide the name of the method to receive requests for.
        If this parameter is not given, all methods not already being specifically targeted by
        a different request to receive_method will be received.
        :param bool block: Indicates if the operation should block until a request is received.
        Default True.
        :param int timeout: Optionally provide a number of seconds until blocking times out.

        :raises: InboxEmpty if timeout occurs on a blocking operation.
        :raises: InboxEmpty if no request is available on a non-blocking operation.

        :returns: MethodRequest object representing the received method request.
        """
        if not self._transport.feature_enabled[constant.METHODS]:
            self._enable_feature(constant.METHODS)

        method_inbox = self._inbox_manager.get_method_request_inbox(method_name)

        logger.info("Waiting for method request...")
        method_call = method_inbox.get(block=block, timeout=timeout)
        logger.info("Received method request")
        return method_call

    def send_method_response(self, method_request, payload, status):
        """Send a response to a method request via the Azure IoT Hub or Azure IoT Edge Hub.

        :param method_request: MethodRequest object representing the method request being
        responded to.
        :param payload: The desired payload for the method response.
        :param int status: The desired return status code for the method response.
        """
        logger.info("Sending method response to Hub...")
        send_complete = Event()

        def callback():
            send_complete.set()
            logger.info("Successfully sent method response to Hub")

        # TODO: maybe consolidate method_request, result and status into a new object
        self._transport.send_method_response(method_request, payload, status, callback=callback)
        send_complete.wait()

    def _enable_feature(self, feature_name):
        """Enable an Azure IoT Hub feature in the transport.

        This is a synchronous call, meaning that this function will not return until the feature
        has been enabled.

        :param feature_name: The name of the feature to enable.
        See azure.iot.device.common.transport.constant for possible values
        """
        logger.info("Enabling feature:" + feature_name + "...")
        enable_complete = Event()

        def callback():
            enable_complete.set()
            logger.info("Successfully enabled feature:" + feature_name)

        self._transport.enable_feature(feature_name, callback=callback)
        enable_complete.wait()


class IoTHubDeviceClient(GenericIoTHubClient, AbstractIoTHubDeviceClient):
    """A synchronous device client that connects to an Azure IoT Hub instance.

    Intended for usage with Python 2.7 or compatibility scenarios for Python 3.5.3+.
    """

    def __init__(self, transport):
        """Initializer for a IoTHubDeviceClient.

        This initializer should not be called directly.
        Instead, the class method `from_authentication_provider` should be used to create a client object.

        :param transport: The transport that the client will use.
        """
        super(IoTHubDeviceClient, self).__init__(transport)
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


class IoTHubModuleClient(GenericIoTHubClient, AbstractIoTHubModuleClient):
    """A synchronous module client that connects to an Azure IoT Hub or Azure IoT Edge instance.

    Intended for usage with Python 2.7 or compatibility scenarios for Python 3.5.3+.
    """

    def __init__(self, transport):
        """Intializer for a IoTHubModuleClient.

        This initializer should not be called directly.
        Instead, the class method `from_authentication_provider` should be used to create a client object.

        :param transport: The transport that the client will use.
        """
        super(IoTHubModuleClient, self).__init__(transport)
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
