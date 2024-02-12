# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains tests that are shared between sync/async clients
i.e. tests for things defined in abstract clients"""

import pytest
import logging
import os
import io
import time
import urllib
from azure.iot.device.common import auth, handle_exceptions
from azure.iot.device.common.auth import sastoken as st
from azure.iot.device.common.auth import connection_string as cs
from azure.iot.device.iothub.pipeline import IoTHubPipelineConfig
from azure.iot.device.common.pipeline.config import DEFAULT_KEEPALIVE
from azure.iot.device.iothub.abstract_clients import (
    RECEIVE_TYPE_NONE_SET,
    RECEIVE_TYPE_HANDLER,
    RECEIVE_TYPE_API,
)
from azure.iot.device.iothub import edge_hsm
from azure.iot.device.iothub import client_event
from azure.iot.device import ProxyOptions
from azure.iot.device import exceptions as client_exceptions

logging.basicConfig(level=logging.DEBUG)


####################
# HELPER FUNCTIONS #
####################


def token_parser(token_str):
    """helper function that parses a token string for individual values"""
    token_map = {}
    kv_string = token_str.split(" ")[1]
    kv_pairs = kv_string.split("&")
    for kv in kv_pairs:
        t = kv.split("=")
        token_map[t[0]] = t[1]
    return token_map


################################
# SHARED DEVICE + MODULE TESTS #
################################


class SharedIoTHubClientInstantiationTests(object):
    @pytest.mark.it(
        "Stores the MQTTPipeline from the 'mqtt_pipeline' parameter in the '_mqtt_pipeline' attribute"
    )
    def test_mqtt_pipeline_attribute(self, client_class, mqtt_pipeline, http_pipeline):
        client = client_class(mqtt_pipeline, http_pipeline)

        assert client._mqtt_pipeline is mqtt_pipeline

    @pytest.mark.it(
        "Stores the HTTPPipeline from the 'http_pipeline' parameter in the '_http_pipeline' attribute"
    )
    def test_sets_http_pipeline_attribute(self, client_class, mqtt_pipeline, http_pipeline):
        client = client_class(mqtt_pipeline, http_pipeline)

        assert client._http_pipeline is http_pipeline

    @pytest.mark.it("Sets on_connected handler in the MQTTPipeline")
    def test_sets_on_connected_handler_in_pipeline(
        self, client_class, mqtt_pipeline, http_pipeline
    ):
        client = client_class(mqtt_pipeline, http_pipeline)

        assert client._mqtt_pipeline.on_connected is not None
        assert client._mqtt_pipeline.on_connected == client._on_connected

    @pytest.mark.it("Sets on_disconnected handler in the MQTTPipeline")
    def test_sets_on_disconnected_handler_in_pipeline(
        self, client_class, mqtt_pipeline, http_pipeline
    ):
        client = client_class(mqtt_pipeline, http_pipeline)

        assert client._mqtt_pipeline.on_disconnected is not None
        assert client._mqtt_pipeline.on_disconnected == client._on_disconnected

    @pytest.mark.it("Sets on_new_sastoken_required handler in the MQTTPipeline")
    def test_sets_on_new_sastoken_required_handler_in_pipeline(
        self, client_class, mqtt_pipeline, http_pipeline
    ):
        client = client_class(mqtt_pipeline, http_pipeline)

        assert client._mqtt_pipeline.on_new_sastoken_required is not None
        assert client._mqtt_pipeline.on_new_sastoken_required == client._on_new_sastoken_required

    @pytest.mark.it("Sets on_background_exception handler in the MQTTPipeline")
    def test_sets_on_background_exception_handler(self, client_class, mqtt_pipeline, http_pipeline):
        client = client_class(mqtt_pipeline, http_pipeline)

        assert client._mqtt_pipeline.on_background_exception is not None
        assert client._mqtt_pipeline.on_background_exception == client._on_background_exception

    @pytest.mark.it("Sets on_method_request_received handler in the MQTTPipeline")
    def test_sets_on_method_request_received_handler_in_pipeline(
        self, client_class, mqtt_pipeline, http_pipeline
    ):
        client = client_class(mqtt_pipeline, http_pipeline)

        assert client._mqtt_pipeline.on_method_request_received is not None
        assert (
            client._mqtt_pipeline.on_method_request_received
            == client._inbox_manager.route_method_request
        )

    @pytest.mark.it("Sets on_twin_patch_received handler in the MQTTPipeline")
    def test_sets_on_twin_patch_received_handler_in_pipeline(
        self, client_class, mqtt_pipeline, http_pipeline
    ):
        client = client_class(mqtt_pipeline, http_pipeline)

        assert client._mqtt_pipeline.on_twin_patch_received is not None
        assert (
            client._mqtt_pipeline.on_twin_patch_received == client._inbox_manager.route_twin_patch
        )

    @pytest.mark.it("Sets the Receive Mode/Type for the client as yet-unchosen")
    def test_initial_receive_mode(self, client_class, mqtt_pipeline, http_pipeline):
        client = client_class(mqtt_pipeline, http_pipeline)

        assert client._receive_type == RECEIVE_TYPE_NONE_SET


@pytest.mark.usefixtures("mock_mqtt_pipeline_init", "mock_http_pipeline_init")
class SharedIoTHubClientCreateMethodUserOptionTests(object):
    @pytest.fixture
    def option_test_required_patching(self, mocker):
        """Override this fixture in a subclass if unique patching is required"""
        pass

    @pytest.mark.it(
        "Sets the 'product_info' user option parameter on the PipelineConfig, if provided"
    )
    def test_product_info_option(
        self,
        option_test_required_patching,
        client_create_method,
        create_method_args,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):

        product_info = "MyProductInfo"
        client_create_method(*create_method_args, product_info=product_info)

        # Get configuration object, and ensure it was used for both protocol pipelines
        assert mock_mqtt_pipeline_init.call_count == 1
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert isinstance(config, IoTHubPipelineConfig)
        assert config == mock_http_pipeline_init.call_args[0][0]

        assert config.product_info == product_info

    @pytest.mark.it(
        "Sets the 'ensure_desired_properties' user option parameter on the PipelineConfig, if provided"
    )
    @pytest.mark.parametrize("edp_value", [True, False])
    def test_ensure_desired_properties_option(
        self,
        option_test_required_patching,
        client_create_method,
        create_method_args,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
        edp_value,
    ):

        client_create_method(*create_method_args, ensure_desired_properties=edp_value)

        # Get configuration object, and ensure it was used for both protocol pipelines
        assert mock_mqtt_pipeline_init.call_count == 1
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert isinstance(config, IoTHubPipelineConfig)
        assert config == mock_http_pipeline_init.call_args[0][0]

        assert config.ensure_desired_properties is edp_value

    @pytest.mark.it(
        "Sets the 'websockets' user option parameter on the PipelineConfig, if provided"
    )
    @pytest.mark.parametrize("ws_value", [True, False])
    def test_websockets_option(
        self,
        option_test_required_patching,
        client_create_method,
        create_method_args,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
        ws_value,
    ):

        client_create_method(*create_method_args, websockets=ws_value)

        # Get configuration object, and ensure it was used for both protocol pipelines
        assert mock_mqtt_pipeline_init.call_count == 1
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert isinstance(config, IoTHubPipelineConfig)
        assert config == mock_http_pipeline_init.call_args[0][0]

        assert config.websockets is ws_value

    # TODO: Show that input in the wrong format is formatted to the correct one. This test exists
    # in the IoTHubPipelineConfig object already, but we do not currently show that this is felt
    # from the API level.
    @pytest.mark.it("Sets the 'cipher' user option parameter on the PipelineConfig, if provided")
    def test_cipher_option(
        self,
        option_test_required_patching,
        client_create_method,
        create_method_args,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        cipher = "DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:ECDHE-ECDSA-AES128-GCM-SHA256"
        client_create_method(*create_method_args, cipher=cipher)

        # Get configuration object, and ensure it was used for both protocol pipelines
        assert mock_mqtt_pipeline_init.call_count == 1
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert isinstance(config, IoTHubPipelineConfig)
        assert config == mock_http_pipeline_init.call_args[0][0]

        assert config.cipher == cipher

    @pytest.mark.it(
        "Sets the 'server_verification_cert' user option parameter on the PipelineConfig, if provided"
    )
    def test_server_verification_cert_option(
        self,
        option_test_required_patching,
        client_create_method,
        create_method_args,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        server_verification_cert = "fake_server_verification_cert"
        client_create_method(*create_method_args, server_verification_cert=server_verification_cert)

        # Get configuration object, and ensure it was used for both protocol pipelines
        assert mock_mqtt_pipeline_init.call_count == 1
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert isinstance(config, IoTHubPipelineConfig)
        assert config == mock_http_pipeline_init.call_args[0][0]

        assert config.server_verification_cert == server_verification_cert

    @pytest.mark.it(
        "Sets the 'gateway_hostname' user option parameter on the PipelineConfig, if provided"
    )
    def test_gateway_hostname_option(
        self,
        option_test_required_patching,
        client_create_method,
        create_method_args,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        gateway_hostname = "my.gateway"
        client_create_method(*create_method_args, gateway_hostname=gateway_hostname)

        # Get configuration object, and ensure it was used for both protocol pipelines
        assert mock_mqtt_pipeline_init.call_count == 1
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert isinstance(config, IoTHubPipelineConfig)
        assert config == mock_http_pipeline_init.call_args[0][0]

        assert config.gateway_hostname == gateway_hostname

    @pytest.mark.it(
        "Sets the 'proxy_options' user option parameter on the PipelineConfig, if provided"
    )
    def test_proxy_options(
        self,
        option_test_required_patching,
        client_create_method,
        create_method_args,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        proxy_options = ProxyOptions(proxy_type="HTTP", proxy_addr="127.0.0.1", proxy_port=8888)
        client_create_method(*create_method_args, proxy_options=proxy_options)

        # Get configuration object, and ensure it was used for both protocol pipelines
        assert mock_mqtt_pipeline_init.call_count == 1
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert isinstance(config, IoTHubPipelineConfig)
        assert config == mock_http_pipeline_init.call_args[0][0]

        assert config.proxy_options is proxy_options

    @pytest.mark.it(
        "Sets the 'keep_alive' user option parameter on the PipelineConfig, if provided"
    )
    def test_keep_alive_options(
        self,
        option_test_required_patching,
        client_create_method,
        create_method_args,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        keepalive_value = 60
        client_create_method(*create_method_args, keep_alive=keepalive_value)

        # Get configuration object, and ensure it was used for both protocol pipelines
        assert mock_mqtt_pipeline_init.call_count == 1
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert isinstance(config, IoTHubPipelineConfig)
        assert config == mock_http_pipeline_init.call_args[0][0]

        assert config.keep_alive == keepalive_value

    @pytest.mark.it(
        "Sets the 'auto_connect' user option parameter on the PipelineConfig, if provided"
    )
    @pytest.mark.parametrize("auto_connect_value", [True, False])
    def test_auto_connect_option(
        self,
        option_test_required_patching,
        client_create_method,
        create_method_args,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
        auto_connect_value,
    ):
        client_create_method(*create_method_args, auto_connect=auto_connect_value)

        # Get configuration object, and ensure it was used for both protocol pipelines
        assert mock_mqtt_pipeline_init.call_count == 1
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert isinstance(config, IoTHubPipelineConfig)
        assert config == mock_http_pipeline_init.call_args[0][0]

        assert config.auto_connect == auto_connect_value

    @pytest.mark.it(
        "Sets the 'connection_retry' user option parameter on the PipelineConfig, if provided"
    )
    @pytest.mark.parametrize("connection_retry_value", [True, False])
    def test_connection_retry_option(
        self,
        option_test_required_patching,
        client_create_method,
        create_method_args,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
        connection_retry_value,
    ):
        connection_retry_value = False
        client_create_method(*create_method_args, connection_retry=connection_retry_value)

        # Get configuration object, and ensure it was used for both protocol pipelines
        assert mock_mqtt_pipeline_init.call_count == 1
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert isinstance(config, IoTHubPipelineConfig)
        assert config == mock_http_pipeline_init.call_args[0][0]

        assert config.connection_retry == connection_retry_value

    @pytest.mark.it(
        "Sets the 'connection_retry_interval' user option parameter on the PipelineConfig, if provided"
    )
    def test_connection_retry_interval_option(
        self,
        option_test_required_patching,
        client_create_method,
        create_method_args,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        connection_retry_interval_value = 17
        client_create_method(
            *create_method_args, connection_retry_interval=connection_retry_interval_value
        )

        # Get configuration object, and ensure it was used for both protocol pipelines
        assert mock_mqtt_pipeline_init.call_count == 1
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert isinstance(config, IoTHubPipelineConfig)
        assert config == mock_http_pipeline_init.call_args[0][0]

        assert config.connection_retry_interval == connection_retry_interval_value

    @pytest.mark.it("Raises a TypeError if an invalid user option parameter is provided")
    def test_invalid_option(
        self, option_test_required_patching, client_create_method, create_method_args
    ):
        with pytest.raises(TypeError):
            client_create_method(*create_method_args, invalid_option="some_value")

    # NOTE: If any further tests need to override this test, it's time to restructure.
    @pytest.mark.it("Sets default user options if none are provided")
    def test_default_options(
        self,
        mocker,
        option_test_required_patching,
        client_create_method,
        create_method_args,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        client_create_method(*create_method_args)

        # Both pipelines use the same IoTHubPipelineConfig
        assert mock_mqtt_pipeline_init.call_count == 1
        assert mock_http_pipeline_init.call_count == 1
        assert mock_mqtt_pipeline_init.call_args[0][0] is mock_http_pipeline_init.call_args[0][0]
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert isinstance(config, IoTHubPipelineConfig)

        # Pipeline Config has default options set that were not user-specified
        assert config.product_info == ""
        assert config.websockets is False
        assert config.cipher == ""
        assert config.proxy_options is None
        assert config.server_verification_cert is None
        assert config.gateway_hostname is None
        assert config.keep_alive == DEFAULT_KEEPALIVE
        assert config.auto_connect is True
        assert config.connection_retry is True
        assert config.connection_retry_interval == 10
        assert config.ensure_desired_properties is True


# TODO: consider splitting this test class up into device/module specific test classes to avoid
# the conditional logic in some tests
@pytest.mark.usefixtures("mock_mqtt_pipeline_init", "mock_http_pipeline_init")
class SharedIoTHubClientCreateFromConnectionStringTests(
    SharedIoTHubClientCreateMethodUserOptionTests
):
    @pytest.fixture
    def client_create_method(self, client_class):
        """Provides the specific create method for use in universal tests"""
        return client_class.create_from_connection_string

    @pytest.fixture
    def create_method_args(self, connection_string):
        """Provides the specific create method args for use in universal tests"""
        return [connection_string]

    @pytest.mark.it(
        "Raises a TypeError if the 'gateway_hostname' user option parameter is provided"
    )
    def test_gateway_hostname_option(
        self,
        option_test_required_patching,
        client_create_method,
        create_method_args,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        """THIS TEST OVERRIDES AN INHERITED TEST"""
        # Override to test that gateway_hostname CANNOT be provided in Edge scenarios

        with pytest.raises(TypeError):
            client_create_method(*create_method_args, gateway_hostname="my.gateway.device")

    @pytest.mark.it("Sets default user options if none are provided")
    def test_default_options(
        self,
        mocker,
        option_test_required_patching,
        client_create_method,
        create_method_args,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        """THIS TEST OVERRIDES AN INHERITED TEST"""
        # Override to remove an assertion about gateway_hostname

        client_create_method(*create_method_args)

        # Both pipelines use the same IoTHubPipelineConfig
        assert mock_mqtt_pipeline_init.call_count == 1
        assert mock_http_pipeline_init.call_count == 1
        assert mock_mqtt_pipeline_init.call_args[0][0] is mock_http_pipeline_init.call_args[0][0]
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert isinstance(config, IoTHubPipelineConfig)

        # Pipeline Config has default options set that were not user-specified
        assert config.product_info == ""
        assert config.websockets is False
        assert config.cipher == ""
        assert config.proxy_options is None
        assert config.server_verification_cert is None
        assert config.keep_alive == DEFAULT_KEEPALIVE
        assert config.auto_connect is True
        assert config.connection_retry is True
        assert config.connection_retry_interval == 10

    @pytest.mark.it(
        "Creates a SasToken that uses a SymmetricKeySigningMechanism, from the values in the provided connection string"
    )
    def test_sastoken(self, mocker, client_class, connection_string):
        sksm_mock = mocker.patch.object(auth, "SymmetricKeySigningMechanism")
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")
        cs_obj = cs.ConnectionString(connection_string)

        custom_ttl = 1000
        client_class.create_from_connection_string(connection_string, sastoken_ttl=custom_ttl)

        # Determine expected URI based on class under test
        if client_class.__name__ == "IoTHubDeviceClient":
            expected_uri = "{hostname}/devices/{device_id}".format(
                hostname=cs_obj[cs.HOST_NAME], device_id=cs_obj[cs.DEVICE_ID]
            )
        else:
            expected_uri = "{hostname}/devices/{device_id}/modules/{module_id}".format(
                hostname=cs_obj[cs.HOST_NAME],
                device_id=cs_obj[cs.DEVICE_ID],
                module_id=cs_obj[cs.MODULE_ID],
            )

        # SymmetricKeySigningMechanism created using the connection string's SharedAccessKey
        assert sksm_mock.call_count == 1
        assert sksm_mock.call_args == mocker.call(key=cs_obj[cs.SHARED_ACCESS_KEY])

        # Token was created with a SymmetricKeySigningMechanism, the expected URI, and custom ttl
        assert sastoken_mock.call_count == 1
        assert sastoken_mock.call_args == mocker.call(
            expected_uri, sksm_mock.return_value, ttl=custom_ttl
        )

    @pytest.mark.it(
        "Uses 3600 seconds (1 hour) as the default SasToken TTL if no custom TTL is provided"
    )
    def test_sastoken_default(self, mocker, client_class, connection_string):
        sksm_mock = mocker.patch.object(auth, "SymmetricKeySigningMechanism")
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")
        cs_obj = cs.ConnectionString(connection_string)

        client_class.create_from_connection_string(connection_string)

        # Determine expected URI based on class under test
        if client_class.__name__ == "IoTHubDeviceClient":
            expected_uri = "{hostname}/devices/{device_id}".format(
                hostname=cs_obj[cs.HOST_NAME], device_id=cs_obj[cs.DEVICE_ID]
            )
        else:
            expected_uri = "{hostname}/devices/{device_id}/modules/{module_id}".format(
                hostname=cs_obj[cs.HOST_NAME],
                device_id=cs_obj[cs.DEVICE_ID],
                module_id=cs_obj[cs.MODULE_ID],
            )

        # SymmetricKeySigningMechanism created using the connection string's SharedAccessKey
        assert sksm_mock.call_count == 1
        assert sksm_mock.call_args == mocker.call(key=cs_obj[cs.SHARED_ACCESS_KEY])

        # Token was created with a SymmetricKeySigningMechanism, the expected URI, and default ttl
        assert sastoken_mock.call_count == 1
        assert sastoken_mock.call_args == mocker.call(
            expected_uri, sksm_mock.return_value, ttl=3600
        )

    @pytest.mark.it(
        "Creates MQTT and HTTP Pipelines with an IoTHubPipelineConfig object containing the SasToken and values from the connection string"
    )
    def test_pipeline_config(
        self,
        mocker,
        client_class,
        connection_string,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")
        cs_obj = cs.ConnectionString(connection_string)

        client_class.create_from_connection_string(connection_string)

        # Verify pipelines created with an IoTHubPipelineConfig
        assert mock_mqtt_pipeline_init.call_count == 1
        assert mock_http_pipeline_init.call_count == 1
        assert mock_mqtt_pipeline_init.call_args[0][0] is mock_http_pipeline_init.call_args[0][0]
        assert isinstance(mock_mqtt_pipeline_init.call_args[0][0], IoTHubPipelineConfig)

        # Verify the IoTHubPipelineConfig is constructed as expected
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert config.device_id == cs_obj[cs.DEVICE_ID]
        assert config.hostname == cs_obj[cs.HOST_NAME]
        assert config.sastoken is sastoken_mock.return_value
        if client_class.__name__ == "IoTHubModuleClient":
            assert config.module_id == cs_obj[cs.MODULE_ID]
            assert config.blob_upload is False
            assert config.method_invoke is False
        else:
            assert config.module_id is None
            assert config.blob_upload is True
            assert config.method_invoke is False
        if cs_obj.get(cs.GATEWAY_HOST_NAME):
            assert config.gateway_hostname == cs_obj[cs.GATEWAY_HOST_NAME]
        else:
            assert config.gateway_hostname is None

    @pytest.mark.it(
        "Returns an instance of an IoTHub client using the created MQTT and HTTP pipelines"
    )
    def test_client_returned(
        self,
        mocker,
        client_class,
        connection_string,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        client = client_class.create_from_connection_string(connection_string)
        assert isinstance(client, client_class)
        assert client._mqtt_pipeline is mock_mqtt_pipeline_init.return_value
        assert client._http_pipeline is mock_http_pipeline_init.return_value

    @pytest.mark.it("Raises ValueError when given an invalid connection string")
    @pytest.mark.parametrize(
        "bad_cs",
        [
            pytest.param("not-a-connection-string", id="Garbage string"),
            pytest.param(
                "HostName=value.domain.net;DeviceId=my_device;SharedAccessKey=Invalid",
                id="Shared Access Key invalid",
            ),
            pytest.param(
                "HostName=value.domain.net;WrongValue=Invalid;SharedAccessKey=Zm9vYmFy",
                id="Contains extraneous data",
            ),
            pytest.param("HostName=value.domain.net;DeviceId=my_device", id="Incomplete"),
            pytest.param(
                "HostName=value.domain.net;DeviceId=my_device;x509=True",
                id="X509 Connection String",
            ),
        ],
    )
    def test_raises_value_error_on_bad_connection_string(self, client_class, bad_cs):
        with pytest.raises(ValueError):
            client_class.create_from_connection_string(bad_cs)

    @pytest.mark.it("Raises ValueError if a SasToken creation results in failure")
    def test_raises_value_error_on_sastoken_failure(self, mocker, client_class, connection_string):
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")
        token_err = st.SasTokenError("Some SasToken failure")
        sastoken_mock.side_effect = token_err

        with pytest.raises(ValueError) as e_info:
            client_class.create_from_connection_string(connection_string)
        assert e_info.value.__cause__ is token_err


class SharedIoTHubClientPROPERTYHandlerTests(object):
    @pytest.mark.it("Can have its value set and retrieved")
    def test_read_write(self, client, handler, handler_name):
        assert getattr(client, handler_name) is None
        setattr(client, handler_name, handler)
        assert getattr(client, handler_name) is handler

    @pytest.mark.it("Reflects the value of the handler manager property of the same name")
    def test_set_on_handler_manager(self, client, handler, handler_name):
        assert getattr(client, handler_name) is None
        assert getattr(client, handler_name) is getattr(client._handler_manager, handler_name)
        setattr(client, handler_name, handler)
        assert getattr(client, handler_name) is handler
        assert getattr(client, handler_name) is getattr(client._handler_manager, handler_name)


class SharedIoTHubClientPROPERTYReceiverHandlerTests(SharedIoTHubClientPROPERTYHandlerTests):
    @pytest.mark.it("Can have its value set and retrieved")
    def test_read_write(self, client, handler, handler_name):
        assert getattr(client, handler_name) is None
        setattr(client, handler_name, handler)
        assert getattr(client, handler_name) is handler

    @pytest.mark.it("Reflects the value of the handler manager property of the same name")
    def test_set_on_handler_manager(self, client, handler, handler_name):
        assert getattr(client, handler_name) is None
        assert getattr(client, handler_name) is getattr(client._handler_manager, handler_name)
        setattr(client, handler_name, handler)
        assert getattr(client, handler_name) is handler
        assert getattr(client, handler_name) is getattr(client._handler_manager, handler_name)

    @pytest.mark.it(
        "Implicitly enables the corresponding feature if not already enabled, when a handler value is set"
    )
    def test_enables_feature_only_if_not_already_enabled(
        self, mocker, client, handler, handler_name, feature_name, mqtt_pipeline
    ):
        # Feature will appear disabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = False
        # Set handler
        setattr(client, handler_name, handler)
        # Feature was enabled
        assert mqtt_pipeline.enable_feature.call_count == 1
        assert mqtt_pipeline.enable_feature.call_args[0][0] == feature_name

        mqtt_pipeline.enable_feature.reset_mock()

        # Feature will appear already enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = True
        # Set handler
        setattr(client, handler_name, handler)
        # Feature was not enabled again
        assert mqtt_pipeline.enable_feature.call_count == 0

    @pytest.mark.it(
        "Implicitly disables the corresponding feature if not already disabled, when handler value is set back to None"
    )
    def test_disables_feature_only_if_not_already_disabled(
        self, mocker, client, handler_name, feature_name, mqtt_pipeline
    ):
        # Feature will appear enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = True
        # Set handler to None
        setattr(client, handler_name, None)
        # Feature was disabled
        assert mqtt_pipeline.disable_feature.call_count == 1
        assert mqtt_pipeline.disable_feature.call_args[0][0] == feature_name

        mqtt_pipeline.disable_feature.reset_mock()

        # Feature will appear already disabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = False
        # Set handler to None
        setattr(client, handler_name, None)
        # Feature was not disabled again
        assert mqtt_pipeline.disable_feature.call_count == 0

    @pytest.mark.it(
        "Locks the client to Handler Receive Mode if the receive mode has not yet been set"
    )
    def test_receive_mode_not_set(self, client, handler, handler_name):
        assert client._receive_type is RECEIVE_TYPE_NONE_SET
        setattr(client, handler_name, handler)
        assert client._receive_type is RECEIVE_TYPE_HANDLER

    @pytest.mark.it(
        "Does not modify the client receive mode if it has already been set to Handler Receive Mode"
    )
    def test_receive_mode_set_handler(self, client, handler, handler_name):
        client._receive_type = RECEIVE_TYPE_HANDLER
        setattr(client, handler_name, handler)
        assert client._receive_type is RECEIVE_TYPE_HANDLER

    @pytest.mark.it(
        "Raises a ClientError and does nothing else if the client receive mode has already been set to  API Receive Mode"
    )
    def test_receive_mode_set_api(self, client, handler, handler_name, mqtt_pipeline):
        client._receive_type = RECEIVE_TYPE_API
        # Error was raised
        with pytest.raises(client_exceptions.ClientError):
            setattr(client, handler_name, handler)
        # Feature was not enabled
        assert mqtt_pipeline.enable_feature.call_count == 0


# NOTE: If more properties are added, this class should become a general purpose properties test class
class SharedIoTHubClientPROPERTYConnectedTests(object):
    @pytest.mark.it("Cannot be changed")
    def test_read_only(self, client):
        with pytest.raises(AttributeError):
            client.connected = not client.connected

    @pytest.mark.it("Reflects the value of the root stage property of the same name")
    def test_reflects_pipeline_property(self, client, mqtt_pipeline):
        mqtt_pipeline.connected = True
        assert client.connected
        mqtt_pipeline.connected = False
        assert not client.connected


class SharedIoTHubClientOCCURRENCEConnectTests(object):
    @pytest.mark.it(
        "Adds a CONNECTION_STATE_CHANGE ClientEvent to the ClientEvent Inbox if the HandlerManager is currently handling ClientEvents"
    )
    def test_handler_manager_handling_events(self, client, mocker):
        # NOTE: It's hard to mock a read-only property (.handling_client_events), so we're breaking
        # the rule about black-boxing other modules to simulate what we want. Sorry.
        client._handler_manager._client_event_runner = mocker.MagicMock()  # fake thread
        assert client._handler_manager.handling_client_events is True
        client_event_inbox = client._inbox_manager.get_client_event_inbox()
        inbox_put_spy = mocker.spy(client_event_inbox, "put")
        assert client_event_inbox.empty()

        client._on_connected()

        # ClientEvent was added
        assert not client_event_inbox.empty()
        assert inbox_put_spy.call_count == 1
        event = inbox_put_spy.call_args[0][0]
        assert isinstance(event, client_event.ClientEvent)
        assert event.name == client_event.CONNECTION_STATE_CHANGE
        assert event.args_for_user == ()

    @pytest.mark.it(
        "Does not add any ClientEvents to the ClientEvent Inbox if the HandlerManager is not currently handling ClientEvents"
    )
    def test_handler_manager_not_handling_events(self, client):
        assert client._handler_manager.handling_client_events is False
        client_event_inbox = client._inbox_manager.get_client_event_inbox()
        assert client_event_inbox.empty()

        client._on_connected()

        # Inbox is still empty
        assert client_event_inbox.empty()

    @pytest.mark.it("Ensures that the HandlerManager is running")
    @pytest.mark.parametrize(
        "handling_client_events",
        [True, False],
        ids=["Manager Handling ClientEvents", "Manager Not Handling ClientEvents"],
    )
    def test_ensure_handler_manager_running_on_connect(
        self, client, mocker, handling_client_events
    ):
        if handling_client_events:
            # NOTE: It's hard to mock a read-only property (.handling_client_events), so we're breaking
            # the rule about black-boxing other modules to simulate what we want. Sorry.
            client._handler_manager._client_event_runner = mocker.MagicMock()  # fake thread
        assert client._handler_manager.handling_client_events is handling_client_events
        ensure_running_spy = mocker.spy(client._handler_manager, "ensure_running")
        client._on_connected()
        assert ensure_running_spy.call_count == 1


class SharedIoTHubClientOCCURRENCEDisconnectTests(object):
    @pytest.mark.it(
        "Adds a CONNECTION_STATE_CHANGE ClientEvent to the ClientEvent Inbox if the HandlerManager is currently handling ClientEvents"
    )
    def test_handler_manager_handling_event(self, client, mocker):
        # NOTE: It's hard to mock a read-only property (.handling_client_events), so we're breaking
        # the rule about black-boxing other modules to simulate what we want. Sorry.
        client._handler_manager._client_event_runner = mocker.MagicMock()  # fake thread
        assert client._handler_manager.handling_client_events is True
        client_event_inbox = client._inbox_manager.get_client_event_inbox()
        inbox_put_spy = mocker.spy(client_event_inbox, "put")
        assert client_event_inbox.empty()

        client._on_disconnected()

        assert not client_event_inbox.empty()
        assert inbox_put_spy.call_count == 1
        event = inbox_put_spy.call_args[0][0]
        assert isinstance(event, client_event.ClientEvent)
        assert event.name == client_event.CONNECTION_STATE_CHANGE
        assert event.args_for_user == ()

    @pytest.mark.it(
        "Does not add any ClientEvents to the ClientEvent Inbox if the HandlerManager is not currently handling ClientEvents"
    )
    def test_handler_manager_not_handling_events(self, client):
        assert client._handler_manager.handling_client_events is False
        client_event_inbox = client._inbox_manager.get_client_event_inbox()
        assert client_event_inbox.empty()

        client._on_disconnected()

        # Inbox is still empty
        assert client_event_inbox.empty()

    @pytest.mark.it("Clears all pending MethodRequests")
    @pytest.mark.parametrize(
        "handling_client_events",
        [True, False],
        ids=["Manager Handling ClientEvents", "Manager Not Handling ClientEvents"],
    )
    def test_state_change_handler_clears_method_request_inboxes_on_disconnect(
        self, client, mocker, handling_client_events
    ):
        if handling_client_events:
            # NOTE: It's hard to mock a read-only property (.handling_client_events), so we're breaking
            # the rule about black-boxing other modules to simulate what we want. Sorry.
            client._handler_manager._client_event_runner = mocker.MagicMock()  # fake thread
        assert client._handler_manager.handling_client_events is handling_client_events
        clear_method_request_spy = mocker.spy(client._inbox_manager, "clear_all_method_requests")
        client._on_disconnected()
        assert clear_method_request_spy.call_count == 1


class SharedIoTHubClientOCCURRENCENewSastokenRequired(object):
    @pytest.mark.it(
        "Adds a NEW_SASTOKEN_REQUIRED ClientEvent to the ClientEvent Inbox if the HandlerManager is currently handling ClientEvents"
    )
    def test_handler_manager_handling_events(self, client, mocker):
        # NOTE: It's hard to mock a read-only property (.handling_client_events), so we're breaking
        # the rule about black-boxing other modules to simulate what we want. Sorry.
        client._handler_manager._client_event_runner = mocker.MagicMock()  # fake thread
        assert client._handler_manager.handling_client_events is True
        client_event_inbox = client._inbox_manager.get_client_event_inbox()
        inbox_put_spy = mocker.spy(client_event_inbox, "put")
        assert client_event_inbox.empty()

        client._on_new_sastoken_required()

        assert not client_event_inbox.empty()
        assert inbox_put_spy.call_count == 1
        event = inbox_put_spy.call_args[0][0]
        assert isinstance(event, client_event.ClientEvent)
        assert event.name == client_event.NEW_SASTOKEN_REQUIRED
        assert event.args_for_user == ()

    @pytest.mark.it(
        "Does not add any ClientEvents to the ClientEvent Inbox if the HandlerManager is not currently handling ClientEvents"
    )
    def test_handler_manager_not_handling_events(self, client):
        assert client._handler_manager.handling_client_events is False
        client_event_inbox = client._inbox_manager.get_client_event_inbox()
        assert client_event_inbox.empty()

        client._on_new_sastoken_required()

        # Inbox still empty
        assert client_event_inbox.empty()


class SharedIoTHubClientOCCURRENCEBackgroundException(object):
    @pytest.mark.it("Sends the exception to the handle_exceptions module")
    @pytest.mark.parametrize(
        "handling_client_events",
        [True, False],
        ids=["Manager Handling ClientEvents", "Manager Not Handling ClientEvents"],
    )
    def test_handle_exceptions_module(
        self, client, mocker, arbitrary_exception, handling_client_events
    ):
        if handling_client_events:
            # NOTE: It's hard to mock a read-only property (.handling_client_events), so we're breaking
            # the rule about black-boxing other modules to simulate what we want. Sorry.
            client._handler_manager._client_event_runner = mocker.MagicMock()  # fake thread
        assert client._handler_manager.handling_client_events is handling_client_events
        background_exc_spy = mocker.spy(handle_exceptions, "handle_background_exception")

        client._on_background_exception(arbitrary_exception)

        assert background_exc_spy.call_count == 1
        assert background_exc_spy.call_args == mocker.call(arbitrary_exception)

    @pytest.mark.it(
        "Adds a BACKGROUND_EXCEPTION ClientEvent (containing the exception) to the ClientEvent Inbox if the HandlerManager is currently handling ClientEvents"
    )
    def test_handler_manager_handling_events(self, client, mocker, arbitrary_exception):
        # NOTE: It's hard to mock a read-only property (.handling_client_events), so we're breaking
        # the rule about black-boxing other modules to simulate what we want. Sorry.
        client._handler_manager._client_event_runner = mocker.MagicMock()  # fake thread
        assert client._handler_manager.handling_client_events is True
        client_event_inbox = client._inbox_manager.get_client_event_inbox()
        inbox_put_spy = mocker.spy(client_event_inbox, "put")
        assert client_event_inbox.empty()

        client._on_background_exception(arbitrary_exception)

        assert not client_event_inbox.empty()
        assert inbox_put_spy.call_count == 1
        event = inbox_put_spy.call_args[0][0]
        assert isinstance(event, client_event.ClientEvent)
        assert event.name == client_event.BACKGROUND_EXCEPTION
        assert event.args_for_user == (arbitrary_exception,)

    @pytest.mark.it(
        "Does not add any ClientEvents to the ClientEvent Inbox if the HandlerManager is not currently handling ClientEvents"
    )
    def test_handler_manager_not_handling_events(self, client, arbitrary_exception):
        assert client._handler_manager.handling_client_events is False
        client_event_inbox = client._inbox_manager.get_client_event_inbox()
        assert client_event_inbox.empty()

        client._on_background_exception(arbitrary_exception)

        # Inbox is still empty
        assert client_event_inbox.empty()


##############################
# SHARED DEVICE CLIENT TESTS #
##############################


@pytest.mark.usefixtures("mock_mqtt_pipeline_init", "mock_http_pipeline_init")
class SharedIoTHubDeviceClientCreateFromSastokenTests(
    SharedIoTHubClientCreateMethodUserOptionTests
):
    @pytest.fixture
    def client_create_method(self, client_class):
        """Provides the specific create method for use in universal tests"""
        return client_class.create_from_sastoken

    @pytest.fixture
    def create_method_args(self, sas_token_string):
        """Provides the specific create method args for use in universal tests"""
        return [sas_token_string]

    @pytest.mark.it(
        "Creates a NonRenewableSasToken from the SAS token string provided in parameters"
    )
    def test_sastoken(self, mocker, client_class, sas_token_string):
        real_sastoken = st.NonRenewableSasToken(sas_token_string)
        sastoken_mock = mocker.patch.object(st, "NonRenewableSasToken")
        sastoken_mock.return_value = real_sastoken

        client_class.create_from_sastoken(sastoken=sas_token_string)

        # NonRenewableSasToken created from sastoken string
        assert sastoken_mock.call_count == 1
        assert sastoken_mock.call_args == mocker.call(sas_token_string)

    @pytest.mark.it(
        "Creates MQTT and HTTP pipelines with an IoTHubPipelineConfig object containing the SasToken and values extracted from the SasToken"
    )
    def test_pipeline_config(
        self,
        mocker,
        client_class,
        sas_token_string,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        real_sastoken = st.NonRenewableSasToken(sas_token_string)
        sastoken_mock = mocker.patch.object(st, "NonRenewableSasToken")
        sastoken_mock.return_value = real_sastoken
        client_class.create_from_sastoken(sas_token_string)

        token_uri_pieces = real_sastoken.resource_uri.split("/")
        expected_hostname = token_uri_pieces[0]
        expected_device_id = token_uri_pieces[2]

        # Verify pipelines created with an IoTHubPipelineConfig
        assert mock_mqtt_pipeline_init.call_count == 1
        assert mock_http_pipeline_init.call_count == 1
        assert mock_mqtt_pipeline_init.call_args[0][0] is mock_http_pipeline_init.call_args[0][0]
        assert isinstance(mock_mqtt_pipeline_init.call_args[0][0], IoTHubPipelineConfig)

        # Verify the IoTHubPipelineConfig is constructed as expected
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert config.device_id == expected_device_id
        assert config.module_id == ""
        assert config.hostname == expected_hostname
        assert config.gateway_hostname is None
        assert config.sastoken is sastoken_mock.return_value
        assert config.blob_upload is True
        assert config.method_invoke is False

    @pytest.mark.it(
        "Returns an instance of an IoTHubDeviceClient using the created MQTT and HTTP pipelines"
    )
    def test_client_returned(
        self,
        mocker,
        client_class,
        sas_token_string,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        client = client_class.create_from_sastoken(sastoken=sas_token_string)
        assert isinstance(client, client_class)
        assert client._mqtt_pipeline is mock_mqtt_pipeline_init.return_value
        assert client._http_pipeline is mock_http_pipeline_init.return_value

    @pytest.mark.it("Raises ValueError if NonRenewableSasToken creation results in failure")
    def test_raises_value_error_on_sastoken_failure(self, sas_token_string, mocker, client_class):
        # NOTE: specific inputs that could cause this are tested in the sastoken test module
        sastoken_mock = mocker.patch.object(st, "NonRenewableSasToken")
        token_err = st.SasTokenError("Some SasToken failure")
        sastoken_mock.side_effect = token_err

        with pytest.raises(ValueError) as e_info:
            client_class.create_from_sastoken(sastoken=sas_token_string)
        assert e_info.value.__cause__ is token_err

    @pytest.mark.it("Raises ValueError if the provided SAS token string has an invalid URI")
    @pytest.mark.parametrize(
        "invalid_token_uri",
        [
            pytest.param("some.hostname/devices", id="Too short"),
            pytest.param("some.hostname/devices/my_device/somethingElse", id="Too long"),
            pytest.param(
                "some.hostname/not-devices/device_id", id="Incorrectly formatted device notation"
            ),
            pytest.param("some.hostname/devices/my_device/modules/my_module", id="Module URI"),
        ],
    )
    def test_raises_value_error_invalid_uri(self, mocker, client_class, invalid_token_uri):
        sastoken_str = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}".format(
            resource=urllib.parse.quote(invalid_token_uri, safe=""),
            signature=urllib.parse.quote("ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI=", safe=""),
            expiry=int(time.time() + 3600),
        )

        with pytest.raises(ValueError):
            client_class.create_from_sastoken(sastoken=sastoken_str)

    @pytest.mark.it("Raises ValueError if the provided SAS token string has already expired")
    def test_expired_token(self, mocker, client_class):
        sastoken_str = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}".format(
            resource=urllib.parse.quote("some.hostname/devices/my_device", safe=""),
            signature=urllib.parse.quote("ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI=", safe=""),
            expiry=int(time.time() - 3600),  # expired
        )

        with pytest.raises(ValueError):
            client_class.create_from_sastoken(sastoken=sastoken_str)

    @pytest.mark.it("Raises a TypeError if the 'sastoken_ttl' kwarg is supplied by the user")
    def test_sastoken_ttl(self, client_class, sas_token_string):
        with pytest.raises(TypeError):
            client_class.create_from_sastoken(sastoken=sas_token_string, sastoken_ttl=1000)


@pytest.mark.usefixtures("mock_mqtt_pipeline_init", "mock_http_pipeline_init")
class SharedIoTHubDeviceClientCreateFromSymmetricKeyTests(
    SharedIoTHubClientCreateMethodUserOptionTests
):
    hostname = "durmstranginstitute.farend"
    device_id = "MySnitch"
    symmetric_key = "Zm9vYmFy"

    @pytest.fixture
    def client_create_method(self, client_class):
        """Provides the specific create method for use in universal tests"""
        return client_class.create_from_symmetric_key

    @pytest.fixture
    def create_method_args(self):
        """Provides the specific create method args for use in universal tests"""
        return [self.symmetric_key, self.hostname, self.device_id]

    @pytest.mark.it(
        "Creates a SasToken that uses a SymmetricKeySigningMechanism, from the values provided in parameters"
    )
    def test_sastoken(self, mocker, client_class):
        sksm_mock = mocker.patch.object(auth, "SymmetricKeySigningMechanism")
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")
        expected_uri = "{hostname}/devices/{device_id}".format(
            hostname=self.hostname, device_id=self.device_id
        )

        custom_ttl = 1000
        client_class.create_from_symmetric_key(
            symmetric_key=self.symmetric_key,
            hostname=self.hostname,
            device_id=self.device_id,
            sastoken_ttl=custom_ttl,
        )

        # SymmetricKeySigningMechanism created using the provided symmetric key
        assert sksm_mock.call_count == 1
        assert sksm_mock.call_args == mocker.call(key=self.symmetric_key)

        # SasToken created with the SymmetricKeySigningMechanism, the expected URI, and the custom ttl
        assert sastoken_mock.call_count == 1
        assert sastoken_mock.call_args == mocker.call(
            expected_uri, sksm_mock.return_value, ttl=custom_ttl
        )

    @pytest.mark.it(
        "Uses 3600 seconds (1 hour) as the default SasToken TTL if no custom TTL is provided"
    )
    def test_sastoken_default(self, mocker, client_class):
        sksm_mock = mocker.patch.object(auth, "SymmetricKeySigningMechanism")
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")
        expected_uri = "{hostname}/devices/{device_id}".format(
            hostname=self.hostname, device_id=self.device_id
        )

        client_class.create_from_symmetric_key(
            symmetric_key=self.symmetric_key, hostname=self.hostname, device_id=self.device_id
        )

        # SymmetricKeySigningMechanism created using the provided symmetric key
        assert sksm_mock.call_count == 1
        assert sksm_mock.call_args == mocker.call(key=self.symmetric_key)

        # SasToken created with the SymmetricKeySigningMechanism, the expected URI, and the default ttl
        assert sastoken_mock.call_count == 1
        assert sastoken_mock.call_args == mocker.call(
            expected_uri, sksm_mock.return_value, ttl=3600
        )

    @pytest.mark.it(
        "Creates MQTT and HTTP pipelines with an IoTHubPipelineConfig object containing the SasToken and values provided in parameters"
    )
    def test_pipeline_config(
        self, mocker, client_class, mock_mqtt_pipeline_init, mock_http_pipeline_init
    ):
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")

        client_class.create_from_symmetric_key(
            symmetric_key=self.symmetric_key, hostname=self.hostname, device_id=self.device_id
        )

        # Verify pipelines created with an IoTHubPipelineConfig
        assert mock_mqtt_pipeline_init.call_count == 1
        assert mock_http_pipeline_init.call_count == 1
        assert mock_mqtt_pipeline_init.call_args[0][0] is mock_http_pipeline_init.call_args[0][0]
        assert isinstance(mock_mqtt_pipeline_init.call_args[0][0], IoTHubPipelineConfig)

        # Verify the IoTHubPipelineConfig is constructed as expected
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert config.device_id == self.device_id
        assert config.hostname == self.hostname
        assert config.gateway_hostname is None
        assert config.sastoken is sastoken_mock.return_value
        assert config.blob_upload is True
        assert config.method_invoke is False

    @pytest.mark.it(
        "Returns an instance of an IoTHubDeviceClient using the created MQTT and HTTP pipelines"
    )
    def test_client_returned(
        self, mocker, client_class, mock_mqtt_pipeline_init, mock_http_pipeline_init
    ):
        client = client_class.create_from_symmetric_key(
            symmetric_key=self.symmetric_key, hostname=self.hostname, device_id=self.device_id
        )
        assert isinstance(client, client_class)
        assert client._mqtt_pipeline is mock_mqtt_pipeline_init.return_value
        assert client._http_pipeline is mock_http_pipeline_init.return_value

    @pytest.mark.it("Raises ValueError if a SasToken creation results in failure")
    def test_raises_value_error_on_sastoken_failure(self, mocker, client_class):
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")
        token_err = st.SasTokenError("Some SasToken failure")
        sastoken_mock.side_effect = token_err

        with pytest.raises(ValueError) as e_info:
            client_class.create_from_symmetric_key(
                symmetric_key=self.symmetric_key, hostname=self.hostname, device_id=self.device_id
            )
        assert e_info.value.__cause__ is token_err


@pytest.mark.usefixtures("mock_mqtt_pipeline_init", "mock_http_pipeline_init")
class SharedIoTHubDeviceClientCreateFromX509CertificateTests(
    SharedIoTHubClientCreateMethodUserOptionTests
):
    hostname = "durmstranginstitute.farend"
    device_id = "MySnitch"

    @pytest.fixture
    def client_create_method(self, client_class):
        """Provides the specific create method for use in universal tests"""
        return client_class.create_from_x509_certificate

    @pytest.fixture
    def create_method_args(self, x509):
        """Provides the specific create method args for use in universal tests"""
        return [x509, self.hostname, self.device_id]

    @pytest.mark.it(
        "Creates MQTT and HTTP pipelines with an IoTHubPipelineConfig object containing the X509 and other values provided in parameters"
    )
    def test_pipeline_config(
        self, mocker, client_class, x509, mock_mqtt_pipeline_init, mock_http_pipeline_init
    ):
        client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id
        )

        # Verify pipelines created with an IoTHubPipelineConfig
        assert mock_mqtt_pipeline_init.call_count == 1
        assert mock_http_pipeline_init.call_count == 1
        assert mock_mqtt_pipeline_init.call_args[0][0] == mock_http_pipeline_init.call_args[0][0]
        assert isinstance(mock_mqtt_pipeline_init.call_args[0][0], IoTHubPipelineConfig)

        # Verify the IoTHubPipelineConfig is constructed as expected
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert config.device_id == self.device_id
        assert config.hostname == self.hostname
        assert config.gateway_hostname is None
        assert config.x509 is x509
        assert config.blob_upload is True
        assert config.method_invoke is False

    @pytest.mark.it(
        "Returns an instance of an IoTHubDeviceclient using the created MQTT and HTTP pipelines"
    )
    def test_client_returned(
        self, mocker, client_class, x509, mock_mqtt_pipeline_init, mock_http_pipeline_init
    ):
        client = client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id
        )
        assert isinstance(client, client_class)
        assert client._mqtt_pipeline is mock_mqtt_pipeline_init.return_value
        assert client._http_pipeline is mock_http_pipeline_init.return_value

    @pytest.mark.it("Raises a TypeError if the 'sastoken_ttl' kwarg is supplied by the user")
    def test_sastoken_ttl(self, client_class, x509):
        with pytest.raises(TypeError):
            client_class.create_from_x509_certificate(
                x509=x509, hostname=self.hostname, device_id=self.device_id, sastoken_ttl=1000
            )


##############################
# SHARED MODULE CLIENT TESTS #
##############################


@pytest.mark.usefixtures("mock_mqtt_pipeline_init", "mock_http_pipeline_init")
class SharedIoTHubModuleClientCreateFromSastokenTests(
    SharedIoTHubClientCreateMethodUserOptionTests
):
    @pytest.fixture
    def client_create_method(self, client_class):
        """Provides the specific create method for use in universal tests"""
        return client_class.create_from_sastoken

    @pytest.fixture
    def create_method_args(self, sas_token_string):
        """Provides the specific create method args for use in universal tests"""
        return [sas_token_string]

    @pytest.mark.it(
        "Creates a NonRenewableSasToken from the SAS token string provided in parameters"
    )
    def test_sastoken(self, mocker, client_class, sas_token_string):
        real_sastoken = st.NonRenewableSasToken(sas_token_string)
        sastoken_mock = mocker.patch.object(st, "NonRenewableSasToken")
        sastoken_mock.return_value = real_sastoken

        client_class.create_from_sastoken(sastoken=sas_token_string)

        # NonRenewableSasToken created from sastoken string
        assert sastoken_mock.call_count == 1
        assert sastoken_mock.call_args == mocker.call(sas_token_string)

    @pytest.mark.it(
        "Creates MQTT and HTTP pipelines with an IoTHubPipelineConfig object containing the SasToken and values extracted from the SasToken"
    )
    def test_pipeline_config(
        self,
        mocker,
        client_class,
        sas_token_string,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        real_sastoken = st.NonRenewableSasToken(sas_token_string)
        sastoken_mock = mocker.patch.object(st, "NonRenewableSasToken")
        sastoken_mock.return_value = real_sastoken
        client_class.create_from_sastoken(sastoken=sas_token_string)

        token_uri_pieces = real_sastoken.resource_uri.split("/")
        expected_hostname = token_uri_pieces[0]
        expected_device_id = token_uri_pieces[2]
        expected_module_id = token_uri_pieces[4]

        # Verify pipelines created with an IoTHubPipelineConfig
        assert mock_mqtt_pipeline_init.call_count == 1
        assert mock_http_pipeline_init.call_count == 1
        assert mock_mqtt_pipeline_init.call_args[0][0] is mock_http_pipeline_init.call_args[0][0]
        assert isinstance(mock_mqtt_pipeline_init.call_args[0][0], IoTHubPipelineConfig)

        # Verify the IoTHubPipelineConfig is constructed as expected
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert config.device_id == expected_device_id
        assert config.module_id == expected_module_id
        assert config.hostname == expected_hostname
        assert config.gateway_hostname is None
        assert config.sastoken is sastoken_mock.return_value
        assert config.blob_upload is False
        assert config.method_invoke is False

    @pytest.mark.it(
        "Returns an instance of an IoTHubModuleClient using the created MQTT and HTTP pipelines"
    )
    def test_client_returned(
        self,
        mocker,
        client_class,
        sas_token_string,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        client = client_class.create_from_sastoken(sastoken=sas_token_string)
        assert isinstance(client, client_class)
        assert client._mqtt_pipeline is mock_mqtt_pipeline_init.return_value
        assert client._http_pipeline is mock_http_pipeline_init.return_value

    @pytest.mark.it("Raises ValueError if NonRenewableSasToken creation results in failure")
    def test_raises_value_error_on_sastoken_failure(self, mocker, client_class, sas_token_string):
        # NOTE: specific inputs that could cause this are tested in the sastoken test module
        sastoken_mock = mocker.patch.object(st, "NonRenewableSasToken")
        token_err = st.SasTokenError("Some SasToken failure")
        sastoken_mock.side_effect = token_err

        with pytest.raises(ValueError) as e_info:
            client_class.create_from_sastoken(sastoken=sas_token_string)
        assert e_info.value.__cause__ is token_err

    @pytest.mark.it("Raises ValueError if the provided SAS token string has an invalid URI")
    @pytest.mark.parametrize(
        "invalid_token_uri",
        [
            pytest.param("some.hostname/devices/my_device/modules/", id="Too short"),
            pytest.param(
                "some.hostname/devices/my_device/modules/my_module/somethingElse", id="Too long"
            ),
            pytest.param(
                "some.hostname/not-devices/device_id/modules/module_id",
                id="Incorrectly formatted device notation",
            ),
            pytest.param(
                "some.hostname/devices/device_id/not-modules/module_id",
                id="Incorrectly formatted module notation",
            ),
            pytest.param("some.hostname/devices/my_device/", id="Device URI"),
        ],
    )
    def test_raises_value_error_invalid_uri(self, mocker, client_class, invalid_token_uri):
        sastoken_str = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}".format(
            resource=urllib.parse.quote(invalid_token_uri, safe=""),
            signature=urllib.parse.quote("ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI=", safe=""),
            expiry=int(time.time() + 3600),
        )

        with pytest.raises(ValueError):
            client_class.create_from_sastoken(sastoken=sastoken_str)

    @pytest.mark.it("Raises ValueError if the provided SAS token string has already expired")
    def test_expired_token(self, mocker, client_class):
        sastoken_str = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}".format(
            resource=urllib.parse.quote(
                "some.hostname/devices/my_device/modules/my_module", safe=""
            ),
            signature=urllib.parse.quote("ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI=", safe=""),
            expiry=int(time.time() - 3600),  # expired
        )

        with pytest.raises(ValueError):
            client_class.create_from_sastoken(sastoken=sastoken_str)

    @pytest.mark.it("Raises a TypeError if the 'sastoken_ttl' kwarg is supplied by the user")
    def test_sastoken_ttl(self, client_class, sas_token_string):
        with pytest.raises(TypeError):
            client_class.create_from_sastoken(sastoken=sas_token_string, sastoken_ttl=1000)


@pytest.mark.usefixtures("mock_mqtt_pipeline_init", "mock_http_pipeline_init")
class SharedIoTHubModuleClientCreateFromX509CertificateTests(
    SharedIoTHubClientCreateMethodUserOptionTests
):
    hostname = "durmstranginstitute.farend"
    device_id = "MySnitch"
    module_id = "Charms"

    @pytest.fixture
    def client_create_method(self, client_class):
        """Provides the specific create method for use in universal tests"""
        return client_class.create_from_x509_certificate

    @pytest.fixture
    def create_method_args(self, x509):
        """Provides the specific create method args for use in universal tests"""
        return [x509, self.hostname, self.device_id, self.module_id]

    @pytest.mark.it(
        "Creates MQTT and HTTP pipelines with an IoTHubPipelineConfig object containing the X509 and other values provided in parameters"
    )
    def test_pipeline_config(
        self, mocker, client_class, x509, mock_mqtt_pipeline_init, mock_http_pipeline_init
    ):
        client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id, module_id=self.module_id
        )

        # Verify pipelines created with an IoTHubPipelineConfig
        assert mock_mqtt_pipeline_init.call_count == 1
        assert mock_http_pipeline_init.call_count == 1
        assert mock_mqtt_pipeline_init.call_args[0][0] == mock_http_pipeline_init.call_args[0][0]
        assert isinstance(mock_mqtt_pipeline_init.call_args[0][0], IoTHubPipelineConfig)

        # Verify the IoTHubPipelineConfig is constructed as expected
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert config.device_id == self.device_id
        assert config.hostname == self.hostname
        assert config.gateway_hostname is None
        assert config.x509 is x509
        assert config.blob_upload is False
        assert config.method_invoke is False

    @pytest.mark.it(
        "Returns an instance of an IoTHubDeviceclient using the created MQTT and HTTP pipelines"
    )
    def test_client_returned(
        self, mocker, client_class, x509, mock_mqtt_pipeline_init, mock_http_pipeline_init
    ):
        client = client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id, module_id=self.module_id
        )
        assert isinstance(client, client_class)
        assert client._mqtt_pipeline is mock_mqtt_pipeline_init.return_value
        assert client._http_pipeline is mock_http_pipeline_init.return_value

    @pytest.mark.it("Raises a TypeError if the 'sastoken_ttl' kwarg is supplied by the user")
    def test_sastoken_ttl(self, client_class, x509):
        with pytest.raises(TypeError):
            client_class.create_from_x509_certificate(
                x509=x509, hostname=self.hostname, device_id=self.device_id, sastoken_ttl=1000
            )


@pytest.mark.usefixtures("mock_mqtt_pipeline_init", "mock_http_pipeline_init")
class SharedIoTHubModuleClientClientCreateFromEdgeEnvironmentUserOptionTests(
    SharedIoTHubClientCreateMethodUserOptionTests
):
    """This class inherits the user option tests shared by all create method APIs, and overrides
    tests in order to accommodate unique requirements for the .create_from_edge_environment() method.

    Because .create_from_edge_environment() tests are spread across multiple test units
    (i.e. test classes), these overrides are done in this class, which is then inherited by all
    .create_from_edge_environment() test units below.
    """

    @pytest.fixture
    def client_create_method(self, client_class):
        """Provides the specific create method for use in universal tests"""
        return client_class.create_from_edge_environment

    @pytest.fixture
    def create_method_args(self):
        """Provides the specific create method args for use in universal tests"""
        return []

    @pytest.mark.it(
        "Raises a TypeError if the 'server_verification_cert' user option parameter is provided"
    )
    def test_server_verification_cert_option(
        self,
        option_test_required_patching,
        client_create_method,
        create_method_args,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        """THIS TEST OVERRIDES AN INHERITED TEST"""
        # Override to test that server_verification_cert CANNOT be provided in Edge scenarios

        with pytest.raises(TypeError):
            client_create_method(
                *create_method_args, server_verification_cert="fake_server_verification_cert"
            )

    @pytest.mark.it(
        "Raises a TypeError if the 'gateway_hostname' user option parameter is provided"
    )
    def test_gateway_hostname_option(
        self,
        option_test_required_patching,
        client_create_method,
        create_method_args,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        """THIS TEST OVERRIDES AN INHERITED TEST"""
        # Override to test that gateway_hostname CANNOT be provided in Edge scenarios

        with pytest.raises(TypeError):
            client_create_method(*create_method_args, gateway_hostname="my.gateway.device")

    @pytest.mark.it("Sets default user options if none are provided")
    def test_default_options(
        self,
        mocker,
        option_test_required_patching,
        client_create_method,
        create_method_args,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        """THIS TEST OVERRIDES AN INHERITED TEST"""
        # Override so that can avoid the check on server_verification_cert being None
        # as in Edge scenarios, it is not None

        client_create_method(*create_method_args)

        # Both pipelines use the same IoTHubPipelineConfig
        assert mock_mqtt_pipeline_init.call_count == 1
        assert mock_http_pipeline_init.call_count == 1
        assert mock_mqtt_pipeline_init.call_args[0][0] is mock_http_pipeline_init.call_args[0][0]
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert isinstance(config, IoTHubPipelineConfig)

        # Pipeline Config has default options that were not specified
        assert config.product_info == ""
        assert config.websockets is False
        assert config.cipher == ""
        assert config.proxy_options is None
        assert config.keep_alive == DEFAULT_KEEPALIVE


@pytest.mark.usefixtures("mock_mqtt_pipeline_init", "mock_http_pipeline_init")
class SharedIoTHubModuleClientCreateFromEdgeEnvironmentWithContainerEnvTests(
    SharedIoTHubModuleClientClientCreateFromEdgeEnvironmentUserOptionTests
):
    @pytest.fixture
    def option_test_required_patching(self, mocker, mock_edge_hsm, edge_container_environment):
        """THIS FIXTURE OVERRIDES AN INHERITED FIXTURE"""
        mocker.patch.dict(os.environ, edge_container_environment, clear=True)

    @pytest.mark.it(
        "Creates a SasToken that uses an IoTEdgeHsm, from the values extracted from the Edge environment and the user-provided TTL"
    )
    def test_sastoken(self, mocker, client_class, mock_edge_hsm, edge_container_environment):
        mocker.patch.dict(os.environ, edge_container_environment, clear=True)
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")

        expected_uri = "{hostname}/devices/{device_id}/modules/{module_id}".format(
            hostname=edge_container_environment["IOTEDGE_IOTHUBHOSTNAME"],
            device_id=edge_container_environment["IOTEDGE_DEVICEID"],
            module_id=edge_container_environment["IOTEDGE_MODULEID"],
        )

        custom_ttl = 1000
        client_class.create_from_edge_environment(sastoken_ttl=custom_ttl)

        # IoTEdgeHsm created using the extracted values
        assert mock_edge_hsm.call_count == 1
        assert mock_edge_hsm.call_args == mocker.call(
            module_id=edge_container_environment["IOTEDGE_MODULEID"],
            generation_id=edge_container_environment["IOTEDGE_MODULEGENERATIONID"],
            workload_uri=edge_container_environment["IOTEDGE_WORKLOADURI"],
            api_version=edge_container_environment["IOTEDGE_APIVERSION"],
        )

        # SasToken created with the IoTEdgeHsm, the expected URI and the custom ttl
        assert sastoken_mock.call_count == 1
        assert sastoken_mock.call_args == mocker.call(
            expected_uri, mock_edge_hsm.return_value, ttl=custom_ttl
        )

    @pytest.mark.it(
        "Uses 3600 seconds (1 hour) as the default SasToken TTL if no custom TTL is provided"
    )
    def test_sastoken_default(
        self, mocker, client_class, mock_edge_hsm, edge_container_environment
    ):
        mocker.patch.dict(os.environ, edge_container_environment, clear=True)
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")

        expected_uri = "{hostname}/devices/{device_id}/modules/{module_id}".format(
            hostname=edge_container_environment["IOTEDGE_IOTHUBHOSTNAME"],
            device_id=edge_container_environment["IOTEDGE_DEVICEID"],
            module_id=edge_container_environment["IOTEDGE_MODULEID"],
        )

        client_class.create_from_edge_environment()

        # IoTEdgeHsm created using the extracted values
        assert mock_edge_hsm.call_count == 1
        assert mock_edge_hsm.call_args == mocker.call(
            module_id=edge_container_environment["IOTEDGE_MODULEID"],
            generation_id=edge_container_environment["IOTEDGE_MODULEGENERATIONID"],
            workload_uri=edge_container_environment["IOTEDGE_WORKLOADURI"],
            api_version=edge_container_environment["IOTEDGE_APIVERSION"],
        )

        # SasToken created with the IoTEdgeHsm, the expected URI, and the default ttl
        assert sastoken_mock.call_count == 1
        assert sastoken_mock.call_args == mocker.call(
            expected_uri, mock_edge_hsm.return_value, ttl=3600
        )

    @pytest.mark.it(
        "Uses an IoTEdgeHsm as the SasToken signing mechanism even if any Edge local debug environment variables may also be present"
    )
    def test_hybrid_env(
        self,
        mocker,
        client_class,
        mock_edge_hsm,
        edge_container_environment,
        edge_local_debug_environment,
    ):
        hybrid_environment = merge_dicts(edge_container_environment, edge_local_debug_environment)
        mocker.patch.dict(os.environ, hybrid_environment, clear=True)
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")
        mock_sksm = mocker.patch.object(auth, "SymmetricKeySigningMechanism")

        client_class.create_from_edge_environment()

        assert mock_sksm.call_count == 0  # we did NOT use SK signing mechanism
        assert mock_edge_hsm.call_count == 1  # instead, we still used edge hsm
        assert mock_edge_hsm.call_args == mocker.call(
            module_id=edge_container_environment["IOTEDGE_MODULEID"],
            generation_id=edge_container_environment["IOTEDGE_MODULEGENERATIONID"],
            workload_uri=edge_container_environment["IOTEDGE_WORKLOADURI"],
            api_version=edge_container_environment["IOTEDGE_APIVERSION"],
        )
        assert sastoken_mock.call_count == 1
        assert sastoken_mock.call_args == mocker.call(
            mocker.ANY, mock_edge_hsm.return_value, ttl=3600
        )

    @pytest.mark.it(
        "Creates MQTT and HTTP pipelines with an IoTHubPipelineConfig object containing the SasToken and values extracted from the Edge environment"
    )
    def test_pipeline_config(
        self,
        mocker,
        client_class,
        mock_edge_hsm,
        edge_container_environment,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        mocker.patch.dict(os.environ, edge_container_environment, clear=True)
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")

        client_class.create_from_edge_environment()

        # Verify pipelines created with an IoTHubPipelineConfig
        assert mock_mqtt_pipeline_init.call_count == 1
        assert mock_http_pipeline_init.call_count == 1
        assert mock_mqtt_pipeline_init.call_args[0][0] is mock_http_pipeline_init.call_args[0][0]
        assert isinstance(mock_mqtt_pipeline_init.call_args[0][0], IoTHubPipelineConfig)

        # Verify the IoTHubPipelineConfig is constructed as expected
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert config.device_id == edge_container_environment["IOTEDGE_DEVICEID"]
        assert config.module_id == edge_container_environment["IOTEDGE_MODULEID"]
        assert config.hostname == edge_container_environment["IOTEDGE_IOTHUBHOSTNAME"]
        assert config.gateway_hostname == edge_container_environment["IOTEDGE_GATEWAYHOSTNAME"]
        assert config.sastoken is sastoken_mock.return_value
        assert (
            config.server_verification_cert
            == mock_edge_hsm.return_value.get_certificate.return_value
        )
        assert config.method_invoke is True
        assert config.blob_upload is False

    @pytest.mark.it(
        "Returns an instance of an IoTHubModuleClient using the created MQTT and HTTP pipelines"
    )
    def test_client_returns(
        self,
        mocker,
        client_class,
        mock_edge_hsm,
        edge_container_environment,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        mocker.patch.dict(os.environ, edge_container_environment, clear=True)

        client = client_class.create_from_edge_environment()
        assert isinstance(client, client_class)
        assert client._mqtt_pipeline is mock_mqtt_pipeline_init.return_value
        assert client._http_pipeline is mock_http_pipeline_init.return_value

    @pytest.mark.it("Raises OSError if the environment is missing required variables")
    @pytest.mark.parametrize(
        "missing_env_var",
        [
            "IOTEDGE_MODULEID",
            "IOTEDGE_DEVICEID",
            "IOTEDGE_IOTHUBHOSTNAME",
            "IOTEDGE_GATEWAYHOSTNAME",
            "IOTEDGE_APIVERSION",
            "IOTEDGE_MODULEGENERATIONID",
            "IOTEDGE_WORKLOADURI",
        ],
    )
    def test_bad_environment(
        self, mocker, client_class, edge_container_environment, missing_env_var
    ):
        # Remove a variable from the fixture
        del edge_container_environment[missing_env_var]
        mocker.patch.dict(os.environ, edge_container_environment, clear=True)

        with pytest.raises(OSError):
            client_class.create_from_edge_environment()

    @pytest.mark.it(
        "Raises OSError if there is an error retrieving the server verification certificate from Edge with the IoTEdgeHsm"
    )
    def test_bad_edge_auth(self, mocker, client_class, edge_container_environment, mock_edge_hsm):
        mocker.patch.dict(os.environ, edge_container_environment, clear=True)
        my_edge_error = edge_hsm.IoTEdgeError()
        mock_edge_hsm.return_value.get_certificate.side_effect = my_edge_error

        with pytest.raises(OSError) as e_info:
            client_class.create_from_edge_environment()
        assert e_info.value.__cause__ is my_edge_error

    @pytest.mark.it("Raises ValueError if a SasToken creation results in failure")
    def test_raises_value_error_on_sastoken_failure(
        self, mocker, client_class, edge_container_environment, mock_edge_hsm
    ):
        mocker.patch.dict(os.environ, edge_container_environment, clear=True)
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")
        token_err = st.SasTokenError("Some SasToken failure")
        sastoken_mock.side_effect = token_err

        with pytest.raises(ValueError) as e_info:
            client_class.create_from_edge_environment()
        assert e_info.value.__cause__ is token_err


@pytest.mark.usefixtures("mock_mqtt_pipeline_init", "mock_http_pipeline_init")
class SharedIoTHubModuleClientCreateFromEdgeEnvironmentWithDebugEnvTests(
    SharedIoTHubModuleClientClientCreateFromEdgeEnvironmentUserOptionTests
):
    @pytest.fixture
    def option_test_required_patching(self, mocker, mock_open, edge_local_debug_environment):
        """THIS FIXTURE OVERRIDES AN INHERITED FIXTURE"""
        mocker.patch.dict(os.environ, edge_local_debug_environment, clear=True)

    @pytest.fixture
    def mock_open(self, mocker):
        return mocker.patch.object(io, "open")

    @pytest.mark.it(
        "Creates a SasToken that uses a SymmetricKeySigningMechanism, from the values in the connection string extracted from the Edge local debug environment, as well as the user-provided TTL"
    )
    def test_sastoken(self, mocker, client_class, mock_open, edge_local_debug_environment):
        mocker.patch.dict(os.environ, edge_local_debug_environment, clear=True)
        sksm_mock = mocker.patch.object(auth, "SymmetricKeySigningMechanism")
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")
        cs_obj = cs.ConnectionString(edge_local_debug_environment["EdgeHubConnectionString"])
        expected_uri = "{hostname}/devices/{device_id}/modules/{module_id}".format(
            hostname=cs_obj[cs.HOST_NAME],
            device_id=cs_obj[cs.DEVICE_ID],
            module_id=cs_obj[cs.MODULE_ID],
        )

        custom_ttl = 1000
        client_class.create_from_edge_environment(sastoken_ttl=custom_ttl)

        # SymmetricKeySigningMechanism created using the connection string's Shared Access Key
        assert sksm_mock.call_count == 1
        assert sksm_mock.call_args == mocker.call(key=cs_obj[cs.SHARED_ACCESS_KEY])

        # SasToken created with the SymmetricKeySigningMechanism, the expected URI, and the custom ttl
        assert sastoken_mock.call_count == 1
        assert sastoken_mock.call_args == mocker.call(
            expected_uri, sksm_mock.return_value, ttl=custom_ttl
        )

    @pytest.mark.it(
        "Uses 3600 seconds (1 hour) as the default SasToken TTL if no custom TTL is provided"
    )
    def test_sastoken_default(self, mocker, client_class, mock_open, edge_local_debug_environment):
        mocker.patch.dict(os.environ, edge_local_debug_environment, clear=True)
        sksm_mock = mocker.patch.object(auth, "SymmetricKeySigningMechanism")
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")
        cs_obj = cs.ConnectionString(edge_local_debug_environment["EdgeHubConnectionString"])
        expected_uri = "{hostname}/devices/{device_id}/modules/{module_id}".format(
            hostname=cs_obj[cs.HOST_NAME],
            device_id=cs_obj[cs.DEVICE_ID],
            module_id=cs_obj[cs.MODULE_ID],
        )

        client_class.create_from_edge_environment()

        # SymmetricKeySigningMechanism created using the connection string's Shared Access Key
        assert sksm_mock.call_count == 1
        assert sksm_mock.call_args == mocker.call(key=cs_obj[cs.SHARED_ACCESS_KEY])

        # SasToken created with the SymmetricKeySigningMechanism, the expected URI and default ttl
        assert sastoken_mock.call_count == 1
        assert sastoken_mock.call_args == mocker.call(
            expected_uri, sksm_mock.return_value, ttl=3600
        )

    @pytest.mark.it(
        "Only uses Edge local debug variables if no Edge container variables are present in the environment"
    )
    def test_auth_provider_and_pipeline_hybrid_env(
        self,
        mocker,
        client_class,
        edge_container_environment,
        edge_local_debug_environment,
        mock_open,
        mock_edge_hsm,
    ):
        # This test verifies that the presence of edge container environment variables means the
        # code will follow the edge container environment creation path (using the IoTEdgeHsm)
        # even if edge local debug variables are present.
        hybrid_environment = merge_dicts(edge_container_environment, edge_local_debug_environment)
        mocker.patch.dict(os.environ, hybrid_environment, clear=True)
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")
        sksm_mock = mocker.patch.object(auth, "SymmetricKeySigningMechanism")

        client_class.create_from_edge_environment()

        assert sksm_mock.call_count == 0  # we did NOT use SK signing mechanism
        assert mock_edge_hsm.call_count == 1  # instead, we still used edge HSM
        assert mock_edge_hsm.call_args == mocker.call(
            module_id=edge_container_environment["IOTEDGE_MODULEID"],
            generation_id=edge_container_environment["IOTEDGE_MODULEGENERATIONID"],
            workload_uri=edge_container_environment["IOTEDGE_WORKLOADURI"],
            api_version=edge_container_environment["IOTEDGE_APIVERSION"],
        )
        assert sastoken_mock.call_count == 1
        assert sastoken_mock.call_args == mocker.call(
            mocker.ANY, mock_edge_hsm.return_value, ttl=3600
        )

    @pytest.mark.it(
        "Extracts the server verification certificate from the file indicated by the filepath extracted from the Edge local debug environment"
    )
    def test_open_ca_cert(self, mocker, client_class, edge_local_debug_environment, mock_open):
        mock_file_handle = mock_open.return_value.__enter__.return_value
        mocker.patch.dict(os.environ, edge_local_debug_environment, clear=True)

        client_class.create_from_edge_environment()

        assert mock_open.call_count == 1
        assert mock_open.call_args == mocker.call(
            edge_local_debug_environment["EdgeModuleCACertificateFile"], mode="r"
        )
        assert mock_file_handle.read.call_count == 1
        assert mock_file_handle.read.call_args == mocker.call()

    @pytest.mark.it(
        "Creates MQTT and HTTP pipelines with an IoTHubPipelineConfig object containing the SasToken and values extracted from the Edge local debug environment"
    )
    def test_pipeline_config(
        self,
        mocker,
        client_class,
        mock_open,
        edge_local_debug_environment,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        mocker.patch.dict(os.environ, edge_local_debug_environment, clear=True)
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")
        mock_file_handle = mock_open.return_value.__enter__.return_value
        ca_cert_file_contents = "some cert"
        mock_file_handle.read.return_value = ca_cert_file_contents

        cs_obj = cs.ConnectionString(edge_local_debug_environment["EdgeHubConnectionString"])

        client_class.create_from_edge_environment()

        # Verify pipelines created with an IoTHubPipelineConfig
        assert mock_mqtt_pipeline_init.call_count == 1
        assert mock_http_pipeline_init.call_count == 1
        assert mock_mqtt_pipeline_init.call_args[0][0] is mock_http_pipeline_init.call_args[0][0]
        assert isinstance(mock_mqtt_pipeline_init.call_args[0][0], IoTHubPipelineConfig)

        # Verify the IoTHubPipelineConfig is constructed as expected
        config = mock_mqtt_pipeline_init.call_args[0][0]
        assert config.device_id == cs_obj[cs.DEVICE_ID]
        assert config.module_id == cs_obj[cs.MODULE_ID]
        assert config.hostname == cs_obj[cs.HOST_NAME]
        assert config.gateway_hostname == cs_obj[cs.GATEWAY_HOST_NAME]
        assert config.sastoken is sastoken_mock.return_value
        assert config.server_verification_cert == ca_cert_file_contents
        assert config.method_invoke is True
        assert config.blob_upload is False

    @pytest.mark.it(
        "Returns an instance of an IoTHub client using the created MQTT and HTTP pipelines"
    )
    def test_client_returned(
        self,
        mocker,
        client_class,
        mock_open,
        edge_local_debug_environment,
        mock_mqtt_pipeline_init,
        mock_http_pipeline_init,
    ):
        mocker.patch.dict(os.environ, edge_local_debug_environment, clear=True)

        client = client_class.create_from_edge_environment()

        assert isinstance(client, client_class)
        assert client._mqtt_pipeline is mock_mqtt_pipeline_init.return_value
        assert client._http_pipeline is mock_http_pipeline_init.return_value

    @pytest.mark.it("Raises OSError if the environment is missing required variables")
    @pytest.mark.parametrize(
        "missing_env_var", ["EdgeHubConnectionString", "EdgeModuleCACertificateFile"]
    )
    def test_bad_environment(
        self, mocker, client_class, edge_local_debug_environment, missing_env_var, mock_open
    ):
        # Remove a variable from the fixture
        del edge_local_debug_environment[missing_env_var]
        mocker.patch.dict(os.environ, edge_local_debug_environment, clear=True)

        with pytest.raises(OSError):
            client_class.create_from_edge_environment()

    @pytest.mark.it(
        "Raises ValueError if the connection string in the EdgeHubConnectionString environment variable is invalid"
    )
    @pytest.mark.parametrize(
        "bad_cs",
        [
            pytest.param("not-a-connection-string", id="Garbage string"),
            pytest.param(
                "HostName=value.domain.net;DeviceId=my_device;ModuleId=my_module;SharedAccessKey=Invalid",
                id="Shared Access Key invalid",
            ),
            pytest.param(
                "HostName=value.domain.net;WrongValue=Invalid;SharedAccessKey=Zm9vYmFy",
                id="Contains extraneous data",
            ),
            pytest.param("HostName=value.domain.net;DeviceId=my_device", id="Incomplete"),
        ],
    )
    def test_bad_connection_string(
        self, mocker, client_class, edge_local_debug_environment, bad_cs, mock_open
    ):
        edge_local_debug_environment["EdgeHubConnectionString"] = bad_cs
        mocker.patch.dict(os.environ, edge_local_debug_environment, clear=True)

        with pytest.raises(ValueError):
            client_class.create_from_edge_environment()

    @pytest.mark.it(
        "Raises FileNotFoundError if the filepath in the EdgeModuleCACertificateFile environment variable is invalid"
    )
    def test_bad_filepath(self, mocker, client_class, edge_local_debug_environment, mock_open):
        mocker.patch.dict(os.environ, edge_local_debug_environment, clear=True)
        my_fnf_error = FileNotFoundError()
        mock_open.side_effect = my_fnf_error
        with pytest.raises(FileNotFoundError) as e_info:
            client_class.create_from_edge_environment()
        assert e_info.value is my_fnf_error

    @pytest.mark.it(
        "Raises ValueError if the file referenced by the filepath in the EdgeModuleCACertificateFile environment variable cannot be opened"
    )
    def test_bad_file_io(self, mocker, client_class, edge_local_debug_environment, mock_open):
        mocker.patch.dict(os.environ, edge_local_debug_environment, clear=True)
        my_os_error = OSError()
        mock_open.side_effect = my_os_error
        with pytest.raises(ValueError) as e_info:
            client_class.create_from_edge_environment()
        assert e_info.value.__cause__ is my_os_error

    @pytest.mark.it("Raises ValueError if a SasToken creation results in failure")
    def test_raises_value_error_on_sastoken_failure(
        self, mocker, client_class, edge_local_debug_environment, mock_open
    ):
        mocker.patch.dict(os.environ, edge_local_debug_environment, clear=True)
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")
        token_err = st.SasTokenError("Some SasToken failure")
        sastoken_mock.side_effect = token_err

        with pytest.raises(ValueError) as e_info:
            client_class.create_from_edge_environment()
        assert e_info.value.__cause__ is token_err


####################
# HELPER FUNCTIONS #
####################
def merge_dicts(d1, d2):
    d3 = d1.copy()
    d3.update(d2)
    return d3
