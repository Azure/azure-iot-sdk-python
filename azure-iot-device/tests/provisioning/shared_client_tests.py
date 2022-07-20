# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains tests that are shared between sync/async clients
i.e. tests for things defined in abstract clients"""

import pytest
import logging

from azure.iot.device.common import auth, handle_exceptions
from azure.iot.device.common.auth import sastoken as st
from azure.iot.device.provisioning.pipeline import ProvisioningPipelineConfig
from azure.iot.device import ProxyOptions
from azure.iot.device.common.pipeline.config import DEFAULT_KEEPALIVE

logging.basicConfig(level=logging.DEBUG)


fake_provisioning_host = "hostname.com"
fake_registration_id = "MyRegId"
fake_id_scope = "Some0000Scope7898"
fake_symmetric_key = "Zm9vYmFy"


class SharedProvisioningClientInstantiationTests(object):
    @pytest.mark.it(
        "Stores the ProvisioningPipeline from the 'pipeline' parameter in the '_pipeline' attribute"
    )
    def test_sets_provisioning_pipeline(self, client_class, provisioning_pipeline):
        client = client_class(provisioning_pipeline)

        assert client._pipeline is provisioning_pipeline

    @pytest.mark.it(
        "Sets the pipeline's `on_background_exception` handler to the `handle_background_exception` function from the `handle_exceptions` module"
    )
    def test_pipeline_on_background_exception(self, client_class, provisioning_pipeline):
        client = client_class(provisioning_pipeline)
        assert (
            client._pipeline.on_background_exception
            is handle_exceptions.handle_background_exception
        )

    @pytest.mark.it(
        "Instantiates with the initial value of the '_provisioning_payload' attribute set to None"
    )
    def test_payload(self, client_class, provisioning_pipeline):
        client = client_class(provisioning_pipeline)

        assert client._provisioning_payload is None


class SharedProvisioningClientCreateMethodUserOptionTests(object):
    @pytest.mark.it(
        "Sets the 'server_verification_cert' user option parameter on the PipelineConfig, if provided"
    )
    def test_server_verification_cert_option(
        self, client_create_method, create_method_args, mock_pipeline_init
    ):
        server_verification_cert = "fake_server_verification_cert"
        client_create_method(*create_method_args, server_verification_cert=server_verification_cert)

        # Get configuration object
        assert mock_pipeline_init.call_count == 1
        config = mock_pipeline_init.call_args[0][0]
        assert isinstance(config, ProvisioningPipelineConfig)

        assert config.server_verification_cert == server_verification_cert

    @pytest.mark.it(
        "Sets the 'gateway_hostname' user option parameter on the PipelineConfig, if provided"
    )
    def test_gateway_hostname_option(
        self, client_create_method, create_method_args, mock_pipeline_init
    ):
        gateway_hostname = "my.gateway.hostname"
        client_create_method(*create_method_args, gateway_hostname=gateway_hostname)

        # Get configuration object
        assert mock_pipeline_init.call_count == 1
        config = mock_pipeline_init.call_args[0][0]
        assert isinstance(config, ProvisioningPipelineConfig)

        assert config.gateway_hostname == gateway_hostname

    @pytest.mark.it(
        "Sets the 'websockets' user option parameter on the PipelineConfig, if provided"
    )
    def test_websockets_option(
        self, mocker, client_create_method, create_method_args, mock_pipeline_init
    ):
        client_create_method(*create_method_args, websockets=True)

        # Get configuration object
        assert mock_pipeline_init.call_count == 1
        config = mock_pipeline_init.call_args[0][0]
        assert isinstance(config, ProvisioningPipelineConfig)

        assert config.websockets

    # TODO: Show that input in the wrong format is formatted to the correct one. This test exists
    # in the ProvisioningPipelineConfig object already, but we do not currently show that this is felt
    # from the API level.
    @pytest.mark.it("Sets the 'cipher' user option parameter on the PipelineConfig, if provided")
    def test_cipher_option(self, client_create_method, create_method_args, mock_pipeline_init):

        cipher = "DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:ECDHE-ECDSA-AES128-GCM-SHA256"
        client_create_method(*create_method_args, cipher=cipher)

        # Get configuration object
        assert mock_pipeline_init.call_count == 1
        config = mock_pipeline_init.call_args[0][0]
        assert isinstance(config, ProvisioningPipelineConfig)

        assert config.cipher == cipher

    @pytest.mark.it("Sets the 'proxy_options' user option parameter on the PipelineConfig")
    def test_proxy_options(self, client_create_method, create_method_args, mock_pipeline_init):
        proxy_options = ProxyOptions(proxy_type="HTTP", proxy_addr="127.0.0.1", proxy_port=8888)
        client_create_method(*create_method_args, proxy_options=proxy_options)

        # Get configuration object
        assert mock_pipeline_init.call_count == 1
        config = mock_pipeline_init.call_args[0][0]
        assert isinstance(config, ProvisioningPipelineConfig)

        assert config.proxy_options is proxy_options

    @pytest.mark.it(
        "Sets the 'keep_alive' user option parameter on the PipelineConfig, if provided"
    )
    def test_keep_alive_options(self, client_create_method, create_method_args, mock_pipeline_init):
        keepalive_value = 60
        client_create_method(*create_method_args, keep_alive=keepalive_value)

        # Get configuration object, and ensure it was used for both protocol pipelines
        assert mock_pipeline_init.call_count == 1
        config = mock_pipeline_init.call_args[0][0]
        assert isinstance(config, ProvisioningPipelineConfig)

        assert config.keep_alive == keepalive_value

    @pytest.mark.it("Raises a TypeError if an invalid user option parameter is provided")
    def test_invalid_option(
        self, mocker, client_create_method, create_method_args, mock_pipeline_init
    ):
        with pytest.raises(TypeError):
            client_create_method(*create_method_args, invalid_option="some_value")

    @pytest.mark.it("Sets default user options if none are provided")
    def test_default_options(
        self, mocker, client_create_method, create_method_args, mock_pipeline_init
    ):
        client_create_method(*create_method_args)

        # Pipeline uses a ProvisioningPipelineConfig
        assert mock_pipeline_init.call_count == 1
        config = mock_pipeline_init.call_args[0][0]
        assert isinstance(config, ProvisioningPipelineConfig)

        # ProvisioningPipelineConfig has default options set that were not user-specified
        assert config.server_verification_cert is None
        assert config.gateway_hostname is None
        assert config.websockets is False
        assert config.cipher == ""
        assert config.proxy_options is None
        assert config.keep_alive == DEFAULT_KEEPALIVE


@pytest.mark.usefixtures("mock_pipeline_init")
class SharedProvisioningClientCreateFromSymmetricKeyTests(
    SharedProvisioningClientCreateMethodUserOptionTests
):
    @pytest.fixture
    def client_create_method(self, client_class):
        return client_class.create_from_symmetric_key

    @pytest.fixture
    def create_method_args(self):
        return [fake_provisioning_host, fake_registration_id, fake_id_scope, fake_symmetric_key]

    @pytest.mark.it(
        "Creates a SasToken that uses a SymmetricKeySigningMechanism, from the values provided in parameters"
    )
    def test_sastoken(self, mocker, client_class):
        sksm_mock = mocker.patch.object(auth, "SymmetricKeySigningMechanism")
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")
        expected_uri = "{id_scope}/registrations/{registration_id}".format(
            id_scope=fake_id_scope, registration_id=fake_registration_id
        )

        custom_ttl = 1000
        client_class.create_from_symmetric_key(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
            symmetric_key=fake_symmetric_key,
            sastoken_ttl=custom_ttl,
        )

        # SymmetricKeySigningMechanism created using the provided symmetric key
        assert sksm_mock.call_count == 1
        assert sksm_mock.call_args == mocker.call(key=fake_symmetric_key)

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
        expected_uri = "{id_scope}/registrations/{registration_id}".format(
            id_scope=fake_id_scope, registration_id=fake_registration_id
        )

        client_class.create_from_symmetric_key(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
            symmetric_key=fake_symmetric_key,
        )

        # SymmetricKeySigningMechanism created using the provided symmetric key
        assert sksm_mock.call_count == 1
        assert sksm_mock.call_args == mocker.call(key=fake_symmetric_key)

        # SasToken created with the SymmetricKeySigningMechanism, the expected URI, and the default ttl
        assert sastoken_mock.call_count == 1
        assert sastoken_mock.call_args == mocker.call(
            expected_uri, sksm_mock.return_value, ttl=3600
        )

    @pytest.mark.it(
        "Creates an MQTT pipeline with a ProvisioningPipelineConfig object containing the SasToken and values provided in the parameters"
    )
    def test_pipeline_config(self, mocker, client_class, mock_pipeline_init):
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")

        client_class.create_from_symmetric_key(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
            symmetric_key=fake_symmetric_key,
        )

        # Verify pipeline was created with a ProvisioningPipelineConfig
        assert mock_pipeline_init.call_count == 1
        assert isinstance(mock_pipeline_init.call_args[0][0], ProvisioningPipelineConfig)

        # Verify the ProvisioningPipelineConfig is constructed as expected
        config = mock_pipeline_init.call_args[0][0]
        assert config.hostname == fake_provisioning_host
        assert config.gateway_hostname is None
        assert config.registration_id == fake_registration_id
        assert config.id_scope == fake_id_scope
        assert config.sastoken is sastoken_mock.return_value

    @pytest.mark.it(
        "Returns an instance of a ProvisioningDeviceClient using the created MQTT pipeline"
    )
    def test_client_returned(self, mocker, client_class, mock_pipeline_init):
        client = client_class.create_from_symmetric_key(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
            symmetric_key=fake_symmetric_key,
        )
        assert isinstance(client, client_class)
        assert client._pipeline is mock_pipeline_init.return_value

    @pytest.mark.it("Raises ValueError if a SasToken creation results in failure")
    def test_sastoken_failure(self, mocker, client_class):
        sastoken_mock = mocker.patch.object(st, "RenewableSasToken")
        token_err = st.SasTokenError("Some SasToken failure")
        sastoken_mock.side_effect = token_err

        with pytest.raises(ValueError) as e_info:
            client_class.create_from_symmetric_key(
                provisioning_host=fake_provisioning_host,
                registration_id=fake_registration_id,
                id_scope=fake_id_scope,
                symmetric_key=fake_symmetric_key,
            )
        assert e_info.value.__cause__ is token_err

    @pytest.mark.parametrize(
        "registration_id",
        [
            pytest.param(None, id="No Registration Id provided"),
            pytest.param(" ", id="Blank Registration Id provided"),
            pytest.param("", id="Empty Registration Id provided"),
        ],
    )
    @pytest.mark.it("Raises a ValueError if an invalid 'registration_id' parameter is provided")
    def test_invalid_registration_id(self, client_class, registration_id):
        with pytest.raises(ValueError):
            client_class.create_from_symmetric_key(
                provisioning_host=fake_provisioning_host,
                registration_id=registration_id,
                id_scope=fake_id_scope,
                symmetric_key=fake_symmetric_key,
            )


@pytest.mark.usefixtures("mock_pipeline_init")
class SharedProvisioningClientCreateFromX509CertificateTests(
    SharedProvisioningClientCreateMethodUserOptionTests
):
    @pytest.fixture
    def client_create_method(self, client_class):
        return client_class.create_from_x509_certificate

    @pytest.fixture
    def create_method_args(self, x509):
        return [fake_provisioning_host, fake_registration_id, fake_id_scope, x509]

    @pytest.mark.it(
        "Creates MQTT pipeline with a ProvisioningPipelineConfig object containing the X509 and other values provided in parameters"
    )
    def test_pipeline_config(self, mocker, client_class, x509, mock_pipeline_init):
        client_class.create_from_x509_certificate(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
            x509=x509,
        )

        # Verify pipeline created with a ProvisioningPipelineConfig
        assert mock_pipeline_init.call_count == 1
        assert isinstance(mock_pipeline_init.call_args[0][0], ProvisioningPipelineConfig)

        # Verify the ProvisioningPipelineConfig is constructed as expected
        config = mock_pipeline_init.call_args[0][0]
        assert config.hostname == fake_provisioning_host
        assert config.gateway_hostname is None
        assert config.registration_id == fake_registration_id
        assert config.id_scope == fake_id_scope
        assert config.x509 is x509

    @pytest.mark.it(
        "Returns an instance of a ProvisioningDeviceClient using the created MQTT pipeline"
    )
    def test_client_returned(self, mocker, client_class, x509, mock_pipeline_init):
        client = client_class.create_from_x509_certificate(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
            x509=x509,
        )

        assert isinstance(client, client_class)
        assert client._pipeline is mock_pipeline_init.return_value

    @pytest.mark.it("Raises a TypeError if the 'sastoken_ttl' kwarg is supplied by the user")
    def test_sastoken_ttl(self, client_class, x509):
        with pytest.raises(TypeError):
            client_class.create_from_x509_certificate(
                provisioning_host=fake_provisioning_host,
                registration_id=fake_registration_id,
                id_scope=fake_id_scope,
                x509=x509,
                sastoken_ttl=1000,
            )

    @pytest.mark.parametrize(
        "registration_id",
        [
            pytest.param(None, id="No Registration Id provided"),
            pytest.param(" ", id="Blank Registration Id provided"),
            pytest.param("", id="Empty Registration Id provided"),
        ],
    )
    @pytest.mark.it("Raises a ValueError if an invalid 'registration_id' parameter is provided")
    def test_invalid_registration_id(self, client_class, registration_id, x509):
        with pytest.raises(ValueError):
            client_class.create_from_x509_certificate(
                provisioning_host=fake_provisioning_host,
                registration_id=registration_id,
                id_scope=fake_id_scope,
                x509=x509,
            )
