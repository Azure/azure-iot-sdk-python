# coding=utf-8
# --------------------------------------------------------------------------
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class DigitalTwinInterfacesPatchInterfacesValue(Model):
    """DigitalTwinInterfacesPatchInterfacesValue.

    :param properties: List of properties to update in an interface.
    :type properties: dict[str,
     ~protocol.models.DigitalTwinInterfacesPatchInterfacesValuePropertiesValue]
    """

    _attribute_map = {
        'properties': {'key': 'properties', 'type': '{DigitalTwinInterfacesPatchInterfacesValuePropertiesValue}'},
    }

    def __init__(self, *, properties=None, **kwargs) -> None:
        super(DigitalTwinInterfacesPatchInterfacesValue, self).__init__(**kwargs)
        self.properties = properties
