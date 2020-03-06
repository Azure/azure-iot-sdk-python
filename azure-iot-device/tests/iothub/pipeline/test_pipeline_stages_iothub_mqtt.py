# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import json
import sys
import six.moves.urllib as urllib
from azure.iot.device.common.pipeline import (
    pipeline_events_base,
    pipeline_ops_base,
    pipeline_stages_base,
    pipeline_ops_mqtt,
    pipeline_events_mqtt,
)
from azure.iot.device.iothub.pipeline import (
    constant,
    pipeline_events_iothub,
    pipeline_ops_iothub,
    pipeline_stages_iothub_mqtt,
    config,
)
from azure.iot.device.iothub.pipeline.exceptions import OperationError, PipelineError
from azure.iot.device.iothub.models.message import Message
from azure.iot.device.iothub.models.methods import MethodRequest, MethodResponse
from tests.common.pipeline.helpers import all_common_ops, all_common_events, StageTestBase
from tests.iothub.pipeline.helpers import all_iothub_ops, all_iothub_events
from tests.common.pipeline import pipeline_stage_test
from azure.iot.device import constant as pkg_constant
from azure.iot.device.product_info import ProductInfo

logging.basicConfig(level=logging.DEBUG)

this_module = sys.modules[__name__]


# This fixture makes it look like all test in this file  tests are running
# inside the pipeline thread.  Because this is an autouse fixture, we
# manually add it to the individual test.py files that need it.  If,
# instead, we had added it to some conftest.py, it would be applied to
# every tests in every file and we don't want that.
@pytest.fixture(autouse=True)
def apply_fake_pipeline_thread(fake_pipeline_thread):
    pass


fake_device_id = "__fake_device_id__"
fake_module_id = "__fake_module_id__"
fake_hostname = "__fake_hostname__"
fake_gateway_hostname = "__fake_gateway_hostname__"
fake_server_verification_cert = "__fake_server_verification_cert__"
fake_client_cert = "__fake_client_cert__"
fake_sas_token = "__fake_sas_token__"

fake_message_id = "ee9e738b-4f47-447a-9892-5b1d1d7ca5"
fake_message_id_encoded = "%24.mid=ee9e738b-4f47-447a-9892-5b1d1d7ca5"
fake_message_body = "__fake_message_body__"
fake_output_name = "__fake_output_name__"
fake_output_name_encoded = "%24.on=__fake_output_name__"
fake_content_type = "text/json"
fake_content_type_encoded = "%24.ct=text%2Fjson"
fake_content_encoding = "utf-16"
fake_content_encoding_encoded = "%24.ce=utf-16"
default_content_type = "application/json"
default_content_type_encoded = "%24.ct=application%2Fjson"
default_content_encoding_encoded = "%24.ce=utf-8"
fake_message = Message(fake_message_body)
security_message_interface_id_encoded = "%24.ifid=urn%3Aazureiot%3ASecurity%3ASecurityAgent%3A1"
fake_request_id = "__fake_request_id__"
fake_method_name = "__fake_method_name__"
fake_method_payload = "__fake_method_payload__"
fake_method_status = "__fake_method_status__"
fake_method_response = MethodResponse(
    request_id=fake_request_id, status=fake_method_status, payload=fake_method_payload
)

invalid_feature_name = "__invalid_feature_name__"
unmatched_mqtt_topic = "__unmatched_mqtt_topic__"
fake_mqtt_payload = "__fake_mqtt_payload__"

fake_c2d_topic = "devices/{}/messages/devicebound/".format(fake_device_id)
fake_c2d_topic_with_content_type = "{}{}".format(fake_c2d_topic, fake_content_type_encoded)
fake_c2d_topic_for_another_device = "devices/__other_device__/messages/devicebound/"

fake_input_name = "__fake_input_name__"
fake_input_message_topic = "devices/{}/modules/{}/inputs/{}/".format(
    fake_device_id, fake_module_id, fake_input_name
)
fake_input_message_topic_with_content_type = "{}{}".format(
    fake_input_message_topic, fake_content_type_encoded
)
fake_input_message_topic_for_another_module = "devices/{}/modules/__other_module__/messages/devicebound/".format(
    fake_device_id
)
fake_input_message_topic_for_another_device = "devices/__other_device__/modules/{}/messages/devicebound/".format(
    fake_module_id
)

fake_method_request_topic = "$iothub/methods/POST/{}/?$rid={}".format(
    fake_method_name, fake_request_id
)
fake_method_request_payload = "{}".encode("utf-8")

encoded_user_agent = urllib.parse.quote_plus(ProductInfo.get_iothub_user_agent())

fake_message_user_property_1_key = "is-muggle"
fake_message_user_property_1_value = "yes"
fake_message_user_property_2_key = "sorted-house"
fake_message_user_property_2_value = "hufflepuff"
fake_message_user_property_1_encoded = "is-muggle=yes"
fake_message_user_property_2_encoded = "sorted-house=hufflepuff"

ops_handled_by_this_stage = [
    pipeline_ops_iothub.SetIoTHubConnectionArgsOperation,
    pipeline_ops_iothub.SendD2CMessageOperation,
    pipeline_ops_base.UpdateSasTokenOperation,
    pipeline_ops_iothub.SendOutputEventOperation,
    pipeline_ops_iothub.SendMethodResponseOperation,
    pipeline_ops_base.RequestOperation,
    pipeline_ops_base.EnableFeatureOperation,
    pipeline_ops_base.DisableFeatureOperation,
]

events_handled_by_this_stage = [pipeline_events_mqtt.IncomingMQTTMessageEvent]

pipeline_stage_test.add_base_pipeline_stage_tests_old(
    cls=pipeline_stages_iothub_mqtt.IoTHubMQTTTranslationStage,
    module=this_module,
    all_ops=all_common_ops + all_iothub_ops,
    handled_ops=ops_handled_by_this_stage,
    all_events=all_common_events + all_iothub_events,
    handled_events=events_handled_by_this_stage,
    extra_initializer_defaults={"feature_to_topic": dict},
)


def create_message_with_user_properties(message_content, is_multiple):
    m = Message(message_content)
    m.custom_properties[fake_message_user_property_1_key] = fake_message_user_property_1_value
    if is_multiple:
        m.custom_properties[fake_message_user_property_2_key] = fake_message_user_property_2_value
    return m


def create_security_message(message_content):
    msg = Message(message_content)
    msg.set_as_security_message()
    return msg


def create_message_with_system_and_user_properties(message_content, is_multiple):
    if is_multiple:
        msg = Message(message_content, message_id=fake_message_id, output_name=fake_output_name)
    else:
        msg = Message(message_content, message_id=fake_message_id)

    msg.custom_properties[fake_message_user_property_1_key] = fake_message_user_property_1_value
    if is_multiple:
        msg.custom_properties[fake_message_user_property_2_key] = fake_message_user_property_2_value
    return msg


def create_security_message_with_system_and_user_properties(message_content, is_multiple):
    if is_multiple:
        msg = Message(message_content, message_id=fake_message_id, output_name=fake_output_name)
    else:
        msg = Message(message_content, message_id=fake_message_id)

    msg.custom_properties[fake_message_user_property_1_key] = fake_message_user_property_1_value
    if is_multiple:
        msg.custom_properties[fake_message_user_property_2_key] = fake_message_user_property_2_value
    msg.set_as_security_message()
    return msg


