# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import aiohttp
import asyncio
import logging
import urllib.parse
from typing import Optional, cast
from .custom_typing import DirectMethodParameters, DirectMethodResult, StorageInfo
from .iot_exceptions import IoTHubClientError, IoTHubError, IoTEdgeError
from . import config, constant, user_agent
from . import http_path_iothub as http_path

logger = logging.getLogger(__name__)

# Header Definitions
HEADER_AUTHORIZATION = "Authorization"
HEADER_EDGE_MODULE_ID = "x-ms-edge-moduleId"
HEADER_USER_AGENT = "User-Agent"

# Query parameter definitions
PARAM_API_VERISON = "api-version"

# Other definitions
HTTP_TIMEOUT = 10

# NOTE: Outstanding items in this module:
# TODO: document aiohttp exceptions that can be raised
# TODO: URL Encoding logic
# TODO: Proxy support
# TODO: Should direct method responses be a DirectMethodResponse object? If so, what is the rid?
# See specific inline commentary for more details on what is required


# NOTE: aiohttp 3.x is bugged on Windows on Python 3.8.x - 3.10.6
# If running the application using asyncio.run(), there will be an issue with the Event Loop
# raising a spurious RuntimeError on application exit.
#
# Windows Event Loops are notoriously tricky to deal with. This issue stems from the use of the
# default ProactorEventLoop, and can be mitigated by switching to a SelectorEventLoop, but
# we as SDK developers really ought not be modifying the end user's event loop, or monkeypatching
# error suppression into it. Furthermore, switching to a SelectorEvenLoop has some degradation of
# functionality.
#
# The best course of action is for the end user to use loop.run_until_complete() instead of
# asyncio.run() in their application, as this will allow for better cleanup.
#
# Eventually when there is an aiohttp 4.x released, this bug will be eliminated from all versions
# of Python, but until then, there's not much to be done about it.
#
# See: https://github.com/aio-libs/aiohttp/issues/4324, as well as many, many other similar issues
# for more details.


