# coding=utf-8
# --------------------------------------------------------------------------
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class ConfigurationContent(Model):
    """Configuration Content for Devices or Modules on Edge Devices.

    :param device_content: Gets or sets device Configurations
    :type device_content: dict[str, object]
    :param modules_content: Gets or sets Modules Configurations
    :type modules_content: dict[str, dict[str, object]]
    :param module_content: Gets or sets Module Configurations
    :type module_content: dict[str, object]
    """

    _attribute_map = {
        "device_content": {"key": "deviceContent", "type": "{object}"},
        "modules_content": {"key": "modulesContent", "type": "{{object}}"},
        "module_content": {"key": "moduleContent", "type": "{object}"},
    }

    def __init__(self, **kwargs):
        super(ConfigurationContent, self).__init__(**kwargs)
        self.device_content = kwargs.get("device_content", None)
        self.modules_content = kwargs.get("modules_content", None)
        self.module_content = kwargs.get("module_content", None)