def create_message_for_output_with_user_properties(message_content, is_multiple):
    m = Message(message_content, output_name=fake_output_name)
    m.custom_properties[fake_message_user_property_1_key] = fake_message_user_property_1_value
    if is_multiple:
        m.custom_properties[fake_message_user_property_2_key] = fake_message_user_property_2_value
    return m


def create_message_for_output_with_system_and_user_properties(message_content, is_multiple):
    if is_multiple:
        msg = Message(
            message_content,
            output_name=fake_output_name,
            message_id=fake_message_id,
            content_type=fake_content_type,
        )
    else:
        msg = Message(message_content, output_name=fake_output_name, message_id=fake_message_id)

    msg.custom_properties[fake_message_user_property_1_key] = fake_message_user_property_1_value
    if is_multiple:
        msg.custom_properties[fake_message_user_property_2_key] = fake_message_user_property_2_value
    return msg


@pytest.fixture
def set_connection_args(mocker):
    return pipeline_ops_iothub.SetIoTHubConnectionArgsOperation(
        device_id=fake_device_id, hostname=fake_hostname, callback=mocker.MagicMock()
    )


@pytest.fixture
def set_connection_args_for_device(set_connection_args):
    return set_connection_args


@pytest.fixture
def set_connection_args_for_module(set_connection_args):
    set_connection_args.module_id = fake_module_id
    return set_connection_args


