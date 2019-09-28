# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module should be replaced when there are actual tests for the azure.iot.hub library"""

import pytest
from azure.iot.hub.iothub_registry_manager import IoTHubRegistryManager
from azure.iot.hub.protocol.iot_hub_gateway_service_ap_is20190630 import (
    IotHubGatewayServiceAPIs20190630,
)

from azure.iot.hub.auth import ConnectionStringAuthentication

from azure.iot.hub.protocol.models import AuthenticationMechanism


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
fake_etag = "taggedbymisnitryogmagic"
fake_status = "flying"


@pytest.fixture(scope="function")
def mock_service_operations(mocker):
    mock_service_operations_init = mocker.patch(
        "azure.iot.hub.protocol.iot_hub_gateway_service_ap_is20190630.ServiceOperations"
    )
    return mock_service_operations_init.return_value


@pytest.fixture(scope="function")
def mock_device_constructor(mocker):
    return mocker.patch("azure.iot.hub.iothub_registry_manager.Device")


@pytest.fixture(scope="function")
def mock_module_constructor(mocker):
    return mocker.patch("azure.iot.hub.iothub_registry_manager.Module")


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


@pytest.mark.describe("IoTHubRegistryManager")
class TestIoTHubRegistryManagerInit(object):
    @pytest.mark.it("instantiates correctly with auth")
    def test_init_auth(self, iothub_registry_manager):
        assert iothub_registry_manager is not None
        assert iothub_registry_manager.auth is not None
        assert isinstance(iothub_registry_manager.auth, ConnectionStringAuthentication)

    @pytest.mark.it("instantiates correctly with protocol client with correct Service API version")
    def test_init_protocol_client(self, iothub_registry_manager):
        assert iothub_registry_manager is not None
        assert iothub_registry_manager.protocol is not None
        assert isinstance(iothub_registry_manager.protocol, IotHubGatewayServiceAPIs20190630)


different_devices_sas = [
    pytest.param(
        {
            "function_name": "create_device_with_sas",
            "init_kwargs": {
                "device_id": fake_device_id,
                "primary_key": fake_primary_key,
                "secondary_key": None,
                "status": fake_status,
            },
            "etag": None,
        },
        id="Create with Primary Key",
    ),
    pytest.param(
        {
            "function_name": "create_device_with_sas",
            "init_kwargs": {
                "device_id": fake_device_id,
                "primary_key": None,
                "secondary_key": fake_secondary_key,
                "status": fake_status,
            },
            "etag": None,
        },
        id="Create with Secondary Key",
    ),
    pytest.param(
        {
            "function_name": "update_device_with_sas",
            "init_kwargs": {
                "device_id": fake_device_id,
                "primary_key": fake_primary_key,
                "secondary_key": None,
                "status": fake_status,
                "etag": fake_etag,
            },
            "etag": fake_etag,
        },
        id="Update with Primary Key",
    ),
    pytest.param(
        {
            "function_name": "update_device_with_sas",
            "init_kwargs": {
                "device_id": fake_device_id,
                "primary_key": None,
                "secondary_key": fake_secondary_key,
                "status": fake_status,
                "etag": fake_etag,
            },
            "etag": fake_etag,
        },
        id="Update with Secondary Key",
    ),
]


