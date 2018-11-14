## Overview

The `SymmetricKeyAuthenticationProvider` class represents a type of `AuthenticationProvider` which can accept a connection string.
The authentication provider is created by first parsing the connection string. 
HostName=<hostname>;DeviceId=<device_id>;ModuleId=<module_id>;SharedAccessKey=<shared_access_key>;SharedAccessKeyName=<key_name>
For a device connection string the parsed fields are :- `HostName`, `DeviceId` , `SharedAccessKey`, and an optional `SharedAccessKeyName`.
For a module connection string the parsed fields are :- `HostName`, `DeviceId` , `ModuleId`, `SharedAccessKey`, and an optional `SharedAccessKeyName`.

## Private Dunder Init
Creates a new instance of the `SymmetricKeyAuthenticationProvider` object. It takes in parameters `hostname`, `device_id`, optional `module_id` and `sas_token_str`.
```
hostname : Hostname of the Azure IoT hub.
device_id: Identifier for the device
module_id: Identifier for the module on the device
sas_token_str: the string representation of the shared access signature already passed in by the user.
```

## Static Method
The static method `parse` is overridden from the base class and is responsible for parsing out the different attributes in the passed in connection string.

### parse(connection_string) [static]
The `parse` static method takes in a string representation of the entire `connection information` which is already available to the user. The string format looks like one of the options below.

- `HostName=<hostname>;DeviceId=<device_id>;SharedAccessKey=<shared_access_key>`
- `HostName=<hostname>;DeviceId=<device_id>;SharedAccessKey=<shared_access_key>;SharedAccessKeyName=<key_name>`
- `HostName=<hostname>;DeviceId=<device_id>;ModuleId=<module_id>;SharedAccessKey=<shared_access_key>;SharedAccessKeyName=<key_name>`

The `parse` method is responsible for the following :-

* Parses the 'name=value' field found in source.
* Validates the information present in the source.
* Creates a base64-encoded HMAC-SHA256 hash of the string to sign.
* Create the resource uri and quotes it as well.
* Then uses the resource uri, signature, optional key name and a default expiry of 1 hr to create a shared access signature string.
* Finally returns a new instance of the `SymmetricKeyAuthenticationProvider` object. 

## Instance method
The instance method `get_current_sas_token` gives back the current shared access signature string.

## Helper Methods

* `_validate_keys` : This private helper method validates the correct combination of the name, value pairs in the string provided during parse.
* `_signature` : This private helper method creates the hash to provide the sig portion of the shared access signature string.
* `_create_sas` : Creates the shared access signature string.

