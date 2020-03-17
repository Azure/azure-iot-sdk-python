# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.hub.protocol.models import AuthenticationMechanism
from azure.iot.hub.iothub_registry_manager import IoTHubRegistryManager
from azure.iot.hub.iothub_amqp_client import IoTHubAmqpClient as iothub_amqp_client

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
fake_configuration_id = "fake_configuration"
fake_configuration = "fake_config"
fake_max_count = 42
fake_configuration_queries = "fake_configuration_queries"
fake_devices = "fake_devices"
fake_query_specification = "fake_query_specification"
fake_configuration_content = "fake_configuration_content"
fake_job_id = "fake_job_id"
fake_start_time = "fake_start_time"
fake_end_time = "fake_end_time"
fake_job_type = "fake_job_type"
fake_job_request = "fake_job_request"
fake_job_status = "fake_status"
fake_job_properties = "fake_job_properties"
fake_device_twin = "fake_device_twin"
fake_module_twin = "fake_module_twin"
fake_direct_method_request_with_payload_none = "fake_direct_method_request"


class Fake_direct_method_request_with_payload:
    payload = ""


fake_direct_method_request_with_payload = Fake_direct_method_request_with_payload()


class Fake_direct_method_request_with_payload_none:
    payload = None


fake_direct_method_request_with_payload_none = Fake_direct_method_request_with_payload_none()
fake_message_to_send = "fake_message_to_send"

"""----Shared fixtures----"""


@pytest.fixture(scope="function", autouse=True)
def mock_registry_manager_operations(mocker):
    mock_registry_manager_operations_init = mocker.patch(
        "azure.iot.hub.protocol.iot_hub_gateway_service_ap_is.RegistryManagerOperations"
    )
    return mock_registry_manager_operations_init.return_value


@pytest.fixture(scope="function", autouse=True)
def mock_twin_operations(mocker):
    mock_twin_operations_init = mocker.patch(
        "azure.iot.hub.protocol.iot_hub_gateway_service_ap_is.TwinOperations"
    )
    return mock_twin_operations_init.return_value


@pytest.fixture(scope="function", autouse=True)
def mock_device_method_operations(mocker):
    mock_device_method_operations_init = mocker.patch(
        "azure.iot.hub.protocol.iot_hub_gateway_service_ap_is.DeviceMethodOperations"
    )
    return mock_device_method_operations_init.return_value


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


@pytest.fixture(scope="function")
def mock_uamqp_send_message_to_device(mocker):
    mock_uamqp_send = mocker.patch.object(iothub_amqp_client, "send_message_to_device")
    return mock_uamqp_send


