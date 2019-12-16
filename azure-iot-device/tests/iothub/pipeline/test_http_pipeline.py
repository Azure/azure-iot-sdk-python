# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
import six.moves.urllib as urllib
from azure.iot.device.common import handle_exceptions
from azure.iot.device.common.pipeline import (
    pipeline_stages_base,
    pipeline_stages_http,
    pipeline_ops_base,
)
from azure.iot.device.iothub.pipeline import (
    pipeline_stages_iothub,
    pipeline_stages_iothub_http,
    pipeline_ops_iothub,
    pipeline_ops_iothub_http,
)
from azure.iot.device.iothub.pipeline import HTTPPipeline, constant
from azure.iot.device.iothub.auth import (
    SymmetricKeyAuthenticationProvider,
    X509AuthenticationProvider,
)

logging.basicConfig(level=logging.DEBUG)
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")

fake_device_id = "__fake_device_id__"
fake_module_id = "__fake_module_id__"
fake_blob_name = "__fake_blob_name__"


@pytest.fixture
def auth_provider(mocker):
    return mocker.MagicMock()


@pytest.fixture
def pipeline_configuration(mocker):
    mocked_configuration = mocker.MagicMock()
    mocked_configuration.blob_upload = True
    mocked_configuration.method_invoke = True
    return mocked_configuration


@pytest.fixture
def pipeline(mocker, auth_provider, pipeline_configuration):
    pipeline = HTTPPipeline(auth_provider, pipeline_configuration)
    mocker.patch.object(pipeline._pipeline, "run_op")
    return pipeline


@pytest.fixture
def twin_patch():
    return {"key": "value"}


# automatically mock the transport for all tests in this file.
@pytest.fixture(autouse=True)
def mock_transport(mocker):
    print("mocking transport")
    mocker.patch(
        "azure.iot.device.common.pipeline.pipeline_stages_http.HTTPTransport", autospec=True
    )


@pytest.mark.describe("HTTPPipeline - Instantiation")
class TestHTTPPipelineInstantiation(object):
    @pytest.mark.it("Configures the pipeline with a series of PipelineStages")
    def test_pipeline_configuration(self, auth_provider, pipeline_configuration):
        pipeline = HTTPPipeline(auth_provider, pipeline_configuration)
        curr_stage = pipeline._pipeline

        expected_stage_order = [
            pipeline_stages_base.PipelineRootStage,
            pipeline_stages_iothub.UseAuthProviderStage,
            pipeline_stages_iothub_http.IoTHubHTTPTranslationStage,
            pipeline_stages_http.HTTPTransportStage,
        ]

        # Assert that all PipelineStages are there, and they are in the right order
        for i in range(len(expected_stage_order)):
            expected_stage = expected_stage_order[i]
            assert isinstance(curr_stage, expected_stage)
            curr_stage = curr_stage.next

        # Assert there are no more additional stages
        assert curr_stage is None

    # TODO: revist these tests after auth revision
    # They are too tied to auth types (and there's too much variance in auths to effectively test)
    # Ideally HTTPPipeline is entirely insulated from any auth differential logic (and module/device distinctions)
    # In the meantime, we are using a device auth with connection string to stand in for generic SAS auth
    # and device auth with X509 certs to stand in for generic X509 auth
    @pytest.mark.it(
        "Runs a SetAuthProviderOperation with the provided AuthenticationProvider on the pipeline, if using SAS based authentication"
    )
    def test_sas_auth(self, mocker, device_connection_string, pipeline_configuration):
        mocker.spy(pipeline_stages_base.PipelineRootStage, "run_op")
        auth_provider = SymmetricKeyAuthenticationProvider.parse(device_connection_string)
        pipeline = HTTPPipeline(auth_provider, pipeline_configuration)
        op = pipeline._pipeline.run_op.call_args[0][1]
        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(op, pipeline_ops_iothub.SetAuthProviderOperation)
        assert op.auth_provider is auth_provider

    @pytest.mark.it(
        "Raises exceptions that occurred in execution upon unsuccessful completion of the SetAuthProviderOperation"
    )
    def test_sas_auth_op_fail(
        self, mocker, device_connection_string, arbitrary_exception, pipeline_configuration
    ):
        old_run_op = pipeline_stages_base.PipelineRootStage._run_op

        def fail_set_auth_provider(self, op):
            if isinstance(op, pipeline_ops_iothub.SetAuthProviderOperation):
                op.complete(error=arbitrary_exception)
            else:
                old_run_op(self, op)

        mocker.patch.object(
            pipeline_stages_base.PipelineRootStage,
            "_run_op",
            side_effect=fail_set_auth_provider,
            autospec=True,
        )

        auth_provider = SymmetricKeyAuthenticationProvider.parse(device_connection_string)
        with pytest.raises(arbitrary_exception.__class__) as e_info:
            HTTPPipeline(auth_provider, pipeline_configuration)
        assert e_info.value is arbitrary_exception

    @pytest.mark.it(
        "Runs a SetX509AuthProviderOperation with the provided AuthenticationProvider on the pipeline, if using SAS based authentication"
    )
    def test_cert_auth(self, mocker, x509, pipeline_configuration):
        mocker.spy(pipeline_stages_base.PipelineRootStage, "run_op")
        auth_provider = X509AuthenticationProvider(
            hostname="somehostname", device_id=fake_device_id, x509=x509
        )
        pipeline = HTTPPipeline(auth_provider, pipeline_configuration)
        op = pipeline._pipeline.run_op.call_args[0][1]
        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(op, pipeline_ops_iothub.SetX509AuthProviderOperation)
        assert op.auth_provider is auth_provider

    @pytest.mark.it(
        "Raises exceptions that occurred in execution upon unsuccessful completion of the SetX509AuthProviderOperation"
    )
    def test_cert_auth_op_fail(self, mocker, x509, arbitrary_exception, pipeline_configuration):
        old_run_op = pipeline_stages_base.PipelineRootStage._run_op

        def fail_set_auth_provider(self, op):
            if isinstance(op, pipeline_ops_iothub.SetX509AuthProviderOperation):
                op.complete(error=arbitrary_exception)
            else:
                old_run_op(self, op)

        mocker.patch.object(
            pipeline_stages_base.PipelineRootStage,
            "_run_op",
            side_effect=fail_set_auth_provider,
            autospec=True,
        )

        auth_provider = X509AuthenticationProvider(
            hostname="somehostname", device_id=fake_device_id, x509=x509
        )
        with pytest.raises(arbitrary_exception.__class__):
            HTTPPipeline(auth_provider, pipeline_configuration)


