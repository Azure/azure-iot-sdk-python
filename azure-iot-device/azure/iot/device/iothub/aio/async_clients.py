# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains user-facing asynchronous clients for the
Azure IoTHub Device SDK for Python.
"""

import logging
from azure.iot.device.common import async_adapter
from azure.iot.device.iothub.abstract_clients import (
    AbstractIoTHubClient,
    AbstractIoTHubDeviceClient,
    AbstractIoTHubModuleClient,
)
from azure.iot.device.iothub.models import Message
from azure.iot.device.iothub.pipeline import constant
from azure.iot.device.iothub.pipeline import exceptions as pipeline_exceptions
from azure.iot.device import exceptions
from azure.iot.device.iothub.inbox_manager import InboxManager
from .async_inbox import AsyncClientInbox
from azure.iot.device import constant as device_constant

logger = logging.getLogger(__name__)


async def handle_result(callback):
    try:
        return await callback.completion()
    except pipeline_exceptions.ConnectionDroppedError as e:
        raise exceptions.ConnectionDroppedError(message="Lost connection to IoTHub", cause=e)
    except pipeline_exceptions.ConnectionFailedError as e:
        raise exceptions.ConnectionFailedError(message="Could not connect to IoTHub", cause=e)
    except pipeline_exceptions.UnauthorizedError as e:
        raise exceptions.CredentialError(message="Credentials invalid, could not connect", cause=e)
    except pipeline_exceptions.ProtocolClientError as e:
        raise exceptions.ClientError(message="Error in the IoTHub client", cause=e)
    except pipeline_exceptions.TlsExchangeAuthError as e:
        raise exceptions.ClientError(
            message="Error in the IoTHub client due to TLS exchanges.", cause=e
        )
    except Exception as e:
        raise exceptions.ClientError(message="Unexpected failure", cause=e)


class GenericIoTHubClient(AbstractIoTHubClient):
    """A super class representing a generic asynchronous client.
    This class needs to be extended for specific clients.
    """

    def __init__(self, **kwargs):
        """Initializer for a generic asynchronous client.

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
        super().__init__(**kwargs)
        self._inbox_manager = InboxManager(inbox_type=AsyncClientInbox)
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

    async def connect(self):
        """Connects the client to an Azure IoT Hub or Azure IoT Edge Hub instance.

        The destination is chosen based on the credentials passed via the auth_provider parameter
        that was provided when this object was initialized.

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
        connect_async = async_adapter.emulate_async(self._iothub_pipeline.connect)

        callback = async_adapter.AwaitableCallback()
        await connect_async(callback=callback)
        await handle_result(callback)

        logger.info("Successfully connected to Hub")

    async def disconnect(self):
        """Disconnect the client from the Azure IoT Hub or Azure IoT Edge Hub instance.

        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        logger.info("Disconnecting from Hub...")
        disconnect_async = async_adapter.emulate_async(self._iothub_pipeline.disconnect)

        callback = async_adapter.AwaitableCallback()
        await disconnect_async(callback=callback)
        await handle_result(callback)

        logger.info("Successfully disconnected from Hub")

    async def send_message(self, message):
        """Sends a message to the default events endpoint on the Azure IoT Hub or Azure IoT Edge Hub instance.

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
        :raises: ValueError if the message fails size validation.
        """
        if not isinstance(message, Message):
            message = Message(message)

        if message.get_size() > device_constant.TELEMETRY_MESSAGE_SIZE_LIMIT:
            raise ValueError("Size of telemetry message can not exceed 256 KB.")

        logger.info("Sending message to Hub...")
        send_message_async = async_adapter.emulate_async(self._iothub_pipeline.send_message)

        callback = async_adapter.AwaitableCallback()
        await send_message_async(message, callback=callback)
        await handle_result(callback)

        logger.info("Successfully sent message to Hub")

    async def receive_method_request(self, method_name=None):
        """Receive a method request via the Azure IoT Hub or Azure IoT Edge Hub.

        If no method request is yet available, will wait until it is available.

        :param str method_name: Optionally provide the name of the method to receive requests for.
            If this parameter is not given, all methods not already being specifically targeted by
            a different call to receive_method will be received.

        :returns: MethodRequest object representing the received method request.
        :rtype: `azure.iot.device.MethodRequest`
        """
        if not self._iothub_pipeline.feature_enabled[constant.METHODS]:
            await self._enable_feature(constant.METHODS)

        method_inbox = self._inbox_manager.get_method_request_inbox(method_name)

        logger.info("Waiting for method request...")
        method_request = await method_inbox.get()
        logger.info("Received method request")
        return method_request

    async def send_method_response(self, method_response):
        """Send a response to a method request via the Azure IoT Hub or Azure IoT Edge Hub.

        If the connection to the service has not previously been opened by a call to connect, this
        function will open the connection before sending the event.

        :param method_response: The MethodResponse to send
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
        send_method_response_async = async_adapter.emulate_async(
            self._iothub_pipeline.send_method_response
        )

        callback = async_adapter.AwaitableCallback()

        # TODO: maybe consolidate method_request, result and status into a new object
        await send_method_response_async(method_response, callback=callback)
        await handle_result(callback)

        logger.info("Successfully sent method response to Hub")

    async def _enable_feature(self, feature_name):
        """Enable an Azure IoT Hub feature

        :param feature_name: The name of the feature to enable.
            See azure.iot.device.common.pipeline.constant for possible values.
        """
        logger.info("Enabling feature:" + feature_name + "...")
        enable_feature_async = async_adapter.emulate_async(self._iothub_pipeline.enable_feature)

        callback = async_adapter.AwaitableCallback()
        await enable_feature_async(feature_name, callback=callback)
        await handle_result(callback)

        logger.info("Successfully enabled feature:" + feature_name)

    async def get_twin(self):
        """
        Gets the device or module twin from the Azure IoT Hub or Azure IoT Edge Hub service.

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
        logger.info("Getting twin")

        if not self._iothub_pipeline.feature_enabled[constant.TWIN]:
            await self._enable_feature(constant.TWIN)

        get_twin_async = async_adapter.emulate_async(self._iothub_pipeline.get_twin)

        callback = async_adapter.AwaitableCallback(return_arg_name="twin")
        await get_twin_async(callback=callback)
        twin = await handle_result(callback)
        logger.info("Successfully retrieved twin")
        return twin

    async def patch_twin_reported_properties(self, reported_properties_patch):
        """
        Update reported properties with the Azure IoT Hub or Azure IoT Edge Hub service.

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
        logger.info("Patching twin reported properties")

        if not self._iothub_pipeline.feature_enabled[constant.TWIN]:
            await self._enable_feature(constant.TWIN)

        patch_twin_async = async_adapter.emulate_async(
            self._iothub_pipeline.patch_twin_reported_properties
        )

        callback = async_adapter.AwaitableCallback()
        await patch_twin_async(patch=reported_properties_patch, callback=callback)
        await handle_result(callback)

        logger.info("Successfully sent twin patch")

    async def receive_twin_desired_properties_patch(self):
        """
        Receive a desired property patch via the Azure IoT Hub or Azure IoT Edge Hub.

        If no method request is yet available, will wait until it is available.

        :returns: Twin Desired Properties patch as a JSON dict
        :rtype: dict
        """
        if not self._iothub_pipeline.feature_enabled[constant.TWIN_PATCHES]:
            await self._enable_feature(constant.TWIN_PATCHES)
        twin_patch_inbox = self._inbox_manager.get_twin_patch_inbox()

        logger.info("Waiting for twin patches...")
        patch = await twin_patch_inbox.get()
        logger.info("twin patch received")
        return patch

    async def get_storage_info_for_blob(self, blob_name):
        """Sends a POST request over HTTP to an IoTHub endpoint that will return information for uploading via the Azure Storage Account linked to the IoTHub your device is connected to.

        :param str blob_name: The name in string format of the blob that will be uploaded using the storage API. This name will be used to generate the proper credentials for Storage, and needs to match what will be used with the Azure Storage SDK to perform the blob upload.

        :returns: A JSON-like (dictionary) object from IoT Hub that will contain relevant information including: correlationId, hostName, containerName, blobName, sasToken.
        """
        get_storage_info_for_blob_async = async_adapter.emulate_async(
            self._http_pipeline.get_storage_info_for_blob
        )

        callback = async_adapter.AwaitableCallback(return_arg_name="storage_info")
        await get_storage_info_for_blob_async(blob_name=blob_name, callback=callback)
        storage_info = await handle_result(callback)
        logger.info("Successfully retrieved storage_info")
        return storage_info

    async def notify_blob_upload_status(
        self, correlation_id, is_success, status_code, status_description
    ):
        """When the upload is complete, the device sends a POST request to the IoT Hub endpoint with information on the status of an upload to blob attempt. This is used by IoT Hub to notify listening clients.

        :param str correlation_id: Provided by IoT Hub on get_storage_info_for_blob request.
        :param bool is_success: A boolean that indicates whether the file was uploaded successfully.
        :param int status_code: A numeric status code that is the status for the upload of the fiel to storage.
        :param str status_description: A description that corresponds to the status_code.
        """
        notify_blob_upload_status_async = async_adapter.emulate_async(
            self._http_pipeline.notify_blob_upload_status
        )

        callback = async_adapter.AwaitableCallback()
        await notify_blob_upload_status_async(
            correlation_id=correlation_id,
            is_success=is_success,
            status_code=status_code,
            status_description=status_description,
            callback=callback,
        )
        await handle_result(callback)
        logger.info("Successfully notified blob upload status")


class IoTHubDeviceClient(GenericIoTHubClient, AbstractIoTHubDeviceClient):
    """An asynchronous device client that connects to an Azure IoT Hub instance.

    Intended for usage with Python 3.5.3+
    """

    def __init__(self, iothub_pipeline, http_pipeline):
        """Initializer for a IoTHubDeviceClient.

        This initializer should not be called directly.
        Instead, use one of the 'create_from_' classmethods to instantiate

        :param iothub_pipeline: The pipeline used to connect to the IoTHub endpoint.
        :type iothub_pipeline: :class:`azure.iot.device.iothub.pipeline.IoTHubPipeline`
        """
        super().__init__(iothub_pipeline=iothub_pipeline, http_pipeline=http_pipeline)
        self._iothub_pipeline.on_c2d_message_received = self._inbox_manager.route_c2d_message

    async def receive_message(self):
        """Receive a message that has been sent from the Azure IoT Hub.

        If no message is yet available, will wait until an item is available.

        :returns: Message that was sent from the Azure IoT Hub.
        :rtype: :class:`azure.iot.device.Message`
        """
        if not self._iothub_pipeline.feature_enabled[constant.C2D_MSG]:
            await self._enable_feature(constant.C2D_MSG)
        c2d_inbox = self._inbox_manager.get_c2d_message_inbox()

        logger.info("Waiting for message from Hub...")
        message = await c2d_inbox.get()
        logger.info("Message received")
        return message


class IoTHubModuleClient(GenericIoTHubClient, AbstractIoTHubModuleClient):
    """An asynchronous module client that connects to an Azure IoT Hub or Azure IoT Edge instance.

    Intended for usage with Python 3.5.3+
    """

    def __init__(self, iothub_pipeline, http_pipeline):
        """Intializer for a IoTHubModuleClient.

        This initializer should not be called directly.
        Instead, use one of the 'create_from_' classmethods to instantiate

        :param iothub_pipeline: The pipeline used to connect to the IoTHub endpoint.
        :type iothub_pipeline: :class:`azure.iot.device.iothub.pipeline.IoTHubPipeline`
        """
        super().__init__(iothub_pipeline=iothub_pipeline, http_pipeline=http_pipeline)
        self._iothub_pipeline.on_input_message_received = self._inbox_manager.route_input_message

    async def send_message_to_output(self, message, output_name):
        """Sends an event/message to the given module output.

        These are outgoing events and are meant to be "output events"

        If the connection to the service has not previously been opened by a call to connect, this
        function will open the connection before sending the event.

        :param message: Message to send to the given output. Anything passed that is not an
            instance of the Message class will be converted to Message object.
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
        :raises: ValueError if the message fails size validation.
        """
        if not isinstance(message, Message):
            message = Message(message)

        if message.get_size() > device_constant.TELEMETRY_MESSAGE_SIZE_LIMIT:
            raise ValueError("Size of message can not exceed 256 KB.")

        message.output_name = output_name

        logger.info("Sending message to output:" + output_name + "...")
        send_output_event_async = async_adapter.emulate_async(
            self._iothub_pipeline.send_output_event
        )

        callback = async_adapter.AwaitableCallback()
        await send_output_event_async(message, callback=callback)
        await handle_result(callback)

        logger.info("Successfully sent message to output: " + output_name)

    async def receive_message_on_input(self, input_name):
        """Receive an input message that has been sent from another Module to a specific input.

        If no message is yet available, will wait until an item is available.

        :param str input_name: The input name to receive a message on.

        :returns: Message that was sent to the specified input.
        :rtype: :class:`azure.iot.device.Message`
        """
        if not self._iothub_pipeline.feature_enabled[constant.INPUT_MSG]:
            await self._enable_feature(constant.INPUT_MSG)
        inbox = self._inbox_manager.get_input_message_inbox(input_name)

        logger.info("Waiting for input message on: " + input_name + "...")
        message = await inbox.get()
        logger.info("Input message received on: " + input_name)
        return message

    async def invoke_method(self, method_params, device_id, module_id=None):
        """Invoke a method from your client onto a device or module client, and receive the response to the method call.

        :param dict method_params: Should contain a method_name, payload, connect_timeout_in_seconds, response_timeout_in_seconds.
        :param str device_id: Device ID of the target device where the method will be invoked.
        :param str module_id: Module ID of the target module where the method will be invoked. (Optional)

        :returns: method_result should contain a status, and a payload
        :rtype: dict
        """
        invoke_method_async = async_adapter.emulate_async(self._http_pipeline.invoke_method)
        callback = async_adapter.AwaitableCallback(return_arg_name="invoke_method_response")
        await invoke_method_async(device_id, method_params, callback=callback, module_id=module_id)

        method_response = await handle_result(callback)
        logger.info("Successfully invoked method")
        return method_response
