# Azure IoT Device SDK for Python Migration Guide - ProvisioningDeviceClient -> ProvisioningSession

This guide details how to update existing code for IoT Hub provisioning that uses an `azure-iot-device` V2 release to use a V3 release instead.

**Note that currently V3 only presents an async set of APIs. This guide will be updated when that changes**

For changes when communicating between a device and IoT Hub, please refer to `migration_guide_iothub.md` in this same directory.

## Default usage of the Global Provisioning Endpoint
The Global Provisioning Endpoint - `global.azure-devices-provisioning.net` previously had to be manually provided via the `provisioning_host` argument to any factory method. For V3, the argument has been renamed to `provisioning_endpoint` and is now provided directly to the `ProvisioningSession` constructor. It defaults to the Global Provisioning Endpoint if not provided, so the vast majority of users can simply not provide anything. The only time the `provisioning_endpoint` argument is necessary in V3 is if your solution involves using a private endpoint.


## Provisioning using Shared Access Key (Symmetric Key)
Using shared access key authentication (formerly called 'symmetric key authentication') is now provided via the `shared_access_key` argument instead of the `symmetric_key` parameter. This parameter is now provided directly to the `ProvisioningSession` constructor, rather than using the `create_from_symmetric_key()` factory method.

#### V2
```python
from azure.iot.device.aio import ProvisioningDeviceClient

async def main():
    provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host="global.azure-devices-provisioning.net",
            registration_id="<Your Registration ID>",
            id_scope="<Your ID Scope>",
            symmetric_key="<Your Shared Access Key>",
        )

    provisioning_device_client.provisioning_payload = "<Your Payload>"

    result = await provisioning_device_client.register()
```

#### V3
```python
from azure.iot.device import ProvisioningSession

async def main():
    async with ProvisioningSession(
        id_scope="<Your ID Scope>",
        registration_id="<Your Registration ID>",
        shared_access_key="<Your Shared Access Key>"
    ) as session:
        result = await session.register(payload="<Your Payload>")
```


## Provisioning using X509 Certificates
X509 authentication is now provided via the new `ssl_context` keyword argument for the `ProvisioningSession` constructor, rather than using `.create_from_x509_certificate()` factory method. This is to allow additional flexibility for
customers who wish to have more control over their TLS/SSL authentication. See "TLS/SSL customization" below for more information.

#### V2
```python
from azure.iot.device.aio import ProvisioningDeviceClient
from azure.iot.device import X509

async def main():
    x509 = X509(
        cert_file="<Your X509 Cert File Path>",
        key_file="<Your X509 Key File>",
        pass_phrase="<Your X509 Pass Phrase>",
    )

    provisioning_device_client = ProvisioningDeviceClient.create_from_x509_certificate(
            provisioning_host="global.azure-devices-provisioning.net",
            registration_id="<Your Registration ID>",
            id_scope="<Your ID Scope>",
            x509=x509,
        )
    
    provisioning_device_client.provisioning_payload = "<Your Payload>"

    result = await provisioning_device_client.register()
```

#### V3
```python
from azure.iot.device import ProvisioningSession
import ssl

async def main():
    ssl_context = ssl.SSLContext.create_default_context()
    ssl_context.load_cert_chain(
        certfile="<Your X509 Cert File Path>",
        keyfile="<Your X509 Key File>",
        password="<Your X509 Pass Phrase>",
    )

    async with ProvisioningSession(
        id_scope="<Your ID Scope>",
        registration_id="<Your Registration ID>",
        ssl_context=ssl_context
    ) as session:
        result = await session.register(payload="<Your Payload>")
```

## TLS/SSL Customization
To allow users more flexibility with TLS/SSL authentication, we have added the ability to inject an `SSLContext` object into the `ProvisioningSession` via the optional `ssl_context` keyword argument that is present on the constructor and factory methods. As a result, some features previously handled via client APIs are now expected to have been directly set on the injected `SSLContext`.

By moving to a model that allows `SSLContext` injection we can allow for users to modify any aspect of their `SSLContext`, not just the ones we previously supported via API.


### Server Verification Certificates (CA certs)
#### V2
```python
from azure.iot.device.aio import ProvisioningDeviceClient

certfile = open("<Your CA Certificate File Path>")
root_ca_cert = certfile.read()

provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
    provisioning_host="global.azure-devices-provisioning.net",
    registration_id="<Your Registration ID>",
    id_scope="<Your ID Scope>",
    symmetric_key="<Your Shared Access Key>",
    server_verification_cert=root_ca_cert,
)
```

#### V3
```python
from azure.iot.device import ProvisioningSession
import ssl

ssl_context = ssl.SSLContext.create_default_context(
    cafile="<Your CA Certificate File Path>",
)

session = ProvisioningSession(
    registration_id="<Your Registration ID>",
    id_scope="<Your ID Scope>",
    symmetric_key="<Your Shared Access Key>",
    ssl_context=ssl_context,
)
```

### Cipher Suites
#### V2
```python
from azure.iot.device.aio import ProvisioningDeviceClient

provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
    provisioning_host="global.azure-devices-provisioning.net",,
    registration_id="<Your Registration ID>",
    id_scope="<Your ID Scope>",
    symmetric_key="<Your Shared Access Key>",
    cipher="<Your Cipher>",
)
```

#### V3
```python
from azure.iot.device import ProvisioningSession
import ssl

ssl_context = ssl.SSLContext.create_default_context()
ssl_context.set_ciphers("<Your Cipher>")

session = ProvisioningSession(
    registration_id="<Your Registration ID>",
    id_scope="<Your ID Scope>",
    symmetric_key="<Your Shared Access Key>",
    ssl_context=ssl_context,
)
```

## Removed Keyword Arguments

Some keyword arguments provided at client creation in V2 have been removed in V3 as they are no longer necessary.

| V2                          | V3               | Explanation                                              |
|-----------------------------|------------------|----------------------------------------------------------|
| `gateway_hostname`          | **REMOVED**      | Unsupported scenario (was unnecessary in V2)             |
| `server_verification_cert`  | **REMOVED**      | Supported via SSL injection                              |
| `cipher`                    | **REMOVED**      | Supported via SSL injection                              |
