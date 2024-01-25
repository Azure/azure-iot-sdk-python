# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains user-facing synchronous clients for the
Azure IoTHub Device SDK for Python.
"""
from __future__ import annotations  # Needed for annotation bug < 3.10
import logging
from queue import Queue
import deprecation
from .abstract_clients import (
    AbstractIoTHubClient,
    AbstractIoTHubDeviceClient,
    AbstractIoTHubModuleClient,
)
from .models import Message, MethodResponse, MethodRequest
from .inbox_manager import InboxManager
from .sync_inbox import SyncClientInbox, InboxEmpty
from . import sync_handler_manager
from .pipeline import constant as pipeline_constant
from .pipeline import exceptions as pipeline_exceptions
from azure.iot.device import exceptions
from azure.iot.device.common.evented_callback import EventedCallback
from azure.iot.device import constant as device_constant
from .pipeline import MQTTPipeline, HTTPPipeline
from azure.iot.device.custom_typing import FunctionOrCoroutine, StorageInfo, Twin, TwinPatch
from typing import Optional, Union

logger = logging.getLogger(__name__)


def handle_result(callback):
    try:
        return callback.wait_for_completion()
    except pipeline_exceptions.ConnectionDroppedError as e:
        raise exceptions.ConnectionDroppedError("Lost connection to IoTHub") from e
    except pipeline_exceptions.ConnectionFailedError as e:
        raise exceptions.ConnectionFailedError("Could not connect to IoTHub") from e
    except pipeline_exceptions.NoConnectionError as e:
        raise exceptions.NoConnectionError("Client is not connected to IoTHub") from e
    except pipeline_exceptions.UnauthorizedError as e:
        raise exceptions.CredentialError("Credentials invalid, could not connect") from e
    except pipeline_exceptions.ProtocolClientError as e:
        raise exceptions.ClientError("Error in the IoTHub client") from e
    except pipeline_exceptions.TlsExchangeAuthError as e:
        raise exceptions.ClientError("Error in the IoTHub client due to TLS exchanges.") from e
    except pipeline_exceptions.ProtocolProxyError as e:
        raise exceptions.ClientError(
            "Error in the IoTHub client raised due to proxy connections."
        ) from e
    except pipeline_exceptions.PipelineNotRunning as e:
        raise exceptions.ClientError("Client has already been shut down") from e
    except pipeline_exceptions.OperationCancelled as e:
        raise exceptions.OperationCancelled("Operation was cancelled before completion") from e
    except pipeline_exceptions.OperationTimeout as e:
        raise exceptions.OperationTimeout("Could not complete operation before timeout") from e
    except Exception as e:
        raise exceptions.ClientError("Unexpected failure") from e


class GenericIoTHubClient(AbstractIoTHubClient):
    """A superclass representing a generic synchronous client.
    This class needs to be extended for specific clients.
    """

    def __init__(self, **kwargs):
        """Initializer for a generic synchronous client.

        This initializer should not be called directly.
        Instead, use one of the 'create_from_' classmethods to instantiate

        :param mqtt_pipeline: The MQTTPipeline used for the client
        :type mqtt_pipeline: :class:`azure.iot.device.iothub.pipeline.MQTTPipeline`
        :param http_pipeline: The HTTPPipeline used for the client
        :type http_pipeline: :class:`azure.iot.device.iothub.pipeline.HTTPPipeline`
        """
        # Depending on the subclass calling this __init__, there could be different arguments,
        # and the super() call could call a different class, due to the different MROs
        # in the class hierarchies of different clients. Thus, args here must be passed along as
        # **kwargs.
        super().__init__(**kwargs)
        self._inbox_manager = InboxManager(inbox_type=SyncClientInbox)
        self._handler_manager = sync_handler_manager.SyncHandlerManager(self._inbox_manager)

        # Set pipeline handlers for client events
        self._mqtt_pipeline.on_connected = self._on_connected
        self._mqtt_pipeline.on_disconnected = self._on_disconnected
        self._mqtt_pipeline.on_new_sastoken_required = self._on_new_sastoken_required
        self._mqtt_pipeline.on_background_exception = self._on_background_exception

        # Set pipeline handlers for data receives
        self._mqtt_pipeline.on_method_request_received = self._inbox_manager.route_method_request
        self._mqtt_pipeline.on_twin_patch_received = self._inbox_manager.route_twin_patch

    def _enable_feature(self, feature_name: str) -> None:
        """Enable an Azure IoT Hub feature.

        This is a synchronous call, meaning that this function will not return until the feature
        has been enabled.

        :param feature_name: The name of the feature to enable.
            See azure.iot.device.common.pipeline.constant for possible values
        """
        logger.info("Enabling feature:" + feature_name + "...")
        if not self._mqtt_pipeline.feature_enabled[feature_name]:
            callback = EventedCallback()
            self._mqtt_pipeline.enable_feature(feature_name, callback=callback)
            callback.wait_for_completion()

            logger.info("Successfully enabled feature:" + feature_name)
        else:
            # This branch shouldn't be reached, but in case it is, log it
            logger.info("Feature ({}) already disabled - skipping".format(feature_name))

    def _disable_feature(self, feature_name: str) -> None:
        """Disable an Azure IoT Hub feature

        This is a synchronous call, meaning that this function will not return until the feature
        has been disabled.

        :param feature_name: The name of the feature to disable.
            See azure.iot.device.common.pipeline.constant for possible values
        """
        logger.info("Disabling feature: {}...".format(feature_name))
        if self._mqtt_pipeline.feature_enabled[feature_name]:
            # Disable the feature if not already disabled
            callback = EventedCallback()
            self._mqtt_pipeline.disable_feature(feature_name, callback=callback)
            callback.wait_for_completion()

            logger.info("Successfully disabled feature: {}".format(feature_name))
        else:
            # This branch shouldn't be reached, but in case it is, log it
            logger.info("Feature ({}) already disabled - skipping".format(feature_name))

    def _generic_receive_handler_setter(
        self, handler_name: str, feature_name: str, new_handler: FunctionOrCoroutine[[None], None]
    ) -> None:
        """Set a receive handler on the handler manager and enable the corresponding feature.

        This is a synchronous call, meaning that this function will not return until the feature
        has been enabled (if necessary).

        :param str handler_name: The name of the handler on the handler manager to set
        :param str feature_name: The name of the pipeline feature that corresponds to the handler
        :param new_handler: The function to be set as the handler
        """
        self._check_receive_mode_is_handler()
        # Set the handler on the handler manager
        setattr(self._handler_manager, handler_name, new_handler)

        # Enable the feature if necessary
        if new_handler is not None and not self._mqtt_pipeline.feature_enabled[feature_name]:
            self._enable_feature(feature_name)

        # Disable the feature if necessary
        elif new_handler is None and self._mqtt_pipeline.feature_enabled[feature_name]:
            self._disable_feature(feature_name)

    def shutdown(self) -> None:
        """Shut down the client for graceful exit.

        Once this method is called, any attempts at further client calls will result in a
        ClientError being raised

        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        logger.info("Initiating client shutdown")
        # Note that client disconnect does the following:
        #   - Disconnects the pipeline
        #   - Resolves all pending receiver handler calls
        #   - Stops receiver handler threads
        self.disconnect()

        # Note that shutting down the following:
        #   - Disconnects the MQTT pipeline
        #   - Stops MQTT pipeline threads
        logger.debug("Beginning pipeline shutdown operation")
        callback = EventedCallback()
        self._mqtt_pipeline.shutdown(callback=callback)
        handle_result(callback)
        logger.debug("Completed pipeline shutdown operation")

        # Stop the Client Event handlers now that everything else is completed
        if self._handler_manager is not None:
            self._handler_manager.stop(receiver_handlers_only=False)

        # Yes, that means the pipeline is disconnected twice (well, actually three times if you
        # consider that the client-level disconnect causes two pipeline-level disconnects for
        # reasons explained in comments in the client's .disconnect() method).
        #
        # This last disconnect that occurs as a result of the pipeline shutdown is a bit different
        # from the first though, in that it's more "final" and can't simply just be reconnected.

        # Note also that only the MQTT pipeline is shut down. The reason is twofold:
        #   1. There are no known issues related to graceful exit if the HTTP pipeline is not
        #      explicitly shut down
        #   2. The HTTP pipeline is planned for eventual removal from the client
        # In light of these two facts, it seemed irrelevant to spend time implementing shutdown
        # capability for HTTP pipeline.
        logger.info("Client shutdown complete")

    def connect(self) -> None:
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
        :raises: :class:`azure.iot.device.exceptions.OperationTimeout` if the connection times out.
        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        logger.info("Connecting to Hub...")

        callback = EventedCallback()
        self._mqtt_pipeline.connect(callback=callback)
        handle_result(callback)

        logger.info("Successfully connected to Hub")

    def disconnect(self) -> None:
        """Disconnect the client from the Azure IoT Hub or Azure IoT Edge Hub instance.

        It is recommended that you make sure to call this function when you are completely done
        with the your client instance.

        This is a synchronous call, meaning that this function will not return until the connection
        to the service has been completely closed.

        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        logger.info("Disconnecting from Hub...")

        logger.debug("Executing initial disconnect")
        callback = EventedCallback()
        self._mqtt_pipeline.disconnect(callback=callback)
        handle_result(callback)
        logger.debug("Successfully executed initial disconnect")

        # Note that in the process of stopping the handlers and resolving pending calls
        # a user-supplied handler may cause a reconnection to occur
        logger.debug("Stopping handlers...")
        if self._handler_manager is not None:
            self._handler_manager.stop(receiver_handlers_only=True)
        logger.debug("Successfully stopped handlers")

        # Disconnect again to ensure disconnection has occurred due to the issue mentioned above
        logger.debug("Executing secondary disconnect...")
        callback = EventedCallback()
        self._mqtt_pipeline.disconnect(callback=callback)
        handle_result(callback)
        logger.debug("Successfully executed secondary disconnect")

        # It's also possible that in the (very short) time between stopping the handlers and
        # the second disconnect, additional items were received (e.g. C2D Message)
        # Currently, this isn't really possible to accurately check due to a
        # race condition / thread timing issue with inboxes where we can't guarantee how many
        # items are truly in them.
        # This has always been true of this client, even before handlers.
        #
        # However, even if the race condition is addressed, that will only allow us to log that
        # messages were lost. To actually fix the problem, IoTHub needs to support MQTT5 so that
        # we can unsubscribe from receiving data.

        logger.info("Successfully disconnected from Hub")

    def update_sastoken(self, sastoken: str) -> None:
        """
        Update the client's SAS Token used for authentication, then reauthorizes the connection.

        This API can only be used if the client was initially created with a SAS Token.

        :param str sastoken: The new SAS Token string for the client to use

        :raises: ValueError if the sastoken parameter is invalid
        :raises: :class:`azure.iot.device.exceptions.CredentialError` if credentials are invalid
            and a connection cannot be re-established.
        :raises: :class:`azure.iot.device.exceptions.ConnectionFailedError` if a re-establishing
            the connection results in failure.
        :raises: :class:`azure.iot.device.exceptions.ConnectionDroppedError` if connection is lost
            during execution.
        :raises: :class:`azure.iot.device.exceptions.OperationTimeout` if the reauthorization
            attempt times out.
        :raises: :class:`azure.iot.device.exceptions.ClientError` if the client was not initially
            created with a SAS token.
        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        self._replace_user_supplied_sastoken(sastoken)

        # Reauthorize the connection
        logger.info("Reauthorizing connection with Hub...")
        callback = EventedCallback()
        self._mqtt_pipeline.reauthorize_connection(callback=callback)
        handle_result(callback)
        # NOTE: Currently due to the MQTT3 implementation, the pipeline reauthorization will return
        # after the disconnect. It does not wait for the reconnect to complete. This means that
        # any errors that may occur as part of the connect will not return via this callback.
        # They will instead go to the background exception handler.

        logger.info("Successfully reauthorized connection to Hub")

    def send_message(self, message: Union[Message, str]) -> None:
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
        :raises: :class:`azure.iot.device.exceptions.OperationTimeout` if connection attempt
            times out
        :raises: :class:`azure.iot.device.exceptions.NoConnectionError` if the client is not
            connected (and there is no auto-connect enabled)
        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        :raises: ValueError if the message fails size validation.
        """
        if not isinstance(message, Message):
            message = Message(message)

        if message.get_size() > device_constant.TELEMETRY_MESSAGE_SIZE_LIMIT:
            raise ValueError("Size of telemetry message can not exceed 256 KB.")

        logger.info("Sending message to Hub...")

        callback = EventedCallback()
        self._mqtt_pipeline.send_message(message, callback=callback)
        handle_result(callback)

        logger.info("Successfully sent message to Hub")

    @deprecation.deprecated(
        deprecated_in="2.3.0",
        current_version=device_constant.VERSION,
        details="We recommend that you use the .on_method_request_received property to set a handler instead",
    )
    def receive_method_request(
        self, method_name: Optional[str] = None, block: bool = True, timeout: Optional[int] = None
    ) -> Optional[MethodRequest]:
        """Receive a method request via the Azure IoT Hub or Azure IoT Edge Hub.

        :param str method_name: Optionally provide the name of the method to receive requests for.
            If this parameter is not given, all methods not already being specifically targeted by
            a different request to receive_method will be received.
        :param bool block: Indicates if the operation should block until a request is received.
        :param int timeout: Optionally provide a number of seconds until blocking times out.

        :returns: MethodRequest object representing the received method request, or None if
            no method request has been received by the end of the blocking period.
        """
        self._check_receive_mode_is_api()

        if not self._mqtt_pipeline.feature_enabled[pipeline_constant.METHODS]:
            self._enable_feature(pipeline_constant.METHODS)

        if self._inbox_manager is not None:
            method_inbox : Queue[MethodRequest] = self._inbox_manager.get_method_request_inbox(method_name)

        logger.info("Waiting for method request...")
        try:
            method_request = method_inbox.get(block=block, timeout=timeout)
            logger.info("Received method request")
        except InboxEmpty:
            method_request = None
            logger.info("Did not receive method request")
        return method_request

    def send_method_response(self, method_response: MethodResponse) -> None:
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
        :raises: :class:`azure.iot.device.exceptions.OperationTimeout` if connection attempt
            times out
        :raises: :class:`azure.iot.device.exceptions.NoConnectionError` if the client is not
            connected (and there is no auto-connect enabled)
        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        logger.info("Sending method response to Hub...")

        callback = EventedCallback()
        self._mqtt_pipeline.send_method_response(method_response, callback=callback)
        handle_result(callback)

        logger.info("Successfully sent method response to Hub")

    def get_twin(self) -> Twin:
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
        :raises: :class:`azure.iot.device.exceptions.OperationTimeout` if connection attempt
            times out
        :raises: :class:`azure.iot.device.exceptions.NoConnectionError` if the client is not
            connected (and there is no auto-connect enabled)
        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        if not self._mqtt_pipeline.feature_enabled[pipeline_constant.TWIN]:
            self._enable_feature(pipeline_constant.TWIN)

        callback = EventedCallback(return_arg_name="twin")
        self._mqtt_pipeline.get_twin(callback=callback)
        twin = handle_result(callback)

        logger.info("Successfully retrieved twin")
        return twin

    def patch_twin_reported_properties(self, reported_properties_patch: TwinPatch) -> None:
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
        :raises: :class:`azure.iot.device.exceptions.OperationTimeout` if connection attempt
            times out
        :raises: :class:`azure.iot.device.exceptions.NoConnectionError` if the client is not
            connected (and there is no auto-connect enabled)
        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        if not self._mqtt_pipeline.feature_enabled[pipeline_constant.TWIN]:
            self._enable_feature(pipeline_constant.TWIN)

        callback = EventedCallback()
        self._mqtt_pipeline.patch_twin_reported_properties(
            patch=reported_properties_patch, callback=callback
        )
        handle_result(callback)

        logger.info("Successfully patched twin")

    @deprecation.deprecated(
        deprecated_in="2.3.0",
        current_version=device_constant.VERSION,
        details="We recommend that you use the .on_twin_desired_properties_patch_received property to set a handler instead",
    )
    def receive_twin_desired_properties_patch(self, block=True, timeout=None) -> TwinPatch:
        """
        Receive a desired property patch via the Azure IoT Hub or Azure IoT Edge Hub.

        This is a synchronous call, which means the following:
        1. If block=True, this function will block until one of the following happens:
           * a desired property patch is received from the Azure IoT Hub or Azure IoT Edge Hub.
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
        self._check_receive_mode_is_api()

        if not self._mqtt_pipeline.feature_enabled[pipeline_constant.TWIN_PATCHES]:
            self._enable_feature(pipeline_constant.TWIN_PATCHES)
        if self._inbox_manager is not None:
            twin_patch_inbox : Queue[TwinPatch] = self._inbox_manager.get_twin_patch_inbox()

        logger.info("Waiting for twin patches...")
        try:
            patch = twin_patch_inbox.get(block=block, timeout=timeout)
            logger.info("twin patch received")
        except InboxEmpty:
            logger.info("Did not receive twin patch")
            return None
        return patch


