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
from .sync_inbox import SyncClientInbox, InboxEmpty
from .pipeline import constant as pipeline_constant
from .pipeline import exceptions as pipeline_exceptions
from azure.iot.device import exceptions
from azure.iot.device.common.evented_callback import EventedCallback
from azure.iot.device.common.callable_weak_method import CallableWeakMethod

logger = logging.getLogger(__name__)


def handle_result(callback):
    try:
        return callback.wait_for_completion()
    except pipeline_exceptions.ConnectionDroppedError as e:
        raise exceptions.ConnectionDroppedError(message="Lost connection to IoTHub", cause=e)
    except pipeline_exceptions.ConnectionFailedError as e:
        raise exceptions.ConnectionFailedError(message="Could not connect to IoTHub", cause=e)
    except pipeline_exceptions.UnauthorizedError as e:
        raise exceptions.CredentialError(message="Credentials invalid, could not connect", cause=e)
    except pipeline_exceptions.ProtocolClientError as e:
        raise exceptions.ClientError(message="Error in the IoTHub client", cause=e)
    except Exception as e:
        raise exceptions.ClientError(message="Unexpected failure", cause=e)


class GenericIoTHubClient(AbstractIoTHubClient):
    """A superclass representing a generic synchronous client.
    This class needs to be extended for specific clients.
    """

    def __init__(self, **kwargs):
        """Initializer for a generic synchronous client.

        This initializer should not be called directly.
        Instead, use one of the 'create_from_' classmethods to instantiate

        :param iothub_pipeline: The IoTHubPipeline used for the client
        :type iothub_pipeline: :class:`azure.iot.device.iothub.pipeline.IoTHubPipeline`
        :param http_pipeline: The HTTPPipeline used for the client
        :type http_pipeline: :class:`azure.iot.device.iothub.pipeline.HTTPPipeline`
        """
        # Depending on the subclass calling this __init__, there could be different arguments,
        # and the super() call could call a different class, due to the different MROs
        # in the class hierarchies of different clients. Thus, args here must be passed along as
        # **kwargs.
        super(GenericIoTHubClient, self).__init__(**kwargs)
        self._inbox_manager = InboxManager(inbox_type=SyncClientInbox)
        self._iothub_pipeline.on_connected = CallableWeakMethod(self, "_on_connected")
        self._iothub_pipeline.on_disconnected = CallableWeakMethod(self, "_on_disconnected")
        self._iothub_pipeline.on_method_request_received = CallableWeakMethod(
            self._inbox_manager, "route_method_request"
        )
        self._iothub_pipeline.on_twin_patch_received = CallableWeakMethod(
            self._inbox_manager, "route_twin_patch"
        )

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

        :raises: :class:`azure.iot.device.exceptions.CredentialError` if credentials are invalid
            and a connection cannot be established.
        :raises: :class:`azure.iot.device.exceptions.ConnectionFailedError` if a establishing a
            connection results in failure.
        :raises: :class:`azure.iot.device.exceptions.ConnectionDroppedError` if connection is lost
            during execution.
        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        logger.info("Connecting to Hub...")

        callback = EventedCallback()
        self._iothub_pipeline.connect(callback=callback)
        handle_result(callback)

        logger.info("Successfully connected to Hub")

    def disconnect(self):
        """Disconnect the client from the Azure IoT Hub or Azure IoT Edge Hub instance.

        This is a synchronous call, meaning that this function will not return until the connection
        to the service has been completely closed.

        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        logger.info("Disconnecting from Hub...")

        callback = EventedCallback()
        self._iothub_pipeline.disconnect(callback=callback)
        handle_result(callback)

        logger.info("Successfully disconnected from Hub")

    def send_message(self, message):
        """Sends a message to the default events endpoint on the Azure IoT Hub or Azure IoT Edge Hub instance.

        This is a synchronous event, meaning that this function will not return until the event
        has been sent to the service and the service has acknowledged receipt of the event.

        If the connection to the service has not previously been opened by a call to connect, this
        function will open the connection before sending the event.

        :param message: The actual message to send. Anything passed that is not an instance of the
            Message class will be converted to Message object.
        :type message: :class:`azure.iot.device.Message` or str

        :raises: :class:`azure.iot.device.exceptions.CredentialError` if credentials are invalid
            and a connection cannot be established.
        :raises: :class:`azure.iot.device.exceptions.ConnectionFailedError` if a establishing a
            connection results in failure.
        :raises: :class:`azure.iot.device.exceptions.ConnectionDroppedError` if connection is lost
            during execution.
        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        if not isinstance(message, Message):
            message = Message(message)

        logger.info("Sending message to Hub...")

        callback = EventedCallback()
        self._iothub_pipeline.send_message(message, callback=callback)
        handle_result(callback)

        logger.info("Successfully sent message to Hub")

    def receive_method_request(self, method_name=None, block=True, timeout=None):
        """Receive a method request via the Azure IoT Hub or Azure IoT Edge Hub.

        :param str method_name: Optionally provide the name of the method to receive requests for.
            If this parameter is not given, all methods not already being specifically targeted by
            a different request to receive_method will be received.
        :param bool block: Indicates if the operation should block until a request is received.
        :param int timeout: Optionally provide a number of seconds until blocking times out.

        :returns: MethodRequest object representing the received method request, or None if
            no method request has been received by the end of the blocking period.
        """
        if not self._iothub_pipeline.feature_enabled[pipeline_constant.METHODS]:
            self._enable_feature(pipeline_constant.METHODS)

        method_inbox = self._inbox_manager.get_method_request_inbox(method_name)

        logger.info("Waiting for method request...")
        try:
            method_request = method_inbox.get(block=block, timeout=timeout)
        except InboxEmpty:
            method_request = None
        logger.info("Received method request")
        return method_request

    def send_method_response(self, method_response):
        """Send a response to a method request via the Azure IoT Hub or Azure IoT Edge Hub.

        This is a synchronous event, meaning that this function will not return until the event
        has been sent to the service and the service has acknowledged receipt of the event.

        If the connection to the service has not previously been opened by a call to connect, this
        function will open the connection before sending the event.

        :param method_response: The MethodResponse to send.
        :type method_response: :class:`azure.iot.device.MethodResponse`

        :raises: :class:`azure.iot.device.exceptions.CredentialError` if credentials are invalid
            and a connection cannot be established.
        :raises: :class:`azure.iot.device.exceptions.ConnectionFailedError` if a establishing a
            connection results in failure.
        :raises: :class:`azure.iot.device.exceptions.ConnectionDroppedError` if connection is lost
            during execution.
        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        logger.info("Sending method response to Hub...")

        callback = EventedCallback()
        self._iothub_pipeline.send_method_response(method_response, callback=callback)
        handle_result(callback)

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

        :returns: Complete Twin as a JSON dict
        :rtype: dict

        :raises: :class:`azure.iot.device.exceptions.CredentialError` if credentials are invalid
            and a connection cannot be established.
        :raises: :class:`azure.iot.device.exceptions.ConnectionFailedError` if a establishing a
            connection results in failure.
        :raises: :class:`azure.iot.device.exceptions.ConnectionDroppedError` if connection is lost
            during execution.
        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        if not self._iothub_pipeline.feature_enabled[pipeline_constant.TWIN]:
            self._enable_feature(pipeline_constant.TWIN)

        callback = EventedCallback(return_arg_name="twin")
        self._iothub_pipeline.get_twin(callback=callback)
        twin = handle_result(callback)

        logger.info("Successfully retrieved twin")
        return twin

    def patch_twin_reported_properties(self, reported_properties_patch):
        """
        Update reported properties with the Azure IoT Hub or Azure IoT Edge Hub service.

        This is a synchronous call, meaning that this function will not return until the patch
        has been sent to the service and acknowledged.

        If the service returns an error on the patch operation, this function will raise the
        appropriate error.

        :param reported_properties_patch: Twin Reported Properties patch as a JSON dict
        :type reported_properties_patch: dict

        :raises: :class:`azure.iot.device.exceptions.CredentialError` if credentials are invalid
            and a connection cannot be established.
        :raises: :class:`azure.iot.device.exceptions.ConnectionFailedError` if a establishing a
            connection results in failure.
        :raises: :class:`azure.iot.device.exceptions.ConnectionDroppedError` if connection is lost
            during execution.
        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        if not self._iothub_pipeline.feature_enabled[pipeline_constant.TWIN]:
            self._enable_feature(pipeline_constant.TWIN)

        callback = EventedCallback()
        self._iothub_pipeline.patch_twin_reported_properties(
            patch=reported_properties_patch, callback=callback
        )
        handle_result(callback)

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
        :param int timeout: Optionally provide a number of seconds until blocking times out.

        :returns: Twin Desired Properties patch as a JSON dict, or None if no patch has been
            received by the end of the blocking period
        :rtype: dict or None
        """
        if not self._iothub_pipeline.feature_enabled[pipeline_constant.TWIN_PATCHES]:
            self._enable_feature(pipeline_constant.TWIN_PATCHES)
        twin_patch_inbox = self._inbox_manager.get_twin_patch_inbox()

        logger.info("Waiting for twin patches...")
        try:
            patch = twin_patch_inbox.get(block=block, timeout=timeout)
        except InboxEmpty:
            return None
        logger.info("twin patch received")
        return patch

    def get_storage_info(self, blob_name):
        """Call up to the IoT Hub Endpoint over HTTP to get information on
        the storage blob for uploads.
        """
        # TODO: Check that the HTTP Pipeline has been set properly.
        # if not self._http_pipeline:
        #     # raise error
        #     raise exceptions.ClientError(
        #         "No Upload Pipeline Initialized. get_storage_info cannot be called without an HTTP Pipeline set."
        #     )
        # else:
        callback = EventedCallback(return_arg_name="storage_info")
        self._http_pipeline.get_storage_info(blob_name=blob_name, callback=callback)
        storage_info = handle_result(callback)
        logger.info("Successfully retrieved storage_info")
        return storage_info

    def notify_blob_upload_status(
        self, correlation_id, upload_response, status_code, status_description
    ):
        """
        """
        # if not self._http_pipeline:
        #     # raise error
        #     raise exceptions.ClientError(
        #         "No Upload Pipeline Initialized. notify_blob_upload_status cannot be called without an HTTP Pipeline set."
        #     )
        # else:
        callback = EventedCallback()
        self._http_pipeline.notify_blob_upload_status(
            correlation_id=correlation_id,
            upload_response=upload_response,
            status_code=status_code,
            status_description=status_description,
            callback=callback,
        )
        handle_result(callback)
        logger.info("Successfully notified blob upload status")


class IoTHubDeviceClient(GenericIoTHubClient, AbstractIoTHubDeviceClient):
    """A synchronous device client that connects to an Azure IoT Hub instance.

    Intended for usage with Python 2.7 or compatibility scenarios for Python 3.5.3+.
    """

    def __init__(self, iothub_pipeline, http_pipeline=None):
        """Initializer for a IoTHubDeviceClient.

        This initializer should not be called directly.
        Instead, use one of the 'create_from_' classmethods to instantiate

        :param iothub_pipeline: The pipeline used to connect to the IoTHub endpoint.
        :type iothub_pipeline: :class:`azure.iot.device.iothub.pipeline.IoTHubPipeline`
        """
        super(IoTHubDeviceClient, self).__init__(
            iothub_pipeline=iothub_pipeline, http_pipeline=http_pipeline
        )
        self._iothub_pipeline.on_c2d_message_received = CallableWeakMethod(
            self._inbox_manager, "route_c2d_message"
        )

    def receive_message(self, block=True, timeout=None):
        """Receive a message that has been sent from the Azure IoT Hub.

        :param bool block: Indicates if the operation should block until a message is received.
        :param int timeout: Optionally provide a number of seconds until blocking times out.

        :returns: Message that was sent from the Azure IoT Hub, or None if
            no method request has been received by the end of the blocking period.
        :rtype: :class:`azure.iot.device.Message` or None
        """
        if not self._iothub_pipeline.feature_enabled[pipeline_constant.C2D_MSG]:
            self._enable_feature(pipeline_constant.C2D_MSG)
        c2d_inbox = self._inbox_manager.get_c2d_message_inbox()

        logger.info("Waiting for message from Hub...")
        try:
            message = c2d_inbox.get(block=block, timeout=timeout)
        except InboxEmpty:
            message = None
        logger.info("Message received")
        return message


class IoTHubModuleClient(GenericIoTHubClient, AbstractIoTHubModuleClient):
    """A synchronous module client that connects to an Azure IoT Hub or Azure IoT Edge instance.

    Intended for usage with Python 2.7 or compatibility scenarios for Python 3.5.3+.
    """

    def __init__(self, iothub_pipeline, http_pipeline=None):
        """Intializer for a IoTHubModuleClient.

        This initializer should not be called directly.
        Instead, use one of the 'create_from_' classmethods to instantiate

        :param iothub_pipeline: The pipeline used to connect to the IoTHub endpoint.
        :type iothub_pipeline: :class:`azure.iot.device.iothub.pipeline.IoTHubPipeline`
        :param http_pipeline: The pipeline used to connect to the IoTHub endpoint via HTTP.
        :type http_pipeline: :class:`azure.iot.device.iothub.pipeline.HTTPPipeline`
        """
        super(IoTHubModuleClient, self).__init__(
            iothub_pipeline=iothub_pipeline, http_pipeline=http_pipeline
        )
        self._iothub_pipeline.on_input_message_received = CallableWeakMethod(
            self._inbox_manager, "route_input_message"
        )

    def send_message_to_output(self, message, output_name):
        """Sends an event/message to the given module output.

        These are outgoing events and are meant to be "output events".

        This is a synchronous event, meaning that this function will not return until the event
        has been sent to the service and the service has acknowledged receipt of the event.

        If the connection to the service has not previously been opened by a call to connect, this
        function will open the connection before sending the event.

        :param message: Message to send to the given output. Anything passed that is not an instance of the
            Message class will be converted to Message object.
        :type message: :class:`azure.iot.device.Message` or str
        :param str output_name: Name of the output to send the event to.

        :raises: :class:`azure.iot.device.exceptions.CredentialError` if credentials are invalid
            and a connection cannot be established.
        :raises: :class:`azure.iot.device.exceptions.ConnectionFailedError` if a establishing a
            connection results in failure.
        :raises: :class:`azure.iot.device.exceptions.ConnectionDroppedError` if connection is lost
            during execution.
        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        if not isinstance(message, Message):
            message = Message(message)
        message.output_name = output_name

        logger.info("Sending message to output:" + output_name + "...")

        callback = EventedCallback()
        self._iothub_pipeline.send_output_event(message, callback=callback)
        handle_result(callback)

        logger.info("Successfully sent message to output: " + output_name)

    def receive_message_on_input(self, input_name, block=True, timeout=None):
        """Receive an input message that has been sent from another Module to a specific input.

        :param str input_name: The input name to receive a message on.
        :param bool block: Indicates if the operation should block until a message is received.
        :param int timeout: Optionally provide a number of seconds until blocking times out.

        :returns: Message that was sent to the specified input, or None if
            no method request has been received by the end of the blocking period.
        """
        if not self._iothub_pipeline.feature_enabled[pipeline_constant.INPUT_MSG]:
            self._enable_feature(pipeline_constant.INPUT_MSG)
        input_inbox = self._inbox_manager.get_input_message_inbox(input_name)

        logger.info("Waiting for input message on: " + input_name + "...")
        try:
            message = input_inbox.get(block=block, timeout=timeout)
        except InboxEmpty:
            message = None
        logger.info("Input message received on: " + input_name)
        return message

    def invoke_method(self, method_params, device_id, module_id=None):
        # TODO: Should the pipeline level be split into two? According to everyone,
        # it should be only one in the pipeline level, so I should change this.
        """
        method_params should contain a method_name, payload, conenct_timeout_in_seconds, response_timeout_in_seconds
        method_result should contain a status, and a payload
        """
        # if not self._http_pipeline:
        #     # TODO: Is this the right type of Error? CC: Carter
        #     raise exceptions.ClientError(message="Method Invoke only avaiable on Edge Modules")

        callback = EventedCallback(return_arg_name="invoke_method_response")
        self._http_pipeline.invoke_method(device_id, method_params, callback, module_id=module_id)
        invoke_method_response = handle_result(callback)
        logger.info("Successfully invoked method")
        return invoke_method_response
