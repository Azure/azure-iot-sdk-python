# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.hub.protocol.models import AuthenticationMechanism
from azure.iot.hub.iothub_digitaltwin_manager import IoTHubDigitalTwinManager
from azure.iot.hub.auth import ConnectionStringAuthentication
from azure.iot.hub.protocol.iot_hub_gateway_service_ap_is import IotHubGatewayServiceAPIs

"""---Constants---"""

fake_hostname = "beauxbatons.academy-net"
fake_device_id = "MyPensieve"
fake_shared_access_key_name = "alohomora"
fake_shared_access_key = "Zm9vYmFy"
fake_digital_twin_id = "fake_digital_twin_id"
fake_digital_twin_patch = "fake_digital_twin_patch"
fake_etag = "fake_etag"
fake_component_path = "fake_component_path"
fake_component_name = "fake_component_name"
fake_payload = "fake_payload"
fake_model_id = "fake_model_id"


"""----Shared fixtures----"""


@pytest.fixture(scope="function", autouse=True)
def mock_digital_twin_operations(mocker):
    mock_digital_twin_operations_init = mocker.patch(
        "azure.iot.hub.protocol.iot_hub_gateway_service_ap_is.DigitalTwinOperations"
    )
    return mock_digital_twin_operations_init.return_value


@pytest.fixture(scope="function")
def iothub_digitaltwin_manager():
    connection_string = "HostName={hostname};DeviceId={device_id};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
        hostname=fake_hostname,
        device_id=fake_device_id,
        skn=fake_shared_access_key_name,
        sk=fake_shared_access_key,
    )
    iothub_digitaltwin_manager = IoTHubDigitalTwinManager(connection_string)
    return iothub_digitaltwin_manager


@pytest.mark.describe("IoTHubDigitalTwinManager - Instantiation")
class TestDigitalTwinManager(object):
    @pytest.mark.it("Instantiation sets the auth and protocol attributes")
    def test_instantiates_auth_and_protocol_attributes(self, iothub_digitaltwin_manager):
        assert isinstance(iothub_digitaltwin_manager.auth, ConnectionStringAuthentication)
        assert isinstance(iothub_digitaltwin_manager.protocol, IotHubGatewayServiceAPIs)

    @pytest.mark.it(
        "Raises a ValueError exception when instantiated with an empty connection string"
    )
    def test_instantiates_with_empty_connection_string(self):
        with pytest.raises(ValueError):
            IoTHubDigitalTwinManager("")

    @pytest.mark.it(
        "Raises a ValueError exception when instantiated with a connection string without HostName"
    )
    def test_instantiates_with_connection_string_no_host_name(self):
        connection_string = "DeviceId={device_id};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
            device_id=fake_device_id, skn=fake_shared_access_key_name, sk=fake_shared_access_key
        )
        with pytest.raises(ValueError):
            IoTHubDigitalTwinManager(connection_string)

    @pytest.mark.it("Instantiates with an connection string without DeviceId")
    def test_instantiates_with_connection_string_no_device_id(self):
        connection_string = "HostName={hostname};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
            hostname=fake_hostname, skn=fake_shared_access_key_name, sk=fake_shared_access_key
        )
        obj = IoTHubDigitalTwinManager(connection_string)
        assert isinstance(obj, IoTHubDigitalTwinManager)

    @pytest.mark.it("Instantiates with an connection string without SharedAccessKeyName")
    def test_instantiates_with_connection_string_no_shared_access_key_name(self):
        connection_string = "HostName={hostname};DeviceId={device_id};SharedAccessKey={sk}".format(
            hostname=fake_hostname, device_id=fake_device_id, sk=fake_shared_access_key
        )
        obj = IoTHubDigitalTwinManager(connection_string)
        assert isinstance(obj, IoTHubDigitalTwinManager)

    @pytest.mark.it(
        "Raises a ValueError exception when instantiated with a connection string without SharedAccessKey"
    )
    def test_instantiates_with_connection_string_no_shared_access_key(self):
        connection_string = "HostName={hostname};DeviceId={device_id};SharedAccessKeyName={skn}".format(
            hostname=fake_hostname, device_id=fake_device_id, skn=fake_shared_access_key_name
        )
        with pytest.raises(ValueError):
            IoTHubDigitalTwinManager(connection_string)


@pytest.mark.describe("IoTHubDigitalTwinManager - .get_digital_twin()")
class TestGetDigitalTwin(object):
    @pytest.mark.it("Uses protocol layer DigitalTwin Client runtime to get a digital twin")
    def test_get_digital_twin(
        self, mocker, mock_digital_twin_operations, iothub_digitaltwin_manager
    ):
        ret_val = iothub_digitaltwin_manager.get_digital_twin(fake_digital_twin_id)
        assert mock_digital_twin_operations.get_digital_twin.call_count == 1
        assert mock_digital_twin_operations.get_digital_twin.call_args == mocker.call(
            fake_digital_twin_id
        )
        assert ret_val == mock_digital_twin_operations.get_digital_twin()


@pytest.mark.describe("IoTHubDigitalTwinManager - .update_digital_twin()")
class TestUpdateDigitalTwin(object):
    @pytest.mark.it("Uses protocol layer DigitalTwin Client runtime to update a digital twin")
    def test_update_digital_twin(
        self, mocker, mock_digital_twin_operations, iothub_digitaltwin_manager
    ):
        ret_val = iothub_digitaltwin_manager.update_digital_twin(
            fake_digital_twin_id, fake_digital_twin_patch, fake_etag
        )
        assert mock_digital_twin_operations.update_digital_twin.call_count == 1
        assert mock_digital_twin_operations.update_digital_twin.call_args == mocker.call(
            fake_digital_twin_id, fake_digital_twin_patch, fake_etag
        )
        assert ret_val == mock_digital_twin_operations.update_digital_twin()


