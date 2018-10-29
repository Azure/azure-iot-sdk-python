## Overview

The `SharedAccessSignatureAuthenticationProvider` class represents a type of `AuthenticationProvider` which can accept a shared access signature string.
The authentication provider is created by first parsing the shared access signature string.
The parsed fields are :- `sr`, `sig` , `se`, an optional `skn`
The `resource_uri` it also unquoted and parsed to get `hostname`, `device_id` and optional `module_id` and stored as public attributes.

## Private Dunder Init
Creates a new instance of the `SharedAccessSignatureAuthenticationProvider` object. It takes in parameters `hostname`, `device_id`,  optional `module_id` and `sas_token_str`.
```
hostname : Hostname of the Azure IoT hub.
device_id: Identifier for the device
module_id: Identifier for the module on the device
sas_token_str: the string representation of the shared access signature already passed in by the user.
```

## Static Method
The static method `parse` is overridden from the base class and is responsible for parsing out the different attributes in the passed in shared access signature string.

### parse(sas_token_str) [static]
The `parse` static method returns a new instance of the `SharedAccessSignatureAuthenticationProvider` object with properties corresponding to each 'name=value' field found in source.
It takes in a string representation of the entire `shared access signature` which is already available to the user. The string format looks like one of the options below.

- `SharedAccessSignature sr=<quoted_resource_uri>&sig=<signature>&se=<expiry>`
- `SharedAccessSignature sr=<quoted_resource_uri>&sig=<signature>&se=<expiry>&skn=<keyname>`

## Instance method
The instance method `get_current_sas_token` gives back the current shared access signature string.

## Helper Method
The private helper method `_validate_required_keys` validates the correct combination of the name, value pairs in the string provided during parse.
