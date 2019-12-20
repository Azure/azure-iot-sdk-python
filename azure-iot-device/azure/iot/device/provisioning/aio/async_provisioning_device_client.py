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
from azure.iot.device.provisioning.internal.polling_machine import PollingMachine

logger = logging.getLogger(__name__)


class ProvisioningDeviceClient(AbstractProvisioningDeviceClient):
    """
    Client which can be used to run the registration of a device with provisioning service
    using Symmetric Key authentication.
    """

    def __init__(self, provisioning_pipeline):
        """
        Initializer for the Provisioning Client.

        NOTE: This initializer should not be called directly.
        Instead, the class methods that start with `create_from_` should be used to create a
        client object.

        :param provisioning_pipeline: The protocol pipeline for provisioning.
        :type provisioning_pipeline: :class:`azure.iot.device.provisioning.pipeline.ProvisioningPipeline`
        """
        super(ProvisioningDeviceClient, self).__init__(provisioning_pipeline)
        self._polling_machine = PollingMachine(provisioning_pipeline)

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
        register_async = async_adapter.emulate_async(self._polling_machine.register)

        callback = async_adapter.AwaitableCallback(return_arg_name="result")
        await register_async(payload=self._provisioning_payload, callback=callback)
        result = await callback.completion()

        log_on_register_complete(result)
        return result
