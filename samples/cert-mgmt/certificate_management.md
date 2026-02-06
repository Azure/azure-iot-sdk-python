# Azure Device Provisioning Certificate Management

Azure Device Provisioning Service is capable (through pairing with Azure Device Registry service) of issuing a certificate chain for Azure IoT Hub authentication.
This is done by sending a Certificate Signing Request when the device registration is performed against the Device Provisioning Service.

This sample shows how to use the Azure IoT Python SDK Device Provisiong Client to perform a registration with Certificate-Signing Request and authenticate against the Azure IoT Hub with the issued certificate chain.

# Requirements

- An Azure Device Provisioning Service and Azure IoT Hub configured for CA-based certificate issuance and authentication.

- Azure Device Provisioning Service with a group or individual enrollment created to support Certificate Management.

- If using enrollment group, create the [derived certificate](https://learn.microsoft.com/en-us/azure/iot-dps/concepts-x509-attestation) or [symmetric-key](https://learn.microsoft.com/en-us/azure/iot-dps/concepts-symmetric-key-attestation?tabs=linux#group-enrollments-with-symmetric-keys) for attestation. 

# Sample Configuration

Environment variables are used to configure the `provisioning_client_certificate_issuance.py` sample.

This is a common set of environment variables that must be defined:

Linux:

```bash
export PROVISIONING_HOST="global.azure-devices-provisioning.net" # Or your specific Azure DPS service hostname.
export PROVISIONING_IDSCOPE=<ID_SCOPE of your Azure Device Provisioning Service>
export PROVISIONING_REGISTRATION_ID=<Registration ID> # I.e., the ID of the device to be registered.
```

Windows:
```powershell
$env:PROVISIONING_HOST="global.azure-devices-provisioning.net" # Or your specific Azure DPS service hostname.
$env:PROVISIONING_IDSCOPE="<ID_SCOPE of your Azure Device Provisioning Service>"
$env:PROVISIONING_REGISTRATION_ID="<Registration ID>" # I.e., the ID of the device to be registered.
```

If using x509-based attestation, set:

Linux
```bash
export PROVISIONING_X509_CERT_FILE=<path to enrollment certificate pem file>
export PROVISIONING_X509_KEY_FILE=<path to enrollment certificate private key pem file>
```

Windows:
```powershell
$env:PROVISIONING_X509_CERT_FILE="<path to enrollment certificate pem file>"
$env:PROVISIONING_X509_KEY_FILE="<path to enrollment certificate private key pem file>"
```

Otherwise, if using symmetric-key attestation, set:

Linux
```bash
export PROVISIONING_SAS_KEY="<individual enrollment key or enrollment group derived key>"
```

Windows:
```powershell
$env:PROVISIONING_SAS_KEY="<individual enrollment key or enrollment group derived key>"
```

Finally, set the variables for the certificate-signing request feature.

Linux
```bash
export PROVISIONING_CSR_KEY_FILE=<path to certificate private key used for certificate-signing-request>
export PROVISIONING_CSR=<base64-encoded certificate-signing-request>
export PROVISIONING_ISSUED_CERT_FILE=<arbitrary path where to store issued certificate chain>
```

Windows:
```powershell
$env:PROVISIONING_CSR_KEY_FILE="<path to certificate private key used for certificate-signing-request>"
$env:PROVISIONING_CSR="<base64-encoded certificate-signing-request>"
$env:PROVISIONING_ISSUED_CERT_FILE="<arbitrary path where to store issued certificate chain>"
```

## Generating a Certificate Key and Certificate-Signing-Request for Testing

The steps below can be used **for testing only**.

**Do not use the key or certificate-sigining-request below in production.**

Linux:
```bash
export PROVISIONING_REGISTRATION_ID=<Registration ID> # If not done already above.
export PROVISIONING_CSR_KEY_FILE=$(pwd)/${PROVISIONING_REGISTRATION_ID}-csr-private-key.pem

openssl ecparam -name prime256v1 -genkey -noout | openssl pkcs8 -topk8 -nocrypt -out $PROVISIONING_CSR_KEY_FILE

export PROVISIONING_CSR=$(openssl req -new -key $PROVISIONING_CSR_KEY_FILE -subj "/CN=$PROVISIONING_REGISTRATION_ID" -outform DER | openssl base64 -A)
```

Windows:
```powershell
$env:PROVISIONING_REGISTRATION_ID="<Registration ID>" # If not done already above.
$env:PROVISIONING_CSR_KEY_FILE="$(pwd)\${env:PROVISIONING_REGISTRATION_ID}-csr-private-key.pem"

$privateKey = [System.Security.Cryptography.ECDsa]::Create([System.Security.Cryptography.ECCurve]::CreateFromFriendlyName("nistP256"))

if ($PSVersionTable.PSVersion.Major -lt 7) {
   $base64pkcs8PrivateKey = [Convert]::ToBase64String($privateKey.Key.Export([System.Security.Cryptography.CngKeyBlobFormat]::Pkcs8PrivateBlob), 'InsertLineBreaks')
} else {
   $base64pkcs8PrivateKey = [Convert]::ToBase64String($privateKey.ExportPkcs8PrivateKey(), 'InsertLineBreaks')
}

$dn = New-Object System.Security.Cryptography.X509Certificates.X500DistinguishedName("CN=$env:PROVISIONING_REGISTRATION_ID")
$csr = New-Object System.Security.Cryptography.X509Certificates.CertificateRequest($dn, $privateKey, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
$env:PROVISIONING_CSR = [Convert]::ToBase64String($csr.CreateSigningRequest())

echo "-----BEGIN PRIVATE KEY-----`n$base64pkcs8PrivateKey`n-----END PRIVATE KEY-----" > $env:PROVISIONING_CSR_KEY_FILE
```

# Running the Sample

```bash
git clone -b feature/dps-csr-preview https://github.com/Azure/azure-iot-sdk-python
cd azure-iot-sdk-python
python3 azure-iot-device/samples/dps-cert-mgmt/provisioning_client_certificate_issuance.py
```

Example of sample output:
```bash
Using x509 authentication
The complete registration result is
myDeviceId
myAssignedIoTHub.azure-devices.net
reprovisionedToInitialAssignment
null
Will send telemetry from the provisioned device
sending message #1
sending message #2
sending message #3
sending message #4
sending message #5
sending message #6
sending message #7
sending message #8
sending message #9
sending message #10
done sending message #1
done sending message #2
done sending message #3
done sending message #4
done sending message #5
done sending message #6
done sending message #7
done sending message #8
done sending message #9
done sending message #10
```
