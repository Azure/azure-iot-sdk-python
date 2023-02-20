# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import aiohttp
import logging
import urllib.parse
from typing import Optional, cast
from .custom_typing import MethodParameters, StorageInfo
from .iot_exceptions import IoTHubClientError, IoTHubError
from . import config, constant, user_agent
from . import http_path_iothub as http_path

logger = logging.getLogger(__name__)

# Header Definitions
HEADER_ACCEPT = "Accept"
HEADER_AUTHORIZATION = "Authorization"
HEADER_CONTENT_TYPE = "Content-Type"
HEADER_CONTENT_LENGTH = "Content-Length"
HEADER_EDGE_MODULE_ID = "x-ms-edge-moduleId"
HEADER_HOST = "Host"
HEADER_USER_AGENT = "User-Agent"

# Query parameter definitions
PARAM_API_VERISON = "api-version"

# Other definitions
HTTP_TIMEOUT = 10


class IoTHubHTTPClient:
    def __init__(self, client_config: config.IoTHubClientConfig) -> None:
        self._device_id = client_config.device_id
        self._module_id = client_config.module_id
        self._user_agent_string = user_agent.get_iothub_user_agent() + client_config.product_info
        if client_config.gateway_hostname:
            self._hostname = client_config.gateway_hostname
        else:
            self._hostname = client_config.hostname

        self._sastoken_provider = client_config.sastoken_provider

        self._session = _create_client_session(self._hostname)
        self._ssl_context = client_config.ssl_context

    async def _get_edge_module_id(self):
        """Returns the Edge Module ID, or raises IoTHubClientError if not using Edge"""
        if not self._module_id:
            raise IoTHubClientError("Cannot generate Edge Module ID when not a Module")
        else:
            return "{device_id}/{module_id}".format(
                device_id=self._device_id, module_id=self._module_id
            )

    # TODO: direct method?
    # TODO: should this raise IoTEdgeError instead of IoTHubError?
    # TODO: what is the rtype?
    async def invoke_method(
        self, *, device_id: str, module_id: Optional[str] = None, method_params: MethodParameters
    ):
        """Send a request to invoke a direct method on a target device or module

        :param str device_id: The target device ID
        :param str module_id: The target module ID
        :param dict method_params: The parameters for the method invocation

        :raises: :class:`IoTHubClientError` if not using an Edge Module
        :raises: :class:`IoTHubError` if IoTHub responds with failure
        """
        path = http_path.get_method_invoke_path(device_id, module_id)
        query_params = {PARAM_API_VERISON: constant.IOTHUB_API_VERSION}
        headers = {
            HEADER_HOST: self._hostname,  # TODO: this is always supposed to be Edge gateway hostname, yeah?
            HEADER_CONTENT_TYPE: "application/json",
            HEADER_CONTENT_LENGTH: str(len(str(method_params))),
            HEADER_USER_AGENT: urllib.parse.quote_plus(self._user_agent_string),
            HEADER_EDGE_MODULE_ID: self._get_edge_module_id(),  # TODO: I assume this isn't supposed to be URI encoded just like in MQTT?
        }
        # If using SAS auth, pass the auth header
        if self._sastoken_provider:
            headers[HEADER_AUTHORIZATION] = str(self._sastoken_provider.get_current_sastoken())

        logger.debug(
            "Sending method invocation request to {device_id}/{module_id}".format(
                device_id=device_id, module_id=module_id
            )
        )
        async with self._session as session:
            response = await session.post(
                url=path,
                json=method_params,
                params=query_params,
                ssl=self._ssl_context,
            )
            if response.status >= 300:
                # TODO: semantics - failure response from where?
                logger.error("Received failure response from ??? for method invocation")
                # TODO: should this be IoTEdgeError?
                raise IoTHubError(
                    "??? responded to method invocation with a failed status ({status}) - {reason}".format(
                        status=response.status, reason=response.reason
                    )
                )
            else:
                logger.debug("Successfully received response from ??? for method invocation")
                # TODO: what type is this? What is the format?
                method_response = await response.json()
        return method_response

    async def get_storage_info_for_blob(self, *, blob_name: str) -> StorageInfo:
        """Request information for uploading blob file via the Azure Storage SDK

        :param str blob_name: The name of the blob that will be uploaded to the Azure Storage SDK

        :returns: The Azure Storage information returned by IoTHub
        :rtype: dict

        :raises: :class:`IoTHubError` if IoTHub responds with failure
        """
        path = http_path.get_storage_info_for_blob_path(self._device_id)
        query_params = {PARAM_API_VERISON: constant.IOTHUB_API_VERSION}
        data = {"blobName": blob_name}
        headers = {
            HEADER_HOST: self._hostname,  # TODO: if using Edge, should this be regular, or gateway? Because this value is dynamic right now
            HEADER_ACCEPT: "application/json",
            HEADER_CONTENT_TYPE: "application/json",
            HEADER_CONTENT_LENGTH: str(len(str(data))),
            HEADER_USER_AGENT: urllib.parse.quote_plus(self._user_agent_string),
        }
        # If using SAS auth, pass the auth header
        if self._sastoken_provider:
            headers[HEADER_AUTHORIZATION] = str(self._sastoken_provider.get_current_sastoken())

        logger.debug("Sending storage info request to IoTHub...")
        async with self._session as session:
            response = await session.post(
                url=path,
                json=data,
                params=query_params,
                ssl=self._ssl_context,
            )
            if response.status >= 300:
                logger.error("Received failure response from IoTHub for storage info request")
                raise IoTHubError(
                    "IoTHub responded to storage info request with a failed status ({status}) - {reason}".format(
                        status=response.status, reason=response.reason
                    )
                )
            else:
                logger.debug("Successfully received response from IoTHub for storage info request")
                # TODO: what if this json decoding fails?
                storage_info = cast(StorageInfo, await response.json())
        return storage_info

    async def notify_blob_upload_status(
        self, *, correlation_id: str, is_success: bool, status_code: int, status_description: str
    ) -> None:
        """Notify IoTHub of the result of a Azure Storage SDK blob upload

        :param str correlation_id: ID for the blob upload
        :param bool is_success: Indicates whether the file was uploaded successfully
        :param int status_code: A numeric status code for the file upload
        :param str status_description: A description that corresponds to the status_code

        :raises: :class:`IoTHubError` if IoTHub responds with failure
        """
        path = http_path.get_notify_blob_upload_status_path(self._device_id)
        query_params = {PARAM_API_VERISON: constant.IOTHUB_API_VERSION}
        data = {
            "correlationId": correlation_id,
            "isSuccess": is_success,
            "statusCode": status_code,
            "statusDescription": status_description,
        }
        headers = {
            HEADER_HOST: self._hostname,  # TODO: if using Edge, should this be regular, or gateway? Because this value is dynamic right now
            HEADER_CONTENT_TYPE: "application/json; charset=utf-8",
            HEADER_CONTENT_LENGTH: str(len(str(data))),
            HEADER_USER_AGENT: urllib.parse.quote_plus(self._user_agent_string),
        }
        # If using SAS auth, pass the auth header
        if self._sastoken_provider:
            headers[HEADER_AUTHORIZATION] = str(self._sastoken_provider.get_current_sastoken())

        logger.debug("Sending blob upload notification to IoTHub...")
        async with self._session as session:
            response = await session.post(
                url=path,
                json=data,
                params=query_params,
                ssl=self._ssl_context,
            )
            if response.status >= 300:
                logger.error("Received failure response from IoTHub for blob upload notification")
                raise IoTHubError(
                    "IoTHub responded to blob upload notification with a failed status ({status}) - {reason}".format(
                        status=response.status, reason=response.reason
                    )
                )
            else:
                logger.debug(
                    "Successfully received from response from IoTHub for blob upload notification"
                )


def _create_client_session(hostname: str) -> aiohttp.ClientSession:
    """Create and return a aiohttp ClientSession object"""
    base_url = "https://{hostname}".format(hostname=hostname)
    timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
    session = aiohttp.ClientSession(base_url=base_url, timeout=timeout)
    logger.debug(
        "Creating HTTP Session for {url} with timeout of {timeout}".format(
            url=base_url, timeout=timeout.total
        )
    )
    return session
