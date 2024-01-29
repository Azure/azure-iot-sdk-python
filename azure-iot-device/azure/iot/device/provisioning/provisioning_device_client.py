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
from __future__ import annotations  # Needed for annotation bug < 3.10
import logging
from typing import Any
from azure.iot.device.common.evented_callback import EventedCallback
from azure.iot.device.custom_typing import FunctionOrCoroutine
from .abstract_provisioning_device_client import AbstractProvisioningDeviceClient
from .abstract_provisioning_device_client import log_on_register_complete
from azure.iot.device.provisioning.pipeline import constant as dps_constant
from .pipeline import exceptions as pipeline_exceptions
from azure.iot.device import exceptions
from azure.iot.device.provisioning.models import RegistrationResult


logger = logging.getLogger(__name__)


def handle_result(callback: FunctionOrCoroutine[[Any], None]) -> RegistrationResult:
    try:
        return callback.wait_for_completion()
    except pipeline_exceptions.ConnectionDroppedError as e:
        raise exceptions.ConnectionDroppedError("Lost connection to the provisioning server") from e
    except pipeline_exceptions.ConnectionFailedError as e:
        raise exceptions.ConnectionFailedError(
            "Could not connect to the provisioning server"
        ) from e
    except pipeline_exceptions.UnauthorizedError as e:
        raise exceptions.CredentialError("Credentials invalid, could not connect") from e
    except pipeline_exceptions.ProtocolClientError as e:
        raise exceptions.ClientError("Error in the provisioning client") from e
    except pipeline_exceptions.OperationTimeout as e:
        raise exceptions.OperationTimeout("Could not complete operation before timeout") from e
    except pipeline_exceptions.PipelineNotRunning as e:
        raise exceptions.ClientError("Client has already been shut down") from e
    except Exception as e:
        raise exceptions.ClientError("Unexpected failure") from e


class ProvisioningDeviceClient(AbstractProvisioningDeviceClient):
    """
    Client which can be used to run the registration of a device with provisioning service
    using Symmetric Key or X509 authentication.
    """

    def register(self) -> RegistrationResult:
        """
        Register the device with the provisioning service

        This is a synchronous call, meaning that this function will not return until the
        registration process has completed successfully or the attempt has resulted in a failure.
        Before returning, the client will also disconnect from the provisioning service.
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
        :raises: :class:`azure.iot.device.exceptions.OperationTimeout` if the connection times out.
        :raises: :class:`azure.iot.device.exceptions.ClientError` if there is an unexpected failure
            during execution.
        """
        logger.info("Registering with Provisioning Service...")

        if not self._pipeline.responses_enabled[dps_constant.REGISTER]:
            self._enable_responses()

        # Register
        register_complete = EventedCallback(return_arg_name="result")
        self._pipeline.register(payload=self._provisioning_payload, callback=register_complete)
        result = handle_result(register_complete)

        log_on_register_complete(result)

        # Implicitly shut down the pipeline upon successful completion
        if result is not None and result.status == "assigned":
            logger.debug("Beginning pipeline shutdown operation")
            shutdown_complete = EventedCallback()
            self._pipeline.shutdown(callback=shutdown_complete)
            handle_result(shutdown_complete)
            logger.debug("Completed pipeline shutdown operation")

        return result

    def _enable_responses(self) -> None:
        """Enable to receive responses from Device Provisioning Service.

        This is a synchronous call, meaning that this function will not return until the feature
        has been enabled.

        """
        logger.info("Enabling reception of response from Device Provisioning Service...")

        subscription_complete = EventedCallback()
        self._pipeline.enable_responses(callback=subscription_complete)

        handle_result(subscription_complete)

        logger.info("Successfully subscribed to Device Provisioning Service to receive responses")