class IoTHubMQTTTranslationStageTestBase(StageTestBase):
    @pytest.fixture(autouse=True)
    def stage_base_configuration(self, stage, mocker):
        class NextStageForTest(pipeline_stages_base.PipelineStage):
            def _run_op(self, op):
                pass

        next = NextStageForTest()
        root = (
            pipeline_stages_base.PipelineRootStage(config.IoTHubPipelineConfig())
            .append_stage(stage)
            .append_stage(next)
        )

        mocker.spy(stage, "_run_op")
        mocker.spy(stage, "run_op")

        mocker.spy(next, "_run_op")
        mocker.spy(next, "run_op")

        return root

    @pytest.fixture
    def stage(self, mocker):
        stage = pipeline_stages_iothub_mqtt.IoTHubMQTTTranslationStage()
        mocker.spy(stage, "send_op_down")
        return stage

    @pytest.fixture
    def stage_configured_for_device(
        self, stage, stage_base_configuration, set_connection_args_for_device, mocker
    ):
        set_connection_args_for_device.callback = None
        stage.run_op(set_connection_args_for_device)
        mocker.resetall()

    @pytest.fixture
    def stage_configured_for_module(
        self, stage, stage_base_configuration, set_connection_args_for_module, mocker
    ):
        set_connection_args_for_module.callback = None
        stage.run_op(set_connection_args_for_module)
        mocker.resetall()

    @pytest.fixture(params=["device", "module"])
    def stages_configured_for_both(
        self, request, stage, stage_base_configuration, set_connection_args, mocker
    ):
        set_connection_args.callback = None
        if request.param == "module":
            set_connection_args.module_id = fake_module_id
        stage.run_op(set_connection_args)
        mocker.resetall()


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .run_op() -- called with SetIoTHubConnectionArgsOperation"
)
class TestIoTHubMQTTConverterWithSetAuthProviderArgs(IoTHubMQTTTranslationStageTestBase):
    @pytest.mark.it(
        "Runs a pipeline_ops_mqtt.SetMQTTConnectionArgsOperation worker operation on the next stage"
    )
    def test_runs_set_connection_args(self, mocker, stage, set_connection_args):
        set_connection_args.spawn_worker_op = mocker.MagicMock()
        stage.run_op(set_connection_args)
        assert set_connection_args.spawn_worker_op.call_count == 1
        assert (
            set_connection_args.spawn_worker_op.call_args[1]["worker_op_type"]
            is pipeline_ops_mqtt.SetMQTTConnectionArgsOperation
        )
        worker = set_connection_args.spawn_worker_op.return_value
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(worker)

    @pytest.mark.it(
        "Sets connection_args.client_id to auth_provider_args.device_id if auth_provider_args.module_id is None"
    )
    def test_sets_client_id_for_devices(self, stage, set_connection_args):
        stage.run_op(set_connection_args)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.client_id == fake_device_id

    @pytest.mark.it(
        "Sets connection_args.client_id to auth_provider_args.device_id/auth_provider_args.module_id if auth_provider_args.module_id is not None"
    )
    def test_sets_client_id_for_modules(self, stage, set_connection_args_for_module):
        stage.run_op(set_connection_args_for_module)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.client_id == "{}/{}".format(fake_device_id, fake_module_id)

    @pytest.mark.it(
        "Sets connection_args.hostname to auth_provider.hostname if auth_provider.gateway_hostname is None"
    )
    def test_sets_hostname_if_no_gateway(self, stage, set_connection_args):
        stage.run_op(set_connection_args)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.hostname == fake_hostname

    @pytest.mark.it(
        "Sets connection_args.hostname to auth_provider.gateway_hostname if auth_provider.gateway_hostname is not None"
    )
    def test_sets_hostname_if_yes_gateway(self, stage, set_connection_args):
        set_connection_args.gateway_hostname = fake_gateway_hostname
        stage.run_op(set_connection_args)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.hostname == fake_gateway_hostname

    @pytest.mark.it(
        "Sets connection_args.username to auth_provider.hostname/auth_provider/device_id/?api-version={api_version}&DeviceClientType={user_agent} if auth_provider_args.gateway_hostname is None and module_id is None"
    )
    def test_sets_device_username_if_no_gateway(self, stage, set_connection_args):
        stage.run_op(set_connection_args)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.username == "{}/{}/?api-version={}&DeviceClientType={}".format(
            fake_hostname, fake_device_id, pkg_constant.IOTHUB_API_VERSION, encoded_user_agent
        )

    @pytest.mark.it(
        "Sets connection_args.username to auth_provider.hostname/device_id/?api-version={api_version}&DeviceClientType={user_agent} if auth_provider_args.gateway_hostname is not None and module_id is None"
    )
    def test_sets_device_username_if_yes_gateway(self, stage, set_connection_args):
        set_connection_args.gateway_hostname = fake_gateway_hostname
        stage.run_op(set_connection_args)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.username == "{}/{}/?api-version={}&DeviceClientType={}".format(
            fake_hostname, fake_device_id, pkg_constant.IOTHUB_API_VERSION, encoded_user_agent
        )

    @pytest.mark.it(
        "Sets connection_args.username to auth_provider.hostname/auth_provider/device_id/?api-version={api_version}&DeviceClientType={user_agent} if auth_provider_args.gateway_hostname is None and module_id is None"
    )
    def test_sets_module_username_if_no_gateway(self, stage, set_connection_args_for_module):
        stage.run_op(set_connection_args_for_module)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.username == "{}/{}/{}/?api-version={}&DeviceClientType={}".format(
            fake_hostname,
            fake_device_id,
            fake_module_id,
            pkg_constant.IOTHUB_API_VERSION,
            encoded_user_agent,
        )

    @pytest.mark.it(
        "Sets connection_args.username to auth_provider.hostname/device_id/module_id/?api-version={api_version}&DeviceClientType={user_agent} if auth_provider_args.gateway_hostname is not None and module_id is None"
    )
    def test_sets_module_username_if_yes_gateway(self, stage, set_connection_args_for_module):
        set_connection_args_for_module.gateway_hostname = fake_gateway_hostname
        stage.run_op(set_connection_args_for_module)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.username == "{}/{}/{}/?api-version={}&DeviceClientType={}".format(
            fake_hostname,
            fake_device_id,
            fake_module_id,
            pkg_constant.IOTHUB_API_VERSION,
            encoded_user_agent,
        )

    @pytest.mark.it(
        "Appends product_info to connection_args.username to if self.pipeline_root.pipeline_configuration.product_info is not None"
    )
    @pytest.mark.parametrize(
        "fake_product_info, expected_product_info",
        [
            ("", ""),
            ("__fake:product:info__", "__fake%3Aproduct%3Ainfo__"),
            (4, 4),
            (
                ["fee,fi,fo,fum"],
                "%5B%27fee%2Cfi%2Cfo%2Cfum%27%5D",
            ),  # URI Encoding for str version of list
            (
                {"fake_key": "fake_value"},
                "%7B%27fake_key%27%3A%20%27fake_value%27%7D",
            ),  # URI Encoding for str version of dict
        ],
    )
    def test_appends_product_info_to_device_username(
        self, stage, set_connection_args, fake_product_info, expected_product_info
    ):
        set_connection_args.gateway_hostname = fake_gateway_hostname
        stage.pipeline_root.pipeline_configuration.product_info = fake_product_info
        stage.run_op(set_connection_args)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.username == "{}/{}/?api-version={}&DeviceClientType={}{}".format(
            fake_hostname,
            fake_device_id,
            pkg_constant.IOTHUB_API_VERSION,
            encoded_user_agent,
            expected_product_info,
        )

    @pytest.mark.it(
        "Sets connection_args.server_verification_cert to auth_provider.server_verification_cert"
    )
    def test_sets_server_verification_cert(self, stage, set_connection_args):
        set_connection_args.server_verification_cert = fake_server_verification_cert
        stage.run_op(set_connection_args)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.server_verification_cert == fake_server_verification_cert

    @pytest.mark.it("Sets connection_args.client_cert to auth_provider.client_cert")
    def test_sets_client_cert(self, stage, set_connection_args):
        set_connection_args.client_cert = fake_client_cert
        stage.run_op(set_connection_args)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.client_cert == fake_client_cert

    @pytest.mark.it("Sets connection_args.sas_token to auth_provider.sas_token.")
    def test_sets_sas_token(self, stage, set_connection_args):
        set_connection_args.sas_token = fake_sas_token
        stage.run_op(set_connection_args)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.sas_token == fake_sas_token


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .run_op() -- called with UpdateSasTokenOperation if the transport is disconnected"
)
class TestIoTHubMQTTConverterWithUpdateSasTokenOperationDisconnected(
    IoTHubMQTTTranslationStageTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.UpdateSasTokenOperation(
            sas_token=fake_sas_token, callback=mocker.MagicMock()
        )

    @pytest.fixture(autouse=True)
    def transport_is_disconnected(self, stage):
        stage.pipeline_root.connected = False

    @pytest.mark.it("Immediately passes the operation to the next stage")
    def test_passes_op_immediately(self, stage, op):
        stage.run_op(op)
        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args[0][0] == op


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .run_op() -- called with UpdateSasTokenOperation if the transport is connected"
)
class TestIoTHubMQTTConverterWithUpdateSasTokenOperationConnected(
    IoTHubMQTTTranslationStageTestBase
):
    @pytest.fixture
    def op(self, mocker):
        op = pipeline_ops_base.UpdateSasTokenOperation(
            sas_token=fake_sas_token, callback=mocker.MagicMock()
        )
        mocker.spy(op, "complete")
        return op

    @pytest.fixture(autouse=True)
    def transport_is_connected(self, stage):
        stage.pipeline_root.connected = True

    @pytest.mark.it("Immediately passes the operation to the next stage")
    def test_passes_op_immediately(self, stage, op):
        stage.run_op(op)
        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args[0][0] == op

    @pytest.mark.it(
        "Passes down a ReauthorizeConnectionOperation instead of completing the op with success after the lower level stage returns success for the UpdateSasTokenOperation"
    )
    def test_passes_down_reauthorize_connection(self, stage, op, mocker):
        def run_op(op):
            print("in run_op {}".format(op.__class__.__name__))
            if isinstance(op, pipeline_ops_base.UpdateSasTokenOperation):
                op.complete(error=None)
            else:
                pass

        stage.next.run_op = mocker.MagicMock(side_effect=run_op)
        stage.run_op(op)

        assert stage.next.run_op.call_count == 2
        assert stage.next.run_op.call_args_list[0][0][0] == op
        assert isinstance(
            stage.next.run_op.call_args_list[1][0][0],
            pipeline_ops_base.ReauthorizeConnectionOperation,
        )
        # CT-TODO: Make this test clearer - this below assertion is a bit confusing
        # What is happening here is that the run_op defined above for the mock only completes
        # ops of type UpdateSasTokenOperation (i.e. variable 'op'). However, completing the
        # op triggers a callback which halts the completion, and then spawn a reauthorize_connection worker op,
        # which must be completed before full completion of 'op' can occur. However, as the above
        # run_op mock only completes ops of type UpdateSasTokenOperation, this never happens,
        # thus op is not completed.
        assert not op.completed

    # CT-TODO: remove this once able. This test does not have a high degree of accuracy, and its contents
    # could be tested better once stage tests are restructured. This test is overlapping with tests of
    # worker op functionality, that should not be being tested at this granularity here.
    @pytest.mark.it(
        "Completes the op with success if some lower level stage returns success for the ReauthorizeConnectionOperation"
    )
    def test_reauthorize_connection_succeeds(self, mocker, stage, next_stage_succeeds, op):
        # default is for stage.next.run_op to return success for all ops
        stage.run_op(op)

        assert stage.next.run_op.call_count == 2
        assert stage.next.run_op.call_args_list[0][0][0] == op
        assert isinstance(
            stage.next.run_op.call_args_list[1][0][0],
            pipeline_ops_base.ReauthorizeConnectionOperation,
        )
        assert op.completed
        assert op.complete.call_count == 2  # op was completed twice due to an uncompletion

        # most recent call, i.e. one triggered by the successful reauthorize_connection
        assert op.complete.call_args == mocker.call(error=None)

    # CT-TODO: As above, remove/restructure ASAP
    @pytest.mark.it(
        "Completes the op with failure if some lower level stage returns failure for the ReauthorizeConnectionOperation"
    )
    def test_reauthorize_connection_fails(self, stage, op, mocker, arbitrary_exception):
        cb = op.callback_stack[0]

        def run_op(op):
            print("in run_op {}".format(op.__class__.__name__))
            if isinstance(op, pipeline_ops_base.UpdateSasTokenOperation):
                op.complete(error=None)
            elif isinstance(op, pipeline_ops_base.ReauthorizeConnectionOperation):
                op.complete(error=arbitrary_exception)
            else:
                pass

        stage.next.run_op = mocker.MagicMock(side_effect=run_op)
        stage.run_op(op)

        assert stage.next.run_op.call_count == 2
        assert stage.next.run_op.call_args_list[0][0][0] == op
        assert isinstance(
            stage.next.run_op.call_args_list[1][0][0],
            pipeline_ops_base.ReauthorizeConnectionOperation,
        )
        assert cb.call_count == 1
        assert cb.call_args == mocker.call(op=op, error=arbitrary_exception)


