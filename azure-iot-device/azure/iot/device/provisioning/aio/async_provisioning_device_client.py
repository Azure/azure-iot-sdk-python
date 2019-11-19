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
from azure.iot.device.iothub.pipeline import exceptions as pipeline_exceptions
from azure.iot.device import exceptions
from azure.iot.device.provisioning.pipeline import constant as dps_constant

logger = logging.getLogger(__name__)


async def wait_for_completion(callback):
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
    except Exception as e:
        raise exceptions.ClientError(message="Unexpected failure", cause=e)


class ProvisioningDeviceClient(AbstractProvisioningDeviceClient):
    """
    Client which can be used to run the registration of a device with provisioning service
    using Symmetric Key or X509 authentication.
    """

    async def register(self):
        """
        Register the device with the provisioning service.

        Before returning the client will also disconnect from the provisioning service.
        If a registration attempt is made while a previous registration is in progress it may
        throw an error.

        :returns: RegistrationResult indicating the result of the registration.
        :rtype: :class:`azure.iot.device.RegistrationResult`
        """
        logger.info("Registering with Provisioning Service...")

        if not self._provisioning_pipeline.responses_enabled[dps_constant.REGISTER]:
            await self._enable_responses()

        register_async = async_adapter.emulate_async(self._provisioning_pipeline.register)

        register_complete = async_adapter.AwaitableCallback(return_arg_name="result")
        await register_async(payload=self._provisioning_payload, callback=register_complete)
        result = await wait_for_completion(register_complete)

        log_on_register_complete(result)
        return result

    async def _enable_responses(self):
        """Enable to receive responses from Device Provisioning Service.
        """
        logger.info("Enabling reception of response from Device Provisioning Service...")
        subscribe_async = async_adapter.emulate_async(self._provisioning_pipeline.enable_responses)

        subscription_complete = async_adapter.AwaitableCallback()
        await subscribe_async(callback=subscription_complete)
        await wait_for_completion(subscription_complete)

        logger.info("Successfully subscribed to Device Provisioning Service to receive responses")
