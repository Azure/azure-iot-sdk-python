# Provisioning Device Client SDK

The Provisioning Device SDK enables automatic provisioning of a device using an HSM (Hardware Security Module) against an IoThub.  There are two different authentication mode that the client supports: x509 or TPM.

## Enabling Provisioning Device Client simulator

For development purposes the Provisioning Device Client will use simulators to mock hardware chips.

### Build Python binaries to use them with simulators

```Shell
build_client.cmd --use-tpm-simulator
```

### Pre-built simulator executable
.azure-iot-sdk-python/c/provisioning_client/deps/utpm/tools/tpm_simulator/Simulator.exe
```

### TPM Simulator

The SDK will ship with a windows tpm simulator binary. The following command will enable the sas token authentication and then run the tpm simulator on the windows OS (the Simulator will listen over a socket on ports 2321 and 2322).

### DICE Simulator

For x509 the Provisioning Device Client enables a DICE hardware simulator that emulators the DICE hardware operations.

## Adding Enrollments with Azure Portal

To enroll a device in the azure portal you will need to either get the Registration Id and Endorsement Key for TPM devices or the root CA certificate.  Running the provisioning tool will print out the information to be used in the portal:

### TPM Provisioning Tool

```Shell
.cmake_output_path/provisioning_client/tools/tpm_device_provision/tpm_device_provision.exe
```

### x509 Provisioning Tool

```Shell
./cmake_output_path/provisioning_client/tools/dice_device_provision/dice_device_provision.exe
```

## Running Provisioning Device Client samples

```Python
cd provisioning_device_client/samples
python provisioning_device_client_sample.py -i id_scope -s security_device_type -p protocol
```

## Using Python IoTHub Client with Provisioning Device Client sample

Run the 
Once the device has been provisioned with the Provisioning Device Client the following API will use the `HSM` authentication method to connect with the IoThub:

```Python
cd device/samples
python iothub_client_prov_hsm_sample.py -u iothub_uri, -d device_id, -s security_type -p protocol
```