@pytest.mark.parametrize("params_methods_sas", different_devices_sas)
@pytest.mark.describe("IoTHubRegistryManager Create/Update Device With Symmetric Key")
class TestIoTHubRegistryManagerCreateUpdateDeviceWithSymmetricKey(object):
    @pytest.mark.it("initializes device with device id, status and sas auth")
    def test_initializes_device_with_kwargs(
        self,
        params_methods_sas,
        mock_device_constructor,
        mock_service_operations,
        iothub_registry_manager,
    ):
        func = getattr(iothub_registry_manager, params_methods_sas["function_name"])
        func(**params_methods_sas["init_kwargs"])

        assert mock_device_constructor.call_count == 1

        assert mock_device_constructor.call_args[1]["device_id"] == fake_device_id
        assert mock_device_constructor.call_args[1]["status"] == fake_status
        assert isinstance(
            mock_device_constructor.call_args[1]["authentication"], AuthenticationMechanism
        )
        auth_mechanism = mock_device_constructor.call_args[1]["authentication"]
        assert auth_mechanism.type == "sas"
        assert auth_mechanism.x509_thumbprint is None
        sym_key = auth_mechanism.symmetric_key
        assert sym_key.primary_key == params_methods_sas["init_kwargs"]["primary_key"]
        assert sym_key.secondary_key == params_methods_sas["init_kwargs"]["secondary_key"]

        # Only present for update
        etag = params_methods_sas["etag"]
        if etag:
            assert mock_device_constructor.call_args[1]["etag"] == etag

    @pytest.mark.it(
        "calls method from service operations with device id and previously constructed device"
    )
    def test_create_or_update_device_with_sas(
        self,
        params_methods_sas,
        mock_device_constructor,
        mock_service_operations,
        iothub_registry_manager,
    ):
        func = getattr(iothub_registry_manager, params_methods_sas["function_name"])
        func(**params_methods_sas["init_kwargs"])

        assert mock_service_operations.create_or_update_device.call_count == 1
        assert mock_service_operations.create_or_update_device.call_args[0][0] == fake_device_id
        assert (
            mock_service_operations.create_or_update_device.call_args[0][1]
            == mock_device_constructor.return_value
        )


different_devices_x509 = [
    pytest.param(
        {
            "function_name": "create_device_with_x509",
            "init_kwargs": {
                "device_id": fake_device_id,
                "primary_thumbprint": fake_primary_thumbprint,
                "secondary_thumbprint": None,
                "status": fake_status,
            },
            "etag": None,
        },
        id="Create with Primary Thumbprint",
    ),
    pytest.param(
        {
            "function_name": "create_device_with_x509",
            "init_kwargs": {
                "device_id": fake_device_id,
                "primary_thumbprint": None,
                "secondary_thumbprint": fake_secondary_thumbprint,
                "status": fake_status,
            },
            "etag": None,
        },
        id="Create with Secondary Thumbprint",
    ),
    pytest.param(
        {
            "function_name": "update_device_with_x509",
            "init_kwargs": {
                "device_id": fake_device_id,
                "primary_thumbprint": fake_primary_thumbprint,
                "secondary_thumbprint": None,
                "status": fake_status,
                "etag": fake_etag,
            },
            "etag": fake_etag,
        },
        id="Update with Primary Thumbprint",
    ),
    pytest.param(
        {
            "function_name": "update_device_with_x509",
            "init_kwargs": {
                "device_id": fake_device_id,
                "primary_thumbprint": None,
                "secondary_thumbprint": fake_secondary_thumbprint,
                "status": fake_status,
                "etag": fake_etag,
            },
            "etag": fake_etag,
        },
        id="Update with Secondary Thumbprint",
    ),
]


@pytest.mark.parametrize("params_methods_x509", different_devices_x509)
@pytest.mark.describe("IoTHubRegistryManager Create/Update Device With X509")
class TestIoTHubRegistryManagerCreateUpdateDeviceWithX509(object):
    @pytest.mark.it("initializes device with device id, status and self signed auth")
    def test_initializes_device_with_kwargs(
        self,
        params_methods_x509,
        mock_device_constructor,
        mock_service_operations,
        iothub_registry_manager,
    ):
        func = getattr(iothub_registry_manager, params_methods_x509["function_name"])
        func(**params_methods_x509["init_kwargs"])

        assert mock_device_constructor.call_count == 1
        assert mock_device_constructor.call_args[1]["device_id"] == fake_device_id
        assert mock_device_constructor.call_args[1]["status"] == fake_status
        assert isinstance(
            mock_device_constructor.call_args[1]["authentication"], AuthenticationMechanism
        )
        auth_mechanism = mock_device_constructor.call_args[1]["authentication"]
        assert auth_mechanism.type == "selfSigned"
        assert auth_mechanism.symmetric_key is None
        x509_thumbprint = auth_mechanism.x509_thumbprint
        assert (
            x509_thumbprint.primary_thumbprint
            == params_methods_x509["init_kwargs"]["primary_thumbprint"]
        )
        assert (
            x509_thumbprint.secondary_thumbprint
            == params_methods_x509["init_kwargs"]["secondary_thumbprint"]
        )

        # Only present for update
        etag = params_methods_x509["etag"]
        if etag:
            assert mock_device_constructor.call_args[1]["etag"] == etag

    @pytest.mark.it(
        "calls method from service operations with device id and previously constructed device"
    )
    def test_create_or_update_device_with_x509(
        self,
        params_methods_x509,
        mock_device_constructor,
        mock_service_operations,
        iothub_registry_manager,
    ):

        func = getattr(iothub_registry_manager, params_methods_x509["function_name"])
        func(**params_methods_x509["init_kwargs"])

        assert mock_service_operations.create_or_update_device.call_count == 1
        assert mock_service_operations.create_or_update_device.call_args[0][0] == fake_device_id
        assert (
            mock_service_operations.create_or_update_device.call_args[0][1]
            == mock_device_constructor.return_value
        )