class IoTHubDeviceClient(GenericIoTHubClient, AbstractIoTHubDeviceClient):
    """A synchronous device client that connects to an Azure IoT Hub instance."""

    def __init__(self, mqtt_pipeline: MQTTPipeline, http_pipeline: HTTPPipeline):
        """Initializer for a IoTHubDeviceClient.

        This initializer should not be called directly.
        Instead, use one of the 'create_from_' classmethods to instantiate

        :param mqtt_pipeline: The pipeline used to connect to the IoTHub endpoint.
        :type mqtt_pipeline: :class:`azure.iot.device.iothub.pipeline.MQTTPipeline`
        """
        super().__init__(mqtt_pipeline=mqtt_pipeline, http_pipeline=http_pipeline)
        if self._inbox_manager is not None:
            self._mqtt_pipeline.on_c2d_message_received = self._inbox_manager.route_c2d_message

    @deprecation.deprecated(
        deprecated_in="2.3.0",
        current_version=device_constant.VERSION,
        details="We recommend that you use the .on_message_received property to set a handler instead",
    )
    def receive_message(self, block=True, timeout=None) -> Optional[Message]:
        """Receive a message that has been sent from the Azure IoT Hub.

        :param bool block: Indicates if the operation should block until a message is received.
        :param int timeout: Optionally provide a number of seconds until blocking times out.

        :returns: Message that was sent from the Azure IoT Hub, or None if
            no method request has been received by the end of the blocking period.
        :rtype: :class:`azure.iot.device.Message` or None
        """
        self._check_receive_mode_is_api()

        if not self._mqtt_pipeline.feature_enabled[pipeline_constant.C2D_MSG]:
            self._enable_feature(pipeline_constant.C2D_MSG)
        if self._inbox_manager is not None:
            c2d_inbox : Queue[Message] = self._inbox_manager.get_c2d_message_inbox()

        logger.info("Waiting for message from Hub...")
        try:
            message = c2d_inbox.get(block=block, timeout=timeout)
            logger.info("Message received")
        except InboxEmpty:
            message = None
            logger.info("No message received.")
        return message

    def get_storage_info_for_blob(self, blob_name: str) -> StorageInfo:
        """Sends a POST request over HTTP to an IoTHub endpoint that will return information for uploading via the Azure Storage Account linked to the IoTHub your device is connected to.

        :param str blob_name: The name in string format of the blob that will be uploaded using the storage API. This name will be used to generate the proper credentials for Storage, and needs to match what will be used with the Azure Storage SDK to perform the blob upload.

        :returns: A JSON-like (dictionary) object from IoT Hub that will contain relevant information including: correlationId, hostName, containerName, blobName, sasToken.
        """
        callback = EventedCallback(return_arg_name="storage_info")
        self._http_pipeline.get_storage_info_for_blob(blob_name, callback=callback)
        storage_info = handle_result(callback)
        logger.info("Successfully retrieved storage_info")
        return storage_info

    def notify_blob_upload_status(
        self, correlation_id: str, is_success: bool, status_code: int, status_description: str
    ) -> None:
        """When the upload is complete, the device sends a POST request to the IoT Hub endpoint with information on the status of an upload to blob attempt. This is used by IoT Hub to notify listening clients.

        :param str correlation_id: Provided by IoT Hub on get_storage_info_for_blob request.
        :param bool is_success: A boolean that indicates whether the file was uploaded successfully.
        :param int status_code: A numeric status code that is the status for the upload of the file to storage.
        :param str status_description: A description that corresponds to the status_code.
        """
        callback = EventedCallback()
        self._http_pipeline.notify_blob_upload_status(
            correlation_id=correlation_id,
            is_success=is_success,
            status_code=status_code,
            status_description=status_description,
            callback=callback,
        )
        handle_result(callback)
        logger.info("Successfully notified blob upload status")