@pytest.mark.describe("IoTHubDigitalTwinManager - .update_digital_twin()")
class TestUpdateDigitalTwinNoEtag(object):
    @pytest.mark.it(
        "Uses protocol layer DigitalTwin Client runtime to update a digital twin without etag"
    )
    def test_update_digital_twin(
        self, mocker, mock_digital_twin_operations, iothub_digitaltwin_manager
    ):
        ret_val = iothub_digitaltwin_manager.update_digital_twin(
            fake_digital_twin_id, fake_digital_twin_patch
        )
        assert mock_digital_twin_operations.update_digital_twin.call_count == 1
        assert mock_digital_twin_operations.update_digital_twin.call_args == mocker.call(
            fake_digital_twin_id, fake_digital_twin_patch, None
        )
        assert ret_val == mock_digital_twin_operations.update_digital_twin()


@pytest.mark.describe("IoTHubDigitalTwinManager - .get_components()")
class TestGetComponents(object):
    @pytest.mark.it("Uses protocol layer DigitalTwin Client runtime to get components")
    def test_get_components(self, mocker, mock_digital_twin_operations, iothub_digitaltwin_manager):
        ret_val = iothub_digitaltwin_manager.get_components(fake_digital_twin_id)
        assert mock_digital_twin_operations.get_components.call_count == 1
        assert mock_digital_twin_operations.get_components.call_args == mocker.call(
            fake_digital_twin_id
        )
        assert ret_val == mock_digital_twin_operations.get_components()


@pytest.mark.describe("IoTHubDigitalTwinManager - .update_component()")
class TestUpdateComponent(object):
    @pytest.mark.it("Uses protocol layer DigitalTwin Client runtime to update component")
    def test_update_component(
        self, mocker, mock_digital_twin_operations, iothub_digitaltwin_manager
    ):
        ret_val = iothub_digitaltwin_manager.update_component(
            fake_digital_twin_id, fake_digital_twin_patch, fake_etag
        )
        assert mock_digital_twin_operations.update_component.call_count == 1
        assert mock_digital_twin_operations.update_component.call_args == mocker.call(
            fake_digital_twin_id, fake_digital_twin_patch, fake_etag
        )
        assert ret_val == mock_digital_twin_operations.update_component()


@pytest.mark.describe("IoTHubDigitalTwinManager - .update_component()")
class TestUpdateComponentNoEtag(object):
    @pytest.mark.it(
        "Uses protocol layer DigitalTwin Client runtime to update cmoponent without etag"
    )
    def test_update_component(
        self, mocker, mock_digital_twin_operations, iothub_digitaltwin_manager
    ):
        ret_val = iothub_digitaltwin_manager.update_component(
            fake_digital_twin_id, fake_digital_twin_patch
        )
        assert mock_digital_twin_operations.update_component.call_count == 1
        assert mock_digital_twin_operations.update_component.call_args == mocker.call(
            fake_digital_twin_id, fake_digital_twin_patch, None
        )
        assert ret_val == mock_digital_twin_operations.update_component()


@pytest.mark.describe("IoTHubDigitalTwinManager - .get_component()")
class TestGetComponent(object):
    @pytest.mark.it("Uses protocol layer DigitalTwin Client runtime to get a component")
    def test_get_component(self, mocker, mock_digital_twin_operations, iothub_digitaltwin_manager):
        ret_val = iothub_digitaltwin_manager.get_component(
            fake_digital_twin_id, fake_component_name
        )
        assert mock_digital_twin_operations.get_component.call_count == 1
        assert mock_digital_twin_operations.get_component.call_args == mocker.call(
            fake_digital_twin_id, fake_component_name
        )
        assert ret_val == mock_digital_twin_operations.get_component()


@pytest.mark.describe("IoTHubDigitalTwinManager - .get_model()")
class TestGetModel(object):
    @pytest.mark.it("Uses protocol layer DigitalTwin Client runtime to get a component")
    def test_get_model(self, mocker, mock_digital_twin_operations, iothub_digitaltwin_manager):
        ret_val = iothub_digitaltwin_manager.get_model(fake_model_id)
        assert mock_digital_twin_operations.get_digital_twin_model.call_count == 1
        assert mock_digital_twin_operations.get_digital_twin_model.call_args == mocker.call(
            fake_model_id
        )
        assert ret_val == mock_digital_twin_operations.get_digital_twin_model()


@pytest.mark.describe("IoTHubDigitalTwinManager - .invoke_component_command()")
class TestInvokeComponentCommand(object):
    @pytest.mark.it("Uses protocol layer DigitalTwin Client runtime to invoke a component command")
    def test_invoke_component_command(
        self, mocker, mock_digital_twin_operations, iothub_digitaltwin_manager
    ):
        ret_val = iothub_digitaltwin_manager.invoke_component_command(
            fake_digital_twin_id, fake_component_path, fake_component_name, fake_payload
        )
        assert mock_digital_twin_operations.invoke_component_command1.call_count == 1
        assert mock_digital_twin_operations.invoke_component_command1.call_args == mocker.call(
            fake_digital_twin_id, fake_component_path, fake_component_name, fake_payload
        )
        assert ret_val == mock_digital_twin_operations.invoke_component_command1()