@pytest.mark.describe("HTTPPipeline - .invoke_method()")
class TestHTTPPipelineInvokeMethod(object):
    @pytest.mark.it("Runs a MethodInvokeOperation on the pipeline")
    def test_runs_op(self, pipeline, mocker):
        cb = mocker.MagicMock()
        pipeline.invoke_method(
            device_id=fake_device_id,
            module_id=fake_module_id,
            method_params=mocker.MagicMock(),
            callback=cb,
        )
        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(
            pipeline._pipeline.run_op.call_args[0][0],
            pipeline_ops_iothub_http.MethodInvokeOperation,
        )

    @pytest.mark.it(
        "Calls the callback with the error if the pipeline_configuration.method_invoke is not True"
    )
    def test_op_configuration_fail(self, mocker, pipeline, arbitrary_exception):
        pipeline._pipeline.pipeline_configuration.method_invoke = False
        cb = mocker.MagicMock()

        pipeline.invoke_method(
            device_id=fake_device_id,
            module_id=fake_module_id,
            method_params=mocker.MagicMock(),
            callback=cb,
        )

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=mocker.ANY)

    @pytest.mark.it("Passes the correct parameters to the MethodInvokeOperation")
    def test_passes_params_to_op(self, pipeline, mocker):
        cb = mocker.MagicMock()
        mocked_op = mocker.patch.object(pipeline_ops_iothub_http, "MethodInvokeOperation")
        fake_method_params = mocker.MagicMock()
        pipeline.invoke_method(
            device_id=fake_device_id,
            module_id=fake_module_id,
            method_params=fake_method_params,
            callback=cb,
        )

        assert mocked_op.call_args == mocker.call(
            callback=mocker.ANY,
            method_params=fake_method_params,
            target_device_id=fake_device_id,
            target_module_id=fake_module_id,
        )

    @pytest.mark.it("Triggers the callback upon successful completion of the MethodInvokeOperation")
    def test_op_success_with_callback(self, mocker, pipeline):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.invoke_method(
            device_id=fake_device_id,
            module_id=fake_module_id,
            method_params=mocker.MagicMock(),
            callback=cb,
        )
        assert cb.call_count == 0

        # Trigger op completion
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.method_response = "__fake_method_response__"
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(
            error=None, invoke_method_response="__fake_method_response__"
        )

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the MethodInvokeOperation"
    )
    def test_op_fail(self, mocker, pipeline, arbitrary_exception):
        cb = mocker.MagicMock()

        pipeline.invoke_method(
            device_id=fake_device_id,
            module_id=fake_module_id,
            method_params=mocker.MagicMock(),
            callback=cb,
        )
        op = pipeline._pipeline.run_op.call_args[0][0]

        op.complete(error=arbitrary_exception)
        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception, invoke_method_response=None)