basic_ops = [
    {
        "op_class": pipeline_ops_iothub.SendD2CMessageOperation,
        "op_init_kwargs": {"message": fake_message, "callback": None},
        "new_op_class": pipeline_ops_mqtt.MQTTPublishOperation,
    },
    {
        "op_class": pipeline_ops_iothub.SendOutputEventOperation,
        "op_init_kwargs": {"message": fake_message, "callback": None},
        "new_op_class": pipeline_ops_mqtt.MQTTPublishOperation,
    },
    {
        "op_class": pipeline_ops_iothub.SendMethodResponseOperation,
        "op_init_kwargs": {"method_response": fake_method_response, "callback": None},
        "new_op_class": pipeline_ops_mqtt.MQTTPublishOperation,
    },
    {
        "op_class": pipeline_ops_base.EnableFeatureOperation,
        "op_init_kwargs": {"feature_name": constant.C2D_MSG, "callback": None},
        "new_op_class": pipeline_ops_mqtt.MQTTSubscribeOperation,
    },
    {
        "op_class": pipeline_ops_base.DisableFeatureOperation,
        "op_init_kwargs": {"feature_name": constant.C2D_MSG, "callback": None},
        "new_op_class": pipeline_ops_mqtt.MQTTUnsubscribeOperation,
    },
]


# CT-TODO: simplify this
@pytest.mark.parametrize(
    "params",
    basic_ops,
    ids=["{}->{}".format(x["op_class"].__name__, x["new_op_class"].__name__) for x in basic_ops],
)
@pytest.mark.describe("IoTHubMQTTTranslationStage - .run_op() -- called with basic MQTT operations")
class TestIoTHubMQTTConverterBasicOperations(IoTHubMQTTTranslationStageTestBase):
    @pytest.fixture
    def op(self, params, mocker):
        op = params["op_class"](**params["op_init_kwargs"])
        mocker.spy(op, "spawn_worker_op")
        return op

    @pytest.mark.it("Runs a worker operation on the next stage")
    def test_spawn_worker_op(self, params, stage, stages_configured_for_both, op):
        stage.run_op(op)

        assert op.spawn_worker_op.call_count == 1
        assert op.spawn_worker_op.call_args[1]["worker_op_type"] is params["new_op_class"]
        new_op = stage.next._run_op.call_args[0][0]
        assert isinstance(new_op, params["new_op_class"])


