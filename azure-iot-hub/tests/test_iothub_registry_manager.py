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
fake_configuration_id = "fake_configuration"
fake_configuration = "fake_config"
fake_max_count = 42
fake_target_condition = "fake_target_condition"
fake_custom_metric_queries = {
    "fake_query1_key": "fake_query1_value",
    "fake_query2_key": "fake_query2_value",
}
fake_devices = "fake_devices"
fake_query = "fake_query"
fake_device_configuration = "fake_device_configuration"
fake_modules_configuration = "fake_modules_configuration"
fake_module_configuration = "fake_module_configuration"
fake_job_id = "fake_job_id"
fake_start_time = "fake_start_time"
fake_end_time = "fake_end_time"
fake_job_type = "fake_job_type"
fake_job_request = "fake_job_request"
fake_job_status = "fake_status"
fake_job_request = "fake_request"
fake_progress = "fake_progress"
fake_input_blob_container_uri = "fake_input_blob_container_uri"
fake_input_blob_name = "fake_input_blob_name"
fake_output_blob_container_uri = "fake_output_blob_container_uri"
fake_output_blob_name = "fake_output_blob_name"
fake_exclude_keys_in_export = "fake_exclude_keys_in_export"
fake_failure_reason = "fake_failure_reason"
fake_device_twin = "fake_device_twin"
fake_module_twin = "fake_module_twin"
fake_direct_method_request = "fake_direct_method_request"

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