@pytest.mark.describe("HTTPPipeline - .get_storage_info()")
class TestHTTPPipelineGetStorageInfo(object):
    @pytest.mark.it("Runs a GetStorageInfoOperation on the pipeline")
    def test_runs_op(self, pipeline, mocker):
        pipeline.get_storage_info(blob_name="__fake_blob_name__", callback=mocker.MagicMock())
        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(
            pipeline._pipeline.run_op.call_args[0][0],
            pipeline_ops_iothub_http.GetStorageInfoOperation,
        )

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the GetStorageInfoOperation"
    )
    def test_op_configuration_fail(self, mocker, pipeline):
        pipeline._pipeline.pipeline_configuration.blob_upload = False
        cb = mocker.MagicMock()
        pipeline.get_storage_info(blob_name="__fake_blob_name__", callback=cb)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=mocker.ANY)

    @pytest.mark.it(
        "Triggers the callback upon successful completion of the GetStorageInfoOperation"
    )
    def test_op_success_with_callback(self, mocker, pipeline):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.get_storage_info(blob_name="__fake_blob_name__", callback=cb)
        assert cb.call_count == 0

        # Trigger op completion callback
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.storage_info = "__fake_storage_info__"
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=None, storage_info="__fake_storage_info__")

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the GetStorageInfoOperation"
    )
    def test_op_fail(self, mocker, pipeline, arbitrary_exception):
        cb = mocker.MagicMock()
        pipeline.get_storage_info(blob_name="__fake_blob_name__", callback=cb)

        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=arbitrary_exception)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception, storage_info=None)


@pytest.mark.describe("HTTPPipeline - .notify_blob_upload_status()")
class TestHTTPPipelineNotifyBlobUploadStatus(object):
    @pytest.mark.it(
        "Runs a NotifyBlobUploadStatusOperation with the provided parameters on the pipeline"
    )
    def test_runs_op(self, pipeline, mocker):
        pipeline.notify_blob_upload_status(
            correlation_id="__fake_correlation_id__",
            is_success="__fake_is_success__",
            status_code="__fake_status_code__",
            status_description="__fake_status_description__",
            callback=mocker.MagicMock(),
        )
        op = pipeline._pipeline.run_op.call_args[0][0]

        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(op, pipeline_ops_iothub_http.NotifyBlobUploadStatusOperation)

    @pytest.mark.it(
        "Calls the callback with the error if pipeline_configuration.blob_upload is not True"
    )
    def test_op_configuration_fail(self, mocker, pipeline):
        pipeline._pipeline.pipeline_configuration.blob_upload = False
        cb = mocker.MagicMock()
        pipeline.notify_blob_upload_status(
            correlation_id="__fake_correlation_id__",
            is_success="__fake_is_success__",
            status_code="__fake_status_code__",
            status_description="__fake_status_description__",
            callback=cb,
        )

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=mocker.ANY)

    @pytest.mark.it(
        "Triggers the callback upon successful completion of the NotifyBlobUploadStatusOperation"
    )
    def test_op_success_with_callback(self, mocker, pipeline):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.notify_blob_upload_status(
            correlation_id="__fake_correlation_id__",
            is_success="__fake_is_success__",
            status_code="__fake_status_code__",
            status_description="__fake_status_description__",
            callback=cb,
        )
        assert cb.call_count == 0

        # Trigger op completion callback
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the NotifyBlobUploadStatusOperation"
    )
    def test_op_fail(self, mocker, pipeline, arbitrary_exception):
        cb = mocker.MagicMock()
        pipeline.notify_blob_upload_status(
            correlation_id="__fake_correlation_id__",
            is_success="__fake_is_success__",
            status_code="__fake_status_code__",
            status_description="__fake_status_description__",
            callback=cb,
        )

        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=arbitrary_exception)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception)
