#!/usr/bin/env python

# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

# Dummy API definitions of IotHub Provisioning Device Client for generating API documentation

from enum import Enum

class ProvisioningDeviceRegistrationStatus(Enum):
    CONNECTED = 0
    REGISTERING = 1
    ASSIGNING = 2
    ASSIGNED = 3
    ERROR = 4


class ProvisioningSecurityDeviceType(Enum):
    UNKNOWN = 0
    TPM = 1
    X509 = 2


class ProvisioningDeviceResult(Enum):
    OK = 0
    INVALID_ARG = 1
    SUCCESS = 2
    MEMORY = 3
    PARSING = 4
    TRANSPORT = 5
    INVALID_STATE = 6
    DEV_AUTH_ERROR = 7
    TIMEOUT = 8
    KEY_ERROR = 9
    ERROR = 10


class ProvisioningTransportProvider(Enum):
    HTTP = 0
    AMQP = 1
    MQTT = 2
    AMQP_WS = 3
    MQTT_WS = 4


class ProvisioningError:
    """Generic exception base class.
    """
    pass


class ProvisioningDeviceClientError(ProvisioningError):
    """ProvisioningDeviceClientError exception class, derived from ProvisioningError.
    """
    pass


class ProvisioningHttpProxyOptions:
    """ProvisioningHttpProxyOptions instance holds the proxy configuration options
    to set on ProvisioningDeviceClient.
    """
    def __init__(self, host_address, port, username, password):
        """Creates a ProvisioningHttpProxyOptions instance.

        :param host_address: HTTP host address
        :type host_address: str
        :param port: HTTP proxy port
        :type port: int
        :param username: HTTP Proxy user name
        :type username: str
        :param password: HTTP Proxy password
        :type password: str
        """
        pass


class ProvisioningDeviceClient:
    """ProvisioningDeviceClient instance to use to provision a device to IoTHub.
    """
    def __init__(self, uri, id_scope, security_device_type, protocol):
        """Creates a ProvisioningDeviceClient instance using the given parameters.

        :param uri: The IoTHub uri to connect
        :type uri: str
        :param id_scope: The scope of the device Id
        :type id_scope: str
        :param security_device_type: The security device type
        :type security_device_type: ProvisioningSecurityDeviceType(Enum)
        :param protocol: The protocol to used to communicate with IoTHub
        :type protocol: ProvisioningTransportProvider(Enum)
        :raises: ProvisioningDeviceClientError if the object creation failed
        """
        pass

    @property
    def protocol(self):
        """Getter for the protocol attribute

        :return: The current protocol used for provisioning
        :rtype: ProvisioningTransportProvider(Enum)
        """
        pass

    def register_device(self, register_callback, user_context, register_status_callback, status_user_context):
        """Registers the device on the IoTHub.

        :param register_callback: The callback will be called when the registration completed
        :type register_callback: Callable Python function
        :param user_context:  The user context object used in the registerCallback
        :type user_context: any
        :param register_status_callback: The callback will be called when the registration status changed
        :type register_status_callback: Callable Python function
        :param status_user_context: The user context object used in the registerStatusCallback
        :type status_user_context: any
        :return: ProvisioningDeviceResult instance signaling the result
        :rtype: ProvisioningDeviceResult(Enum)
        :raises: ProvisioningDeviceClientError if the operation failed
        """
        pass

    def set_option(self, option_name, option_value):
        """Sets the given option to the given value.

        :param option_name: The name of the option
        :type option_name: str
        :param option_value: The value to set
        :type option_value: str
        :raises: ProvisioningDeviceClientError if the operation failed
        """
        pass

    def get_version_string(self):
        """Gets the version of the provisioning client.
        
        :return: The version string
        :rtype: str 
        """
        pass