@pytest.mark.describe("IoTHubRegistryManager - .get_modules()")
class TestGetModules(object):
    @pytest.mark.it("Gets all modules from service for provided device")
    def test_get_module(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_modules(fake_device_id)

        assert mock_service_operations.get_modules_on_device.call_count == 1
        assert mock_service_operations.get_modules_on_device.call_args == mocker.call(
            fake_device_id
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


@pytest.mark.describe("IoTHubRegistryManager - .get_configuration()")
class TestGetConfiguration(object):
    @pytest.mark.it("Gets configuration")
    def test_get_configuration(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_configuration(fake_configuration_id)

        assert mock_service_operations.get_configuration.call_count == 1
        assert mock_service_operations.get_configuration.call_args == mocker.call(
            fake_configuration_id
        )


@pytest.mark.describe("IoTHubRegistryManager - .create_configuration()")
class TestCreateConfiguration(object):
    @pytest.mark.it("Creates configuration")
    def test_create_configuration(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.create_configuration(fake_configuration_id, fake_configuration)

        assert mock_service_operations.create_or_update_configuration.call_count == 1
        assert mock_service_operations.create_or_update_configuration.call_args == mocker.call(
            fake_configuration_id, fake_configuration
        )


@pytest.mark.describe("IoTHubRegistryManager - .update_configuration()")
class TestUpdateConfiguration(object):
    @pytest.mark.it("Updates configuration")
    def test_update_configuration(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.update_configuration(
            fake_configuration_id, fake_configuration, fake_etag
        )

        assert mock_service_operations.create_or_update_configuration.call_count == 1
        assert mock_service_operations.create_or_update_configuration.call_args == mocker.call(
            fake_configuration_id, fake_configuration, fake_etag
        )


@pytest.mark.describe("IoTHubRegistryManager - .delete_configuration()")
class TestDeleteConfiguration(object):
    @pytest.mark.it("Deletes configuration")
    def test_delete_configuration(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.delete_configuration(fake_configuration_id)

        assert mock_service_operations.delete_configuration.call_count == 1
        assert mock_service_operations.delete_configuration.call_args == mocker.call(
            fake_configuration_id, "*"
        )

    @pytest.mark.it("Deletes configuration with an etag")
    def test_delete_configuration_with_etag(
        self, mocker, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.delete_configuration(
            configuration_id=fake_configuration_id, etag=fake_etag
        )

        assert mock_service_operations.delete_configuration.call_count == 1
        assert mock_service_operations.delete_configuration.call_args == mocker.call(
            fake_configuration_id, fake_etag
        )


@pytest.mark.describe("IoTHubRegistryManager - .get_configurations()")
class TestGetConfigurations(object):
    @pytest.mark.it("Gets configuration")
    def test_get_configurations(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_configurations(fake_max_count)

        assert mock_service_operations.get_configurations.call_count == 1
        assert mock_service_operations.get_configurations.call_args == mocker.call(fake_max_count)


@pytest.mark.describe("IoTHubRegistryManager - .test_configuration_queries()")
class TestTestConfigurationQueries(object):
    @pytest.mark.it("Test test_configuration_queries")
    def test_test_configuration_queries(
        self, mocker, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.test_configuration_queries(
            fake_target_condition, fake_custom_metric_queries
        )
        fake_input = {
            "target_condition": fake_target_condition,
            "custom_metric_queries": fake_custom_metric_queries,
        }
        assert mock_service_operations.test_configuration_queries.call_count == 1
        assert mock_service_operations.test_configuration_queries.call_args == mocker.call(
            fake_input
        )


@pytest.mark.describe("IoTHubRegistryManager - .bulk_create_or_update_devices()")
class TestBulkCreateUpdateDevices(object):
    @pytest.mark.it("Test bulk_create_or_update_devices")
    def test_bulk_create_or_update_devices(
        self, mocker, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.bulk_create_or_update_devices(fake_devices)
        assert mock_service_operations.bulk_create_or_update_devices.call_count == 1
        assert mock_service_operations.bulk_create_or_update_devices.call_args == mocker.call(
            fake_devices
        )


@pytest.mark.describe("IoTHubRegistryManager - .query_iot_hub()")
class TestQueryIoTHub(object):
    @pytest.mark.it("Test query IoTHub")
    def test_query_iot_hub(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.query_iot_hub(fake_query)
        fake_query_specification = {"query": fake_query}
        assert mock_service_operations.query_iot_hub.call_count == 1
        assert mock_service_operations.query_iot_hub.call_args == mocker.call(
            fake_query_specification
        )


@pytest.mark.describe("IoTHubRegistryManager - .apply_configuration_on_edge_device()")
class TestApplyConfigurationOnEdgeDevice(object):
    @pytest.mark.it("Test apply configuration on edge device")
    def test_apply_configuration_on_edge_device(
        self, mocker, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.apply_configuration_on_edge_device(
            fake_device_id,
            fake_device_configuration,
            fake_modules_configuration,
            fake_module_configuration,
        )
        fake_configuration_content = {
            "device_content": fake_device_configuration,
            "modules_content": fake_modules_configuration,
            "module_content": fake_module_configuration,
        }
        assert mock_service_operations.apply_configuration_on_edge_device.call_count == 1
        assert mock_service_operations.apply_configuration_on_edge_device.call_args == mocker.call(
            fake_device_id, fake_configuration_content
        )


@pytest.mark.describe("IoTHubRegistryManager - .create_import_export_job()")
class TestCreateImportExportJob(object):
    @pytest.mark.it("Test create import export job")
    def test_create_import_export_job(
        self, mocker, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.create_import_export_job(
            fake_job_id,
            fake_start_time,
            fake_end_time,
            fake_job_type,
            fake_job_status,
            fake_progress,
            fake_input_blob_container_uri,
            fake_input_blob_name,
            fake_output_blob_container_uri,
            fake_output_blob_name,
            fake_exclude_keys_in_export,
            fake_failure_reason,
        )
        fake_job_properties = {
            "job_id": fake_job_id,
            "start_time": fake_start_time,
            "end_time": fake_end_time,
            "job_type": fake_job_type,
            "status": fake_job_status,
            "progress": fake_progress,
            "input_blob_container_uri": fake_input_blob_container_uri,
            "input_blob_name": fake_input_blob_name,
            "output_blob_container_uri": fake_output_blob_container_uri,
            "output_blob_name": fake_output_blob_name,
            "exclude_keys_in_export": fake_exclude_keys_in_export,
            "failure_reason": fake_failure_reason,
        }
        assert mock_service_operations.create_import_export_job.call_count == 1
        assert mock_service_operations.create_import_export_job.call_args == mocker.call(
            fake_job_properties
        )


@pytest.mark.describe("IoTHubRegistryManager - .get_import_export_jobs()")
class TestGetImportExportJobs(object):
    @pytest.mark.it("Test get import export jobs")
    def test_get_import_export_jobs(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_import_export_jobs()
        assert mock_service_operations.get_import_export_jobs.call_count == 1
        assert mock_service_operations.get_import_export_jobs.call_args == mocker.call()


@pytest.mark.describe("IoTHubRegistryManager - .get_import_export_job()")
class TestGetImportExportJob(object):
    @pytest.mark.it("Test get import export job")
    def test_get_import_export_job(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_import_export_job(fake_job_id)
        assert mock_service_operations.get_import_export_job.call_count == 1
        assert mock_service_operations.get_import_export_job.call_args == mocker.call(fake_job_id)


@pytest.mark.describe("IoTHubRegistryManager - .cancel_import_export_job()")
class TestCancelImportExportJob(object):
    @pytest.mark.it("Test cancel import export job")
    def test_cancel_import_export_job(
        self, mocker, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.cancel_import_export_job(fake_job_id)
        assert mock_service_operations.cancel_import_export_job.call_count == 1
        assert mock_service_operations.cancel_import_export_job.call_args == mocker.call(
            fake_job_id
        )


@pytest.mark.describe("IoTHubRegistryManager - .purge_command_queue()")
class TestPurgeCommandQueue(object):
    @pytest.mark.it("Test purge command queue")
    def test_purge_command_queue(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.purge_command_queue(fake_device_id)
        assert mock_service_operations.purge_command_queue.call_count == 1
        assert mock_service_operations.purge_command_queue.call_args == mocker.call(fake_device_id)


@pytest.mark.describe("IoTHubRegistryManager - .get_twin()")
class TestGetTwin(object):
    @pytest.mark.it("Test get twin")
    def test_get_twin(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_twin(fake_device_id)
        assert mock_service_operations.get_twin.call_count == 1
        assert mock_service_operations.get_twin.call_args == mocker.call(fake_device_id)


@pytest.mark.describe("IoTHubRegistryManager - .replace_twin()")
class TestReplaceTwin(object):
    @pytest.mark.it("Test replace twin")
    def test_replace_twin(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.replace_twin(fake_device_id, fake_device_twin)
        assert mock_service_operations.replace_twin.call_count == 1
        assert mock_service_operations.replace_twin.call_args == mocker.call(
            fake_device_id, fake_device_twin
        )


@pytest.mark.describe("IoTHubRegistryManager - .update_twin()")
class TestUpdateTwin(object):
    @pytest.mark.it("Test update twin")
    def test_update_twin(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.update_twin(fake_device_id, fake_device_twin, fake_etag)
        assert mock_service_operations.update_twin.call_count == 1
        assert mock_service_operations.update_twin.call_args == mocker.call(
            fake_device_id, fake_device_twin, fake_etag
        )


@pytest.mark.describe("IoTHubRegistryManager - .get_module_twin()")
class TestGetModuleTwin(object):
    @pytest.mark.it("Test get module twin")
    def test_get_module_twin(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_module_twin(fake_device_id, fake_module_id)
        assert mock_service_operations.get_module_twin.call_count == 1
        assert mock_service_operations.get_module_twin.call_args == mocker.call(
            fake_device_id, fake_module_id
        )


@pytest.mark.describe("IoTHubRegistryManager - .replace_module_twin()")
class TestReplaceModuleTwin(object):
    @pytest.mark.it("Test replace module twin")
    def test_replace_module_twin(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.replace_module_twin(
            fake_device_id, fake_module_id, fake_module_twin
        )
        assert mock_service_operations.replace_module_twin.call_count == 1
        assert mock_service_operations.replace_module_twin.call_args == mocker.call(
            fake_device_id, fake_module_id, fake_module_twin
        )


@pytest.mark.describe("IoTHubRegistryManager - .update_module_twin()")
class TestUpdateModuleTwin(object):
    @pytest.mark.it("Test update module twin")
    def test_update_module_twin(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.update_module_twin(
            fake_device_id, fake_module_id, fake_module_twin, fake_etag
        )
        assert mock_service_operations.update_module_twin.call_count == 1
        assert mock_service_operations.update_module_twin.call_args == mocker.call(
            fake_device_id, fake_module_id, fake_module_twin, fake_etag
        )


@pytest.mark.describe("IoTHubRegistryManager - .get_job()")
class TestGetJob(object):
    @pytest.mark.it("Test get job")
    def test_get_job(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_job(fake_job_id)
        assert mock_service_operations.get_job.call_count == 1
        assert mock_service_operations.get_job.call_args == mocker.call(fake_job_id)


@pytest.mark.describe("IoTHubRegistryManager - .create_job()")
class TestCreateJob(object):
    @pytest.mark.it("Test create job")
    def test_create_job(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.create_job(fake_job_id, fake_job_request)
        assert mock_service_operations.create_job.call_count == 1
        assert mock_service_operations.create_job.call_args == mocker.call(
            fake_job_id, fake_job_request
        )


@pytest.mark.describe("IoTHubRegistryManager - .cancel_job()")
class TestCancelJob(object):
    @pytest.mark.it("Test cancel job")
    def test_cancel_job(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.cancel_job(fake_job_id)
        assert mock_service_operations.cancel_job.call_count == 1
        assert mock_service_operations.cancel_job.call_args == mocker.call(fake_job_id)


@pytest.mark.describe("IoTHubRegistryManager - .query_jobs()")
class TestQueryJobs(object):
    @pytest.mark.it("Test query jobs")
    def test_query_jobs(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.query_jobs(fake_job_type, fake_job_status)
        assert mock_service_operations.query_jobs.call_count == 1
        assert mock_service_operations.query_jobs.call_args == mocker.call(
            fake_job_type, fake_job_status
        )


@pytest.mark.describe("IoTHubRegistryManager - .invoke_device_method()")
class TestInvokeDeviceMethod(object):
    @pytest.mark.it("Test invoke device method")
    def test_invoke_device_method(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.invoke_device_method(fake_device_id, fake_direct_method_request)
        assert mock_service_operations.invoke_device_method.call_count == 1
        assert mock_service_operations.invoke_device_method.call_args == mocker.call(
            fake_device_id, fake_direct_method_request
        )


@pytest.mark.describe("IoTHubRegistryManager - .invoke_device_module_method()")
class TestInvokeDeviceModuleMethod(object):
    @pytest.mark.it("Test invoke device module method")
    def test_invoke_device_module_method(
        self, mocker, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.invoke_device_module_method(
            fake_device_id, fake_module_id, fake_direct_method_request
        )
        assert mock_service_operations.invoke_device_module_method.call_count == 1
        assert mock_service_operations.invoke_device_module_method.call_args == mocker.call(
            fake_device_id, fake_module_id, fake_direct_method_request
        )