publish_ops = [
    {
        "name": "send telemetry",
        "stage_type": "device",
        "op_class": pipeline_ops_iothub.SendD2CMessageOperation,
        "op_init_kwargs": {"message": Message(fake_message_body), "callback": None},
        "topic": "devices/{}/messages/events/".format(fake_device_id),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send telemetry with content type and content encoding",
        "stage_type": "device",
        "op_class": pipeline_ops_iothub.SendD2CMessageOperation,
        "op_init_kwargs": {
            "message": Message(
                fake_message_body,
                content_type=fake_content_type,
                content_encoding=fake_content_encoding,
            ),
            "callback": None,
        },
        "topic": "devices/{}/messages/events/{}&{}".format(
            fake_device_id, fake_content_type_encoded, fake_content_encoding_encoded
        ),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send telemetry overriding only the content type",
        "stage_type": "device",
        "op_class": pipeline_ops_iothub.SendD2CMessageOperation,
        "op_init_kwargs": {
            "message": Message(fake_message_body, content_type=fake_content_type),
            "callback": None,
        },
        "topic": "devices/{}/messages/events/{}".format(fake_device_id, fake_content_type_encoded),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send telemetry with single system property",
        "stage_type": "device",
        "op_class": pipeline_ops_iothub.SendD2CMessageOperation,
        "op_init_kwargs": {
            "message": Message(fake_message_body, output_name=fake_output_name),
            "callback": None,
        },
        "topic": "devices/{}/messages/events/{}".format(fake_device_id, fake_output_name_encoded),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send security message",
        "stage_type": "device",
        "op_class": pipeline_ops_iothub.SendD2CMessageOperation,
        "op_init_kwargs": {"message": create_security_message(fake_message_body), "callback": None},
        "topic": "devices/{}/messages/events/{}".format(
            fake_device_id, security_message_interface_id_encoded
        ),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send telemetry with multiple system properties",
        "stage_type": "device",
        "op_class": pipeline_ops_iothub.SendD2CMessageOperation,
        "op_init_kwargs": {
            "message": Message(
                fake_message_body, message_id=fake_message_id, output_name=fake_output_name
            ),
            "callback": None,
        },
        "topic": "devices/{}/messages/events/{}&{}".format(
            fake_device_id, fake_output_name_encoded, fake_message_id_encoded
        ),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send telemetry with only single user property",
        "stage_type": "device",
        "op_class": pipeline_ops_iothub.SendD2CMessageOperation,
        "op_init_kwargs": {
            "message": create_message_with_user_properties(fake_message_body, is_multiple=False),
            "callback": None,
        },
        "topic": "devices/{}/messages/events/{}".format(
            fake_device_id, fake_message_user_property_1_encoded
        ),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send telemetry with only multiple user properties",
        "stage_type": "device",
        "op_class": pipeline_ops_iothub.SendD2CMessageOperation,
        "op_init_kwargs": {
            "message": create_message_with_user_properties(fake_message_body, is_multiple=True),
            "callback": None,
        },
        # For more than 1 user property the order could be different, creating 2 different topics
        "topic1": "devices/{}/messages/events/{}&{}".format(
            fake_device_id,
            fake_message_user_property_1_encoded,
            fake_message_user_property_2_encoded,
        ),
        "topic2": "devices/{}/messages/events/{}&{}".format(
            fake_device_id,
            fake_message_user_property_2_encoded,
            fake_message_user_property_1_encoded,
        ),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send telemetry with 1 system and 1 user property",
        "stage_type": "device",
        "op_class": pipeline_ops_iothub.SendD2CMessageOperation,
        "op_init_kwargs": {
            "message": create_message_with_system_and_user_properties(
                fake_message_body, is_multiple=False
            ),
            "callback": None,
        },
        "topic": "devices/{}/messages/events/{}&{}".format(
            fake_device_id, fake_message_id_encoded, fake_message_user_property_1_encoded
        ),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send telemetry with multiple system and multiple user properties",
        "stage_type": "device",
        "op_class": pipeline_ops_iothub.SendD2CMessageOperation,
        "op_init_kwargs": {
            "message": create_message_with_system_and_user_properties(
                fake_message_body, is_multiple=True
            ),
            "callback": None,
        },
        # For more than 1 user property the order could be different, creating 2 different topics
        "topic1": "devices/{}/messages/events/{}&{}&{}&{}".format(
            fake_device_id,
            fake_output_name_encoded,
            fake_message_id_encoded,
            fake_message_user_property_1_encoded,
            fake_message_user_property_2_encoded,
        ),
        "topic2": "devices/{}/messages/events/{}&{}&{}&{}".format(
            fake_device_id,
            fake_output_name_encoded,
            fake_message_id_encoded,
            fake_message_user_property_2_encoded,
            fake_message_user_property_1_encoded,
        ),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send security message with multiple system and multiple user properties",
        "stage_type": "device",
        "op_class": pipeline_ops_iothub.SendD2CMessageOperation,
        "op_init_kwargs": {
            "message": create_security_message_with_system_and_user_properties(
                fake_message_body, is_multiple=True
            ),
            "callback": None,
        },
        # For more than 1 user property the order could be different, creating 2 different topics
        "topic1": "devices/{}/messages/events/{}&{}&{}&{}&{}".format(
            fake_device_id,
            fake_output_name_encoded,
            fake_message_id_encoded,
            security_message_interface_id_encoded,
            fake_message_user_property_1_encoded,
            fake_message_user_property_2_encoded,
        ),
        "topic2": "devices/{}/messages/events/{}&{}&{}&{}&{}".format(
            fake_device_id,
            fake_output_name_encoded,
            fake_message_id_encoded,
            security_message_interface_id_encoded,
            fake_message_user_property_2_encoded,
            fake_message_user_property_1_encoded,
        ),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send output",
        "stage_type": "module",
        "op_class": pipeline_ops_iothub.SendOutputEventOperation,
        "op_init_kwargs": {
            "message": Message(fake_message_body, output_name=fake_output_name),
            "callback": None,
        },
        "topic": "devices/{}/modules/{}/messages/events/%24.on={}".format(
            fake_device_id, fake_module_id, fake_output_name
        ),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send output with content type and content encoding",
        "stage_type": "module",
        "op_class": pipeline_ops_iothub.SendOutputEventOperation,
        "op_init_kwargs": {
            "message": Message(
                fake_message_body,
                output_name=fake_output_name,
                content_type=fake_content_type,
                content_encoding=fake_content_encoding,
            ),
            "callback": None,
        },
        "topic": "devices/{}/modules/{}/messages/events/%24.on={}&{}&{}".format(
            fake_device_id,
            fake_module_id,
            fake_output_name,
            fake_content_type_encoded,
            fake_content_encoding_encoded,
        ),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send output with system properties",
        "stage_type": "module",
        "op_class": pipeline_ops_iothub.SendOutputEventOperation,
        "op_init_kwargs": {
            "message": Message(
                fake_message_body, message_id=fake_message_id, output_name=fake_output_name
            ),
            "callback": None,
        },
        "topic": "devices/{}/modules/{}/messages/events/%24.on={}&{}".format(
            fake_device_id, fake_module_id, fake_output_name, fake_message_id_encoded
        ),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send output with only 1 user property",
        "stage_type": "module",
        "op_class": pipeline_ops_iothub.SendOutputEventOperation,
        "op_init_kwargs": {
            "message": create_message_for_output_with_user_properties(
                fake_message_body, is_multiple=False
            ),
            "callback": None,
        },
        "topic": "devices/{}/modules/{}/messages/events/%24.on={}&{}".format(
            fake_device_id, fake_module_id, fake_output_name, fake_message_user_property_1_encoded
        ),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send output with only multiple user properties",
        "stage_type": "module",
        "op_class": pipeline_ops_iothub.SendOutputEventOperation,
        "op_init_kwargs": {
            "message": create_message_for_output_with_user_properties(
                fake_message_body, is_multiple=True
            ),
            "callback": None,
        },
        "topic1": "devices/{}/modules/{}/messages/events/%24.on={}&{}&{}".format(
            fake_device_id,
            fake_module_id,
            fake_output_name,
            fake_message_user_property_1_encoded,
            fake_message_user_property_2_encoded,
        ),
        "topic2": "devices/{}/modules/{}/messages/events/%24.on={}&{}&{}".format(
            fake_device_id,
            fake_module_id,
            fake_output_name,
            fake_message_user_property_2_encoded,
            fake_message_user_property_1_encoded,
        ),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send output with 1 system and 1 user property",
        "stage_type": "module",
        "op_class": pipeline_ops_iothub.SendOutputEventOperation,
        "op_init_kwargs": {
            "message": create_message_for_output_with_system_and_user_properties(
                fake_message_body, is_multiple=False
            ),
            "callback": None,
        },
        "topic": "devices/{}/modules/{}/messages/events/%24.on={}&{}&{}".format(
            fake_device_id,
            fake_module_id,
            fake_output_name,
            fake_message_id_encoded,
            fake_message_user_property_1_encoded,
        ),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send method result",
        "stage_type": "both",
        "op_class": pipeline_ops_iothub.SendMethodResponseOperation,
        "op_init_kwargs": {"method_response": fake_method_response, "callback": None},
        "topic": "$iothub/methods/res/__fake_method_status__/?$rid=__fake_request_id__",
        "publish_payload": json.dumps(fake_method_payload),
    },
]


@pytest.mark.parametrize("params", publish_ops, ids=[x["name"] for x in publish_ops])
@pytest.mark.describe("IoTHubMQTTTranslationStage - .run_op() -- called with publish operations")
class TestIoTHubMQTTConverterForPublishOps(IoTHubMQTTTranslationStageTestBase):
    @pytest.fixture
    def op(self, params, mocker):
        op = params["op_class"](**params["op_init_kwargs"])
        op.callback = mocker.MagicMock()
        return op

    @pytest.mark.it("Uses the correct topic and encodes message properties string when publishing")
    def test_uses_device_topic_for_devices(self, stage, stages_configured_for_both, params, op):
        if params["stage_type"] == "device" and stage.module_id:
            pytest.skip()
        elif params["stage_type"] == "module" and not stage.module_id:
            pytest.skip()
        stage.run_op(op)
        new_op = stage.next._run_op.call_args[0][0]
        if "multiple user properties" in params["name"]:
            assert new_op.topic == params["topic1"] or new_op.topic == params["topic2"]
        else:
            assert new_op.topic == params["topic"]

    @pytest.mark.it("Sends the body in the payload of the MQTT publish operation")
    def test_sends_correct_body(self, stage, stages_configured_for_both, params, op):
        stage.run_op(op)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.payload == params["publish_payload"]


feature_name_to_subscribe_topic = [
    {
        "stage_type": "device",
        "feature_name": constant.C2D_MSG,
        "topic": "devices/{}/messages/devicebound/#".format(fake_device_id),
    },
    {
        "stage_type": "module",
        "feature_name": constant.INPUT_MSG,
        "topic": "devices/{}/modules/{}/inputs/#".format(fake_device_id, fake_module_id),
    },
    {"stage_type": "both", "feature_name": constant.METHODS, "topic": "$iothub/methods/POST/#"},
]