@pytest.fixture
def mock_uamqp_disconnect_sync(mocker):
    return mocker.patch.object(iothub_amqp_client, "disconnect_sync")


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
        mock_registry_manager_operations,
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

        assert mock_registry_manager_operations.create_or_update_device.call_count == 1
        assert (
            mock_registry_manager_operations.create_or_update_device.call_args[0][0]
            == fake_device_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_device.call_args[0][1]
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
        mock_registry_manager_operations,
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

        assert mock_registry_manager_operations.create_or_update_device.call_count == 1
        assert (
            mock_registry_manager_operations.create_or_update_device.call_args[0][0]
            == fake_device_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_device.call_args[0][1]
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
        self, mock_device_constructor, mock_registry_manager_operations, iothub_registry_manager
    ):
        iothub_registry_manager.create_device_with_certificate_authority(
            device_id=fake_device_id, status=fake_status
        )

        assert mock_registry_manager_operations.create_or_update_device.call_count == 1
        assert (
            mock_registry_manager_operations.create_or_update_device.call_args[0][0]
            == fake_device_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_device.call_args[0][1]
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
        mock_registry_manager_operations,
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

        assert mock_registry_manager_operations.create_or_update_device.call_count == 1
        assert (
            mock_registry_manager_operations.create_or_update_device.call_args[0][0]
            == fake_device_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_device.call_args[0][1]
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
        mock_registry_manager_operations,
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

        assert mock_registry_manager_operations.create_or_update_device.call_count == 1
        assert (
            mock_registry_manager_operations.create_or_update_device.call_args[0][0]
            == fake_device_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_device.call_args[0][1]
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
        self, mock_device_constructor, mock_registry_manager_operations, iothub_registry_manager
    ):
        iothub_registry_manager.update_device_with_certificate_authority(
            device_id=fake_device_id, status=fake_status, etag=fake_etag
        )

        assert mock_registry_manager_operations.create_or_update_device.call_count == 1
        assert (
            mock_registry_manager_operations.create_or_update_device.call_args[0][0]
            == fake_device_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_device.call_args[0][1]
            == mock_device_constructor.return_value
        )


@pytest.mark.describe("IoTHubRegistryManager -- .get_device()")
class TestGetDevice(object):
    @pytest.mark.it("Gets device from service for provided device id")
    def test_get_device(self, mocker, mock_registry_manager_operations, iothub_registry_manager):
        iothub_registry_manager.get_device(fake_device_id)

        assert mock_registry_manager_operations.get_device.call_count == 1
        assert mock_registry_manager_operations.get_device.call_args == mocker.call(fake_device_id)


@pytest.mark.describe("IoTHubRegistryManager - .delete_device()")
class TestDeleteDevice(object):
    @pytest.mark.it("Deletes device for the provided device id")
    def test_delete_device(self, mocker, mock_registry_manager_operations, iothub_registry_manager):
        iothub_registry_manager.delete_device(fake_device_id)

        assert mock_registry_manager_operations.delete_device.call_count == 1
        assert mock_registry_manager_operations.delete_device.call_args == mocker.call(
            fake_device_id, "*"
        )

    @pytest.mark.it("Deletes device with an etag for the provided device id and etag")
    def test_delete_device_with_etag(
        self, mocker, mock_registry_manager_operations, iothub_registry_manager
    ):
        iothub_registry_manager.delete_device(device_id=fake_device_id, etag=fake_etag)

        assert mock_registry_manager_operations.delete_device.call_count == 1
        assert mock_registry_manager_operations.delete_device.call_args == mocker.call(
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
        mock_registry_manager_operations,
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

        assert mock_registry_manager_operations.create_or_update_module.call_count == 1
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][0]
            == fake_device_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][1]
            == fake_module_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][2]
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
        mock_registry_manager_operations,
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

        assert mock_registry_manager_operations.create_or_update_module.call_count == 1
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][0]
            == fake_device_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][1]
            == fake_module_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][2]
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
        self, mock_module_constructor, mock_registry_manager_operations, iothub_registry_manager
    ):
        iothub_registry_manager.create_module_with_certificate_authority(
            device_id=fake_device_id, module_id=fake_module_id, managed_by=fake_managed_by
        )

        assert mock_registry_manager_operations.create_or_update_module.call_count == 1
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][0]
            == fake_device_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][1]
            == fake_module_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][2]
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
        mock_registry_manager_operations,
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

        assert mock_registry_manager_operations.create_or_update_module.call_count == 1
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][0]
            == fake_device_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][1]
            == fake_module_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][2]
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
        mock_registry_manager_operations,
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

        assert mock_registry_manager_operations.create_or_update_module.call_count == 1
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][0]
            == fake_device_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][1]
            == fake_module_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][2]
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
        self, mock_module_constructor, mock_registry_manager_operations, iothub_registry_manager
    ):
        iothub_registry_manager.update_module_with_certificate_authority(
            device_id=fake_device_id,
            module_id=fake_module_id,
            etag=fake_etag,
            managed_by=fake_managed_by,
        )

        assert mock_registry_manager_operations.create_or_update_module.call_count == 1
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][0]
            == fake_device_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][1]
            == fake_module_id
        )
        assert (
            mock_registry_manager_operations.create_or_update_module.call_args[0][2]
            == mock_module_constructor.return_value
        )


@pytest.mark.describe("IoTHubRegistryManager - .get_module()")
class TestGetModule(object):
    @pytest.mark.it("Gets module from service for provided device id and module id")
    def test_get_module(self, mocker, mock_registry_manager_operations, iothub_registry_manager):
        iothub_registry_manager.get_module(fake_device_id, fake_module_id)

        assert mock_registry_manager_operations.get_module.call_count == 1
        assert mock_registry_manager_operations.get_module.call_args == mocker.call(
            fake_device_id, fake_module_id
        )


