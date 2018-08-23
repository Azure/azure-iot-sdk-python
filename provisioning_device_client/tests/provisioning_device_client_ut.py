# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import sys
import unittest
import provisioning_device_client_mock
from provisioning_device_client_mock import *

provisioning_uri = "global.provisioning.net"
id_scope = "0000001"
security_device_type = ProvisioningSecurityDeviceType.X509
host_address = "host_address"
port = 42
username = "username"
password = "password"

def register_device_callback(register_result, iothub_uri, device_id, user_context):
    return


def register_status_callback(reg_status, user_context):
    return


class TestExceptionDefinitions(unittest.TestCase):

    def test_ProvisioningError(self):
        error = ProvisioningError()
        self.assertIsInstance(error, BaseException)
        self.assertIsInstance(error, ProvisioningError)
        with self.assertRaises(BaseException):
            raise ProvisioningError()
        with self.assertRaises(ProvisioningError):
            raise ProvisioningError()

    def test_ProvisioningDeviceClientError(self):
        error = ProvisioningDeviceClientError()
        self.assertIsInstance(error, BaseException)
        self.assertIsInstance(error, ProvisioningError)
        self.assertIsInstance(error, ProvisioningDeviceClientError)
        with self.assertRaises(BaseException):
            raise ProvisioningDeviceClientError()
        with self.assertRaises(ProvisioningDeviceClientError):
            raise ProvisioningDeviceClientError()
        with self.assertRaises(ProvisioningDeviceClientError):
            raise ProvisioningDeviceClientError()

    def test_ProvisioningDeviceClientErrorArg(self):
        with self.assertRaises(Exception):
            error = ProvisioningDeviceClientErrorArg()
        with self.assertRaises(Exception):
            error = ProvisioningDeviceClientErrorArg(__name__)
        with self.assertRaises(Exception):
            error = ProvisioningDeviceClientErrorArg(__name__, "function")
        with self.assertRaises(Exception):
            error = ProvisioningDeviceClientErrorArg(ProvisioningDeviceResult.ERROR)
        error = ProvisioningDeviceClientErrorArg("function", ProvisioningDeviceResult.ERROR)
        with self.assertRaises(TypeError):
            raise ProvisioningDeviceClientErrorArg("function", ProvisioningDeviceResult.ERROR)


class TestEnumDefinitions(unittest.TestCase):

    def test_ProvisioningDeviceRegistrationStatus(self):
        self.assertEqual(ProvisioningDeviceRegistrationStatus.CONNECTED, 0)
        self.assertEqual(ProvisioningDeviceRegistrationStatus.REGISTERING, 1)
        self.assertEqual(ProvisioningDeviceRegistrationStatus.ASSIGNING, 2)
        self.assertEqual(ProvisioningDeviceRegistrationStatus.ASSIGNED, 3)
        self.assertEqual(ProvisioningDeviceRegistrationStatus.ERROR, 4)
        lastEnum = ProvisioningDeviceRegistrationStatus.ERROR + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(ProvisioningDeviceRegistrationStatus.ANY, 0)

    def test_ProvisioningSecurityDeviceType(self):
        self.assertEqual(ProvisioningSecurityDeviceType.UNKNOWN, 0)
        self.assertEqual(ProvisioningSecurityDeviceType.TPM, 1)
        self.assertEqual(ProvisioningSecurityDeviceType.X509, 2)
        lastEnum = ProvisioningSecurityDeviceType.X509 + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(ProvisioningSecurityDeviceType.ANY, 0)

    def test_ProvisioningSecurityDeviceType(self):
        self.assertEqual(ProvisioningDeviceResult.OK, 0)
        self.assertEqual(ProvisioningDeviceResult.INVALID_ARG, 1)
        self.assertEqual(ProvisioningDeviceResult.SUCCESS, 2)
        self.assertEqual(ProvisioningDeviceResult.MEMORY, 3)
        self.assertEqual(ProvisioningDeviceResult.PARSING, 4)
        self.assertEqual(ProvisioningDeviceResult.TRANSPORT, 5)
        self.assertEqual(ProvisioningDeviceResult.INVALID_STATE, 6)
        self.assertEqual(ProvisioningDeviceResult.DEV_AUTH_ERROR, 7)
        self.assertEqual(ProvisioningDeviceResult.TIMEOUT, 8)
        self.assertEqual(ProvisioningDeviceResult.KEY_ERROR, 9)
        self.assertEqual(ProvisioningDeviceResult.ERROR, 10)
        lastEnum = ProvisioningDeviceResult.ERROR + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(ProvisioningDeviceResult.ANY, 0)

    def test_ProvisioningTransportProvider(self):
        if hasattr(ProvisioningTransportProvider, "MQTT_WS"):
            self.assertEqual(ProvisioningTransportProvider.HTTP, 0)
            self.assertEqual(ProvisioningTransportProvider.AMQP, 1)
            self.assertEqual(ProvisioningTransportProvider.MQTT, 2)
            self.assertEqual(ProvisioningTransportProvider.AMQP_WS, 3)
            self.assertEqual(ProvisioningTransportProvider.MQTT_WS, 4)
            lastEnum = ProvisioningTransportProvider.MQTT_WS + 1
            with self.assertRaises(AttributeError):
                self.assertEqual(ProvisioningTransportProvider.ANY, 0)
        else:
            self.assertEqual(ProvisioningTransportProvider.HTTP, 0)
            self.assertEqual(ProvisioningTransportProvider.AMQP, 1)
            self.assertEqual(ProvisioningTransportProvider.MQTT, 2)
            lastEnum = ProvisioningTransportProvider.MQTT + 1
            with self.assertRaises(AttributeError):
                self.assertEqual(ProvisioningTransportProvider.ANY, 0)


