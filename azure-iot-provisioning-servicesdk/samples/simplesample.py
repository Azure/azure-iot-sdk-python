# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import os
import argparse
from azure.iot.sdk.provisioning.service import ProvisioningServiceClient
from azure.iot.sdk.provisioning.service.models import (
    BulkEnrollmentOperation,
    IndividualEnrollment,
    AttestationMechanism,
    TpmAttestation,
)


def run_sample(cs, ek):
    client = ProvisioningServiceClient(connection_string=cs)

    print("Creating Individual Enrollment with TPM Attestation...")
    tpm = TpmAttestation(endorsement_key=ek)
    am = AttestationMechanism(type="tpm", tpm=tpm)
    ie = IndividualEnrollment(registration_id="reg-id", attestation=am)
    ie = client.create_or_update_individual_enrollment(
        id=ie.registration_id, enrollment=ie
    )  # returns like a get operation
    print("Complete!")

    print("Updating Individual Enrollment...")
    ie.device_id = "dev-id"
    ie = client.create_or_update_individual_enrollment(id=ie.registration_id, enrollment=ie)
    print("Complete!")

    print("Deleting Individual Enrollment...")
    client.delete_individual_enrollment(id=ie.registration_id)
    print("Complete!")

    print("Running Bulk Operation - Create 10 Individual Enrollments...")
    new_enrollments = []
    for i in range(0, 10):
        new_tpm = TpmAttestation(endorsement_key=ek)
        new_am = AttestationMechanism(type="tpm", tpm=new_tpm)
        new_ie = IndividualEnrollment(registration_id=("id-" + str(i)), attestation=new_am)
        new_enrollments.append(new_ie)
    bulk_op = BulkEnrollmentOperation(enrollments=new_enrollments, mode="create")
    client.run_bulk_enrollment_operation(bulk_operation=bulk_op)
    print("Complete!")

    print("Running Bulk Operation - Delete 10 Individual Enrollments...")
    bulk_op.mode = "delete"
    client.run_bulk_enrollment_operation(bulk_operation=bulk_op)
    print("Complete!")


if __name__ == "__main__":
    connection_string_env = "ProvisioningServiceConnectionString"
    endorsement_key_env = "ProvisioningTpmEndorsementKey"

    parser = argparse.ArgumentParser("Run a Provisioning Service sample")
    parser.add_argument(
        "--connection_string",
        "-cs",
        default=os.environ.get(connection_string_env, None),
        help="Provisioning Service Connection String. [default: {} environment variable".format(
            connection_string_env
        ),
    )
    parser.add_argument(
        "--endorsement_key",
        "-ek",
        default=os.environ.get(endorsement_key_env, None),
        help="TPM Endorsement Key. [default: {} environment variable]".format(endorsement_key_env),
    )
    args = parser.parse_args()

    try:
        run_sample(args.connection_string, args.endorsement_key)
    except Exception as e:
        print("Error: {}".format(str(e)))