@pytest.mark.describe("IoTHubRegistryManager - .get_modules()")
class TestGetModules(object):
    @pytest.mark.it("Gets all modules from service for provided device")
    def test_get_module(self, mocker, mock_registry_manager_operations, iothub_registry_manager):
        iothub_registry_manager.get_modules(fake_device_id)

        assert mock_registry_manager_operations.get_modules_on_device.call_count == 1
        assert mock_registry_manager_operations.get_modules_on_device.call_args == mocker.call(
            fake_device_id
        )


@pytest.mark.describe("IoTHubRegistryManager - .delete_module()")
class TestDeleteModule(object):
    @pytest.mark.it("Deletes module for the provided device id")
    def test_delete_module(self, mocker, mock_registry_manager_operations, iothub_registry_manager):
        iothub_registry_manager.delete_module(fake_device_id, fake_module_id)

        assert mock_registry_manager_operations.delete_module.call_count == 1
        assert mock_registry_manager_operations.delete_module.call_args == mocker.call(
            fake_device_id, fake_module_id, "*"
        )

    @pytest.mark.it("Deletes module with an etag for the provided device id and etag")
    def test_delete_module_with_etag(
        self, mocker, mock_registry_manager_operations, iothub_registry_manager
    ):
        iothub_registry_manager.delete_module(
            device_id=fake_device_id, module_id=fake_module_id, etag=fake_etag
        )

        assert mock_registry_manager_operations.delete_module.call_count == 1
        assert mock_registry_manager_operations.delete_module.call_args == mocker.call(
            fake_device_id, fake_module_id, fake_etag
        )


@pytest.mark.describe("IoTHubRegistryManager - .get_service_statistics()")
class TestGetServiceStats(object):
    @pytest.mark.it("Gets service statistics")
    def test_get_service_statistics(
        self, mocker, mock_registry_manager_operations, iothub_registry_manager
    ):
        iothub_registry_manager.get_service_statistics()

        assert mock_registry_manager_operations.get_service_statistics.call_count == 1
        assert mock_registry_manager_operations.get_service_statistics.call_args == mocker.call()


@pytest.mark.describe("IoTHubRegistryManager - .get_device_registry_statistics()")
class TestGetDeviceRegistryStats(object):
    @pytest.mark.it("Gets device registry statistics")
    def test_get_device_registry_statistics(
        self, mocker, mock_registry_manager_operations, iothub_registry_manager
    ):
        iothub_registry_manager.get_device_registry_statistics()

        assert mock_registry_manager_operations.get_device_statistics.call_count == 1
        assert mock_registry_manager_operations.get_device_statistics.call_args == mocker.call()


@pytest.mark.describe("IoTHubRegistryManager - .get_devices()")
class TestGetDevices(object):
    @pytest.mark.it("Gets devices")
    def test_get_devices(self, mocker, mock_registry_manager_operations, iothub_registry_manager):
        iothub_registry_manager.get_devices()

        assert mock_registry_manager_operations.get_devices.call_count == 1
        assert mock_registry_manager_operations.get_devices.call_args == mocker.call(None)


@pytest.mark.describe("IoTHubRegistryManager - .get_devices(max_number_of_devices)")
class TestGetDevicesWithMax(object):
    @pytest.mark.it("Gets devices with max_number_of_devices")
    def test_get_devices(self, mocker, mock_registry_manager_operations, iothub_registry_manager):
        max_number_of_devices = 42
        iothub_registry_manager.get_devices(max_number_of_devices)

        assert mock_registry_manager_operations.get_devices.call_count == 1
        assert mock_registry_manager_operations.get_devices.call_args == mocker.call(
            max_number_of_devices
        )


@pytest.mark.describe("IoTHubRegistryManager - .bulk_create_or_update_devices()")
class TestBulkCreateUpdateDevices(object):
    @pytest.mark.it("Test bulk_create_or_update_devices")
    def test_bulk_create_or_update_devices(
        self, mocker, mock_registry_manager_operations, iothub_registry_manager
    ):
        iothub_registry_manager.bulk_create_or_update_devices(fake_devices)
        assert mock_registry_manager_operations.bulk_device_crud.call_count == 1
        assert mock_registry_manager_operations.bulk_device_crud.call_args == mocker.call(
            fake_devices
        )


