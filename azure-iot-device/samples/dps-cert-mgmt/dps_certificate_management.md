# DPS CERTIFICATE MANAGEMENT

In a nutshell, IoT Device can request a client certificate from a CA through DPS. 
* Connect DPS to the private CA hosted by one of our CA partners. 
* IoT device sends a CSR to DPS
* DPS forwards it to the CA for signing and returns an X.509 client certificate to device. 
* Device uses certificate to authenticate with IoT Hub.

## Steps for making it work in preview (api-version=2021-11-01-preview)

### Prerequisite Steps for DPS , enrollment and CA

These steps must be done for any scenario inside DPS Cert Management.

* A new DPS instance must created in __West Central US__.
* Create an Enrollment Group or Individual Enrollment in this DPS instance.
    * Choose to use symmetric key, TPM key or X.509 for this enrollment.
    * Link an IoT Hub to the enrollment.
* Create an internal-use test account with one of Microsoft CA partners by emailing _iotcerts@microsoft.com_
    * Additionally, request them to add the DPS Service Endpoint to the allow list. `What allow list?`
* Once the CA account is created there are 2 pieces of that will be provided.
    * `api_key` -  DigiCert API key AND `profile_id` - DigiCert Client Cert Profile ID.
* Use DPS Service API to associate the CA object above to the DPS. 
    ```bash
    curl -k -L -i -X PUT https://<dps_service_endpoint>/certificateAuthorities/<ca_name>?api-version=2021-11-01-preview -H 'Authorization: <service_api_sas_token>' -H 'Content-Type: application/json' -H 'Content-Encoding: utf-8' -d'{"certificateAuthorityType":"DigiCertCertificateAuthority","apiKey":"<api_key>","profileName":"<profile_id>"}'
    ```
   where,
    * `dps_service_endpoint` - available in overview blade of the DPS details.
    * `ca_name` - this is an user chosen friendly name (e.g. myca1).
    * `service_api_sas_token` - generated using shared access policy `provisioningserviceowner`
    * `api_key` and `profile_id` obtained before.
* Query the Service API for the individual or group enrollment and save it to a file called enrollment.json. 
_NOTE: This is a preferred way so that for updating the enrollment only modification of the enrollment.json file is needed._
    ```bash
    curl -X GET -H "Content-Type: application/json" -H "Content-Encoding:  utf-8" -H "Authorization: <service_api_sas_token>" https://<dps_service_endpoint>/enrollments/<registration_id>?api-version=2021-11-01-preview > enrollment.json
    ```
     
### Client Certificate Issuance
* All prerequisite steps must be done before following the rest.
* Use DPS Service API to connect the CA to the __individual__ enrollment or group enrollment.
    * First, update the enrollment.json file to add the following
    ```
    "clientCertificateIssuancePolicy": {"certificateAuthorityName": "<ca_name>"}
    ```
    where,
    * `ca_name` - The friendly name that was assigned to the CA created in previous 5 (e.g. myca1).
    * Then, update the enrollment information:
   ```bash
   curl -k -L -i -X PUT -H "Content-Type: application/json" -H "Content-Encoding:  utf-8" -H "Authorization: <service_api_sas_token>" https://<dps_service_endpoint>/enrollments/<registration_id>?api-version=2021-11-01-preview -H "If-Match: <etag>" -d @enrollment.json 
   ```
   where,
    * `dps_service_endpoint` - available in overview blade of the DPS details.
    * `registration_id` – Is your individual enrollment registration id (e.g. mydevice1).
    * `service_api_sas_token` - The DPS Service API shared access token generated previously.
    
* If a group enrollment was created then similar command must be performed for the group.
* Generate an ECC P-256 keypair using OpenSSL as follows:
    ```bash
    openssl ecparam -genkey -name prime256v1 -out ec256-key-pair.key
    ```
* Generate a CSR using OpenSSL. Replace the CN with the registration ID of the device. __Important: DPS has character set restrictions for registration ID.__
Note: The same CSR can be reused and sent to DPS multiple times.
    ```bash
    openssl req -new -key ec256-key-pair.key -out ecc256.csr -subj '/CN=<registration_id>'
    ```
* Run [sample](provision_symmetric_key_client_cert_issuance_send_message_x509.py) for DPS. Use the file path of the above generated csr for the environment variable `CSR_FILE` and 
use file path for the key file for the environment variable `X509_KEY_FILE`.

### Trust bundle issuance
* All prerequisite steps must be done before following the rest.
* Use DPS Service API to create a trust bundle
    ```bash
    curl -v -X PUT -H 'Authorization: <service_api_sas_token>' -H 'Content-Type: application/json' https://<dps_service_endpoint>/trustBundles/<trust_bundle_name>?api-version=2021-11-01-preview -d @sample-put-trustbundle-payload.json
    ```
    where,
    * `dps_service_endpoint` - available in overview blade.
    * `trust_bundle_name` – The name you want to assign to your trust bundle (e.g. mytrustbundle1).
    * `service_api_sas_token` - The DPS Service API shared access token generated previously.
    * `sample-put-trustbundle-payload.json` - A file that contains the content for trust bundle as shown below
    
        ```json
        {
            "certificates": [
                {
                    "certificate": "-----BEGIN CERTIFICATE-----\r\nsome content\r\nsome content\r\nsome content\r\n-----END CERTIFICATE-----\r\n"
                }
            ]
        }
        ```
* Use DPS Service API to connect the trust bundle or update the __individual__ enrollment with the trust bundle.
    ```bash
    curl -k -L -i -X PUT -H "Content-Type: application/json" -H "Content-Encoding:  utf-8" -H "Authorization: <service_api_sas_token>" https://<dps_service_endpoint>/enrollments/<registration_id>?api-version=2021-11-01-preview -H "If-Match: <etag>" -d @enrollment.json
    ```
    where,
    * `dps_service_endpoint` - available in overview blade.
    * `registration_id` – Is your individual enrollment registration id (e.g. mydevice1).
    * `etag` - The etag of the individual enrollment.
    * `service_api_sas_token` - The DPS Service API shared access token generated previously.
    * `enrollment.json` - A file that contains all the enrollment details that was retrieved. Update this file and the following details must be present tp update the individual enrollment
        ```
        "clientCertificateIssuancePolicy":{"certificateAuthorityName":"<ca_name>"}, 
        "trustBundleId":"<trust_bundle_name>"
        ```
* Run [sample](provision_symmetric_key_trust_bundle_issuance.py) for DPS.