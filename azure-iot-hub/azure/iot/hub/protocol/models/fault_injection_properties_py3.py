# coding=utf-8
# --------------------------------------------------------------------------
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class FaultInjectionProperties(Model):
    """FaultInjectionProperties.

    :param iot_hub_name:
    :type iot_hub_name: str
    :param connection:
    :type connection: ~protocol.models.FaultInjectionConnectionProperties
    :param last_updated_time_utc: Service generated.
    :type last_updated_time_utc: datetime
    """

    _attribute_map = {
        'iot_hub_name': {'key': 'IotHubName', 'type': 'str'},
        'connection': {'key': 'connection', 'type': 'FaultInjectionConnectionProperties'},
        'last_updated_time_utc': {'key': 'lastUpdatedTimeUtc', 'type': 'iso-8601'},
    }

    def __init__(self, *, iot_hub_name: str=None, connection=None, last_updated_time_utc=None, **kwargs) -> None:
        super(FaultInjectionProperties, self).__init__(**kwargs)
        self.iot_hub_name = iot_hub_name
        self.connection = connection
        self.last_updated_time_utc = last_updated_time_utc