@pytest.mark.describe("IoTHubRegistryManager - .query_iot_hub()")
class TestQueryIoTHub(object):
    @pytest.mark.it("Test query IoTHub")
    def test_query_iot_hub(self, mocker, mock_registry_manager_operations, iothub_registry_manager):
        iothub_registry_manager.query_iot_hub(fake_query_specification)
        assert mock_registry_manager_operations.query_iot_hub.call_count == 1
        assert mock_registry_manager_operations.query_iot_hub.call_args == mocker.call(
            fake_query_specification, None, None, None, True
        )


@pytest.mark.describe("IoTHubRegistryManager - .query_iot_hub(continuation_token)")
class TestQueryIoTHubWithContinuationToken(object):
    @pytest.mark.it("Test query IoTHub with continuation token")
    def test_query_iot_hub(self, mocker, mock_registry_manager_operations, iothub_registry_manager):
        continuation_token = 42
        iothub_registry_manager.query_iot_hub(fake_query_specification, continuation_token)
        assert mock_registry_manager_operations.query_iot_hub.call_count == 1
        assert mock_registry_manager_operations.query_iot_hub.call_args == mocker.call(
            fake_query_specification, continuation_token, None, None, True
        )


@pytest.mark.describe("IoTHubRegistryManager - .query_iot_hub(continuation_token, max_item_count)")
class TestQueryIoTHubWithContinuationTokenAndMaxItermCount(object):
    @pytest.mark.it("Test query IoTHub with continuation token and max item count")
    def test_query_iot_hub(self, mocker, mock_registry_manager_operations, iothub_registry_manager):
        continuation_token = 42
        max_item_count = 84
        iothub_registry_manager.query_iot_hub(
            fake_query_specification, continuation_token, max_item_count
        )
        assert mock_registry_manager_operations.query_iot_hub.call_count == 1
        assert mock_registry_manager_operations.query_iot_hub.call_args == mocker.call(
            fake_query_specification, continuation_token, max_item_count, None, True
        )


@pytest.mark.describe("IoTHubRegistryManager - .get_twin()")
class TestGetTwin(object):
    @pytest.mark.it("Test get twin")
    def test_get_twin(self, mocker, mock_twin_operations, iothub_registry_manager):
        iothub_registry_manager.get_twin(fake_device_id)
        assert mock_twin_operations.get_device_twin.call_count == 1
        assert mock_twin_operations.get_device_twin.call_args == mocker.call(fake_device_id)


@pytest.mark.describe("IoTHubRegistryManager - .replace_twin()")
class TestReplaceTwin(object):
    @pytest.mark.it("Test replace twin")
    def test_replace_twin(self, mocker, mock_twin_operations, iothub_registry_manager):
        iothub_registry_manager.replace_twin(fake_device_id, fake_device_twin)
        assert mock_twin_operations.replace_device_twin.call_count == 1
        assert mock_twin_operations.replace_device_twin.call_args == mocker.call(
            fake_device_id, fake_device_twin
        )


@pytest.mark.describe("IoTHubRegistryManager - .update_twin()")
class TestUpdateTwin(object):
    @pytest.mark.it("Test update twin")
    def test_update_twin(self, mocker, mock_twin_operations, iothub_registry_manager):
        iothub_registry_manager.update_twin(fake_device_id, fake_device_twin, fake_etag)
        assert mock_twin_operations.update_device_twin.call_count == 1
        assert mock_twin_operations.update_device_twin.call_args == mocker.call(
            fake_device_id, fake_device_twin, fake_etag
        )


@pytest.mark.describe("IoTHubRegistryManager - .get_module_twin()")
class TestGetModuleTwin(object):
    @pytest.mark.it("Test get module twin")
    def test_get_module_twin(self, mocker, mock_twin_operations, iothub_registry_manager):
        iothub_registry_manager.get_module_twin(fake_device_id, fake_module_id)
        assert mock_twin_operations.get_module_twin.call_count == 1
        assert mock_twin_operations.get_module_twin.call_args == mocker.call(
            fake_device_id, fake_module_id
        )


@pytest.mark.describe("IoTHubRegistryManager - .replace_module_twin()")
class TestReplaceModuleTwin(object):
    @pytest.mark.it("Test replace module twin")
    def test_replace_module_twin(self, mocker, mock_twin_operations, iothub_registry_manager):
        iothub_registry_manager.replace_module_twin(
            fake_device_id, fake_module_id, fake_module_twin
        )
        assert mock_twin_operations.replace_module_twin.call_count == 1
        assert mock_twin_operations.replace_module_twin.call_args == mocker.call(
            fake_device_id, fake_module_id, fake_module_twin
        )


