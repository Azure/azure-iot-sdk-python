# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.provisioning.protocol.models import CertificateAuthority
from azure.iot.provisioning.protocol.provisioning_service_client import ProvisioningServiceClient
from azure.iot.provisioning.iot_provisioning_service_client import IoTProvisioningServiceClient

"""---Constants---"""

fake_hostname = "beauxbatons.academy-net"
fake_device_id = "MyPensieve"
fake_shared_access_key_name = "alohomora"
fake_shared_access_key = "Zm9vYmFy"

fake_name = "fake_name"
fake_group_name = "fake_group_name"
fake_object = "fake_object"
fake_etag = "fake_etag"
fake_query = "fake_query"
fake_count = 41

"""----Shared fixtures----"""


@pytest.fixture(scope="function", autouse=True)
def mock_service_client_protocol(mocker):
    mock_service_client_protocol_init = mocker.patch(
        "azure.iot.provisioning.iot_provisioning_service_client.protocol_client"
    )
    return mock_service_client_protocol_init


@pytest.fixture(scope="function")
def iot_provisioning_service_client():
    connection_string = "HostName={hostname};DeviceId={device_id};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
        hostname=fake_hostname,
        device_id=fake_device_id,
        skn=fake_shared_access_key_name,
        sk=fake_shared_access_key,
    )
    iot_provisioning_service_client = IoTProvisioningServiceClient(connection_string)
    return iot_provisioning_service_client


