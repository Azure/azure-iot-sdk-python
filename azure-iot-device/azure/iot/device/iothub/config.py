import logging
from azure.iot.device.common.config import BasePipelineConfig

logger = logging.getLogger(__name__)


class IoTHubPipelineConfig(BasePipelineConfig):
    """A BasePipelineConfig object which contains all possible options for the iothub client.
    """

    def __init__(self, websockets=False):
        """Initializer for IoTHubPipelineConfig

        :param bool websockets: Enabling/disabling websockets in MQTT. This feature is relevant if a firewall blocks port 8883 from use.
        """
        self.websockets = websockets