class TestProvisioningDeviceClient(unittest.TestCase):

    def test_ProvisioningHttpProxyOptions(self):
        # constructor
        with self.assertRaises(Exception):
            proxy_options = ProvisioningHttpProxyOptions()
        with self.assertRaises(Exception):
            proxy_options = ProvisioningHttpProxyOptions(host_address, host_address)
        with self.assertRaises(Exception):
            proxy_options = ProvisioningHttpProxyOptions(host_address, port, port)
        with self.assertRaises(Exception):
            proxy_options = ProvisioningHttpProxyOptions(host_address, port, username, port)

        proxy_options = ProvisioningHttpProxyOptions(host_address, port, username, password)
        self.assertIsInstance(proxy_options, ProvisioningHttpProxyOptions)
        self.assertEqual(proxy_options.host_address, host_address)
        self.assertEqual(proxy_options.port, port)
        self.assertEqual(proxy_options.username, username)
        self.assertEqual(proxy_options.password, password)

    def test_ProvisioningDeviceClient(self):
        # constructor
        global provisioning_uri
        global id_scope
        global security_device_type

        with self.assertRaises(Exception):
            client = ProvisioningDeviceClient()
        with self.assertRaises(Exception):
            client = ProvisioningDeviceClient(1)
        with self.assertRaises(Exception):
            client = ProvisioningDeviceClient(provisioning_uri)
        with self.assertRaises(Exception):
            client = ProvisioningDeviceClient(provisioning_uri, 1)
        with self.assertRaises(Exception):
            client = ProvisioningDeviceClient(provisioning_uri, id_scope)
        with self.assertRaises(Exception):
            client = ProvisioningDeviceClient(provisioning_uri, id_scope, 1)
        with self.assertRaises(Exception):
            client = ProvisioningDeviceClient(provisioning_uri, id_scope, security_device_type)
        with self.assertRaises(Exception):
            client = ProvisioningDeviceClient(provisioning_uri, id_scope, security_device_type, 1)

        if hasattr(ProvisioningTransportProvider, "HTTP"):
            provisioningDeviceClient = ProvisioningDeviceClient(provisioning_uri, id_scope, ProvisioningSecurityDeviceType.X509, ProvisioningTransportProvider.HTTP)
            self.assertIsInstance(provisioningDeviceClient, ProvisioningDeviceClient)
            self.assertEqual(provisioningDeviceClient.protocol, ProvisioningTransportProvider.HTTP)
            with self.assertRaises(AttributeError):
                provisioningDeviceClient.protocol = ProvisioningTransportProvider.AMQP

        if hasattr(ProvisioningTransportProvider, "AMQP"):
            provisioningDeviceClient = ProvisioningDeviceClient(provisioning_uri, id_scope, ProvisioningSecurityDeviceType.TPM, ProvisioningTransportProvider.AMQP)
            self.assertIsInstance(provisioningDeviceClient, ProvisioningDeviceClient)
            self.assertEqual(provisioningDeviceClient.protocol, ProvisioningTransportProvider.AMQP)
            with self.assertRaises(AttributeError):
                provisioningDeviceClient.protocol = ProvisioningTransportProvider.HTTP

        if hasattr(ProvisioningTransportProvider, "MQTT"):
            provisioningDeviceClient = ProvisioningDeviceClient(provisioning_uri, id_scope, ProvisioningSecurityDeviceType.TPM, ProvisioningTransportProvider.MQTT)
            self.assertIsInstance(provisioningDeviceClient, ProvisioningDeviceClient)
            self.assertEqual(provisioningDeviceClient.protocol, ProvisioningTransportProvider.MQTT)
            with self.assertRaises(AttributeError):
                provisioningDeviceClient.protocol = ProvisioningTransportProvider.HTTP

        if hasattr(ProvisioningTransportProvider, "AMQP_WS"):
            provisioningDeviceClient = ProvisioningDeviceClient(provisioning_uri, id_scope, ProvisioningSecurityDeviceType.TPM, ProvisioningTransportProvider.AMQP_WS)
            self.assertIsInstance(provisioningDeviceClient, ProvisioningDeviceClient)
            self.assertEqual(provisioningDeviceClient.protocol, ProvisioningTransportProvider.AMQP_WS)
            with self.assertRaises(AttributeError):
                provisioningDeviceClient.protocol = ProvisioningTransportProvider.HTTP

        if hasattr(ProvisioningTransportProvider, "MQTT_WS"):
            provisioningDeviceClient = ProvisioningDeviceClient(provisioning_uri, id_scope, ProvisioningSecurityDeviceType.TPM, ProvisioningTransportProvider.MQTT_WS)
            self.assertIsInstance(provisioningDeviceClient, ProvisioningDeviceClient)
            self.assertEqual(provisioningDeviceClient.protocol, ProvisioningTransportProvider.MQTT_WS)
            with self.assertRaises(AttributeError):
                provisioningDeviceClient.protocol = ProvisioningTransportProvider.HTTP


        # register_device
        register_device_callback_counter = 1
        user_context = {"a": "b"}
        register_status_callback_counter = 1
        status_user_context = {"c": "d"}

        with self.assertRaises(AttributeError):
            provisioningDeviceClient.RegisterDevice()
        with self.assertRaises(Exception):
            provisioningDeviceClient.register_device()
        with self.assertRaises(Exception):
            provisioningDeviceClient.register_device(register_device_callback)
        with self.assertRaises(Exception):
            provisioningDeviceClient.register_device(user_context, register_device_callback)
        with self.assertRaises(Exception):
            provisioningDeviceClient.register_device(register_device_callback, user_context, register_status_callback_counter)
        with self.assertRaises(Exception):
            provisioningDeviceClient.register_device(user_context, register_device_callback, register_status_callback_counter)
        result = provisioningDeviceClient.register_device(register_device_callback, user_context, register_status_callback, status_user_context)
        self.assertEqual(result, ProvisioningDeviceResult.OK)


        # set_option
        timeout = 241000
        with self.assertRaises(AttributeError):
            provisioningDeviceClient.SetOption()
        with self.assertRaises(Exception):
            provisioningDeviceClient.set_option(1)
        with self.assertRaises(Exception):
            provisioningDeviceClient.set_option(timeout)
        with self.assertRaises(Exception):
            provisioningDeviceClient.set_option("timeout", bytearray("241000"))

        result = provisioningDeviceClient.set_option("TrustedCerts", "cert_info")
        self.assertIsNone(result)
        result = provisioningDeviceClient.set_option("logtrace", True)
        self.assertIsNone(result)
        provisioningHttpProxyOptions = ProvisioningHttpProxyOptions("aaa", 42, "bbb", "ccc")
        result = provisioningDeviceClient.set_option("proxy_data", provisioningHttpProxyOptions)
        self.assertIsNone(result)


        # get_twin
        version_string = provisioningDeviceClient.get_version_string()


if __name__ == '__main__':
    unittest.main(verbosity=2)