@pytest.mark.describe("IoTProvisioningServiceClient")
class TestIoTProvisioningServiceClient(object):
    @pytest.mark.it("IoTProvisioningServiceClient -- .get_certificate_authority")
    def test_get_certificate_authority(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.get_certificate_authority(fake_name)
        assert mock_service_client_protocol.get_certificate_authority.call_count == 1
        assert mock_service_client_protocol.get_certificate_authority.call_args[0][0] == fake_name
        assert mock_service_client_protocol.get_certificate_authority.call_args[0][1] is None
        assert mock_service_client_protocol.get_certificate_authority.call_args[0][2] is False
        assert mock_service_client_protocol.get_certificate_authority.call_args[0][3] is None
        assert result == mock_service_client_protocol.get_certificate_authority()

    @pytest.mark.it("IoTProvisioningServiceClient -- .create_certificate_authority")
    def test_create_certificate_authority(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.create_certificate_authority(
            fake_name, fake_object
        )
        assert mock_service_client_protocol.create_or_replace_certificate_authority.call_count == 1
        assert (
            mock_service_client_protocol.create_or_replace_certificate_authority.call_args[0][0]
            == fake_name
        )
        assert (
            mock_service_client_protocol.create_or_replace_certificate_authority.call_args[0][1]
            == fake_object
        )
        assert (
            mock_service_client_protocol.create_or_replace_certificate_authority.call_args[0][2]
            is None
        )
        assert (
            mock_service_client_protocol.create_or_replace_certificate_authority.call_args[0][3]
            is None
        )
        assert (
            mock_service_client_protocol.create_or_replace_certificate_authority.call_args[0][4]
            is False
        )
        assert (
            mock_service_client_protocol.create_or_replace_certificate_authority.call_args[0][5]
            is None
        )
        assert result == mock_service_client_protocol.create_or_replace_certificate_authority()

    @pytest.mark.it("IoTProvisioningServiceClient -- .replace_certificate_authority")
    def test_replace_certificate_authority(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.replace_certificate_authority(
            fake_name, fake_object, fake_etag
        )
        assert mock_service_client_protocol.create_or_replace_certificate_authority.call_count == 1
        assert (
            mock_service_client_protocol.create_or_replace_certificate_authority.call_args[0][0]
            == fake_name
        )
        assert (
            mock_service_client_protocol.create_or_replace_certificate_authority.call_args[0][1]
            == fake_object
        )
        assert (
            mock_service_client_protocol.create_or_replace_certificate_authority.call_args[0][2]
            == fake_etag
        )
        assert (
            mock_service_client_protocol.create_or_replace_certificate_authority.call_args[0][3]
            is None
        )
        assert (
            mock_service_client_protocol.create_or_replace_certificate_authority.call_args[0][4]
            is False
        )
        assert (
            mock_service_client_protocol.create_or_replace_certificate_authority.call_args[0][5]
            is None
        )
        assert result == mock_service_client_protocol.create_or_replace_certificate_authority()

    @pytest.mark.it("IoTProvisioningServiceClient -- .replace_certificate_authority - etag None")
    def test_replace_certificate_authority_etag_none(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        with pytest.raises(ValueError):
            iot_provisioning_service_client.replace_certificate_authority(
                fake_name, fake_object, None
            )

    @pytest.mark.it("IoTProvisioningServiceClient -- .delete_certificate_authority")
    def test_delete_certificate_authority(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.delete_certificate_authority(fake_name, fake_etag)
        assert mock_service_client_protocol.delete_certificate_authority.call_count == 1
        assert (
            mock_service_client_protocol.delete_certificate_authority.call_args[0][0] == fake_name
        )
        assert (
            mock_service_client_protocol.delete_certificate_authority.call_args[0][1] == fake_etag
        )
        assert mock_service_client_protocol.delete_certificate_authority.call_args[0][2] is None
        assert mock_service_client_protocol.delete_certificate_authority.call_args[0][3] is False
        assert mock_service_client_protocol.delete_certificate_authority.call_args[0][4] is None
        assert result is None

    @pytest.mark.it("IoTProvisioningServiceClient -- .get_device_group")
    def test_get_device_group(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.get_device_group(fake_name)
        assert mock_service_client_protocol.get_device_group.call_count == 1
        assert mock_service_client_protocol.get_device_group.call_args[0][0] == fake_name
        assert mock_service_client_protocol.get_device_group.call_args[0][1] is None
        assert mock_service_client_protocol.get_device_group.call_args[0][2] is False
        assert mock_service_client_protocol.get_device_group.call_args[0][3] is None
        assert result == mock_service_client_protocol.get_device_group()

    @pytest.mark.it("IoTProvisioningServiceClient -- .create_device_group")
    def test_create_device_group(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.create_device_group(fake_name, fake_object)
        assert mock_service_client_protocol.create_or_replace_device_group.call_count == 1
        assert (
            mock_service_client_protocol.create_or_replace_device_group.call_args[0][0] == fake_name
        )
        assert (
            mock_service_client_protocol.create_or_replace_device_group.call_args[0][1]
            == fake_object
        )
        assert mock_service_client_protocol.create_or_replace_device_group.call_args[0][2] is None
        assert mock_service_client_protocol.create_or_replace_device_group.call_args[0][3] is None
        assert mock_service_client_protocol.create_or_replace_device_group.call_args[0][4] is False
        assert mock_service_client_protocol.create_or_replace_device_group.call_args[0][5] is None
        assert result == mock_service_client_protocol.create_or_replace_device_group()

    @pytest.mark.it("IoTProvisioningServiceClient -- .replace_device_group")
    def test_replace_device_group(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.replace_device_group(
            fake_name, fake_object, fake_etag
        )
        assert mock_service_client_protocol.create_or_replace_device_group.call_count == 1
        assert (
            mock_service_client_protocol.create_or_replace_device_group.call_args[0][0] == fake_name
        )
        assert (
            mock_service_client_protocol.create_or_replace_device_group.call_args[0][1]
            == fake_object
        )
        assert (
            mock_service_client_protocol.create_or_replace_device_group.call_args[0][2] == fake_etag
        )
        assert mock_service_client_protocol.create_or_replace_device_group.call_args[0][3] is None
        assert mock_service_client_protocol.create_or_replace_device_group.call_args[0][4] is False
        assert mock_service_client_protocol.create_or_replace_device_group.call_args[0][5] is None
        assert result == mock_service_client_protocol.create_or_replace_device_group()

    @pytest.mark.it("IoTProvisioningServiceClient -- .replace_device_group - etag None")
    def test_replace_device_group_etag_none(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        with pytest.raises(ValueError):
            iot_provisioning_service_client.replace_device_group(fake_name, fake_object, None)

    @pytest.mark.it("IoTProvisioningServiceClient -- .delete_device_group")
    def test_delete_device_group(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.delete_device_group(fake_name, fake_etag)
        assert mock_service_client_protocol.delete_device_group.call_count == 1
        assert mock_service_client_protocol.delete_device_group.call_args[0][0] == fake_name
        assert mock_service_client_protocol.delete_device_group.call_args[0][1] == fake_etag
        assert mock_service_client_protocol.delete_device_group.call_args[0][2] is None
        assert mock_service_client_protocol.delete_device_group.call_args[0][3] is False
        assert mock_service_client_protocol.delete_device_group.call_args[0][4] is None
        assert result is None

    @pytest.mark.it("IoTProvisioningServiceClient -- .get_device_record")
    def test_get_device_record(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.get_device_record(fake_name, fake_device_id)
        assert mock_service_client_protocol.get_device_record.call_count == 1
        assert mock_service_client_protocol.get_device_record.call_args[0][0] == fake_name
        assert mock_service_client_protocol.get_device_record.call_args[0][1] == fake_device_id
        assert mock_service_client_protocol.get_device_record.call_args[0][2] == "all"
        assert mock_service_client_protocol.get_device_record.call_args[0][3] is None
        assert mock_service_client_protocol.get_device_record.call_args[0][4] is False
        assert mock_service_client_protocol.get_device_record.call_args[0][5] is None
        assert result == mock_service_client_protocol.get_device_record()

    @pytest.mark.it("IoTProvisioningServiceClient -- .create_device_record")
    def test_create_device_record(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.create_device_record(
            fake_name, fake_group_name, fake_object
        )
        assert mock_service_client_protocol.create_or_replace_device_record.call_count == 1
        assert (
            mock_service_client_protocol.create_or_replace_device_record.call_args[0][0]
            == fake_name
        )
        assert (
            mock_service_client_protocol.create_or_replace_device_record.call_args[0][1]
            == fake_group_name
        )
        assert (
            mock_service_client_protocol.create_or_replace_device_record.call_args[0][2]
            == fake_object
        )
        assert mock_service_client_protocol.create_or_replace_device_record.call_args[0][3] is None
        assert mock_service_client_protocol.create_or_replace_device_record.call_args[0][4] is None
        assert mock_service_client_protocol.create_or_replace_device_record.call_args[0][5] is False
        assert mock_service_client_protocol.create_or_replace_device_record.call_args[0][6] is None
        assert result == mock_service_client_protocol.create_or_replace_device_record()

    @pytest.mark.it("IoTProvisioningServiceClient -- .replace_device_record")
    def test_replace_device_record(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.replace_device_record(
            fake_name, fake_group_name, fake_object, fake_etag
        )
        assert (
            mock_service_client_protocol.create_or_replace_device_record.call_args[0][0]
            == fake_name
        )
        assert (
            mock_service_client_protocol.create_or_replace_device_record.call_args[0][1]
            == fake_group_name
        )
        assert (
            mock_service_client_protocol.create_or_replace_device_record.call_args[0][2]
            == fake_object
        )
        assert (
            mock_service_client_protocol.create_or_replace_device_record.call_args[0][3]
            == fake_etag
        )
        assert mock_service_client_protocol.create_or_replace_device_record.call_args[0][4] is None
        assert mock_service_client_protocol.create_or_replace_device_record.call_args[0][5] is False
        assert mock_service_client_protocol.create_or_replace_device_record.call_args[0][6] is None
        assert result == mock_service_client_protocol.create_or_replace_device_record()

    @pytest.mark.it("IoTProvisioningServiceClient -- .replace_device_record - etag None")
    def test_replace_device_record_etag_none(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        with pytest.raises(ValueError):
            iot_provisioning_service_client.replace_device_record(
                fake_name, fake_group_name, fake_object, None
            )

    @pytest.mark.it("IoTProvisioningServiceClient -- .delete_device_record")
    def test_delete_device_record(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.delete_device_record(
            fake_name, fake_group_name, fake_etag
        )
        assert mock_service_client_protocol.delete_device_record.call_count == 1
        assert mock_service_client_protocol.delete_device_record.call_args[0][0] == fake_name
        assert mock_service_client_protocol.delete_device_record.call_args[0][1] == fake_group_name
        assert mock_service_client_protocol.delete_device_record.call_args[0][2] == fake_etag
        assert mock_service_client_protocol.delete_device_record.call_args[0][3] is None
        assert mock_service_client_protocol.delete_device_record.call_args[0][4] is False
        assert mock_service_client_protocol.delete_device_record.call_args[0][5] is None
        assert result is None

    @pytest.mark.it("IoTProvisioningServiceClient -- .get_group_record")
    def test_get_group_record(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.get_group_record(fake_name, fake_device_id)
        assert mock_service_client_protocol.get_group_record.call_count == 1
        assert mock_service_client_protocol.get_group_record.call_args[0][0] == fake_name
        assert mock_service_client_protocol.get_group_record.call_args[0][1] == fake_device_id
        assert mock_service_client_protocol.get_group_record.call_args[0][2] == "all"
        assert mock_service_client_protocol.get_group_record.call_args[0][3] is None
        assert mock_service_client_protocol.get_group_record.call_args[0][4] is False
        assert mock_service_client_protocol.get_group_record.call_args[0][5] is None
        assert result == mock_service_client_protocol.get_group_record()

    @pytest.mark.it("IoTProvisioningServiceClient -- .create_group_record")
    def test_create_group_record(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.create_group_record(
            fake_name, fake_group_name, fake_object
        )
        assert mock_service_client_protocol.create_or_replace_group_record.call_count == 1
        assert (
            mock_service_client_protocol.create_or_replace_group_record.call_args[0][0] == fake_name
        )
        assert (
            mock_service_client_protocol.create_or_replace_group_record.call_args[0][1]
            == fake_group_name
        )
        assert (
            mock_service_client_protocol.create_or_replace_group_record.call_args[0][2]
            == fake_object
        )
        assert mock_service_client_protocol.create_or_replace_group_record.call_args[0][3] is None
        assert mock_service_client_protocol.create_or_replace_group_record.call_args[0][4] is None
        assert mock_service_client_protocol.create_or_replace_group_record.call_args[0][5] is False
        assert mock_service_client_protocol.create_or_replace_group_record.call_args[0][6] is None
        assert result == mock_service_client_protocol.create_or_replace_group_record()

    @pytest.mark.it("IoTProvisioningServiceClient -- .replace_group_record")
    def test_replace_group_record(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.replace_group_record(
            fake_name, fake_group_name, fake_object, fake_etag
        )
        assert (
            mock_service_client_protocol.create_or_replace_group_record.call_args[0][0] == fake_name
        )
        assert (
            mock_service_client_protocol.create_or_replace_group_record.call_args[0][1]
            == fake_group_name
        )
        assert (
            mock_service_client_protocol.create_or_replace_group_record.call_args[0][2]
            == fake_object
        )
        assert (
            mock_service_client_protocol.create_or_replace_group_record.call_args[0][3] == fake_etag
        )
        assert mock_service_client_protocol.create_or_replace_group_record.call_args[0][4] is None
        assert mock_service_client_protocol.create_or_replace_group_record.call_args[0][5] is False
        assert mock_service_client_protocol.create_or_replace_group_record.call_args[0][6] is None
        assert result == mock_service_client_protocol.create_or_replace_group_record()

    @pytest.mark.it("IoTProvisioningServiceClient -- .replace_group_record - etag None")
    def test_replace_group_record_etag_none(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        with pytest.raises(ValueError):
            iot_provisioning_service_client.replace_group_record(
                fake_name, fake_group_name, fake_object, None
            )

    @pytest.mark.it("IoTProvisioningServiceClient -- .delete_group_record")
    def test_delete_group_record(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.delete_group_record(
            fake_name, fake_group_name, fake_etag
        )
        assert mock_service_client_protocol.delete_group_record.call_count == 1
        assert mock_service_client_protocol.delete_group_record.call_args[0][0] == fake_name
        assert mock_service_client_protocol.delete_group_record.call_args[0][1] == fake_group_name
        assert mock_service_client_protocol.delete_group_record.call_args[0][2] == fake_etag
        assert mock_service_client_protocol.delete_group_record.call_args[0][3] is None
        assert mock_service_client_protocol.delete_group_record.call_args[0][4] is False
        assert mock_service_client_protocol.delete_group_record.call_args[0][5] is None
        assert result is None

    @pytest.mark.it("IoTProvisioningServiceClient -- .get_linked_hub")
    def test_get_linked_hub(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.get_linked_hub(fake_name)
        assert mock_service_client_protocol.get_linked_hub.call_count == 1
        assert mock_service_client_protocol.get_linked_hub.call_args[0][0] == fake_name
        assert mock_service_client_protocol.get_linked_hub.call_args[0][1] is None
        assert mock_service_client_protocol.get_linked_hub.call_args[0][2] is False
        assert mock_service_client_protocol.get_linked_hub.call_args[0][3] is None
        assert result == mock_service_client_protocol.get_linked_hub()

    @pytest.mark.it("IoTProvisioningServiceClient -- .create_linked_hub")
    def test_create_linked_hub(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.create_linked_hub(fake_name, fake_object)
        assert mock_service_client_protocol.create_or_replace_linked_hub.call_count == 1
        assert (
            mock_service_client_protocol.create_or_replace_linked_hub.call_args[0][0] == fake_name
        )
        assert (
            mock_service_client_protocol.create_or_replace_linked_hub.call_args[0][1] == fake_object
        )
        assert mock_service_client_protocol.create_or_replace_linked_hub.call_args[0][2] is None
        assert mock_service_client_protocol.create_or_replace_linked_hub.call_args[0][3] is None
        assert mock_service_client_protocol.create_or_replace_linked_hub.call_args[0][4] is False
        assert mock_service_client_protocol.create_or_replace_linked_hub.call_args[0][5] is None
        assert result == mock_service_client_protocol.create_or_replace_linked_hub()

    @pytest.mark.it("IoTProvisioningServiceClient -- .replace_linked_hub")
    def test_replace_linked_hub(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.replace_linked_hub(
            fake_name, fake_object, fake_etag
        )
        assert (
            mock_service_client_protocol.create_or_replace_linked_hub.call_args[0][0] == fake_name
        )
        assert (
            mock_service_client_protocol.create_or_replace_linked_hub.call_args[0][1] == fake_object
        )
        assert (
            mock_service_client_protocol.create_or_replace_linked_hub.call_args[0][2] == fake_etag
        )
        assert mock_service_client_protocol.create_or_replace_linked_hub.call_args[0][3] is None
        assert mock_service_client_protocol.create_or_replace_linked_hub.call_args[0][4] is False
        assert mock_service_client_protocol.create_or_replace_linked_hub.call_args[0][5] is None
        assert result == mock_service_client_protocol.create_or_replace_linked_hub()

    @pytest.mark.it("IoTProvisioningServiceClient -- .replace_linked_hub - etag None")
    def test_replace_linked_hub_etag_none(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        with pytest.raises(ValueError):
            iot_provisioning_service_client.replace_linked_hub(fake_name, fake_object, None)

    @pytest.mark.it("IoTProvisioningServiceClient -- .delete_linked_hub")
    def test_delete_linked_hub(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.delete_linked_hub(fake_name, fake_etag)
        assert mock_service_client_protocol.delete_linked_hub.call_count == 1
        assert mock_service_client_protocol.delete_linked_hub.call_args[0][0] == fake_name
        assert mock_service_client_protocol.delete_linked_hub.call_args[0][1] == fake_etag
        assert mock_service_client_protocol.delete_linked_hub.call_args[0][2] is None
        assert mock_service_client_protocol.delete_linked_hub.call_args[0][3] is False
        assert mock_service_client_protocol.delete_linked_hub.call_args[0][4] is None
        assert result is None

    @pytest.mark.it("IoTProvisioningServiceClient -- .get_provisioning_settings")
    def test_get_provisioning_settings(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.get_provisioning_settings(fake_name)
        assert mock_service_client_protocol.get_provisioning_settings.call_count == 1
        assert mock_service_client_protocol.get_provisioning_settings.call_args[0][0] == fake_name
        assert mock_service_client_protocol.get_provisioning_settings.call_args[0][1] is None
        assert mock_service_client_protocol.get_provisioning_settings.call_args[0][2] is False
        assert mock_service_client_protocol.get_provisioning_settings.call_args[0][3] is None
        assert result == mock_service_client_protocol.get_provisioning_settings()

    @pytest.mark.it("IoTProvisioningServiceClient -- .create_provisioning_settings")
    def test_create_provisioning_settings(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.create_provisioning_settings(
            fake_name, fake_object
        )
        assert mock_service_client_protocol.create_or_replace_provisioning_settings.call_count == 1
        assert (
            mock_service_client_protocol.create_or_replace_provisioning_settings.call_args[0][0]
            == fake_name
        )
        assert (
            mock_service_client_protocol.create_or_replace_provisioning_settings.call_args[0][1]
            == fake_object
        )
        assert (
            mock_service_client_protocol.create_or_replace_provisioning_settings.call_args[0][2]
            is None
        )
        assert (
            mock_service_client_protocol.create_or_replace_provisioning_settings.call_args[0][3]
            is None
        )
        assert (
            mock_service_client_protocol.create_or_replace_provisioning_settings.call_args[0][4]
            is False
        )
        assert (
            mock_service_client_protocol.create_or_replace_provisioning_settings.call_args[0][5]
            is None
        )
        assert result == mock_service_client_protocol.create_or_replace_provisioning_settings()

    @pytest.mark.it("IoTProvisioningServiceClient -- .replace_provisioning_settings")
    def test_replace_provisioning_settings(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.replace_provisioning_settings(
            fake_name, fake_object, fake_etag
        )
        assert (
            mock_service_client_protocol.create_or_replace_provisioning_settings.call_args[0][0]
            == fake_name
        )
        assert (
            mock_service_client_protocol.create_or_replace_provisioning_settings.call_args[0][1]
            == fake_object
        )
        assert (
            mock_service_client_protocol.create_or_replace_provisioning_settings.call_args[0][2]
            == fake_etag
        )
        assert (
            mock_service_client_protocol.create_or_replace_provisioning_settings.call_args[0][3]
            is None
        )
        assert (
            mock_service_client_protocol.create_or_replace_provisioning_settings.call_args[0][4]
            is False
        )
        assert (
            mock_service_client_protocol.create_or_replace_provisioning_settings.call_args[0][5]
            is None
        )
        assert result == mock_service_client_protocol.create_or_replace_provisioning_settings()

    @pytest.mark.it("IoTProvisioningServiceClient -- .replace_provisioning_settings - etag None")
    def test_replace_provisioning_settings_etag_none(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        with pytest.raises(ValueError):
            iot_provisioning_service_client.replace_provisioning_settings(
                fake_name, fake_object, None
            )

    @pytest.mark.it("IoTProvisioningServiceClient -- .delete_provisioning_settings")
    def test_delete_provisioning_settings(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.delete_provisioning_settings(fake_name, fake_etag)
        assert mock_service_client_protocol.delete_provisioning_settings.call_count == 1
        assert (
            mock_service_client_protocol.delete_provisioning_settings.call_args[0][0] == fake_name
        )
        assert (
            mock_service_client_protocol.delete_provisioning_settings.call_args[0][1] == fake_etag
        )
        assert mock_service_client_protocol.delete_provisioning_settings.call_args[0][2] is None
        assert mock_service_client_protocol.delete_provisioning_settings.call_args[0][3] is False
        assert mock_service_client_protocol.delete_provisioning_settings.call_args[0][4] is None
        assert result is None

    @pytest.mark.it("IoTProvisioningServiceClient -- .get_provisioning_record")
    def test_get_provisioning_record(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.get_provisioning_record(fake_name, fake_device_id)
        assert mock_service_client_protocol.get_provisioning_record.call_count == 1
        assert mock_service_client_protocol.get_provisioning_record.call_args[0][0] == fake_name
        assert (
            mock_service_client_protocol.get_provisioning_record.call_args[0][1] == fake_device_id
        )
        assert mock_service_client_protocol.get_provisioning_record.call_args[0][2] is None
        assert mock_service_client_protocol.get_provisioning_record.call_args[0][3] is False
        assert mock_service_client_protocol.get_provisioning_record.call_args[0][4] is None
        assert result == mock_service_client_protocol.get_provisioning_record()

    @pytest.mark.it("IoTProvisioningServiceClient -- .query_certificate_authorities")
    def test_query_certificate_authorities(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.query_certificate_authorities(
            fake_query, fake_count
        )
        assert mock_service_client_protocol.query_certificate_authorities.call_count == 1
        assert (
            mock_service_client_protocol.query_certificate_authorities.call_args[0][0] == fake_query
        )
        assert (
            mock_service_client_protocol.query_certificate_authorities.call_args[0][1] == fake_count
        )
        assert mock_service_client_protocol.query_certificate_authorities.call_args[0][2] is None
        assert mock_service_client_protocol.query_certificate_authorities.call_args[0][3] is False
        assert mock_service_client_protocol.query_certificate_authorities.call_args[0][4] is None
        assert result == mock_service_client_protocol.query_certificate_authorities()

    @pytest.mark.it("IoTProvisioningServiceClient -- .query_device_groups")
    def test_query_device_groups(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.query_device_groups(fake_query, fake_count)
        assert mock_service_client_protocol.query_device_groups.call_count == 1
        assert mock_service_client_protocol.query_device_groups.call_args[0][0] == fake_query
        assert mock_service_client_protocol.query_device_groups.call_args[0][1] == fake_count
        assert mock_service_client_protocol.query_device_groups.call_args[0][2] is None
        assert mock_service_client_protocol.query_device_groups.call_args[0][3] is False
        assert mock_service_client_protocol.query_device_groups.call_args[0][4] is None
        assert result == mock_service_client_protocol.query_device_groups()

    @pytest.mark.it("IoTProvisioningServiceClient -- .query_device_records")
    def test_query_device_records(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.query_device_records(fake_query, fake_count)
        assert mock_service_client_protocol.query_device_records.call_count == 1
        assert mock_service_client_protocol.query_device_records.call_args[0][0] == fake_query
        assert mock_service_client_protocol.query_device_records.call_args[0][1] == fake_count
        assert mock_service_client_protocol.query_device_records.call_args[0][2] == "all"
        assert mock_service_client_protocol.query_device_records.call_args[0][3] is None
        assert mock_service_client_protocol.query_device_records.call_args[0][4] is False
        assert mock_service_client_protocol.query_device_records.call_args[0][5] is None
        assert result == mock_service_client_protocol.query_device_records()

    @pytest.mark.it("IoTProvisioningServiceClient -- .query_group_records")
    def test_query_group_records(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.query_group_records(fake_query, fake_count)
        assert mock_service_client_protocol.query_group_records.call_count == 1
        assert mock_service_client_protocol.query_group_records.call_args[0][0] == fake_query
        assert mock_service_client_protocol.query_group_records.call_args[0][1] == fake_count
        assert mock_service_client_protocol.query_group_records.call_args[0][2] == "all"
        assert mock_service_client_protocol.query_group_records.call_args[0][3] is None
        assert mock_service_client_protocol.query_group_records.call_args[0][4] is False
        assert mock_service_client_protocol.query_group_records.call_args[0][5] is None
        assert result == mock_service_client_protocol.query_group_records()

    @pytest.mark.it("IoTProvisioningServiceClient -- .query_linked_hubs")
    def test_query_linked_hubs(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.query_linked_hubs(fake_query, fake_count)
        assert mock_service_client_protocol.query_linked_hubs.call_count == 1
        assert mock_service_client_protocol.query_linked_hubs.call_args[0][0] == fake_query
        assert mock_service_client_protocol.query_linked_hubs.call_args[0][1] == fake_count
        assert mock_service_client_protocol.query_linked_hubs.call_args[0][2] is None
        assert mock_service_client_protocol.query_linked_hubs.call_args[0][3] is False
        assert mock_service_client_protocol.query_linked_hubs.call_args[0][4] is None
        assert result == mock_service_client_protocol.query_linked_hubs()

    @pytest.mark.it("IoTProvisioningServiceClient -- .query_provisioning_records")
    def test_query_provisioning_records(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.query_provisioning_records(fake_query, fake_count)
        assert mock_service_client_protocol.query_provisioning_records.call_count == 1
        assert mock_service_client_protocol.query_provisioning_records.call_args[0][0] == fake_query
        assert mock_service_client_protocol.query_provisioning_records.call_args[0][1] == fake_count
        assert mock_service_client_protocol.query_provisioning_records.call_args[0][2] is None
        assert mock_service_client_protocol.query_provisioning_records.call_args[0][3] is False
        assert mock_service_client_protocol.query_provisioning_records.call_args[0][4] is None
        assert result == mock_service_client_protocol.query_provisioning_records()

    @pytest.mark.it("IoTProvisioningServiceClient -- .query_provisioning_settings")
    def test_query_provisioning_settings(
        self, mocker, mock_service_client_protocol, iot_provisioning_service_client
    ):
        result = iot_provisioning_service_client.query_provisioning_settings(fake_query, fake_count)
        assert mock_service_client_protocol.query_provisioning_settings.call_count == 1
        assert (
            mock_service_client_protocol.query_provisioning_settings.call_args[0][0] == fake_query
        )
        assert (
            mock_service_client_protocol.query_provisioning_settings.call_args[0][1] == fake_count
        )
        assert mock_service_client_protocol.query_provisioning_settings.call_args[0][2] is None
        assert mock_service_client_protocol.query_provisioning_settings.call_args[0][3] is False
        assert mock_service_client_protocol.query_provisioning_settings.call_args[0][4] is None
        assert result == mock_service_client_protocol.query_provisioning_settings()
