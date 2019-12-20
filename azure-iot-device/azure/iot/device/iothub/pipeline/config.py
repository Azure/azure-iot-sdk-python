# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
from azure.iot.device.common.pipeline.config import BasePipelineConfig

logger = logging.getLogger(__name__)


class IoTHubPipelineConfig(BasePipelineConfig):
    """A base class for storing all configurations/options shared across the Azure IoT Python Device Client Library.
    More specific configurations such as those that only apply to the IoT Hub Client will be found in the respective
    config files.
    """

    def __init__(self, product_info="", **kwargs):
        """Initializer for IoTHubPipelineConfig which passes all unrecognized keyword-args down to BasePipelineConfig
        to be evaluated. This stacked options setting is to allow for unique configuration options to exist between the
        IoTHub Client and the Provisioning Client, while maintaining a base configuration class with shared config options.

        :param str product_info: A custom identification string for the type of device connecting to Azure IoT Hub.
        """
        super(IoTHubPipelineConfig, self).__init__(**kwargs)
        self.product_info = product_info

        # Now, the parameters below are not exposed to the user via kwargs. They need to be set by manipulating the IoTHubPipelineConfig object.
        # They are not in the BasePipelineConfig because these do not apply to the provisioning client.
        self.blob_upload = False
        self.method_invoke = False
