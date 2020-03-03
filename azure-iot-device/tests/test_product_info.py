# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from azure.iot.device.product_info import ProductInfo
import platform
from azure.iot.device.constant import VERSION, IOTHUB_IDENTIFIER, PROVISIONING_IDENTIFIER


check_agent_format = (
    "{identifier}/{version}({python_runtime};{os_type} {os_release};{architecture})"
)


@pytest.mark.describe("ProductInfo")
class TestProductInfo(object):
    @pytest.mark.it(
        "Contains python version, operating system and architecture of the system in the iothub agent string"
    )
    def test_get_iothub_user_agent(self):
        user_agent = ProductInfo.get_iothub_user_agent()

        assert IOTHUB_IDENTIFIER in user_agent
        assert VERSION in user_agent
        assert platform.python_version() in user_agent
        assert platform.system() in user_agent
        assert platform.version() in user_agent
        assert platform.machine() in user_agent

    @pytest.mark.it("Checks if the format of the agent string is as expected")
    def test_checks_format_iothub_agent(self):
        expected_part_agent = check_agent_format.format(
            identifier=IOTHUB_IDENTIFIER,
            version=VERSION,
            python_runtime=platform.python_version(),
            os_type=platform.system(),
            os_release=platform.version(),
            architecture=platform.machine(),
        )
        user_agent = ProductInfo.get_iothub_user_agent()
        assert expected_part_agent in user_agent

    @pytest.mark.it(
        "Contains python version, operating system and architecture of the system in the provisioning agent string"
    )
    def test_get_provisioning_user_agent(self):
        user_agent = ProductInfo.get_provisioning_user_agent()

        assert PROVISIONING_IDENTIFIER in user_agent
        assert VERSION in user_agent
        assert platform.python_version() in user_agent
        assert platform.system() in user_agent
        assert platform.version() in user_agent
        assert platform.machine() in user_agent

    @pytest.mark.it("Checks if the format of the agent string is as expected")
    def test_checks_format_provisioning_agent(self):
        expected_part_agent = check_agent_format.format(
            identifier=PROVISIONING_IDENTIFIER,
            version=VERSION,
            python_runtime=platform.python_version(),
            os_type=platform.system(),
            os_release=platform.version(),
            architecture=platform.machine(),
        )
        user_agent = ProductInfo.get_provisioning_user_agent()
        assert expected_part_agent in user_agent