class IoTHubModuleClient(GenericIoTHubClient, AbstractIoTHubModuleClient):
    """A synchronous module client that connects to an Azure IoT Hub or Azure IoT Edge instance."""

    def __init__(self, mqtt_pipeline: MQTTPipeline, http_pipeline: HTTPPipeline):
        """Initializer for a IoTHubModuleClient.

        This initializer should not be called directly.
        Instead, use one of the 'create_from_' classmethods to instantiate

        :param mqtt_pipeline: The pipeline used to connect to the IoTHub endpoint.
        :type mqtt_pipeline: :class:`azure.iot.device.iothub.pipeline.MQTTPipeline`
        :param http_pipeline: The pipeline used to connect to the IoTHub endpoint via HTTP.
        :type http_pipeline: :class:`azure.iot.device.iothub.pipeline.HTTPPipeline`
        """
        super().__init__(mqtt_pipeline=mqtt_pipeline, http_pipeline=http_pipeline)
        if self._inbox_manager is not None:
            self._mqtt_pipeline.on_input_message_received = self._inbox_manager.route_input_message

    def send_message_to_output(self, message: Union[Message, str], output_name: str) -> None:
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
        :raises: :class:`azure.iot.device.exceptions.OperationTimeout` if connection attempt
            times out
        :raises: :class:`azure.iot.device.exceptions.NoConnectionError` if the client is not
            connected (and there is no auto-connect enabled)
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

        callback = EventedCallback()
        self._mqtt_pipeline.send_output_message(message, callback=callback)
        handle_result(callback)

        logger.info("Successfully sent message to output: " + output_name)

    @deprecation.deprecated(
        deprecated_in="2.3.0",
        current_version=device_constant.VERSION,
        details="We recommend that you use the .on_message_received property to set a handler instead",
    )
    def receive_message_on_input(
        self, input_name: str, block: bool = True, timeout: Optional[int] = None
    ) -> Optional[Message]:
        """Receive an input message that has been sent from another Module to a specific input.

        :param str input_name: The input name to receive a message on.
        :param bool block: Indicates if the operation should block until a message is received.
        :param int timeout: Optionally provide a number of seconds until blocking times out.

        :returns: Message that was sent to the specified input, or None if
            no method request has been received by the end of the blocking period.
        """
        self._check_receive_mode_is_api()

        if not self._mqtt_pipeline.feature_enabled[pipeline_constant.INPUT_MSG]:
            self._enable_feature(pipeline_constant.INPUT_MSG)
        if self._inbox_manager is not None:
            input_inbox : Queue[Message] = self._inbox_manager.get_input_message_inbox(input_name)

        logger.info("Waiting for input message on: " + input_name + "...")
        try:
            message = input_inbox.get(block=block, timeout=timeout)
            logger.info("Input message received on: " + input_name)
        except InboxEmpty:
            message = None
            logger.info("No input message received on: " + input_name)
        return message

    def invoke_method(self, method_params: dict, device_id: str, module_id=None):
        """Invoke a method from your client onto a device or module client, and receive the response to the method call.

        :param dict method_params: Should contain a methodName (str), payload (str),
            connectTimeoutInSeconds (int), responseTimeoutInSeconds (int).
        :param str device_id: Device ID of the target device where the method will be invoked.
        :param str module_id: Module ID of the target module where the method will be invoked. (Optional)

        :returns: method_result should contain a status, and a payload
        :rtype: dict
        """
        logger.info(
            "Invoking {} method on {}{}".format(method_params["methodName"], device_id, module_id)
        )
        callback = EventedCallback(return_arg_name="invoke_method_response")
        self._http_pipeline.invoke_method(
            device_id, method_params, callback=callback, module_id=module_id
        )
        invoke_method_response = handle_result(callback)
        logger.info("Successfully invoked method")
        return invoke_method_response