different_devices_ca = [
    pytest.param(
        {
            "function_name": "create_device_with_certificate_authority",
            "init_kwargs": {"device_id": fake_device_id, "status": fake_status},
            "etag": None,
        },
        id="Create with CA",
    ),
    pytest.param(
        {
            "function_name": "update_device_with_certificate_authority",
            "init_kwargs": {"device_id": fake_device_id, "status": fake_status, "etag": fake_etag},
            "etag": fake_etag,
        },
        id="Update with CA",
    ),
]


@pytest.mark.parametrize("params_methods_ca", different_devices_ca)
@pytest.mark.describe("IoTHubRegistryManager Create/Update With CA")
class TestIoTHubRegistryManagerCreateUpdateDeviceWithCA(object):
    @pytest.mark.it("initializes device with device id, status and ca auth")
    def test_initializes_device_with_kwargs(
        self,
        params_methods_ca,
        mock_device_constructor,
        mock_service_operations,
        iothub_registry_manager,
    ):
        func = getattr(iothub_registry_manager, params_methods_ca["function_name"])
        func(**params_methods_ca["init_kwargs"])

        assert mock_device_constructor.call_count == 1
        assert mock_device_constructor.call_args[1]["device_id"] == fake_device_id
        assert mock_device_constructor.call_args[1]["status"] == fake_status
        assert isinstance(
            mock_device_constructor.call_args[1]["authentication"], AuthenticationMechanism
        )
        auth_mechanism = mock_device_constructor.call_args[1]["authentication"]
        assert auth_mechanism.type == "certificateAuthority"
        assert auth_mechanism.x509_thumbprint is None
        assert auth_mechanism.symmetric_key is None

        # Only present for update
        etag = params_methods_ca["etag"]
        if etag:
            assert mock_device_constructor.call_args[1]["etag"] == etag

    @pytest.mark.it(
        "calls method from service operations with device id and previously constructed device"
    )
    def test_create_device_with_certificate_authority(
        self,
        params_methods_ca,
        mock_device_constructor,
        mock_service_operations,
        iothub_registry_manager,
    ):

        func = getattr(iothub_registry_manager, params_methods_ca["function_name"])
        func(**params_methods_ca["init_kwargs"])

        assert mock_service_operations.create_or_update_device.call_count == 1
        assert mock_service_operations.create_or_update_device.call_args[0][0] == fake_device_id
        assert (
            mock_service_operations.create_or_update_device.call_args[0][1]
            == mock_device_constructor.return_value
        )


different_modules_sas = [
    pytest.param(
        {
            "function_name": "create_module_with_sas",
            "init_kwargs": {
                "device_id": fake_device_id,
                "module_id": fake_module_id,
                "managed_by": fake_managed_by,
                "primary_key": fake_primary_key,
                "secondary_key": None,
                "status": fake_status,
            },
            "etag": None,
        },
        id="Create with Primary Key",
    ),
    pytest.param(
        {
            "function_name": "create_module_with_sas",
            "init_kwargs": {
                "device_id": fake_device_id,
                "module_id": fake_module_id,
                "managed_by": fake_managed_by,
                "primary_key": None,
                "secondary_key": fake_secondary_key,
                "status": fake_status,
            },
            "etag": None,
        },
        id="Create with Secondary Key",
    ),
    pytest.param(
        {
            "function_name": "update_module_with_sas",
            "init_kwargs": {
                "device_id": fake_device_id,
                "module_id": fake_module_id,
                "managed_by": fake_managed_by,
                "primary_key": fake_primary_key,
                "secondary_key": None,
                "status": fake_status,
                "etag": fake_etag,
            },
            "etag": fake_etag,
        },
        id="Update with Primary Key",
    ),
    pytest.param(
        {
            "function_name": "update_module_with_sas",
            "init_kwargs": {
                "device_id": fake_device_id,
                "module_id": fake_module_id,
                "managed_by": fake_managed_by,
                "primary_key": None,
                "secondary_key": fake_secondary_key,
                "status": fake_status,
                "etag": fake_etag,
            },
            "etag": fake_etag,
        },
        id="Update with Secondary Key",
    ),
]