sub_unsub_operations = [
    {
        "op_class": pipeline_ops_base.EnableFeatureOperation,
        "new_op": pipeline_ops_mqtt.MQTTSubscribeOperation,
    },
    {
        "op_class": pipeline_ops_base.DisableFeatureOperation,
        "new_op": pipeline_ops_mqtt.MQTTUnsubscribeOperation,
    },
]


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .run_op() -- called with EnableFeature or DisableFeature"
)
class TestIoTHubMQTTConverterWithEnableFeature(IoTHubMQTTTranslationStageTestBase):
    @pytest.mark.parametrize(
        "topic_parameters",
        feature_name_to_subscribe_topic,
        ids=[
            "{} {}".format(x["stage_type"], x["feature_name"])
            for x in feature_name_to_subscribe_topic
        ],
    )
    @pytest.mark.parametrize(
        "op_parameters",
        sub_unsub_operations,
        ids=[x["op_class"].__name__ for x in sub_unsub_operations],
    )
    @pytest.mark.it("Converts the feature_name to the correct topic")
    def test_converts_feature_name_to_topic(
        self, mocker, stage, stages_configured_for_both, topic_parameters, op_parameters
    ):
        if topic_parameters["stage_type"] == "device" and stage.module_id:
            pytest.skip()
        elif topic_parameters["stage_type"] == "module" and not stage.module_id:
            pytest.skip()
        stage.next._run_op = mocker.Mock()
        op = op_parameters["op_class"](
            feature_name=topic_parameters["feature_name"], callback=mocker.MagicMock()
        )
        stage.run_op(op)
        new_op = stage.next._run_op.call_args[0][0]
        assert isinstance(new_op, op_parameters["new_op"])
        assert new_op.topic == topic_parameters["topic"]

    @pytest.mark.it("Fails on an invalid feature_name")
    @pytest.mark.parametrize(
        "op_parameters",
        sub_unsub_operations,
        ids=[x["op_class"].__name__ for x in sub_unsub_operations],
    )
    def test_fails_on_invalid_feature_name(
        self, mocker, stage, stages_configured_for_both, op_parameters
    ):
        op = op_parameters["op_class"](
            feature_name=invalid_feature_name, callback=mocker.MagicMock()
        )
        mocker.spy(op, "complete")
        stage.run_op(op)
        assert op.complete.call_count == 1
        assert isinstance(op.complete.call_args[1]["error"], KeyError)
        # assert_callback_failed(op=op, error=KeyError)


@pytest.fixture
def add_pipeline_root(stage, mocker):
    root = pipeline_stages_base.PipelineRootStage(mocker.MagicMock())
    mocker.spy(root, "handle_pipeline_event")
    stage.previous = root
    stage.pipeline_root = root


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .handle_pipeline_event() -- called with unmatched topic"
)
class TestIoTHubMQTTConverterHandlePipelineEvent(IoTHubMQTTTranslationStageTestBase):
    @pytest.mark.it("Passes up any mqtt messages with topics that aren't matched by this stage")
    def test_passes_up_mqtt_message_with_unknown_topic(
        self, stage, stages_configured_for_both, add_pipeline_root, mocker
    ):
        event = pipeline_events_mqtt.IncomingMQTTMessageEvent(
            topic=unmatched_mqtt_topic, payload=fake_mqtt_payload
        )
        stage.handle_pipeline_event(event)
        assert stage.previous.handle_pipeline_event.call_count == 1
        assert stage.previous.handle_pipeline_event.call_args == mocker.call(event)


