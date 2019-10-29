# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.hub.protocol.models import AuthenticationMechanism
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


@pytest.fixture(scope="function", autouse=True)
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


@pytest.fixture(scope="function")
def mock_device_constructor(mocker):
    return mocker.patch("azure.iot.hub.iothub_registry_manager.Device")


@pytest.fixture(scope="function")
def mock_module_constructor(mocker):
    return mocker.patch("azure.iot.hub.iothub_registry_manager.Module")


@pytest.mark.describe("IoTHubRegistryManager - .create_device_with_sas()")
class TestCreateDeviceWithSymmetricKey(object):

    testdata = [
        (fake_primary_key, None),
        (None, fake_secondary_key),
        (fake_primary_key, fake_secondary_key),
    ]

    @pytest.mark.it("Initializes device with device id, status and sas auth")
    @pytest.mark.parametrize(
        "primary_key, secondary_key", testdata, ids=["Primary Key", "Secondary Key", "Both Keys"]
    )
    def test_initializes_device_with_kwargs_for_sas(
        self, iothub_registry_manager, mock_device_constructor, primary_key, secondary_key
    ):
        iothub_registry_manager.create_device_with_sas(
            device_id=fake_device_id,
            status=fake_status,
            primary_key=primary_key,
            secondary_key=secondary_key,
        )

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
        assert sym_key.primary_key == primary_key
        assert sym_key.secondary_key == secondary_key

    @pytest.mark.it(
        "Calls method from service operations with device id and previously constructed device"
    )
    @pytest.mark.parametrize(
        "primary_key, secondary_key", testdata, ids=["Primary Key", "Secondary Key", "Both Keys"]
    )
    def test_calls_create_or_update_device_for_sas(
        self,
        mock_device_constructor,
        mock_service_operations,
        iothub_registry_manager,
        primary_key,
        secondary_key,
    ):
        iothub_registry_manager.create_device_with_sas(
            device_id=fake_device_id,
            status=fake_status,
            primary_key=primary_key,
            secondary_key=secondary_key,
        )

        assert mock_service_operations.create_or_update_device.call_count == 1
        assert mock_service_operations.create_or_update_device.call_args[0][0] == fake_device_id
        assert (
            mock_service_operations.create_or_update_device.call_args[0][1]
            == mock_device_constructor.return_value
        )


@pytest.mark.describe("IoTHubRegistryManager - .create_device_with_x509()")
class TestCreateDeviceWithX509(object):

    testdata = [
        (fake_primary_thumbprint, None),
        (None, fake_secondary_thumbprint),
        (fake_primary_thumbprint, fake_secondary_thumbprint),
    ]

    @pytest.mark.it("Initializes device with device id, status and X509 auth")
    @pytest.mark.parametrize(
        "primary_thumbprint, secondary_thumbprint",
        testdata,
        ids=["Primary Thumbprint", "Secondary Thumbprint", "Both Thumbprints"],
    )
    def test_initializes_device_with_kwargs_for_x509(
        self,
        iothub_registry_manager,
        mock_device_constructor,
        primary_thumbprint,
        secondary_thumbprint,
    ):
        iothub_registry_manager.create_device_with_x509(
            device_id=fake_device_id,
            status=fake_status,
            primary_thumbprint=primary_thumbprint,
            secondary_thumbprint=secondary_thumbprint,
        )

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
        assert x509_thumbprint.primary_thumbprint == primary_thumbprint
        assert x509_thumbprint.secondary_thumbprint == secondary_thumbprint

    @pytest.mark.it(
        "Calls method from service operations with device id and previously constructed device"
    )
    @pytest.mark.parametrize(
        "primary_thumbprint, secondary_thumbprint",
        testdata,
        ids=["Primary Thumbprint", "Secondary Thumbprint", "Both Thumbprints"],
    )
    def test_calls_create_or_update_device_for_x509(
        self,
        mock_device_constructor,
        mock_service_operations,
        iothub_registry_manager,
        primary_thumbprint,
        secondary_thumbprint,
    ):
        iothub_registry_manager.create_device_with_x509(
            device_id=fake_device_id,
            status=fake_status,
            primary_thumbprint=primary_thumbprint,
            secondary_thumbprint=secondary_thumbprint,
        )

        assert mock_service_operations.create_or_update_device.call_count == 1
        assert mock_service_operations.create_or_update_device.call_args[0][0] == fake_device_id
        assert (
            mock_service_operations.create_or_update_device.call_args[0][1]
            == mock_device_constructor.return_value
        )


