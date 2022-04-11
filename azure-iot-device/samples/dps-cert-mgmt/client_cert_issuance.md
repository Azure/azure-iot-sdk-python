# Client cert issuance for IoT devices using a CA

In a nutshell, IoT Device can request a client certificate from a CA through DPS. 
* Connect DPS to the private CA hosted by one of our CA partners. 
* IoT device sends a CSR to DPS
* DPS forwards it to the CA for signing and returns an X.509 client certificate to device. 
* Device uses certificate to authenticate with IoT Hub.

## Steps for making it work in preview (api-version=2021-11-01-preview)

### Steps for DPS , enrollment and 

1. A new DPS instance must created in __West Central US__.
2. Create an Enrollment Group or Individual Enrollment in this DPS instance.
    * Choose to use symmetric key, TPM key or X.509 for this enrollment.
    * Link an IoT Hub to the enrollment.
3. Create an internal-use test account with one of Microsoft CA partners by emailing _iotcerts@microsoft.com_
    * Additionally, request them to add the DPS Service Endpoint to the allow list. `What allow list?`
4. Once the CA account is created there are 2 pieces of that will be provided.
    * `api_key` -  DigiCert API key AND `profile_id` - DigiCert Client Cert Profile ID.
5. Use DPS Service API to associate the CA object above to the DPS. 
    ```bash
    curl -k -L -i -X PUT https://<dps_service_endpoint>/certificateAuthorities/<ca_name>?api-version=2021-11-01-preview -H 'Authorization: <service_api_sas_token>' -H 'Content-Type: application/json' -H 'Content-Encoding: utf-8' -d'{"certificateAuthorityType":"DigiCertCertificateAuthority","apiKey":"<api_key>","profileName":"<profile_id>"}'
    ```
   where,
    * `dps_service_endpoint` - available in overview blade.
    * `ca_name` - this is an user chosen friendly name (e.g. myca1).
    * `service_api_sas_token` - generated using shared access policy `provisioningserviceowner`
    * `api_key` and `profile_id` obtained before.
6. Use DPS Service API to connect the CA to the __individual__ enrollment or group enrollment. Ensure attestation type matches enrollment settings.
Here we have used `symmetrickey`.
   ```bash
   curl -k -L -i -X PUT -H "Content-Type: application/json" -H "Content-Encoding:  utf-8" -H "Authorization: <service_api_sas_token>" https://<dps_service_endpoint>/enrollments/<registration_id>?api-version=2021-11-01-preview -H "If-Match: *" -d '{ "registrationId": "<registration_id>", "attestation": { "type": "symmetricKey" }, "clientCertificateIssuancePolicy": {"certificateAuthorityName":"<ca_name>"} }' 
   ```
   where,
    * `dps_service_endpoint` - available in overview blade.
    * `registration_id` – Is your individual enrollment registration id (e.g. mydevice1).
    * `ca_name` - The friendly name that was assigned to the CA created in step 5 (e.g. myca1).
    * `service_api_sas_token` - The DPS Service API shared access token generated previously.
    
7. If a group enrollment was created then similar command must be performed for the group.
    ```bash
    curl -k -L -i -X PUT -H "Content-Type: application/json" -H "Content-Encoding:  utf-8" -H "Authorization: <service_api_sas_token>" https://<dps_service_endpoint>/enrollmentGroups/<enrollment_group_id>?api-version=2021-11-01-preview -H "If-Match: *" -d '{ "enrollmentGroupId": "<enrollment_group_id>", "attestation": { "type": "symmetricKey" },"clientCertificateIssuancePolicy": {"certificateAuthorityName":"<ca_name>"}}'
    ```
8. Generate an ECC P-256 keypair using OpenSSL as follows:
    ```bash
    openssl ecparam -genkey -name prime256v1 -out ec256-key-pair.key
    ```
9. Generate a CSR using OpenSSL. Replace the CN with the registration ID of the device. __Important: DPS has character set restrictions for registration ID.__
Note: The same CSR can be reused and sent to DPS multiple times.
    ```bash
    openssl req -new -key ec256-key-pair.key -out ecc256.csr -subj '/CN=my-registration-id'
    ```
10. Run sample for DPS. Use the file path of the above generated csr for the environment variable `CSR_FILE` and 
use file path for the key file for the environment variable `X509_KEY_FILE`.

11. 

    

