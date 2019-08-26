# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""
This module contains one of the implementations of the Provisioning Device Client which uses Symmetric Key authentication.
"""
import logging
from threading import Event
from .abstract_provisioning_device_client import AbstractProvisioningDeviceClient
from .abstract_provisioning_device_client import log_on_register_complete
from .internal.polling_machine import PollingMachine

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

    def register(self):
        """
        Register the device with the with the provisioning service

        This is a synchronous call, meaning that this function will not return until the
        registration process has completed successfully or the attempt has resulted in a failure.
        Before returning, the client will also disconnect from the provisioning service.
        If a registration attempt is made while a previous registration is in progress it may
        throw an error.
        """
        logger.info("Registering with Provisioning Service...")
        register_complete = Event()

        # hack to work aroud lack of the "nonlocal" keyword in 2.7.  The non-local "context"
        # object can be read and modified inside the inner function.
        # (https://stackoverflow.com/a/28433571)
        class context:
            registration_result = None

        def on_register_complete(result=None, error=None):
            log_on_register_complete(result, error)
            context.registration_result = result
            register_complete.set()

        self._polling_machine.register(callback=on_register_complete)

        register_complete.wait()
        return context.registration_result

    def cancel(self):
        """
        This is a synchronous call, meaning that this function will not return until the cancellation
        process has completed successfully or the attempt has resulted in a failure. Before returning
        the client will also disconnect from the provisioning service.

        In case there is no registration in process it will throw an error as there is
        no registration process to cancel.
        """
        logger.info("Cancelling the current registration process")
        cancel_complete = Event()

        def on_cancel_complete():
            cancel_complete.set()
            logger.info("Successfully cancelled the current registration process")

        self._polling_machine.cancel(callback=on_cancel_complete)
        cancel_complete.wait()