@pytest.mark.parametrize("params_methods_sas", different_modules_sas)
@pytest.mark.describe("IoTHubRegistryManager Create/Update module With Symmetric Key")
class TestIoTHubRegistryManagerCreateUpdateModuleWithSymmetricKey(object):
    @pytest.mark.it("initializes module with device id, module id, managed by, status and sas auth")
    def test_initializes_module_with_kwargs(
        self,
        params_methods_sas,
        mock_module_constructor,
        mock_service_operations,
        iothub_registry_manager,
    ):
        func = getattr(iothub_registry_manager, params_methods_sas["function_name"])
        func(**params_methods_sas["init_kwargs"])

        assert mock_module_constructor.call_count == 1

        assert mock_module_constructor.call_args[1]["module_id"] == fake_module_id
        assert mock_module_constructor.call_args[1]["managed_by"] == fake_managed_by
        assert mock_module_constructor.call_args[1]["device_id"] == fake_device_id
        assert mock_module_constructor.call_args[1]["status"] == fake_status
        assert isinstance(
            mock_module_constructor.call_args[1]["authentication"], AuthenticationMechanism
        )
        auth_mechanism = mock_module_constructor.call_args[1]["authentication"]
        assert auth_mechanism.type == "sas"
        assert auth_mechanism.x509_thumbprint is None
        sym_key = auth_mechanism.symmetric_key
        assert sym_key.primary_key == params_methods_sas["init_kwargs"]["primary_key"]
        assert sym_key.secondary_key == params_methods_sas["init_kwargs"]["secondary_key"]

        # Only present for update
        etag = params_methods_sas["etag"]
        if etag:
            assert mock_module_constructor.call_args[1]["etag"] == etag

    @pytest.mark.it(
        "calls method from service operations with device id and previously constructed module"
    )
    def test_create_or_update_module_with_sas(
        self,
        params_methods_sas,
        mock_module_constructor,
        mock_service_operations,
        iothub_registry_manager,
    ):
        func = getattr(iothub_registry_manager, params_methods_sas["function_name"])
        func(**params_methods_sas["init_kwargs"])

        assert mock_service_operations.create_or_update_module.call_count == 1
        assert mock_service_operations.create_or_update_module.call_args[0][0] == fake_device_id
        assert mock_service_operations.create_or_update_module.call_args[0][1] == fake_module_id
        assert (
            mock_service_operations.create_or_update_module.call_args[0][2]
            == mock_module_constructor.return_value
        )


different_modules_x509 = [
    pytest.param(
        {
            "function_name": "create_module_with_x509",
            "init_kwargs": {
                "device_id": fake_device_id,
                "module_id": fake_module_id,
                "managed_by": fake_managed_by,
                "primary_thumbprint": fake_primary_thumbprint,
                "secondary_thumbprint": None,
                "status": fake_status,
            },
            "etag": None,
        },
        id="Create with Primary Thumbprint",
    ),
    pytest.param(
        {
            "function_name": "create_module_with_x509",
            "init_kwargs": {
                "device_id": fake_device_id,
                "module_id": fake_module_id,
                "managed_by": fake_managed_by,
                "primary_thumbprint": None,
                "secondary_thumbprint": fake_secondary_thumbprint,
                "status": fake_status,
            },
            "etag": None,
        },
        id="Create with Secondary Thumbprint",
    ),
    pytest.param(
        {
            "function_name": "update_module_with_x509",
            "init_kwargs": {
                "device_id": fake_device_id,
                "module_id": fake_module_id,
                "managed_by": fake_managed_by,
                "primary_thumbprint": fake_primary_thumbprint,
                "secondary_thumbprint": None,
                "status": fake_status,
                "etag": fake_etag,
            },
            "etag": fake_etag,
        },
        id="Update with Primary Thumbprint",
    ),
    pytest.param(
        {
            "function_name": "update_module_with_x509",
            "init_kwargs": {
                "device_id": fake_device_id,
                "module_id": fake_module_id,
                "managed_by": fake_managed_by,
                "primary_thumbprint": None,
                "secondary_thumbprint": fake_secondary_thumbprint,
                "status": fake_status,
                "etag": fake_etag,
            },
            "etag": fake_etag,
        },
        id="Update with Secondary Thumbprint",
    ),
]