@pytest.mark.describe("IoTHubRegistryManager - .update_module_twin()")
class TestUpdateModuleTwin(object):
    @pytest.mark.it("Test update module twin")
    def test_update_module_twin(self, mocker, mock_twin_operations, iothub_registry_manager):
        iothub_registry_manager.update_module_twin(
            fake_device_id, fake_module_id, fake_module_twin, fake_etag
        )
        assert mock_twin_operations.update_module_twin.call_count == 1
        assert mock_twin_operations.update_module_twin.call_args == mocker.call(
            fake_device_id, fake_module_id, fake_module_twin, fake_etag
        )


@pytest.mark.describe("IoTHubRegistryManager - .invoke_device_method() with payload")
class TestInvokeDeviceMethodWithPayload(object):
    @pytest.mark.it("Test invoke device method with payload")
    def test_invoke_device_method_with_payload(
        self, mocker, mock_device_method_operations, iothub_registry_manager
    ):
        iothub_registry_manager.invoke_device_method(
            fake_device_id, fake_direct_method_request_with_payload
        )
        assert mock_device_method_operations.invoke_device_method.call_count == 1
        assert mock_device_method_operations.invoke_device_method.call_args == mocker.call(
            fake_device_id, fake_direct_method_request_with_payload
        )


@pytest.mark.describe("IoTHubRegistryManager - .invoke_device_method() with payload none")
class TestInvokeDeviceMethodWithPayloadNone(object):
    @pytest.mark.it("Test invoke device method with payload None")
    def test_invoke_device_method_payload_none(
        self, mocker, mock_device_method_operations, iothub_registry_manager
    ):
        iothub_registry_manager.invoke_device_method(
            fake_device_id, fake_direct_method_request_with_payload_none
        )
        assert mock_device_method_operations.invoke_device_method.call_count == 1
        assert mock_device_method_operations.invoke_device_method.call_args == mocker.call(
            fake_device_id, fake_direct_method_request_with_payload_none
        )


@pytest.mark.describe("IoTHubRegistryManager - .invoke_device_module_method() with payload")
class TestInvokeDeviceModuleMethodWithPayload(object):
    @pytest.mark.it("Test invoke device module method with payload")
    def test_invoke_device_module_method_with_payload(
        self, mocker, mock_device_method_operations, iothub_registry_manager
    ):
        iothub_registry_manager.invoke_device_module_method(
            fake_device_id, fake_module_id, fake_direct_method_request_with_payload
        )
        assert mock_device_method_operations.invoke_module_method.call_count == 1
        assert mock_device_method_operations.invoke_module_method.call_args == mocker.call(
            fake_device_id, fake_module_id, fake_direct_method_request_with_payload
        )


@pytest.mark.describe("IoTHubRegistryManager - .invoke_device_module_method() with payload none")
class TestInvokeDeviceModuleMethodWithPayloadNone(object):
    @pytest.mark.it("Test invoke device module method with payload None")
    def test_invoke_device_module_method_payload_none(
        self, mocker, mock_device_method_operations, iothub_registry_manager
    ):
        iothub_registry_manager.invoke_device_module_method(
            fake_device_id, fake_module_id, fake_direct_method_request_with_payload_none
        )
        assert mock_device_method_operations.invoke_module_method.call_count == 1
        assert mock_device_method_operations.invoke_module_method.call_args == mocker.call(
            fake_device_id, fake_module_id, fake_direct_method_request_with_payload_none
        )


@pytest.mark.describe("IoTHubRegistryManager - .send_c2d_message()")
class TestSendC2dMessage(object):
    @pytest.mark.it("Test send c2d message")
    def test_send_c2d_message(
        self, mocker, mock_uamqp_send_message_to_device, iothub_registry_manager
    ):

        iothub_registry_manager.send_c2d_message(fake_device_id, fake_message_to_send)

        assert mock_uamqp_send_message_to_device.call_count == 1
        assert mock_uamqp_send_message_to_device.call_args == mocker.call(
            fake_device_id, fake_message_to_send
        )