@pytest.mark.describe("IoTHubRegistryManager - .create_device_with_certificate_authority()")
class TestCreateDeviceWithCA(object):
    @pytest.mark.it("Initializes device with device id, status and ca auth")
    def test_initializes_device_with_kwargs_for_certificate_authority(
        self, mock_device_constructor, iothub_registry_manager
    ):
        iothub_registry_manager.create_device_with_certificate_authority(
            device_id=fake_device_id, status=fake_status
        )

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

    @pytest.mark.it(
        "Calls method from service operations with device id and previously constructed device"
    )
    def test_calls_create_or_update_device_for_certificate_authority(
        self, mock_device_constructor, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.create_device_with_certificate_authority(
            device_id=fake_device_id, status=fake_status
        )

        assert mock_service_operations.create_or_update_device.call_count == 1
        assert mock_service_operations.create_or_update_device.call_args[0][0] == fake_device_id
        assert (
            mock_service_operations.create_or_update_device.call_args[0][1]
            == mock_device_constructor.return_value
        )


@pytest.mark.describe("IoTHubRegistryManager - .update_device_with_sas()")
class TestUpdateDeviceWithSymmetricKey(object):

    testdata = [
        (fake_primary_key, None),
        (None, fake_secondary_key),
        (fake_primary_key, fake_secondary_key),
    ]

    @pytest.mark.it("Initializes device with device id, status, etag and sas auth")
    @pytest.mark.parametrize(
        "primary_key, secondary_key", testdata, ids=["Primary Key", "Secondary Key", "Both Keys"]
    )
    def test_initializes_device_with_kwargs_for_sas(
        self, iothub_registry_manager, mock_device_constructor, primary_key, secondary_key
    ):
        iothub_registry_manager.update_device_with_sas(
            device_id=fake_device_id,
            status=fake_status,
            etag=fake_etag,
            primary_key=primary_key,
            secondary_key=secondary_key,
        )

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
        assert sym_key.primary_key == primary_key
        assert sym_key.secondary_key == secondary_key
        assert mock_device_constructor.call_args[1]["etag"] == fake_etag

    @pytest.mark.it(
        "Calls method from service operations with device id and previously constructed device"
    )
    @pytest.mark.parametrize(
        "primary_key, secondary_key", testdata, ids=["Primary Key", "Secondary Key", "Both Keys"]
    )
    def test_calls_create_or_update_device_for_sas(
        self,
        mock_device_constructor,
        mock_service_operations,
        iothub_registry_manager,
        primary_key,
        secondary_key,
    ):
        iothub_registry_manager.update_device_with_sas(
            device_id=fake_device_id,
            status=fake_status,
            etag=fake_etag,
            primary_key=primary_key,
            secondary_key=secondary_key,
        )

        assert mock_service_operations.create_or_update_device.call_count == 1
        assert mock_service_operations.create_or_update_device.call_args[0][0] == fake_device_id
        assert (
            mock_service_operations.create_or_update_device.call_args[0][1]
            == mock_device_constructor.return_value
        )


@pytest.mark.describe("IoTHubRegistryManager - .update_device_with_x509()")
class TestUpdateDeviceWithX509(object):

    testdata = [
        (fake_primary_thumbprint, None),
        (None, fake_secondary_thumbprint),
        (fake_primary_thumbprint, fake_secondary_thumbprint),
    ]

    @pytest.mark.it("Initializes device with device id, status and X509 auth")
    @pytest.mark.parametrize(
        "primary_thumbprint, secondary_thumbprint",
        testdata,
        ids=["Primary Thumbprint", "Secondary Thumbprint", "Both Thumbprints"],
    )
    def test_initializes_device_with_kwargs_for_x509(
        self,
        iothub_registry_manager,
        mock_device_constructor,
        primary_thumbprint,
        secondary_thumbprint,
    ):
        iothub_registry_manager.update_device_with_x509(
            device_id=fake_device_id,
            status=fake_status,
            etag=fake_etag,
            primary_thumbprint=primary_thumbprint,
            secondary_thumbprint=secondary_thumbprint,
        )

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
        assert x509_thumbprint.primary_thumbprint == primary_thumbprint
        assert x509_thumbprint.secondary_thumbprint == secondary_thumbprint
        assert mock_device_constructor.call_args[1]["etag"] == fake_etag

    @pytest.mark.it(
        "Calls method from service operations with device id and previously constructed device"
    )
    @pytest.mark.parametrize(
        "primary_thumbprint, secondary_thumbprint",
        testdata,
        ids=["Primary Thumbprint", "Secondary Thumbprint", "Both Thumbprints"],
    )
    def test_calls_create_or_update_device_for_x509(
        self,
        mock_device_constructor,
        mock_service_operations,
        iothub_registry_manager,
        primary_thumbprint,
        secondary_thumbprint,
    ):
        iothub_registry_manager.update_device_with_x509(
            device_id=fake_device_id,
            status=fake_status,
            etag=fake_etag,
            primary_thumbprint=primary_thumbprint,
            secondary_thumbprint=secondary_thumbprint,
        )

        assert mock_service_operations.create_or_update_device.call_count == 1
        assert mock_service_operations.create_or_update_device.call_args[0][0] == fake_device_id
        assert (
            mock_service_operations.create_or_update_device.call_args[0][1]
            == mock_device_constructor.return_value
        )


@pytest.mark.describe("IoTHubRegistryManager - .update_device_with_certificate_authority()")
class TestUpdateDeviceWithCA(object):
    @pytest.mark.it("Initializes device with device id, status and ca auth")
    def test_initializes_device_with_kwargs_for_certificate_authority(
        self, mock_device_constructor, iothub_registry_manager
    ):
        iothub_registry_manager.update_device_with_certificate_authority(
            device_id=fake_device_id, status=fake_status, etag=fake_etag
        )

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
        assert mock_device_constructor.call_args[1]["etag"] == fake_etag

    @pytest.mark.it(
        "Calls method from service operations with device id and previously constructed device"
    )
    def test_calls_create_or_update_device_for_certificate_authority(
        self, mock_device_constructor, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.update_device_with_certificate_authority(
            device_id=fake_device_id, status=fake_status, etag=fake_etag
        )

        assert mock_service_operations.create_or_update_device.call_count == 1
        assert mock_service_operations.create_or_update_device.call_args[0][0] == fake_device_id
        assert (
            mock_service_operations.create_or_update_device.call_args[0][1]
            == mock_device_constructor.return_value
        )


@pytest.mark.describe("IoTHubRegistryManager -- .get_device()")
class TestGetDevice(object):
    @pytest.mark.it("Gets device from service for provided device id")
    def test_get_device(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_device(fake_device_id)

        assert mock_service_operations.get_device.call_count == 1
        assert mock_service_operations.get_device.call_args == mocker.call(fake_device_id)


@pytest.mark.describe("IoTHubRegistryManager - .get_device()")
class TestGetConfigOfDevice(object):
    @pytest.mark.it("Gets configuration of device from service for provided device id")
    def test_get_config_of_device(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_configuration(fake_device_id)

        assert mock_service_operations.get_configuration.call_count == 1
        assert mock_service_operations.get_configuration.call_args == mocker.call(fake_device_id)


@pytest.mark.describe("IoTHubRegistryManager - .delete_device()")
class TestDeleteDevice(object):
    @pytest.mark.it("Deletes device for the provided device id")
    def test_delete_device(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.delete_device(fake_device_id)

        assert mock_service_operations.delete_device.call_count == 1
        assert mock_service_operations.delete_device.call_args == mocker.call(fake_device_id, "*")

    @pytest.mark.it("Deletes device with an etag for the provided device id and etag")
    def test_delete_device_with_etag(
        self, mocker, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.delete_device(device_id=fake_device_id, etag=fake_etag)

        assert mock_service_operations.delete_device.call_count == 1
        assert mock_service_operations.delete_device.call_args == mocker.call(
            fake_device_id, fake_etag
        )


@pytest.mark.describe("IoTHubRegistryManager - .create_module_with_sas()")
class TestCreateModuleWithSymmetricKey(object):

    testdata = [
        (fake_primary_key, None),
        (None, fake_secondary_key),
        (fake_primary_key, fake_secondary_key),
    ]

    @pytest.mark.it("Initializes module with device id, module id, managed_by and sas auth")
    @pytest.mark.parametrize(
        "primary_key, secondary_key", testdata, ids=["Primary Key", "Secondary Key", "Both Keys"]
    )
    def test_initializes_device_with_kwargs_for_sas(
        self, iothub_registry_manager, mock_module_constructor, primary_key, secondary_key
    ):
        iothub_registry_manager.create_module_with_sas(
            device_id=fake_device_id,
            module_id=fake_module_id,
            managed_by=fake_managed_by,
            primary_key=primary_key,
            secondary_key=secondary_key,
        )

        assert mock_module_constructor.call_count == 1

        assert mock_module_constructor.call_args[1]["module_id"] == fake_module_id
        assert mock_module_constructor.call_args[1]["managed_by"] == fake_managed_by
        assert mock_module_constructor.call_args[1]["device_id"] == fake_device_id
        assert isinstance(
            mock_module_constructor.call_args[1]["authentication"], AuthenticationMechanism
        )
        auth_mechanism = mock_module_constructor.call_args[1]["authentication"]
        assert auth_mechanism.type == "sas"
        assert auth_mechanism.x509_thumbprint is None
        sym_key = auth_mechanism.symmetric_key
        assert sym_key.primary_key == primary_key
        assert sym_key.secondary_key == secondary_key

    @pytest.mark.it(
        "Calls method from service operations with device id, module id and previously constructed module"
    )
    @pytest.mark.parametrize(
        "primary_key, secondary_key", testdata, ids=["Primary Key", "Secondary Key", "Both Keys"]
    )
    def test_calls_create_or_update_device_for_sas(
        self,
        mock_module_constructor,
        mock_service_operations,
        iothub_registry_manager,
        primary_key,
        secondary_key,
    ):
        iothub_registry_manager.create_module_with_sas(
            device_id=fake_device_id,
            module_id=fake_module_id,
            managed_by=fake_managed_by,
            primary_key=primary_key,
            secondary_key=secondary_key,
        )

        assert mock_service_operations.create_or_update_module.call_count == 1
        assert mock_service_operations.create_or_update_module.call_args[0][0] == fake_device_id
        assert mock_service_operations.create_or_update_module.call_args[0][1] == fake_module_id
        assert (
            mock_service_operations.create_or_update_module.call_args[0][2]
            == mock_module_constructor.return_value
        )


@pytest.mark.describe("IoTHubRegistryManager - .create_module_with_x509()")
class TestCreateModuleWithX509(object):

    testdata = [
        (fake_primary_thumbprint, None),
        (None, fake_secondary_thumbprint),
        (fake_primary_thumbprint, fake_secondary_thumbprint),
    ]

    @pytest.mark.it("Initializes module with device id, module id, managed_by and X509 auth")
    @pytest.mark.parametrize(
        "primary_thumbprint, secondary_thumbprint",
        testdata,
        ids=["Primary Thumbprint", "Secondary Thumbprint", "Both Thumbprints"],
    )
    def test_initializes_device_with_kwargs_for_x509(
        self,
        iothub_registry_manager,
        mock_module_constructor,
        primary_thumbprint,
        secondary_thumbprint,
    ):
        iothub_registry_manager.create_module_with_x509(
            device_id=fake_device_id,
            module_id=fake_module_id,
            managed_by=fake_managed_by,
            primary_thumbprint=primary_thumbprint,
            secondary_thumbprint=secondary_thumbprint,
        )

        assert mock_module_constructor.call_count == 1
        assert mock_module_constructor.call_args[1]["module_id"] == fake_module_id
        assert mock_module_constructor.call_args[1]["managed_by"] == fake_managed_by
        assert mock_module_constructor.call_args[1]["device_id"] == fake_device_id
        assert isinstance(
            mock_module_constructor.call_args[1]["authentication"], AuthenticationMechanism
        )
        auth_mechanism = mock_module_constructor.call_args[1]["authentication"]
        assert auth_mechanism.type == "selfSigned"
        assert auth_mechanism.symmetric_key is None
        x509_thumbprint = auth_mechanism.x509_thumbprint
        assert x509_thumbprint.primary_thumbprint == primary_thumbprint
        assert x509_thumbprint.secondary_thumbprint == secondary_thumbprint

    @pytest.mark.it(
        "Calls method from service operations with device id, module id and previously constructed module"
    )
    @pytest.mark.parametrize(
        "primary_thumbprint, secondary_thumbprint",
        testdata,
        ids=["Primary Thumbprint", "Secondary Thumbprint", "Both Thumbprints"],
    )
    def test_calls_create_or_update_device_for_x509(
        self,
        mock_module_constructor,
        mock_service_operations,
        iothub_registry_manager,
        primary_thumbprint,
        secondary_thumbprint,
    ):
        iothub_registry_manager.create_module_with_x509(
            device_id=fake_device_id,
            module_id=fake_module_id,
            managed_by=fake_managed_by,
            primary_thumbprint=primary_thumbprint,
            secondary_thumbprint=secondary_thumbprint,
        )

        assert mock_service_operations.create_or_update_module.call_count == 1
        assert mock_service_operations.create_or_update_module.call_args[0][0] == fake_device_id
        assert mock_service_operations.create_or_update_module.call_args[0][1] == fake_module_id
        assert (
            mock_service_operations.create_or_update_module.call_args[0][2]
            == mock_module_constructor.return_value
        )


@pytest.mark.describe("IoTHubRegistryManager - .create_module_with_certificate_authority()")
class TestCreateModuleWithCA(object):
    @pytest.mark.it("Initializes module with device id, module id, managed_by and ca auth")
    def test_initializes_device_with_kwargs_for_certificate_authority(
        self, mock_module_constructor, iothub_registry_manager
    ):
        iothub_registry_manager.create_module_with_certificate_authority(
            device_id=fake_device_id, module_id=fake_module_id, managed_by=fake_managed_by
        )

        assert mock_module_constructor.call_count == 1
        assert mock_module_constructor.call_args[1]["module_id"] == fake_module_id
        assert mock_module_constructor.call_args[1]["managed_by"] == fake_managed_by
        assert mock_module_constructor.call_args[1]["device_id"] == fake_device_id
        assert isinstance(
            mock_module_constructor.call_args[1]["authentication"], AuthenticationMechanism
        )
        auth_mechanism = mock_module_constructor.call_args[1]["authentication"]
        assert auth_mechanism.type == "certificateAuthority"
        assert auth_mechanism.x509_thumbprint is None
        assert auth_mechanism.symmetric_key is None

    @pytest.mark.it(
        "Calls method from service operations with device id, module id and previously constructed module"
    )
    def test_calls_create_or_update_device_for_certificate_authority(
        self, mock_module_constructor, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.create_module_with_certificate_authority(
            device_id=fake_device_id, module_id=fake_module_id, managed_by=fake_managed_by
        )

        assert mock_service_operations.create_or_update_module.call_count == 1
        assert mock_service_operations.create_or_update_module.call_args[0][0] == fake_device_id
        assert mock_service_operations.create_or_update_module.call_args[0][1] == fake_module_id
        assert (
            mock_service_operations.create_or_update_module.call_args[0][2]
            == mock_module_constructor.return_value
        )


@pytest.mark.describe("IoTHubRegistryManager - .update_module_with_sas()")
class TestUpdateModuleWithSymmetricKey(object):

    testdata = [(fake_primary_key, None), (None, fake_secondary_key)]

    @pytest.mark.it("Initializes module with device id, module id, managed_by and sas auth")
    @pytest.mark.parametrize(
        "primary_key, secondary_key", testdata, ids=["Primary Key", "Secondary Key"]
    )
    def test_initializes_device_with_kwargs_for_sas(
        self, iothub_registry_manager, mock_module_constructor, primary_key, secondary_key
    ):
        iothub_registry_manager.update_module_with_sas(
            device_id=fake_device_id,
            module_id=fake_module_id,
            managed_by=fake_managed_by,
            etag=fake_etag,
            primary_key=primary_key,
            secondary_key=secondary_key,
        )

        assert mock_module_constructor.call_count == 1

        assert mock_module_constructor.call_args[1]["module_id"] == fake_module_id
        assert mock_module_constructor.call_args[1]["managed_by"] == fake_managed_by
        assert mock_module_constructor.call_args[1]["device_id"] == fake_device_id
        assert isinstance(
            mock_module_constructor.call_args[1]["authentication"], AuthenticationMechanism
        )
        auth_mechanism = mock_module_constructor.call_args[1]["authentication"]
        assert auth_mechanism.type == "sas"
        assert auth_mechanism.x509_thumbprint is None
        sym_key = auth_mechanism.symmetric_key
        assert sym_key.primary_key == primary_key
        assert sym_key.secondary_key == secondary_key

    @pytest.mark.it(
        "Calls method from service operations with device id, module id and previously constructed module"
    )
    @pytest.mark.parametrize(
        "primary_key, secondary_key", testdata, ids=["Primary Key", "Secondary Key"]
    )
    def test_calls_create_or_update_device_for_sas(
        self,
        mock_module_constructor,
        mock_service_operations,
        iothub_registry_manager,
        primary_key,
        secondary_key,
    ):
        iothub_registry_manager.update_module_with_sas(
            device_id=fake_device_id,
            module_id=fake_module_id,
            etag=fake_etag,
            managed_by=fake_managed_by,
            primary_key=primary_key,
            secondary_key=secondary_key,
        )

        assert mock_service_operations.create_or_update_module.call_count == 1
        assert mock_service_operations.create_or_update_module.call_args[0][0] == fake_device_id
        assert mock_service_operations.create_or_update_module.call_args[0][1] == fake_module_id
        assert (
            mock_service_operations.create_or_update_module.call_args[0][2]
            == mock_module_constructor.return_value
        )


@pytest.mark.describe("IoTHubRegistryManager - .update_module_with_x509()")
class TestUpdateModuleWithX509(object):

    testdata = [(fake_primary_thumbprint, None), (None, fake_secondary_thumbprint)]

    @pytest.mark.it("Initializes module with device id, module id, managed_by and X509 auth")
    @pytest.mark.parametrize(
        "primary_thumbprint, secondary_thumbprint",
        testdata,
        ids=["Primary Thumbprint", "Secondary Thumbprint"],
    )
    def test_initializes_device_with_kwargs_for_x509(
        self,
        iothub_registry_manager,
        mock_module_constructor,
        primary_thumbprint,
        secondary_thumbprint,
    ):
        iothub_registry_manager.update_module_with_x509(
            device_id=fake_device_id,
            module_id=fake_module_id,
            etag=fake_etag,
            managed_by=fake_managed_by,
            primary_thumbprint=primary_thumbprint,
            secondary_thumbprint=secondary_thumbprint,
        )

        assert mock_module_constructor.call_count == 1
        assert mock_module_constructor.call_args[1]["module_id"] == fake_module_id
        assert mock_module_constructor.call_args[1]["managed_by"] == fake_managed_by
        assert mock_module_constructor.call_args[1]["device_id"] == fake_device_id
        assert isinstance(
            mock_module_constructor.call_args[1]["authentication"], AuthenticationMechanism
        )
        auth_mechanism = mock_module_constructor.call_args[1]["authentication"]
        assert auth_mechanism.type == "selfSigned"
        assert auth_mechanism.symmetric_key is None
        x509_thumbprint = auth_mechanism.x509_thumbprint
        assert x509_thumbprint.primary_thumbprint == primary_thumbprint
        assert x509_thumbprint.secondary_thumbprint == secondary_thumbprint

    @pytest.mark.it(
        "Calls method from service operations with device id, module id and previously constructed module"
    )
    @pytest.mark.parametrize(
        "primary_thumbprint, secondary_thumbprint",
        testdata,
        ids=["Primary Thumbprint", "Secondary Thumbprint"],
    )
    def test_calls_create_or_update_device_for_x509(
        self,
        mock_module_constructor,
        mock_service_operations,
        iothub_registry_manager,
        primary_thumbprint,
        secondary_thumbprint,
    ):
        iothub_registry_manager.update_module_with_x509(
            device_id=fake_device_id,
            module_id=fake_module_id,
            etag=fake_etag,
            managed_by=fake_managed_by,
            primary_thumbprint=primary_thumbprint,
            secondary_thumbprint=secondary_thumbprint,
        )

        assert mock_service_operations.create_or_update_module.call_count == 1
        assert mock_service_operations.create_or_update_module.call_args[0][0] == fake_device_id
        assert mock_service_operations.create_or_update_module.call_args[0][1] == fake_module_id
        assert (
            mock_service_operations.create_or_update_module.call_args[0][2]
            == mock_module_constructor.return_value
        )


@pytest.mark.describe("IoTHubRegistryManager - .update_module_with_certificate_authority()")
class TestUpdateModuleWithCA(object):
    @pytest.mark.it("Initializes module with device id, module id, managed_by and ca auth")
    def test_initializes_device_with_kwargs_for_certificate_authority(
        self, mock_module_constructor, iothub_registry_manager
    ):
        iothub_registry_manager.update_module_with_certificate_authority(
            device_id=fake_device_id,
            module_id=fake_module_id,
            etag=fake_etag,
            managed_by=fake_managed_by,
        )

        assert mock_module_constructor.call_count == 1
        assert mock_module_constructor.call_args[1]["module_id"] == fake_module_id
        assert mock_module_constructor.call_args[1]["managed_by"] == fake_managed_by
        assert mock_module_constructor.call_args[1]["device_id"] == fake_device_id
        assert isinstance(
            mock_module_constructor.call_args[1]["authentication"], AuthenticationMechanism
        )
        auth_mechanism = mock_module_constructor.call_args[1]["authentication"]
        assert auth_mechanism.type == "certificateAuthority"
        assert auth_mechanism.x509_thumbprint is None
        assert auth_mechanism.symmetric_key is None

    @pytest.mark.it(
        "Calls method from service operations with device id, module id and previously constructed module"
    )
    def test_calls_create_or_update_device_for_certificate_authority(
        self, mock_module_constructor, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.update_module_with_certificate_authority(
            device_id=fake_device_id,
            module_id=fake_module_id,
            etag=fake_etag,
            managed_by=fake_managed_by,
        )

        assert mock_service_operations.create_or_update_module.call_count == 1
        assert mock_service_operations.create_or_update_module.call_args[0][0] == fake_device_id
        assert mock_service_operations.create_or_update_module.call_args[0][1] == fake_module_id
        assert (
            mock_service_operations.create_or_update_module.call_args[0][2]
            == mock_module_constructor.return_value
        )


@pytest.mark.describe("IoTHubRegistryManager - .get_module()")
class TestGetModule(object):
    @pytest.mark.it("Gets module from service for provided device id and module id")
    def test_get_module(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_module(fake_device_id, fake_module_id)

        assert mock_service_operations.get_module.call_count == 1
        assert mock_service_operations.get_module.call_args == mocker.call(
            fake_device_id, fake_module_id
        )


@pytest.mark.describe("IoTHubRegistryManager - .delete_module()")
class TestDeleteModule(object):
    @pytest.mark.it("Deletes module for the provided device id")
    def test_delete_module(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.delete_module(fake_device_id, fake_module_id)

        assert mock_service_operations.delete_module.call_count == 1
        assert mock_service_operations.delete_module.call_args == mocker.call(
            fake_device_id, fake_module_id, "*"
        )

    @pytest.mark.it("Deletes module with an etag for the provided device id and etag")
    def test_delete_module_with_etag(
        self, mocker, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.delete_module(
            device_id=fake_device_id, module_id=fake_module_id, etag=fake_etag
        )

        assert mock_service_operations.delete_module.call_count == 1
        assert mock_service_operations.delete_module.call_args == mocker.call(
            fake_device_id, fake_module_id, fake_etag
        )


@pytest.mark.describe("IoTHubRegistryManager - .get_service_statistics()")
class TestGetServiceStats(object):
    @pytest.mark.it("Gets service statistics")
    def test_get_service_statistics(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_service_statistics()

        assert mock_service_operations.get_service_statistics.call_count == 1
        assert mock_service_operations.get_service_statistics.call_args == mocker.call()


@pytest.mark.describe("IoTHubRegistryManager - .get_device_registry_statistics()")
class TestGetDeviceRegistryStats(object):
    @pytest.mark.it("Gets device registry statistics")
    def test_get_device_registry_statistics(
        self, mocker, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.get_device_registry_statistics()

        assert mock_service_operations.get_device_registry_statistics.call_count == 1
        assert mock_service_operations.get_device_registry_statistics.call_args == mocker.call()
