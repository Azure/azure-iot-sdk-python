# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import pytest
from azure.iot.provisioning.servicesdk import ProvisioningServiceClient
from azure.iot.provisioning.servicesdk.protocol import (
    ProvisioningServiceClient as BaseProvisioningServiceClient,
)
from azure.iot.provisioning.servicesdk.auth import ConnectionStringAuthentication
from azure.iot.provisioning.servicesdk.models import (
    IndividualEnrollment,
    EnrollmentGroup,
    AttestationMechanism,
)


@pytest.fixture(scope="module")
def service_str():
    return "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"


@pytest.fixture(scope="module")
def service_client(service_str):
    return ProvisioningServiceClient(service_str)


@pytest.fixture(scope="module")
def attestation_mechanism():
    return AttestationMechanism.create_with_x509_ca_references("my-certificate-name")


@pytest.fixture()  # don't scope, so changes aren't saved
def individual_enrollment(attestation_mechanism):
    return IndividualEnrollment(
        registration_id="registration_id", attestation=attestation_mechanism
    )


@pytest.fixture()  # don't scope, so changes aren't saved
def enrollment_group(attestation_mechanism):
    return EnrollmentGroup(enrollment_group_id="group_id", attestation=attestation_mechanism)


@pytest.fixture(scope="module")
def etag():
    return "my-etag"


def test_create(mocker, service_str):
    """Test that instantiation of the application ProvisioningServiceClient creates a ConnectionStringAuthentication from
    the provided connection string, and then uses it along with an extracted hostname in the __init__ of the
    superclass - the generated ProvisioningServiceClient from .protocol
    """
    mock_parent_init = mocker.patch.object(BaseProvisioningServiceClient, "__init__", autospec=True)
    auth = ConnectionStringAuthentication(service_str)
    mock_auth = mocker.patch(
        "azure.iot.provisioning.servicesdk.client.ConnectionStringAuthentication",
        return_value=auth,
        autospec=True,
    )
    client = ProvisioningServiceClient(service_str)
    mock_auth.assert_called_once_with(service_str)
    mock_parent_init.assert_called_once_with(client, mock_auth.return_value, "https://my.host.name")
