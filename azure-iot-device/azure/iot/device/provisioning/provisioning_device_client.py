# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""
This module contains user-facing synchronous Provisioning Device Client for Azure Provisioning
Device SDK. This client uses Symmetric Key and X509 authentication to register devices with an
IoT Hub via the Device Provisioning Service.
"""
import logging
from azure.iot.device.common.evented_callback import EventedCallback
from .abstract_provisioning_device_client import AbstractProvisioningDeviceClient
from .abstract_provisioning_device_client import log_on_register_complete
from azure.iot.device.provisioning.pipeline import constant as dps_constant
from .pipeline import exceptions as pipeline_exceptions
from azure.iot.device import exceptions


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


class ProvisioningDeviceClient(AbstractProvisioningDeviceClient):
    """
    Client which can be used to run the registration of a device with provisioning service
    using Symmetric Key orr X509 authentication.
    """

    def register(self):
        """
        Register the device with the with the provisioning service

        This is a synchronous call, meaning that this function will not return until the
        registration process has completed successfully or the attempt has resulted in a failure.
        Before returning, the client will also disconnect from the provisioning service.
        If a registration attempt is made while a previous registration is in progress it may
        throw an error.

        :returns: RegistrationResult indicating the result of the registration.
        :rtype: :class:`azure.iot.device.RegistrationResult`

        :raises: :class:`azure.iot.device.exceptions.CredentialError` if credentials are invalid
            and a connection cannot be established.
        :raises: :class:`azure.iot.device.exceptions.ConnectionFailedError` if a establishing a
            connection results in failure.
        :raises: :class:`azure.iot.device.exceptions.ConnectionDroppedError` if connection is lost
            during execution.
        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        logger.info("Registering with Provisioning Service...")

        if not self._pipeline.responses_enabled[dps_constant.REGISTER]:
            self._enable_responses()

        register_complete = EventedCallback(return_arg_name="result")

        self._pipeline.register(payload=self._provisioning_payload, callback=register_complete)

        result = handle_result(register_complete)

        log_on_register_complete(result)
        return result

    def _enable_responses(self):
        """Enable to receive responses from Device Provisioning Service.

        This is a synchronous call, meaning that this function will not return until the feature
        has been enabled.

        """
        logger.info("Enabling reception of response from Device Provisioning Service...")

        subscription_complete = EventedCallback()
        self._pipeline.enable_responses(callback=subscription_complete)

        handle_result(subscription_complete)

        logger.info("Successfully subscribed to Device Provisioning Service to receive responses")