@pytest.mark.parametrize("params_methods_x509", different_modules_x509)
@pytest.mark.describe("IoTHubRegistryManager Create/Update module With X509")
class TestIoTHubRegistryManagerCreateUpdateModuleWithX509(object):
    @pytest.mark.it(
        "initializes module with device id, module id, managed by, status and self signed auth"
    )
    def test_initializes_module_with_kwargs(
        self,
        params_methods_x509,
        mock_module_constructor,
        mock_service_operations,
        iothub_registry_manager,
    ):

        func = getattr(iothub_registry_manager, params_methods_x509["function_name"])
        func(**params_methods_x509["init_kwargs"])

        assert mock_module_constructor.call_count == 1

        assert mock_module_constructor.call_args[1]["module_id"] == fake_module_id
        assert mock_module_constructor.call_args[1]["managed_by"] == fake_managed_by
        assert mock_module_constructor.call_count == 1
        assert mock_module_constructor.call_args[1]["device_id"] == fake_device_id
        assert mock_module_constructor.call_args[1]["status"] == fake_status
        assert isinstance(
            mock_module_constructor.call_args[1]["authentication"], AuthenticationMechanism
        )
        auth_mechanism = mock_module_constructor.call_args[1]["authentication"]
        assert auth_mechanism.type == "selfSigned"
        assert auth_mechanism.symmetric_key is None
        x509_thumbprint = auth_mechanism.x509_thumbprint
        assert (
            x509_thumbprint.primary_thumbprint
            == params_methods_x509["init_kwargs"]["primary_thumbprint"]
        )
        assert (
            x509_thumbprint.secondary_thumbprint
            == params_methods_x509["init_kwargs"]["secondary_thumbprint"]
        )

        # Only present for update
        etag = params_methods_x509["etag"]
        if etag:
            assert mock_module_constructor.call_args[1]["etag"] == etag

    @pytest.mark.it(
        "calls method from service operations with device id and previously constructed module"
    )
    def test_create_or_update_module_with_x509(
        self,
        params_methods_x509,
        mock_module_constructor,
        mock_service_operations,
        iothub_registry_manager,
    ):
        func = getattr(iothub_registry_manager, params_methods_x509["function_name"])
        func(**params_methods_x509["init_kwargs"])

        assert mock_service_operations.create_or_update_module.call_count == 1
        assert mock_service_operations.create_or_update_module.call_args[0][0] == fake_device_id
        assert mock_service_operations.create_or_update_module.call_args[0][1] == fake_module_id
        assert (
            mock_service_operations.create_or_update_module.call_args[0][2]
            == mock_module_constructor.return_value
        )


different_modules_ca = [
    pytest.param(
        {
            "function_name": "create_module_with_certificate_authority",
            "init_kwargs": {
                "device_id": fake_device_id,
                "module_id": fake_module_id,
                "managed_by": fake_managed_by,
                "status": fake_status,
            },
            "etag": None,
        },
        id="Create",
    ),
    pytest.param(
        {
            "function_name": "update_module_with_certificate_authority",
            "init_kwargs": {
                "device_id": fake_device_id,
                "module_id": fake_module_id,
                "managed_by": fake_managed_by,
                "status": fake_status,
                "etag": fake_etag,
            },
            "etag": fake_etag,
        },
        id="Update",
    ),
]


