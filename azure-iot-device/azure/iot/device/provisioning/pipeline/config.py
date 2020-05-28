# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
from azure.iot.device.common.pipeline.config import BasePipelineConfig

logger = logging.getLogger(__name__)


class ProvisioningPipelineConfig(BasePipelineConfig):
    """A class for storing all configurations/options for Provisioning clients in the Azure IoT Python Device Client Library.
    """

    def __init__(self, hostname, registration_id, id_scope, **kwargs):
        """Initializer for ProvisioningPipelineConfig which passes all unrecognized keyword-args down to BasePipelineConfig
        to be evaluated. This stacked options setting is to allow for unique configuration options to exist between the
        multiple clients, while maintaining a base configuration class with shared config options.

        :param str hostname: The hostname of the Provisioning hub instance to connect to
        :param str registration_id: The device registration identity being provisioned
        :param str id_scope: The identity of the provisoning service being used
        """
        super(ProvisioningPipelineConfig, self).__init__(hostname=hostname, **kwargs)

        # Provisioning Connection Details
        self.registration_id = registration_id
        self.id_scope = id_scope
