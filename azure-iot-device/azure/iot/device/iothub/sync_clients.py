# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains user-facing synchronous clients for the
Azure IoTHub Device SDK for Python.
"""

import logging
from .abstract_clients import (
    AbstractIoTHubClient,
    AbstractIoTHubDeviceClient,
    AbstractIoTHubModuleClient,
)
from .models import Message
from .inbox_manager import InboxManager
from .sync_inbox import SyncClientInbox
from .pipeline import constant
from azure.iot.device.common.evented_callback import EventedCallback

logger = logging.getLogger(__name__)


class GenericIoTHubClient(AbstractIoTHubClient):
    """A superclass representing a generic synchronous client.
    This class needs to be extended for specific clients.
    """

    def __init__(self, **kwargs):
        """Initializer for a generic synchronous client.

        This initializer should not be called directly.
        Instead, use one of the 'create_from_' classmethods to instantiate

        TODO: How to document kwargs?
        Possible values: iothub_pipeline, edge_pipeline
        """
        # Depending on the subclass calling this __init__, there could be different arguments,
        # and the super() call could call a different class, due to the different MROs
        # in the class hierarchies of different clients. Thus, args here must be passed along as
        # **kwargs.
        super(GenericIoTHubClient, self).__init__(**kwargs)
        self._inbox_manager = InboxManager(inbox_type=SyncClientInbox)
        self._iothub_pipeline.on_connected = self._on_connected
        self._iothub_pipeline.on_disconnected = self._on_disconnected
        self._iothub_pipeline.on_method_request_received = self._inbox_manager.route_method_request
        self._iothub_pipeline.on_twin_patch_received = self._inbox_manager.route_twin_patch

    def _on_connected(self):
        """Helper handler that is called upon an iothub pipeline connect"""
        logger.info("Connection State - Connected")

    def _on_disconnected(self):
        """Helper handler that is called upon an iothub pipeline disconnect"""
        logger.info("Connection State - Disconnected")
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

        callback = EventedCallback()
        self._iothub_pipeline.connect(callback=callback)
        callback.wait_for_completion()

        logger.info("Successfully connected to Hub")

    def disconnect(self):
        """Disconnect the client from the Azure IoT Hub or Azure IoT Edge Hub instance.

        This is a synchronous call, meaning that this function will not return until the connection
        to the service has been completely closed.
        """
        logger.info("Disconnecting from Hub...")

        callback = EventedCallback()
        self._iothub_pipeline.disconnect(callback=callback)
        callback.wait_for_completion()

        logger.info("Successfully disconnected from Hub")

    def send_message(self, message):
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

        callback = EventedCallback()
        self._iothub_pipeline.send_message(message, callback=callback)
        callback.wait_for_completion()

        logger.info("Successfully sent message to Hub")

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
        if not self._iothub_pipeline.feature_enabled[constant.METHODS]:
            self._enable_feature(constant.METHODS)

        method_inbox = self._inbox_manager.get_method_request_inbox(method_name)

        logger.info("Waiting for method request...")
        method_request = method_inbox.get(block=block, timeout=timeout)
        logger.info("Received method request")
        return method_request

    def send_method_response(self, method_response):
        """Send a response to a method request via the Azure IoT Hub or Azure IoT Edge Hub.

        This is a synchronous event, meaning that this function will not return until the event
        has been sent to the service and the service has acknowledged receipt of the event.

        If the connection to the service has not previously been opened by a call to connect, this
        function will open the connection before sending the event.

        :param method_response: The MethodResponse to send.
        :type method_response: MethodResponse
        """
        logger.info("Sending method response to Hub...")

        callback = EventedCallback()
        self._iothub_pipeline.send_method_response(method_response, callback=callback)
        callback.wait_for_completion()

        logger.info("Successfully sent method response to Hub")

    def _enable_feature(self, feature_name):
        """Enable an Azure IoT Hub feature.

        This is a synchronous call, meaning that this function will not return until the feature
        has been enabled.

        :param feature_name: The name of the feature to enable.
        See azure.iot.device.common.pipeline.constant for possible values
        """
        logger.info("Enabling feature:" + feature_name + "...")

        callback = EventedCallback()
        self._iothub_pipeline.enable_feature(feature_name, callback=callback)
        callback.wait_for_completion()

        logger.info("Successfully enabled feature:" + feature_name)

    def get_twin(self):
        """
        Gets the device or module twin from the Azure IoT Hub or Azure IoT Edge Hub service.

        This is a synchronous call, meaning that this function will not return until the twin
        has been retrieved from the service.

        :returns: Twin object which was retrieved from the hub
        """
        if not self._iothub_pipeline.feature_enabled[constant.TWIN]:
            self._enable_feature(constant.TWIN)

        callback = EventedCallback(return_arg_name="twin")
        self._iothub_pipeline.get_twin(callback=callback)
        twin = callback.wait_for_completion()

        logger.info("Successfully retrieved twin")
        return twin

    def patch_twin_reported_properties(self, reported_properties_patch):
        """
        Update reported properties with the Azure IoT Hub or Azure IoT Edge Hub service.

        This is a synchronous call, meaning that this function will not return until the patch
        has been sent to the service and acknowledged.

        If the service returns an error on the patch operation, this function will raise the
        appropriate error.

        :param reported_properties_patch:
        :type reported_properties_patch: dict, str, int, float, bool, or None (JSON compatible values)
        """
        if not self._iothub_pipeline.feature_enabled[constant.TWIN]:
            self._enable_feature(constant.TWIN)

        callback = EventedCallback()
        self._iothub_pipeline.patch_twin_reported_properties(
            patch=reported_properties_patch, callback=callback
        )
        callback.wait_for_completion()

        logger.info("Successfully patched twin")

    def receive_twin_desired_properties_patch(self, block=True, timeout=None):
        """
        Receive a desired property patch via the Azure IoT Hub or Azure IoT Edge Hub.

        This is a synchronous call, which means the following:
        1. If block=True, this function will block until one of the following happens:
           * a desired proprety patch is received from the Azure IoT Hub or Azure IoT Edge Hub.
           * the timeout period, if provided, elapses.  If a timeout happens, this function will
             raise a InboxEmpty exception
        2. If block=False, this function will return any desired property patches which may have
           been received by the pipeline, but not yet returned to the application.  If no
           desired property patches have been received by the pipeline, this function will raise
           an InboxEmpty exception

        :param bool block: Indicates if the operation should block until a request is received.
           Default True.
        :param int timeout: Optionally provide a number of seconds until blocking times out.

        :raises: InboxEmpty if timeout occurs on a blocking operation.
        :raises: InboxEmpty if no request is available on a non-blocking operation.

        :returns: desired property patch.  This can be dict, str, int, float, bool, or None (JSON compatible values)
        """
        if not self._iothub_pipeline.feature_enabled[constant.TWIN_PATCHES]:
            self._enable_feature(constant.TWIN_PATCHES)
        twin_patch_inbox = self._inbox_manager.get_twin_patch_inbox()

        logger.info("Waiting for twin patches...")
        patch = twin_patch_inbox.get(block=block, timeout=timeout)
        logger.info("twin patch received")
        return patch


class IoTHubDeviceClient(GenericIoTHubClient, AbstractIoTHubDeviceClient):
    """A synchronous device client that connects to an Azure IoT Hub instance.

    Intended for usage with Python 2.7 or compatibility scenarios for Python 3.5.3+.
    """

    def __init__(self, iothub_pipeline):
        """Initializer for a IoTHubDeviceClient.

        This initializer should not be called directly.
        Instead, use one of the 'create_from_' classmethods to instantiate

        :param iothub_pipeline: The pipeline used to connect to the IoTHub endpoint.
        :type iothub_pipeline: IoTHubPipeline
        """
        super(IoTHubDeviceClient, self).__init__(iothub_pipeline=iothub_pipeline)
        self._iothub_pipeline.on_c2d_message_received = self._inbox_manager.route_c2d_message

    def receive_message(self, block=True, timeout=None):
        """Receive a message that has been sent from the Azure IoT Hub.

        :param bool block: Indicates if the operation should block until a message is received.
        Default True.
        :param int timeout: Optionally provide a number of seconds until blocking times out.

        :raises: InboxEmpty if timeout occurs on a blocking operation.
        :raises: InboxEmpty if no message is available on a non-blocking operation.

        :returns: Message that was sent from the Azure IoT Hub.
        """
        if not self._iothub_pipeline.feature_enabled[constant.C2D_MSG]:
            self._enable_feature(constant.C2D_MSG)
        c2d_inbox = self._inbox_manager.get_c2d_message_inbox()

        logger.info("Waiting for message from Hub...")
        message = c2d_inbox.get(block=block, timeout=timeout)
        logger.info("Message received")
        return message


class IoTHubModuleClient(GenericIoTHubClient, AbstractIoTHubModuleClient):
    """A synchronous module client that connects to an Azure IoT Hub or Azure IoT Edge instance.

    Intended for usage with Python 2.7 or compatibility scenarios for Python 3.5.3+.
    """

    def __init__(self, iothub_pipeline, edge_pipeline=None):
        """Intializer for a IoTHubModuleClient.

        This initializer should not be called directly.
        Instead, use one of the 'create_from_' classmethods to instantiate

        :param iothub_pipeline: The pipeline used to connect to the IoTHub endpoint.
        :type iothub_pipeline: IoTHubPipeline
        :param edge_pipeline: (OPTIONAL) The pipeline used to connect to the Edge endpoint.
        :type edge_pipeline: EdgePipeline
        """
        super(IoTHubModuleClient, self).__init__(
            iothub_pipeline=iothub_pipeline, edge_pipeline=edge_pipeline
        )
        self._iothub_pipeline.on_input_message_received = self._inbox_manager.route_input_message

    def send_message_to_output(self, message, output_name):
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

        callback = EventedCallback()
        self._iothub_pipeline.send_output_event(message, callback=callback)
        callback.wait_for_completion()

        logger.info("Successfully sent message to output: " + output_name)

    def receive_message_on_input(self, input_name, block=True, timeout=None):
        """Receive an input message that has been sent from another Module to a specific input.

        :param str input_name: The input name to receive a message on.
        :param bool block: Indicates if the operation should block until a message is received.
        Default True.
        :param int timeout: Optionally provide a number of seconds until blocking times out.

        :raises: InboxEmpty if timeout occurs on a blocking operation.
        :raises: InboxEmpty if no message is available on a non-blocking operation.

        :returns: Message that was sent to the specified input.
        """
        if not self._iothub_pipeline.feature_enabled[constant.INPUT_MSG]:
            self._enable_feature(constant.INPUT_MSG)
        input_inbox = self._inbox_manager.get_input_message_inbox(input_name)

        logger.info("Waiting for input message on: " + input_name + "...")
        message = input_inbox.get(block=block, timeout=timeout)
        logger.info("Input message received on: " + input_name)
        return message