@pytest.fixture
def c2d_event():
    return pipeline_events_mqtt.IncomingMQTTMessageEvent(
        topic=fake_c2d_topic, payload=fake_mqtt_payload
    )


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .handle_pipeline_event() -- called with C2D topic"
)
class TestIoTHubMQTTConverterHandlePipelineEventC2D(IoTHubMQTTTranslationStageTestBase):
    @pytest.mark.it(
        "Converts mqtt message with topic devices/device_id/message/devicebound/ to c2d event"
    )
    def test_converts_c2d_topic_to_c2d_events(
        self, mocker, stage, stage_configured_for_device, add_pipeline_root, c2d_event
    ):
        stage.handle_pipeline_event(c2d_event)
        assert stage.previous.handle_pipeline_event.call_count == 1
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(new_event, pipeline_events_iothub.C2DMessageEvent)

    @pytest.mark.it("Convers the mqtt payload of a c2d message into a Message object")
    def test_creates_message_object_for_c2d_event(
        self, mocker, stage, stage_configured_for_device, add_pipeline_root, c2d_event
    ):
        stage.handle_pipeline_event(c2d_event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(new_event.message, Message)

    @pytest.mark.it("Extracts message properties from the mqtt topic for c2d messages")
    def test_extracts_c2d_message_properties_from_topic_name(
        self, mocker, stage, stage_configured_for_device, add_pipeline_root
    ):
        event = pipeline_events_mqtt.IncomingMQTTMessageEvent(
            topic=fake_c2d_topic_with_content_type, payload=fake_mqtt_payload
        )
        stage.handle_pipeline_event(event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert new_event.message.content_type == fake_content_type

    @pytest.mark.it("Passes up c2d messages destined for another device")
    def test_if_topic_is_c2d_for_another_device(
        self, mocker, stage, stage_configured_for_device, add_pipeline_root
    ):
        event = pipeline_events_mqtt.IncomingMQTTMessageEvent(
            topic=fake_c2d_topic_for_another_device, payload=fake_mqtt_payload
        )
        stage.handle_pipeline_event(event)
        assert stage.previous.handle_pipeline_event.call_count == 1
        assert stage.previous.handle_pipeline_event.call_args == mocker.call(event)


@pytest.mark.describe("IotHubMQTTConverter - .run_op() -- called with RequestOperation")
class TestIotHubMQTTConverterWithSendIotRequest(IoTHubMQTTTranslationStageTestBase):
    @pytest.fixture
    def fake_request_type(self):
        return "twin"

    @pytest.fixture
    def fake_method(self):
        return "__fake_method__"

    @pytest.fixture
    def fake_resource_location(self):
        return "__fake_resource_location__"

    @pytest.fixture
    def fake_request_body(self):
        return "__fake_request_body__"

    @pytest.fixture
    def fake_request_body_as_string(self, fake_request_body):
        return json.dumps(fake_request_body)

    @pytest.fixture
    def fake_request_id(self):
        return "__fake_request_id__"

    @pytest.fixture
    def op(
        self,
        fake_request_type,
        fake_method,
        fake_resource_location,
        fake_request_body,
        fake_request_id,
        mocker,
    ):
        op = pipeline_ops_base.RequestOperation(
            request_type=fake_request_type,
            method=fake_method,
            resource_location=fake_resource_location,
            request_body=fake_request_body,
            request_id=fake_request_id,
            callback=mocker.MagicMock(),
        )
        mocker.spy(op, "complete")
        mocker.spy(op, "spawn_worker_op")
        return op

    @pytest.mark.it("calls the op callback with an OperationError if request_type is not 'twin'")
    def test_sends_bad_request_type(self, stage, op):
        op.request_type = "not_twin"
        stage.run_op(op)
        assert op.complete.call_count == 1
        assert isinstance(op.complete.call_args[1]["error"], OperationError)

    @pytest.mark.it(
        "Runs an MQTTPublishOperation as a worker op on the next stage with the topic formated as '$iothub/twin/{method}{resource_location}?$rid={request_id}' and the payload as the request_body"
    )
    def test_sends_new_operation(
        self, stage, op, fake_method, fake_resource_location, fake_request_id, fake_request_body
    ):
        stage.run_op(op)
        assert op.spawn_worker_op.call_count == 1
        assert (
            op.spawn_worker_op.call_args[1]["worker_op_type"]
            is pipeline_ops_mqtt.MQTTPublishOperation
        )
        assert stage.next.run_op.call_count == 1
        worker_op = stage.next.run_op.call_args[0][0]
        assert isinstance(worker_op, pipeline_ops_mqtt.MQTTPublishOperation)
        assert (
            worker_op.topic
            == "$iothub/twin/{method}{resource_location}?$rid={request_id}".format(
                method=fake_method,
                resource_location=fake_resource_location,
                request_id=fake_request_id,
            )
        )
        assert worker_op.payload == fake_request_body


@pytest.fixture
def input_message_event():
    return pipeline_events_mqtt.IncomingMQTTMessageEvent(
        topic=fake_input_message_topic, payload=fake_mqtt_payload
    )


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .handle_pipeline_event() -- called with input message topic"
)
class TestIoTHubMQTTConverterHandlePipelineEventInputMessages(IoTHubMQTTTranslationStageTestBase):
    @pytest.mark.it(
        "Converts mqtt message with topic devices/device_id/modules/module_id/inputs/input_name/ to input event"
    )
    def test_converts_input_topic_to_input_event(
        self, mocker, stage, stage_configured_for_module, add_pipeline_root, input_message_event
    ):
        stage.handle_pipeline_event(input_message_event)
        assert stage.previous.handle_pipeline_event.call_count == 1
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(new_event, pipeline_events_iothub.InputMessageEvent)

    @pytest.mark.it("Converts the mqtt payload of an input message into a Message object")
    def test_creates_message_object_for_input_event(
        self, mocker, stage, stage_configured_for_module, add_pipeline_root, input_message_event
    ):
        stage.handle_pipeline_event(input_message_event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(new_event.message, Message)

    @pytest.mark.it("Extracts the input name of an input message from the mqtt topic")
    def test_extracts_input_name_from_topic(
        self, mocker, stage, stage_configured_for_module, add_pipeline_root, input_message_event
    ):
        stage.handle_pipeline_event(input_message_event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert new_event.input_name == fake_input_name

    @pytest.mark.it("Extracts message properties from the mqtt topic for input messages")
    def test_extracts_input_message_properties_from_topic_name(
        self, mocker, stage, stage_configured_for_module, add_pipeline_root
    ):
        event = pipeline_events_mqtt.IncomingMQTTMessageEvent(
            topic=fake_input_message_topic_with_content_type, payload=fake_mqtt_payload
        )
        stage.handle_pipeline_event(event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert new_event.message.content_type == fake_content_type

    @pytest.mark.parametrize(
        "topic",
        [fake_input_message_topic_for_another_device, fake_input_message_topic_for_another_module],
        ids=["different device_id", "same device_id"],
    )
    @pytest.mark.it("Passes up input messages destined for another module")
    def test_if_topic_is_input_message_for_another_module(
        self, mocker, stage, stage_configured_for_module, add_pipeline_root, topic
    ):
        event = pipeline_events_mqtt.IncomingMQTTMessageEvent(
            topic=topic, payload=fake_mqtt_payload
        )
        stage.handle_pipeline_event(event)
        assert stage.previous.handle_pipeline_event.call_count == 1
        assert stage.previous.handle_pipeline_event.call_args == mocker.call(event)


@pytest.fixture
def method_request_event():
    return pipeline_events_mqtt.IncomingMQTTMessageEvent(
        topic=fake_method_request_topic, payload=fake_method_request_payload
    )


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .handle_pipeline_event() -- called with method request topic"
)
class TestIoTHubMQTTConverterHandlePipelineEventMethodRequets(IoTHubMQTTTranslationStageTestBase):
    @pytest.mark.it(
        "Converts mqtt messages with topic $iothub/methods/POST/{method name}/?$rid={request id} to method request events"
    )
    def test_converts_method_request_topic_to_method_request_event(
        self, mocker, stage, stages_configured_for_both, add_pipeline_root, method_request_event
    ):
        stage.handle_pipeline_event(method_request_event)
        assert stage.previous.handle_pipeline_event.call_count == 1
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(new_event, pipeline_events_iothub.MethodRequestEvent)

    @pytest.mark.it("Makes a MethodRequest object to hold the method request details")
    def test_passes_method_request_object_in_method_request_event(
        self, mocker, stage, stages_configured_for_both, add_pipeline_root, method_request_event
    ):
        stage.handle_pipeline_event(method_request_event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(new_event.method_request, MethodRequest)

    @pytest.mark.it("Extracts the method name from the mqtt topic")
    def test_extracts_method_name_from_method_request_topic(
        self, mocker, stage, stages_configured_for_both, add_pipeline_root, method_request_event
    ):
        stage.handle_pipeline_event(method_request_event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert new_event.method_request.name == fake_method_name

    @pytest.mark.it("Extracts the request id from the mqtt topic")
    def test_extracts_request_id_from_method_request_topic(
        self, mocker, stage, stages_configured_for_both, add_pipeline_root, method_request_event
    ):
        stage.handle_pipeline_event(method_request_event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert new_event.method_request.request_id == fake_request_id

    @pytest.mark.it(
        "Puts the payload of the mqtt message as the payload of the method requets object"
    )
    def test_puts_mqtt_payload_in_method_request_payload(
        self, mocker, stage, stages_configured_for_both, add_pipeline_root, method_request_event
    ):
        stage.handle_pipeline_event(method_request_event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert new_event.method_request.payload == json.loads(
            fake_method_request_payload.decode("utf-8")
        )


@pytest.mark.describe(
    "IotHubMQTTConverter - .handle_pipeline_event() -- called with twin response topic"
)
class TestIotHubMQTTConverterHandlePipelineEventTwinResponse(IoTHubMQTTTranslationStageTestBase):
    @pytest.fixture
    def fake_request_id(self):
        return "__fake_request_id__"

    @pytest.fixture
    def fake_status_code(self):
        return 200

    @pytest.fixture
    def bad_status_code(self):
        return "__bad_status_code__"

    @pytest.fixture
    def fake_topic_name(self, fake_request_id, fake_status_code):
        return "$iothub/twin/res/{status_code}/?$rid={request_id}".format(
            status_code=fake_status_code, request_id=fake_request_id
        )

    @pytest.fixture
    def fake_topic_name_with_missing_request_id(self, fake_status_code):
        return "$iothub/twin/res/{status_code}".format(status_code=fake_status_code)

    @pytest.fixture
    def fake_topic_name_with_missing_status_code(self, fake_request_id):
        return "$iothub/twin/res/?$rid={request_id}".format(request_id=fake_request_id)

    @pytest.fixture
    def fake_topic_name_with_bad_status_code(self, fake_request_id, bad_status_code):
        return "$iothub/twin/res/{status_code}/?$rid={request_id}".format(
            request_id=fake_request_id, status_code=bad_status_code
        )

    @pytest.fixture
    def fake_payload(self):
        return "__fake_payload__"

    @pytest.fixture
    def fake_event(self, fake_topic_name, fake_payload):
        return pipeline_events_mqtt.IncomingMQTTMessageEvent(
            topic=fake_topic_name, payload=fake_payload
        )

    @pytest.fixture
    def fixup_stage_for_test(self, stage, add_pipeline_root):
        print("Adding module")
        stage.module_id = fake_module_id
        stage.device_id = fake_device_id

    @pytest.mark.it(
        "Calls .handle_pipeline_event() on the previous stage with an ResponseEvent, with request_id and status_code as attributes extracted from the topic and the response_body attirbute set to the payload"
    )
    def test_extracts_request_id_status_code_and_payload(
        self,
        stage,
        fixup_stage_for_test,
        fake_request_id,
        fake_status_code,
        fake_payload,
        fake_event,
    ):
        stage.handle_pipeline_event(event=fake_event)
        assert stage.previous.handle_pipeline_event.call_count == 1
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(new_event, pipeline_events_base.ResponseEvent)
        assert new_event.status_code == fake_status_code
        assert new_event.request_id == fake_request_id
        assert new_event.response_body == fake_payload

    @pytest.mark.it(
        "Calls the unhandled exception handler with a PipelineError if there is no previous stage"
    )
    def test_no_previous_stage(
        self, stage, fixup_stage_for_test, fake_event, unhandled_error_handler
    ):
        stage.previous = None
        stage.handle_pipeline_event(fake_event)
        assert unhandled_error_handler.call_count == 1
        assert isinstance(unhandled_error_handler.call_args[0][0], PipelineError)

    @pytest.mark.it(
        "Calls the unhandled exception handler if the requet_id is missing from the topic name"
    )
    def test_invalid_topic_with_missing_request_id(
        self,
        stage,
        fixup_stage_for_test,
        fake_event,
        fake_topic_name_with_missing_request_id,
        unhandled_error_handler,
    ):
        fake_event.topic = fake_topic_name_with_missing_request_id
        stage.handle_pipeline_event(event=fake_event)
        assert unhandled_error_handler.call_count == 1
        assert isinstance(unhandled_error_handler.call_args[0][0], IndexError)

    @pytest.mark.it(
        "Calls the unhandled exception handler if the status code is missing from the topic name"
    )
    def test_invlid_topic_with_missing_status_code(
        self,
        stage,
        fixup_stage_for_test,
        fake_event,
        fake_topic_name_with_missing_status_code,
        unhandled_error_handler,
    ):
        fake_event.topic = fake_topic_name_with_missing_status_code
        stage.handle_pipeline_event(event=fake_event)
        assert unhandled_error_handler.call_count == 1
        assert isinstance(unhandled_error_handler.call_args[0][0], ValueError)

    @pytest.mark.it(
        "Calls the unhandled exception handler if the status code in the topic name is not numeric"
    )
    def test_invlid_topic_with_bad_status_code(
        self,
        stage,
        fixup_stage_for_test,
        fake_event,
        fake_topic_name_with_bad_status_code,
        unhandled_error_handler,
    ):
        fake_event.topic = fake_topic_name_with_bad_status_code
        stage.handle_pipeline_event(event=fake_event)
        assert unhandled_error_handler.call_count == 1
        assert isinstance(unhandled_error_handler.call_args[0][0], ValueError)


@pytest.mark.describe(
    "IotHubMQTTConverter - .handle_pipeline_event() -- called with twin patch topic"
)
class TestIotHubMQTTConverterHandlePipelineEventTwinPatch(IoTHubMQTTTranslationStageTestBase):
    @pytest.fixture
    def fake_topic_name(self):
        return "$iothub/twin/PATCH/properties/desired"

    @pytest.fixture
    def fake_patch(self):
        return {"__fake_patch__": "yes"}

    @pytest.fixture
    def fake_patch_as_bytes(self, fake_patch):
        return json.dumps(fake_patch).encode("utf-8")

    @pytest.fixture
    def fake_patch_not_bytes(self):
        return "__fake_patch_that_is_not_bytes__"

    @pytest.fixture
    def fake_patch_not_json(self):
        return "__fake_patch_that_is_not_json__".encode("utf-8")

    @pytest.fixture
    def fake_event(self, fake_topic_name, fake_patch_as_bytes):
        return pipeline_events_mqtt.IncomingMQTTMessageEvent(
            topic=fake_topic_name, payload=fake_patch_as_bytes
        )

    @pytest.fixture
    def fixup_stage_for_test(self, stage, add_pipeline_root):
        print("Adding module")
        stage.module_id = fake_module_id
        stage.device_id = fake_device_id

    @pytest.mark.it(
        "Calls .handle_pipeline_event() on the previous stage with an TwinDesiredPropertiesPatchEvent, with the patch set to the payload after decoding and deserializing it"
    )
    def test_calls_previous_stage(self, stage, fixup_stage_for_test, fake_event, fake_patch):
        stage.handle_pipeline_event(fake_event)
        assert stage.previous.handle_pipeline_event.call_count == 1
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(new_event, pipeline_events_iothub.TwinDesiredPropertiesPatchEvent)
        assert new_event.patch == fake_patch

    @pytest.mark.it(
        "Calls the unhandled exception handler with a PipelineError if there is no previous stage"
    )
    def test_no_previous_stage(
        self, stage, fixup_stage_for_test, fake_event, unhandled_error_handler
    ):
        stage.previous = None
        stage.handle_pipeline_event(fake_event)
        assert unhandled_error_handler.call_count == 1
        assert isinstance(unhandled_error_handler.call_args[0][0], PipelineError)

    @pytest.mark.it("Calls the unhandled exception handler if the payload is not a Bytes object")
    def test_payload_not_bytes(
        self, stage, fixup_stage_for_test, fake_event, fake_patch_not_bytes, unhandled_error_handler
    ):
        fake_event.payload = fake_patch_not_bytes
        stage.handle_pipeline_event(fake_event)
        assert unhandled_error_handler.call_count == 1
        if not (
            isinstance(unhandled_error_handler.call_args[0][0], AttributeError)
            or isinstance(unhandled_error_handler.call_args[0][0], ValueError)
        ):
            assert False

    @pytest.mark.it(
        "Calls the unhandled exception handler if the payload cannot be deserialized as a JSON object"
    )
    def test_payload_not_json(
        self, stage, fixup_stage_for_test, fake_event, fake_patch_not_json, unhandled_error_handler
    ):
        fake_event.payload = fake_patch_not_json
        stage.handle_pipeline_event(fake_event)
        assert unhandled_error_handler.call_count == 1
        assert isinstance(unhandled_error_handler.call_args[0][0], ValueError)
