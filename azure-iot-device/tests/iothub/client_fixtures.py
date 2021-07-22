# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import time
from six.moves import urllib
from azure.iot.device.iothub.pipeline import constant
from azure.iot.device.iothub.models import (
    Message,
    MethodResponse,
    MethodRequest,
    CommandRequest,
    CommandResponse,
    ClientPropertyCollection,
)
from azure.iot.device.common.models.x509 import X509


"""---Constants---"""

shared_access_key = "Zm9vYmFy"
hostname = "beauxbatons.academy-net"
device_id = "MyPensieve"
module_id = "Divination"
gateway_hostname = "EnchantedCeiling"
signature = "ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI="
expiry = str(int(time.time()) + 3600)
fake_x509_cert_value = "fantastic_beasts"
fake_x509_cert_key = "where_to_find_them"
fake_pass_phrase = "alohomora"


"""----Shared model fixtures----"""


@pytest.fixture
def message():
    return Message("Wingardium Leviosa")


@pytest.fixture
def method_response():
    return MethodResponse(request_id="1", status=200, payload={"key": "value"})


@pytest.fixture
def method_request():
    return MethodRequest(request_id="1", name="some_method", payload={"key": "value"})


@pytest.fixture(params=["Component CommandRequest", "Non-Component CommandRequest"])
def method_request_command(request):
    # Method Request object containing CommandRequest info
    if request.param == "Component CommandRequest":
        name = "some_component*some_command"
    else:
        name = "some_command"
    return MethodRequest(request_id="1", name=name, payload={"key": "value"})


@pytest.fixture(params=["Component CommandRequest", "Non-Component CommandRequest"])
def command_request(request):
    if request.param == "Component CommandRequest":
        component_name = "some_component"
    else:
        component_name = None
    return CommandRequest(
        request_id="1",
        component_name=component_name,
        command_name="some_command",
        payload={"key": "value"},
    )


@pytest.fixture
def command_response():
    return CommandResponse(request_id="1", status=200, payload={"key": "value"})


@pytest.fixture(
    params=["Component ClientPropertyCollection", "Non-Component ClientPropertyCollection"]
)
def client_property_collection(request):
    cpc = ClientPropertyCollection()
    cpc.set_property("property1", "value1")
    cpc.set_property("property2", "value2")
    if request.param == "Component ClientPropertyCollection":
        cpc.set_component_property("component1", "property3", "value3")
        cpc.set_component_property("component2", "property4", "value4")
    return cpc


@pytest.fixture
def telemetry_dict():
    return {"temperature": 15.6}


"""----Shared Twin fixtures----"""


@pytest.fixture
def twin_patch_desired():
    return {"foo": 23, "$version": 3}


@pytest.fixture
def twin_patch_reported():
    return {"foo": 12, "bar": 2}


@pytest.fixture
def fake_twin():
    return {
        "desired": {"key1": "value1", "key2": "value2", "$version": 4},
        "reported": {"$version": 1},
    }


@pytest.fixture
def fake_twin_components():
    return {
        "desired": {
            "some_component": {
                "__t": "c",
                "component_key1": "component_value1",
                "component_key2": "component_value2",
            },
            "key1": "value1",
            "key2": "value2",
            "$version": 4,
        },
        "reported": {
            "some_other_component": {
                "__t": "c",
                "component_key3": "component_value3",
                "component_key4": "component_value4",
            },
            "$version": 1,
        },
    }


"""----Shared connection string fixtures----"""

device_connection_string_format = (
    "HostName={hostname};DeviceId={device_id};SharedAccessKey={shared_access_key}"
)
device_connection_string_gateway_format = "HostName={hostname};DeviceId={device_id};SharedAccessKey={shared_access_key};GatewayHostName={gateway_hostname}"

module_connection_string_format = "HostName={hostname};DeviceId={device_id};ModuleId={module_id};SharedAccessKey={shared_access_key}"
module_connection_string_gateway_format = "HostName={hostname};DeviceId={device_id};ModuleId={module_id};SharedAccessKey={shared_access_key};GatewayHostName={gateway_hostname}"


@pytest.fixture(params=["Device Connection String", "Device Connection String w/ Protocol Gateway"])
def device_connection_string(request):
    string_type = request.param
    if string_type == "Device Connection String":
        return device_connection_string_format.format(
            hostname=hostname, device_id=device_id, shared_access_key=shared_access_key
        )
    else:
        return device_connection_string_gateway_format.format(
            hostname=hostname,
            device_id=device_id,
            shared_access_key=shared_access_key,
            gateway_hostname=gateway_hostname,
        )


@pytest.fixture(params=["Module Connection String", "Module Connection String w/ Protocol Gateway"])
def module_connection_string(request):
    string_type = request.param
    if string_type == "Module Connection String":
        return module_connection_string_format.format(
            hostname=hostname,
            device_id=device_id,
            module_id=module_id,
            shared_access_key=shared_access_key,
        )
    else:
        return module_connection_string_gateway_format.format(
            hostname=hostname,
            device_id=device_id,
            module_id=module_id,
            shared_access_key=shared_access_key,
            gateway_hostname=gateway_hostname,
        )


"""----Shared SAS fixtures---"""

