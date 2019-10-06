# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.hub.iothub_registry_manager import IoTHubRegistryManager

"""---Constants---"""

fake_shared_access_key = "Zm9vYmFy"
fake_shared_access_key_name = "alohomora"

fake_primary_key = "petrificus"
fake_secondary_key = "totalus"
fake_primary_thumbprint = "HELFKCPOXAIR9PVNOA3"
fake_secondary_thumbprint = "RGSHARLU4VYYFENINUF"
fake_hostname = "beauxbatons.academy-net"
fake_device_id = "MyPensieve"
fake_module_id = "Divination"
fake_managed_by = "Hogwarts"
fake_etag = "taggedbymisnitryofmagic"
fake_status = "flying"


"""----Shared fixtures----"""


@pytest.fixture(scope="function")
def mock_service_operations(mocker):
    mock_service_operations_init = mocker.patch(
        "azure.iot.hub.protocol.iot_hub_gateway_service_ap_is20190630.ServiceOperations"
    )
    return mock_service_operations_init.return_value


@pytest.fixture(scope="function")
def iothub_registry_manager():
    connection_string = "HostName={hostname};DeviceId={device_id};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
        hostname=fake_hostname,
        device_id=fake_device_id,
        skn=fake_shared_access_key_name,
        sk=fake_shared_access_key,
    )
    iothub_registry_manager = IoTHubRegistryManager(connection_string)
    return iothub_registry_manager
