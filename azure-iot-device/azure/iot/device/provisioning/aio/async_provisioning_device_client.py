# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""
This module contains user-facing asynchronous Provisioning Device Client for Azure Provisioning
Device SDK. This client uses Symmetric Key and X509 authentication to register devices with an
IoT Hub via the Device Provisioning Service.
"""

import logging
from azure.iot.device.common import async_adapter
from azure.iot.device.provisioning.abstract_provisioning_device_client import (
    AbstractProvisioningDeviceClient,
)
from azure.iot.device.provisioning.abstract_provisioning_device_client import (
    log_on_register_complete,
)
from azure.iot.device.provisioning.pipeline import exceptions as pipeline_exceptions
from azure.iot.device import exceptions
from azure.iot.device.provisioning.pipeline import constant as dps_constant

logger = logging.getLogger(__name__)


async def handle_result(callback):
    try:
        return await callback.completion()
    except pipeline_exceptions.ConnectionDroppedError as e:
        raise exceptions.ConnectionDroppedError("Lost connection to IoTHub") from e
    except pipeline_exceptions.ConnectionFailedError as e:
        raise exceptions.ConnectionFailedError("Could not connect to IoTHub") from e
    except pipeline_exceptions.UnauthorizedError as e:
        raise exceptions.CredentialError("Credentials invalid, could not connect") from e
    except pipeline_exceptions.ProtocolClientError as e:
        raise exceptions.ClientError("Error in the IoTHub client") from e
    except pipeline_exceptions.TlsExchangeAuthError as e:
        raise exceptions.ClientError(
            "Error in the provisioning client due to TLS exchanges."
        ) from e
    except pipeline_exceptions.ProtocolProxyError as e:
        raise exceptions.ClientError(
            "Error in the provisioning client raised due to proxy connections."
        ) from e
    except pipeline_exceptions.OperationTimeout as e:
        raise exceptions.OperationTimeout("Could not complete operation before timeout") from e
    except pipeline_exceptions.OperationCancelled as e:
        raise exceptions.OperationCancelled("Operation was cancelled before completion") from e
    except pipeline_exceptions.PipelineNotRunning as e:
        raise exceptions.ClientError("Client has already been shut down") from e
    except Exception as e:
        raise exceptions.ClientError("Unexpected failure") from e


class ProvisioningDeviceClient(AbstractProvisioningDeviceClient):
    """
    Client which can be used to run the registration of a device with provisioning service
    using Symmetric Key or X509 authentication.
    """

    async def shutdown(self):
        """Shut down the client for graceful exit.

        Once this method is called, any attempts at further client calls will result in a
        ClientError being raised

        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        shutdown_async = async_adapter.emulate_async(self._pipeline.shutdown)
        callback = async_adapter.AwaitableCallback()
        await shutdown_async(callback=callback)
        await handle_result(callback)

    async def register(self):
        """
        Register the device with the provisioning service.

        Before returning the client will also disconnect from the provisioning service.
        If a registration attempt is made while a previous registration is in progress it may
        throw an error.

        Once the device is successfully registered, the client will no longer be operable.

        :returns: RegistrationResult indicating the result of the registration.
        :rtype: :class:`azure.iot.device.RegistrationResult`

        :raises: :class:`azure.iot.device.exceptions.CredentialError` if credentials are invalid
            and a connection cannot be established.
        :raises: :class:`azure.iot.device.exceptions.ConnectionFailedError` if establishing a
            connection results in failure.
        :raises: :class:`azure.iot.device.exceptions.ConnectionDroppedError` if connection is lost
            during execution.
        :raises: :class:`azure.iot.device.exceptions.OperationCancelled` if the registration
            attempt is cancelled.
        :raises: :class:`azure.iot.device.exceptions.OperationTimeout` if the connection times out.
        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        logger.info("Registering with Provisioning Service...")

        # Connect
        logger.debug("Starting pipeline connect operation")
        connect_async = async_adapter.emulate_async(self._pipeline.connect)
        connect_complete = async_adapter.AwaitableCallback()
        await connect_async(callback=connect_complete)
        await handle_result(connect_complete)
        logger.debug("Completed pipeline connect operation")

        # Enable (if necessary)
        if not self._pipeline.responses_enabled[dps_constant.REGISTER]:
            logger.debug("Starting pipeline enable operation")
            enable_async = async_adapter.emulate_async(self._pipeline.enable_responses)
            enable_complete = async_adapter.AwaitableCallback()
            await enable_async(callback=enable_complete)
            await handle_result(enable_complete)
            logger.debug("Completed pipeline enable operation")

        # Register
        logger.debug("Starting pipeline register operation")
        register_async = async_adapter.emulate_async(self._pipeline.register)
        register_complete = async_adapter.AwaitableCallback(return_arg_name="result")
        await register_async(payload=self._provisioning_payload, callback=register_complete)
        result = await handle_result(register_complete)
        log_on_register_complete(result)
        logger.debug("Completed pipeline register operation")

        # Disconnect
        try:
            # This shouldn't fail, but we put it in this block anyway to ensure that
            # the result can be returned in the case there is failure for some reason.
            # This is okay to do because even in the case of failure, a disconnect occurs.
            logger.debug("Starting pipeline disconnect operation")
            disconnect_async = async_adapter.emulate_async(self._pipeline.disconnect)
            disconnect_complete = async_adapter.AwaitableCallback()
            await disconnect_async(callback=disconnect_complete)
            await handle_result(disconnect_complete)
            logger.debug("Completed pipeline disconnect operation")
        except Exception as e:
            logger.debug("Pipeline disconnect operation raised exception: {}".format(str(e)))
        finally:
            return result