sas_token_format = "SharedAccessSignature sr={uri}&sig={signature}&se={expiry}"
# when to use the skn format?
sas_token_skn_format = (
    "SharedAccessSignature sr={uri}&sig={signature}&se={expiry}&skn={shared_access_key_name}"
)

# what about variant input with different ordered attributes
# SharedAccessSignature sig={signature-string}&se={expiry}&skn={policyName}&sr={URL-encoded-resourceURI}


@pytest.fixture()
def device_sas_token_string():
    uri = hostname + "/devices/" + device_id
    return sas_token_format.format(
        uri=urllib.parse.quote(uri, safe=""),
        signature=urllib.parse.quote(signature, safe=""),
        expiry=expiry,
    )


@pytest.fixture()
def module_sas_token_string():
    uri = hostname + "/devices/" + device_id + "/modules/" + module_id
    return sas_token_format.format(
        uri=urllib.parse.quote(uri, safe=""),
        signature=urllib.parse.quote(signature, safe=""),
        expiry=expiry,
    )


"""----Shared certificate fixtures----"""


@pytest.fixture()
def x509():
    return X509(fake_x509_cert_value, fake_x509_cert_key, fake_pass_phrase)


"""----Shared Edge Container configuration---"""


@pytest.fixture()
def edge_container_environment():
    return {
        "IOTEDGE_MODULEID": "__FAKE_MODULE_ID__",
        "IOTEDGE_DEVICEID": "__FAKE_DEVICE_ID__",
        "IOTEDGE_IOTHUBHOSTNAME": "__FAKE_HOSTNAME__",
        "IOTEDGE_GATEWAYHOSTNAME": "__FAKE_GATEWAY_HOSTNAME__",
        "IOTEDGE_APIVERSION": "__FAKE_API_VERSION__",
        "IOTEDGE_MODULEGENERATIONID": "__FAKE_MODULE_GENERATION_ID__",
        "IOTEDGE_WORKLOADURI": "http://__FAKE_WORKLOAD_URI__/",
    }


@pytest.fixture()
def edge_local_debug_environment():
    cs = module_connection_string_gateway_format.format(
        hostname=hostname,
        device_id=device_id,
        module_id=module_id,
        shared_access_key=shared_access_key,
        gateway_hostname=gateway_hostname,
    )
    return {
        "EdgeHubConnectionString": cs,
        "EdgeModuleCACertificateFile": "__FAKE_SERVER_VERIFICATION_CERTIFICATE__",
    }


@pytest.fixture
def mock_edge_hsm(mocker):
    mock_edge_hsm = mocker.patch("azure.iot.device.iothub.edge_hsm.IoTEdgeHsm")
    mock_edge_hsm.return_value.sign.return_value = "8NJRMT83CcplGrAGaUVIUM/md5914KpWVNngSVoF9/M="
    mock_edge_hsm.return_value.get_certificate.return_value = (
        "__FAKE_SERVER_VERIFICATION_CERTIFICATE__"
    )
    return mock_edge_hsm


"""----Shared mock pipeline fixture----"""


class FakeIoTHubPipeline:
    def __init__(self):
        self.feature_enabled = {}  # This just has to be here for the spec

    def shutdown(self, callback):
        callback()

    def connect(self, callback):
        callback()

    def disconnect(self, callback):
        callback()

    def reauthorize_connection(self, callback):
        callback()

    def enable_feature(self, feature_name, callback):
        callback()

    def disable_feature(self, feature_name, callback):
        callback()

    def send_message(self, event, callback):
        callback()

    def send_output_message(self, event, callback):
        callback()

    def send_method_response(self, method_response, callback):
        callback()

    def get_twin(self, callback):
        callback(twin={})

    def patch_twin_reported_properties(self, patch, callback):
        callback()


class FakeHTTPPipeline:
    def __init__(self):
        pass

    def invoke_method(self, device_id, method_params, callback, module_id=None):
        callback(invoke_method_response="__fake_method_response__")

    def get_storage_info_for_blob(self, blob_name, callback):
        callback(storage_info="__fake_storage_info__")

    def notify_blob_upload_status(
        self, correlation_id, is_success, status_code, status_description, callback
    ):
        callback()


@pytest.fixture
def mqtt_pipeline(mocker):
    """This fixture will automatically handle callbacks and should be
    used in the majority of tests.
    """
    return mocker.MagicMock(wraps=FakeIoTHubPipeline())


@pytest.fixture
def mqtt_pipeline_manual_cb(mocker):
    """This fixture is for use in tests where manual triggering of a
    callback is required
    """
    return mocker.MagicMock()


@pytest.fixture
def http_pipeline(mocker):
    """This fixture will automatically handle callbacks and should be
    used in the majority of tests
    """
    return mocker.MagicMock(wraps=FakeHTTPPipeline())


@pytest.fixture
def http_pipeline_manual_cb(mocker):
    """This fixture is for use in tests where manual triggering of a
    callback is required
    """
    return mocker.MagicMock()


@pytest.fixture
def mock_mqtt_pipeline_init(mocker):
    return mocker.patch("azure.iot.device.iothub.pipeline.MQTTPipeline")


@pytest.fixture
def mock_http_pipeline_init(mocker):
    return mocker.patch("azure.iot.device.iothub.pipeline.HTTPPipeline")
