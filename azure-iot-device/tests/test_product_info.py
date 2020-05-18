# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from azure.iot.device import product_info
import platform
from azure.iot.device.constant import VERSION, IOTHUB_IDENTIFIER, PROVISIONING_IDENTIFIER


check_agent_format = (
    "{identifier}/{version}({python_runtime};{os_type} {os_release};{architecture})"
)


@pytest.mark.describe(".get_iothub_user_agent()")
class TestGetIothubUserAgent(object):
    @pytest.mark.it(
        "Returns a user agent string formatted for IoTHub, containing python version, operating system and architecture of the system"
    )
    def test_get_iothub_user_agent(self):
        user_agent = product_info.get_iothub_user_agent()

        assert IOTHUB_IDENTIFIER in user_agent
        assert VERSION in user_agent
        assert platform.python_version() in user_agent
        assert platform.system() in user_agent
        assert platform.version() in user_agent
        assert platform.machine() in user_agent
        expected_part_agent = check_agent_format.format(
            identifier=IOTHUB_IDENTIFIER,
            version=VERSION,
            python_runtime=platform.python_version(),
            os_type=platform.system(),
            os_release=platform.version(),
            architecture=platform.machine(),
        )
        assert expected_part_agent == user_agent


@pytest.mark.describe(".get_provisioning_user_agent()")
class TestGetProvisioningUserAgent(object):
    @pytest.mark.it(
        "Returns a user agent string formatted for the Provisioning Service, containing python version, operating system and architecture of the system"
    )
    def test_get_provisioning_user_agent(self):
        user_agent = product_info.get_provisioning_user_agent()

        assert PROVISIONING_IDENTIFIER in user_agent
        assert VERSION in user_agent
        assert platform.python_version() in user_agent
        assert platform.system() in user_agent
        assert platform.version() in user_agent
        assert platform.machine() in user_agent

        expected_part_agent = check_agent_format.format(
            identifier=PROVISIONING_IDENTIFIER,
            version=VERSION,
            python_runtime=platform.python_version(),
            os_type=platform.system(),
            os_release=platform.version(),
            architecture=platform.machine(),
        )
        assert expected_part_agent == user_agent
