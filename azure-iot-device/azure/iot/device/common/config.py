import logging

logger = logging.getLogger(__name__)


class BasePipelineConfig(object):
    """A base class for storing all configurations/options shared across the Azure IoT Python Device Client Library.
    More specific configurations such as those that only apply to the IoT Hub Client will be found in the respective
    config files.
    """

    def __init__(self):
        """Initializer for BasePipelineConfig
        """
