# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains user-facing asynchronous clients for the
Azure Provisioning Device SDK for Python.
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
        NOTE : This initializer should not be called directly.
        Instead, the class method `create_from_security_client` should be used to create a client object.
        :param provisioning_pipeline: The protocol pipeline for provisioning. As of now this only supports MQTT.
        """
        super(ProvisioningDeviceClient, self).__init__(provisioning_pipeline)
        self._polling_machine = PollingMachine(provisioning_pipeline)

    async def register(self):
        """
        Register the device with the provisioning service.
        Before returning the client will also disconnect from the provisioning service.
        If a registration attempt is made while a previous registration is in progress it may throw an error.
        """
        logger.info("Registering with Provisioning Service...")
        register_async = async_adapter.emulate_async(self._polling_machine.register)

        def sync_on_register_complete(result=None, error=None):
            log_on_register_complete(result, error)

        callback = async_adapter.AwaitableCallback(sync_on_register_complete)

        await register_async(callback=callback)
        await callback.completion()

    async def cancel(self):
        """
        Before returning the client will also disconnect from the provisioning service.

        In case there is no registration in process it will throw an error as there is
        no registration process to cancel.
        """
        logger.info("Disconnecting from Provisioning Service...")
        cancel_async = async_adapter.emulate_async(self._polling_machine.cancel)

        def sync_on_cancel_complete():
            logger.info("Successfully cancelled the current registration process")

        callback = async_adapter.AwaitableCallback(sync_on_cancel_complete)

        await cancel_async(callback=callback)
        await callback.completion()