@pytest.mark.parametrize("params_methods_ca", different_modules_ca)
@pytest.mark.describe("IoTHubRegistryManager Create/Update module With CA")
class TestIoTHubRegistryManagerCreateUpdateModuleWithCA(object):
    @pytest.mark.it("initializes module with device id, module id, managed by, status and CA auth")
    def test_initializes_module_with_kwargs(
        self,
        params_methods_ca,
        mock_module_constructor,
        mock_service_operations,
        iothub_registry_manager,
    ):
        func = getattr(iothub_registry_manager, params_methods_ca["function_name"])
        func(**params_methods_ca["init_kwargs"])

        assert mock_module_constructor.call_count == 1

        assert mock_module_constructor.call_args[1]["module_id"] == fake_module_id
        assert mock_module_constructor.call_args[1]["managed_by"] == fake_managed_by
        assert mock_module_constructor.call_count == 1
        assert mock_module_constructor.call_args[1]["device_id"] == fake_device_id
        assert mock_module_constructor.call_args[1]["status"] == fake_status
        assert isinstance(
            mock_module_constructor.call_args[1]["authentication"], AuthenticationMechanism
        )
        auth_mechanism = mock_module_constructor.call_args[1]["authentication"]
        assert auth_mechanism.type == "certificateAuthority"
        assert auth_mechanism.x509_thumbprint is None
        assert auth_mechanism.symmetric_key is None

        # Only present for update
        etag = params_methods_ca["etag"]
        if etag:
            assert mock_module_constructor.call_args[1]["etag"] == etag

    @pytest.mark.it(
        "calls method from service operations with device id and previously constructed module"
    )
    def test_create_or_update_module_with_ca(
        self,
        params_methods_ca,
        mock_module_constructor,
        mock_service_operations,
        iothub_registry_manager,
    ):
        func = getattr(iothub_registry_manager, params_methods_ca["function_name"])
        func(**params_methods_ca["init_kwargs"])

        # if "update" in params_methods_x509["function_name"]:
        assert mock_service_operations.create_or_update_module.call_count == 1
        assert mock_service_operations.create_or_update_module.call_args[0][0] == fake_device_id
        assert mock_service_operations.create_or_update_module.call_args[0][1] == fake_module_id
        assert (
            mock_service_operations.create_or_update_module.call_args[0][2]
            == mock_module_constructor.return_value
        )


@pytest.mark.describe("IoTHubRegistryManager -- Device Related Getters")
class TestGetDevice(object):
    @pytest.mark.it("gets device from service for provided device id")
    def test_get_device(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_device(fake_device_id)

        assert mock_service_operations.get_device.call_args == mocker.call(fake_device_id)

    @pytest.mark.it("gets configuration of device from service for provided device id")
    def test_get_config_of_device(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_configuration(fake_device_id)

        assert mock_service_operations.get_configuration.call_args == mocker.call(fake_device_id)


@pytest.mark.describe("IoTHubRegistryManager -- Module Related Getters")
class TestGetModule(object):
    @pytest.mark.it("gets module from service for provided device id and module id")
    def test_get_module(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_module(fake_device_id, fake_module_id)

        assert mock_service_operations.get_module.call_args == mocker.call(
            fake_device_id, fake_module_id
        )


@pytest.mark.describe("IoTHubRegistryManager -- Delete")
class TestDeleteDeviceModule(object):
    @pytest.mark.it("deletes device for the provided device id")
    def test_delete_device(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.delete_device(fake_device_id)

        assert mock_service_operations.delete_device.call_args == mocker.call(fake_device_id, "*")

    @pytest.mark.it("deletes device with an etag for the provided device id and etag")
    def test_delete_device_with_etag(
        self, mocker, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.delete_device(device_id=fake_device_id, etag=fake_etag)

        assert mock_service_operations.delete_device.call_args == mocker.call(
            fake_device_id, fake_etag
        )

    @pytest.mark.it("deletes module for the provided device id")
    def test_delete_module(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.delete_module(fake_device_id)

        assert mock_service_operations.delete_module.call_args == mocker.call(fake_device_id, "*")

    @pytest.mark.it("deletes module with an etag for the provided device id and etag")
    def test_delete_module_with_etag(
        self, mocker, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.delete_module(device_id=fake_device_id, etag=fake_etag)

        assert mock_service_operations.delete_module.call_args == mocker.call(
            fake_device_id, fake_etag
        )


@pytest.mark.describe("IoTHubRegistryManager -- Service Related Getters")
class TestGetService(object):
    @pytest.mark.it("gets service statistics")
    def test_get_service_statistics(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_service_statistics()

        assert mock_service_operations.get_service_statistics.call_args == mocker.call()

    @pytest.mark.it("gets device registry statistics")
    def test_get_device_registry_statistics(
        self, mocker, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.get_device_registry_statistics()

        assert mock_service_operations.get_device_registry_statistics.call_args == mocker.call()