class IoTHubHTTPClient:
    def __init__(self, client_config: config.IoTHubClientConfig) -> None:
        """Instantiate the client

        :param client_config: The config object for the client
        :type client_config: :class:`IoTHubClientConfig`
        """
        self._device_id = client_config.device_id
        self._module_id = client_config.module_id
        self._edge_module_id = _format_edge_module_id(self._device_id, self._module_id)
        self._user_agent_string = user_agent.get_iothub_user_agent() + client_config.product_info

        # TODO: add proxy support
        # Doing so will require building a custom "Connector" that can be injected into the
        # Session object. There are many examples around online.
        # The built in per-request proxy of aiohttp is only partly functional, so I decided to
        # not even bother implementing it, if it only does half the job.
        if client_config.proxy_options:
            # TODO: these warnings should probably be at API level
            logger.warning("Proxy use with .invoke_direct_method() not supported")
            logger.warning("Proxy use with .get_storage_info_for_blob() not supported")
            logger.warning("Proxy use with .notify_blob_upload_status() not supported")

        self._session = _create_client_session(client_config.hostname)
        self._ssl_context = client_config.ssl_context
        self._sastoken_provider = client_config.sastoken_provider

    async def shutdown(self):
        """Shut down the client

        Invoke only when complete finished with the client for graceful exit.
        """
        await self._session.close()
        # Wait 250ms for the underlying SSL connections to close
        # See: https://docs.aiohttp.org/en/stable/client_advanced.html#graceful-shutdown
        await asyncio.sleep(0.25)

    async def invoke_direct_method(
        self,
        *,
        device_id: str,
        module_id: Optional[str] = None,
        method_params: DirectMethodParameters
    ) -> DirectMethodResult:
        """Send a request to invoke a direct method on a target device or module

        :param str device_id: The target device ID
        :param str module_id: The target module ID
        :param dict method_params: The parameters for the direct method invocation

        :returns: A dictionary containing a status and payload reported by the target device
        :rtype: dict

        :raises: :class:`IoTHubClientError` if not using an IoT Edge Module
        :raises: :class:`IoTHubClientError` if the direct method response cannot be parsed
        :raises: :class:`IoTEdgeError` if IoT Edge responds with failure
        """
        if not self._edge_module_id:
            # NOTE: The Edge Module ID will be exist for any Module, it doesn't actually indicate
            # if it is an Edge Module or not. There's no way to tell, unfortunately.
            raise IoTHubClientError(".invoke_direct_method() only available for Edge Modules")

        path = http_path.get_direct_method_invoke_path(device_id, module_id)
        query_params = {PARAM_API_VERISON: constant.IOTHUB_API_VERSION}
        # NOTE: Other headers are auto-generated by aiohttp
        headers = {
            HEADER_USER_AGENT: urllib.parse.quote_plus(self._user_agent_string),
            HEADER_EDGE_MODULE_ID: self._edge_module_id,  # TODO: I assume this isn't supposed to be URI encoded just like in MQTT?
        }
        # If using SAS auth, pass the auth header
        if self._sastoken_provider:
            headers[HEADER_AUTHORIZATION] = str(self._sastoken_provider.get_current_sastoken())

        logger.debug(
            "Sending direct method invocation request to {device_id}/{module_id}".format(
                device_id=device_id, module_id=module_id
            )
        )
        async with self._session.post(
            url=path,
            json=method_params,
            params=query_params,
            headers=headers,
            ssl=self._ssl_context,
        ) as response:

            if response.status >= 300:
                logger.error("Received failure response from IoT Edge for direct method invocation")
                raise IoTEdgeError(
                    "IoT Edge responded to direct method invocation with a failed status ({status}) - {reason}".format(
                        status=response.status, reason=response.reason
                    )
                )
            else:
                logger.debug(
                    "Successfully received response from IoT Edge for direct method invocation"
                )
                dm_result = cast(DirectMethodResult, await response.json())

        return dm_result

    async def get_storage_info_for_blob(self, *, blob_name: str) -> StorageInfo:
        """Request information for uploading blob file via the Azure Storage SDK

        :param str blob_name: The name of the blob that will be uploaded to the Azure Storage SDK

        :returns: The Azure Storage information returned by IoTHub
        :rtype: dict

        :raises: :class:`IoTHubClientError` if not using a Device
        :raises: :class:`IoTHubError` if IoTHub responds with failure
        """
        if self._module_id:
            raise IoTHubClientError(".get_storage_info_for_blob() only available for Devices")

        path = http_path.get_storage_info_for_blob_path(
            self._device_id
        )  # TODO: is this bad that this is encoding? aiohttp encodes automatically
        query_params = {PARAM_API_VERISON: constant.IOTHUB_API_VERSION}
        data = {"blobName": blob_name}
        # NOTE: Other headers are auto-generated by aiohttp
        headers = {HEADER_USER_AGENT: urllib.parse.quote_plus(self._user_agent_string)}
        # If using SAS auth, pass the auth header
        if self._sastoken_provider:
            headers[HEADER_AUTHORIZATION] = str(self._sastoken_provider.get_current_sastoken())

        logger.debug("Sending storage info request to IoTHub...")
        async with self._session.post(
            url=path,
            json=data,
            params=query_params,
            headers=headers,
            ssl=self._ssl_context,
        ) as response:

            if response.status >= 300:
                logger.error("Received failure response from IoTHub for storage info request")
                raise IoTHubError(
                    "IoTHub responded to storage info request with a failed status ({status}) - {reason}".format(
                        status=response.status, reason=response.reason
                    )
                )
            else:
                logger.debug("Successfully received response from IoTHub for storage info request")
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

        :raises: :class:`IoTHubClientError` if not using a Device
        :raises: :class:`IoTHubError` if IoTHub responds with failure
        """
        if self._module_id:
            raise IoTHubClientError(".notify_blob_upload_status() only available for Devices")

        path = http_path.get_notify_blob_upload_status_path(self._device_id)
        query_params = {PARAM_API_VERISON: constant.IOTHUB_API_VERSION}
        data = {
            "correlationId": correlation_id,
            "isSuccess": is_success,
            "statusCode": status_code,
            "statusDescription": status_description,
        }
        # NOTE: Other headers are auto-generated by aiohttp
        headers = {HEADER_USER_AGENT: urllib.parse.quote_plus(self._user_agent_string)}
        # If using SAS auth, pass the auth header
        if self._sastoken_provider:
            headers[HEADER_AUTHORIZATION] = str(self._sastoken_provider.get_current_sastoken())

        logger.debug("Sending blob upload notification to IoTHub...")
        async with self._session.post(
            url=path,
            json=data,
            params=query_params,
            headers=headers,
            ssl=self._ssl_context,
        ) as response:

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

        return None


def _format_edge_module_id(device_id: str, module_id: Optional[str]) -> Optional[str]:
    """Returns the edge module identifier"""
    if module_id:
        return "{device_id}/{module_id}".format(device_id=device_id, module_id=module_id)
    else:
        return None


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
