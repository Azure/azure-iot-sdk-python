#!/usr/bin/env python

# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import sys
import unittest
import iothub_client_mock
import platform
from iothub_client_mock import *

# connnection strings for mock testing
connection_str = "HostName=mockhub.mock-devices.net;DeviceId=mockdevice;SharedAccessKey=1234567890123456789012345678901234567890ABCD"
uri_str = "aaa.bbb.ccc"
device_id = "device-id"

callback_key = ""
callback_value = ""
callback_message = ""

platform_is_mac = platform.mac_ver()[0]
if platform_is_mac:
    print ("Running on MacOS version " + platform_is_mac)
    print ("Provisioning related unit tests are disabled")

def map_callback_ok(key, value):
    global callback_key
    global callback_value
    callback_key = key
    callback_value = value
    return IoTHubMapResult.OK


def map_callback_reject(key, value):
    global callback_key
    global callback_value
    callback_key = key
    callback_value = value
    return IoTHubMapResult.FILTER_REJECT


def receive_message_callback(message, counter):
    return IoTHubMessageDispositionResult.ACCEPTED


def send_confirmation_callback(message, result, user_context):
    return


def device_twin_callback(update_state, payLoad, user_context):
    return


def send_reported_state_callback(status_code, user_context):
    return


def device_method_callback(method_name, payLoad, size, response, response_size, user_context):
    return


def device_method_callback_ex(method_name, payLoad, size, method_id, user_context):
    return


def blob_upload_callback(result, userContext):
    return

def invokemethod_callback(result, userContext):
    return;

def connection_status_callback(result, reason, user_context):
    return


class TestExceptionDefinitions(unittest.TestCase):

    def test_IoTHubError(self):
        error = IoTHubError()
        self.assertIsInstance(error, BaseException)
        self.assertIsInstance(error, IoTHubError)
        with self.assertRaises(BaseException):
            raise IoTHubError()
        with self.assertRaises(IoTHubError):
            raise IoTHubError()

    def test_IoTHubMapError(self):
        error = IoTHubMapError()
        self.assertIsInstance(error, BaseException)
        self.assertIsInstance(error, IoTHubError)
        self.assertIsInstance(error, IoTHubMapError)
        with self.assertRaises(BaseException):
            raise IoTHubMapError()
        with self.assertRaises(IoTHubError):
            raise IoTHubMapError()
        with self.assertRaises(IoTHubMapError):
            raise IoTHubMapError()

    def test_IoTHubMessageError(self):
        error = IoTHubMessageError()
        self.assertIsInstance(error, BaseException)
        self.assertIsInstance(error, IoTHubError)
        self.assertIsInstance(error, IoTHubMessageError)
        with self.assertRaises(BaseException):
            raise IoTHubMessageError()
        with self.assertRaises(IoTHubError):
            raise IoTHubMessageError()
        with self.assertRaises(IoTHubMessageError):
            raise IoTHubMessageError()

    def test_IoTHubClientError(self):
        error = IoTHubClientError()
        self.assertIsInstance(error, BaseException)
        self.assertIsInstance(error, IoTHubError)
        self.assertIsInstance(error, IoTHubClientError)
        with self.assertRaises(BaseException):
            raise IoTHubClientError()
        with self.assertRaises(IoTHubError):
            raise IoTHubClientError()
        with self.assertRaises(IoTHubClientError):
            raise IoTHubClientError()

    def test_IoTHubMapErrorArg(self):
        with self.assertRaises(Exception):
            error = IoTHubMapErrorArg()
        with self.assertRaises(Exception):
            error = IoTHubMapErrorArg(__name__)
        with self.assertRaises(Exception):
            error = IoTHubMapErrorArg(__name__, "function")
        with self.assertRaises(Exception):
            error = IoTHubMapErrorArg(IoTHubMapResult.ERROR)
        error = IoTHubMapErrorArg("function", IoTHubMapResult.ERROR)
        with self.assertRaises(TypeError):
            raise IoTHubMapErrorArg("function", IoTHubMapResult.ERROR)

    def test_IoTHubMessageErrorArg(self):
        with self.assertRaises(Exception):
            error = IoTHubMessageErrorArg()
        with self.assertRaises(Exception):
            error = IoTHubMessageErrorArg(__name__)
        with self.assertRaises(Exception):
            error = IoTHubMessageErrorArg(__name__, "function")
        with self.assertRaises(Exception):
            error = IoTHubMessageErrorArg(IoTHubMapResult.ERROR)
        error = IoTHubMessageErrorArg("function", IoTHubMessageResult.ERROR)
        with self.assertRaises(TypeError):
            raise IoTHubMessageErrorArg("function", IoTHubMessageResult.ERROR)

    def test_IoTHubClientErrorArg(self):
        with self.assertRaises(Exception):
            error = IoTHubClientErrorArg()
        with self.assertRaises(Exception):
            error = IoTHubClientErrorArg(__name__)
        with self.assertRaises(Exception):
            error = IoTHubClientErrorArg(__name__, "function")
        with self.assertRaises(Exception):
            error = IoTHubClientErrorArg(IoTHubMapResult.ERROR)
        error = IoTHubClientErrorArg("function", IoTHubClientResult.ERROR)
        with self.assertRaises(TypeError):
            raise IoTHubClientErrorArg("function", IoTHubClientResult.ERROR)


class TestEnumDefinitions(unittest.TestCase):

    def test_IoTHubMapResult(self):
        self.assertEqual(IoTHubMapResult.OK, 0)
        self.assertEqual(IoTHubMapResult.ERROR, 1)
        self.assertEqual(IoTHubMapResult.INVALIDARG, 2)
        self.assertEqual(IoTHubMapResult.KEYEXISTS, 3)
        self.assertEqual(IoTHubMapResult.KEYNOTFOUND, 4)
        self.assertEqual(IoTHubMapResult.FILTER_REJECT, 5)
        lastEnum = IoTHubMapResult.FILTER_REJECT + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(IoTHubMapResult.ANY, 0)
        mapResult = IoTHubMapResult()
        self.assertEqual(mapResult, 0)
        self.assertEqual(len(mapResult.names), lastEnum)
        self.assertEqual(len(mapResult.values), lastEnum)

    def test_IoTHubMessageResult(self):
        self.assertEqual(IoTHubMessageResult.OK, 0)
        self.assertEqual(IoTHubMessageResult.INVALID_ARG, 1)
        self.assertEqual(IoTHubMessageResult.INVALID_TYPE, 2)
        self.assertEqual(IoTHubMessageResult.ERROR, 3)
        lastEnum = IoTHubMessageResult.ERROR + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(IoTHubMessageResult.ANY, 0)
        messageResult = IoTHubMessageResult()
        self.assertEqual(messageResult, 0)
        self.assertEqual(len(messageResult.names), lastEnum)
        self.assertEqual(len(messageResult.values), lastEnum)

    def test_IoTHubClientResult(self):
        self.assertEqual(IoTHubClientResult.OK, 0)
        self.assertEqual(IoTHubClientResult.INVALID_ARG, 1)
        self.assertEqual(IoTHubClientResult.ERROR, 2)
        self.assertEqual(IoTHubClientResult.INVALID_SIZE, 3)
        self.assertEqual(IoTHubClientResult.INDEFINITE_TIME, 4)
        lastEnum = IoTHubClientResult.INDEFINITE_TIME + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(IoTHubClientResult.ANY, 0)
        clientResult = IoTHubClientResult()
        self.assertEqual(clientResult, 0)
        self.assertEqual(len(clientResult.names), lastEnum)
        self.assertEqual(len(clientResult.values), lastEnum)

    def test_IoTHubClientStatus(self):
        self.assertEqual(IoTHubClientStatus.IDLE, 0)
        self.assertEqual(IoTHubClientStatus.BUSY, 1)
        lastEnum = IoTHubClientStatus.BUSY + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(IoTHubClientStatus.ANY, 0)
        clientStatus = IoTHubClientStatus()
        self.assertEqual(clientStatus, 0)
        self.assertEqual(len(clientStatus.names), lastEnum)
        self.assertEqual(len(clientStatus.values), lastEnum)

    def test_IoTHubClientConfirmationResult(self):
        self.assertEqual(IoTHubClientConfirmationResult.OK, 0)
        self.assertEqual(IoTHubClientConfirmationResult.BECAUSE_DESTROY, 1)
        self.assertEqual(IoTHubClientConfirmationResult.MESSAGE_TIMEOUT, 2)
        self.assertEqual(IoTHubClientConfirmationResult.ERROR, 3)
        lastEnum = IoTHubClientConfirmationResult.ERROR + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(IoTHubClientConfirmationResult.ANY, 0)
        confirmationResult = IoTHubClientConfirmationResult()
        self.assertEqual(confirmationResult, 0)
        self.assertEqual(len(confirmationResult.names), lastEnum)
        self.assertEqual(len(confirmationResult.values), lastEnum)

    def test_IoTHubMessageDispositionResult(self):
        self.assertEqual(IoTHubMessageDispositionResult.ACCEPTED, 0)
        self.assertEqual(IoTHubMessageDispositionResult.REJECTED, 1)
        self.assertEqual(IoTHubMessageDispositionResult.ABANDONED, 2)
        lastEnum = IoTHubMessageDispositionResult.ABANDONED + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(IoTHubMessageDispositionResult.ANY, 0)
        dispositionResult = IoTHubMessageDispositionResult()
        self.assertEqual(dispositionResult, 0)
        self.assertEqual(len(dispositionResult.names), lastEnum)
        self.assertEqual(len(dispositionResult.values), lastEnum)

    def test_IoTHubMessageContent(self):
        self.assertEqual(IoTHubMessageContent.BYTEARRAY, 0)
        self.assertEqual(IoTHubMessageContent.STRING, 1)
        self.assertEqual(IoTHubMessageContent.UNKNOWN, 2)
        lastEnum = IoTHubMessageContent.UNKNOWN + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(IoTHubMessageContent.ANY, 0)
        dispositionResult = IoTHubMessageContent()
        self.assertEqual(dispositionResult, 0)
        self.assertEqual(len(dispositionResult.names), lastEnum)
        self.assertEqual(len(dispositionResult.values), lastEnum)

    def test_IoTHubConnectionStatus(self):
        self.assertEqual(IoTHubConnectionStatus.AUTHENTICATED, 0)
        self.assertEqual(IoTHubConnectionStatus.UNAUTHENTICATED, 1)
        lastEnum = IoTHubConnectionStatus.UNAUTHENTICATED + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(IoTHubConnectionStatus.ANY, 0)
        dispositionResult = IoTHubConnectionStatus()
        self.assertEqual(dispositionResult, 0)
        self.assertEqual(len(dispositionResult.names), lastEnum)

    def test_IoTHubClientConnectionStatusReason(self):
        self.assertEqual(IoTHubClientConnectionStatusReason.EXPIRED_SAS_TOKEN, 0)
        self.assertEqual(IoTHubClientConnectionStatusReason.DEVICE_DISABLED, 1)
        self.assertEqual(IoTHubClientConnectionStatusReason.BAD_CREDENTIAL, 2)
        self.assertEqual(IoTHubClientConnectionStatusReason.RETRY_EXPIRED, 3)
        self.assertEqual(IoTHubClientConnectionStatusReason.NO_NETWORK, 4)
        self.assertEqual(IoTHubClientConnectionStatusReason.COMMUNICATION_ERROR, 5)
        self.assertEqual(IoTHubClientConnectionStatusReason.CONNECTION_OK, 6)
        lastEnum = IoTHubClientConnectionStatusReason.CONNECTION_OK + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(IoTHubClientConnectionStatusReason.ANY, 0)
        dispositionResult = IoTHubClientConnectionStatusReason()
        self.assertEqual(dispositionResult, 0)
        self.assertEqual(len(dispositionResult.names), lastEnum)

    def test_IoTHubClientRetryPolicy(self):
        self.assertEqual(IoTHubClientRetryPolicy.RETRY_NONE, 0)
        self.assertEqual(IoTHubClientRetryPolicy.RETRY_IMMEDIATE, 1)
        self.assertEqual(IoTHubClientRetryPolicy.RETRY_INTERVAL, 2)
        self.assertEqual(IoTHubClientRetryPolicy.RETRY_LINEAR_BACKOFF, 3)
        self.assertEqual(IoTHubClientRetryPolicy.RETRY_EXPONENTIAL_BACKOFF, 4)
        self.assertEqual(IoTHubClientRetryPolicy.RETRY_EXPONENTIAL_BACKOFF_WITH_JITTER, 5)
        self.assertEqual(IoTHubClientRetryPolicy.RETRY_RANDOM, 6)
        lastEnum = IoTHubClientRetryPolicy.RETRY_RANDOM + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(IoTHubClientRetryPolicy.ANY, 0)
        dispositionResult = IoTHubClientRetryPolicy()
        self.assertEqual(dispositionResult, 0)
        self.assertEqual(len(dispositionResult.names), lastEnum)

    def test_IoTHubTransportProvider(self):
        if hasattr(IoTHubTransportProvider, "MQTT_WS"):
            self.assertEqual(IoTHubTransportProvider.HTTP, 0)
            self.assertEqual(IoTHubTransportProvider.AMQP, 1)
            self.assertEqual(IoTHubTransportProvider.MQTT, 2)
            self.assertEqual(IoTHubTransportProvider.AMQP_WS, 3)
            self.assertEqual(IoTHubTransportProvider.MQTT_WS, 4)
            lastEnum = IoTHubTransportProvider.MQTT_WS + 1
            with self.assertRaises(AttributeError):
                self.assertEqual(IoTHubTransportProvider.ANY, 0)
        else:
            self.assertEqual(IoTHubTransportProvider.HTTP, 0)
            self.assertEqual(IoTHubTransportProvider.AMQP, 1)
            self.assertEqual(IoTHubTransportProvider.MQTT, 2)
            lastEnum = IoTHubTransportProvider.MQTT + 1
            with self.assertRaises(AttributeError):
                self.assertEqual(IoTHubTransportProvider.ANY, 0)

class TestClassDefinitions(unittest.TestCase):

    def test_GetRetryPolicyReturnValue(self):
        # constructor
        getRetryPolicyReturnValue = GetRetryPolicyReturnValue()
        self.assertIsInstance(getRetryPolicyReturnValue, GetRetryPolicyReturnValue)

    def test_IoTHubMap(self):
        # constructor
        map = IoTHubMap(map_callback_ok)
        self.assertIsInstance(map, IoTHubMap)
        map = IoTHubMap()
        self.assertIsInstance(map, IoTHubMap)
        with self.assertRaises(Exception):
            map1 = IoTHubMap(1)
        # add
        map = IoTHubMap()
        with self.assertRaises(AttributeError):
            map.Add()
        with self.assertRaises(Exception):
            map.add()
        with self.assertRaises(Exception):
            map.add("key")
        with self.assertRaises(Exception):
            map.add(["key", "value"])
        result = map.add("key", "value")
        self.assertIsNone(result)
        # add_or_update
        with self.assertRaises(AttributeError):
            map.AddOrUpdate()
        with self.assertRaises(Exception):
            map.add_or_update()
        with self.assertRaises(Exception):
            map.add_or_update("key")
        with self.assertRaises(Exception):
            map.add_or_update(["key", "value"])
        result = map.add_or_update("key", "value")
        self.assertIsNone(result)
        # add, cannot change existing key
        with self.assertRaises(IoTHubMapError):
            result = map.add("key", "value")
        # contains_key
        with self.assertRaises(AttributeError):
            map.ContainsKey()
        with self.assertRaises(Exception):
            map.contains_key()
        with self.assertRaises(Exception):
            map.contains_key("key", "value")
        with self.assertRaises(Exception):
            map.contains_key(["key", "value"])
        self.assertTrue(map.contains_key("key"))
        self.assertFalse(map.contains_key("anykey"))
        # contains_value
        with self.assertRaises(AttributeError):
            map.ContainsValue()
        with self.assertRaises(Exception):
            map.contains_value()
        with self.assertRaises(Exception):
            map.contains_value("key", "value")
        with self.assertRaises(Exception):
            map.contains_value(["key", "value"])
        self.assertTrue(map.contains_value("value"))
        self.assertFalse(map.contains_value("anyvalue"))
        # get_value_from_key
        with self.assertRaises(AttributeError):
            map.GetValueFromKey()
        with self.assertRaises(Exception):
            map.get_value_from_key()
        with self.assertRaises(Exception):
            map.get_value_from_key("key", "value")
        with self.assertRaises(Exception):
            map.get_value_from_key(["key", "value"])
        self.assertEqual(map.get_value_from_key("key"), "value")
        with self.assertRaises(IoTHubMapError):
            result = map.get_value_from_key("anykey")
        # get_internals
        with self.assertRaises(AttributeError):
            map.GetInternals()
        with self.assertRaises(Exception):
            map.get_internals("key")
        with self.assertRaises(Exception):
            map.get_internals("key", "value")
        with self.assertRaises(Exception):
            map.get_internals(["key", "value"])
        keymap = map.get_internals()
        self.assertEqual(len(keymap), 1)
        self.assertEqual(keymap, {"key": "value"})
        # delete
        with self.assertRaises(AttributeError):
            map.Delete()
        with self.assertRaises(Exception):
            map.delete()
        with self.assertRaises(Exception):
            map.delete("key", "value")
        with self.assertRaises(Exception):
            map.delete(["key", "value"])
        result = map.delete("key")
        self.assertIsNone(result)
        with self.assertRaises(IoTHubMapError):
            result = map.delete("key")
        # get_internals
        keymap = map.get_internals()
        self.assertIsNotNone(keymap)
        self.assertEqual(len(keymap), 0)
        self.assertEqual(keymap, {})
        # test filter callback
        global callback_key
        global callback_value
        callback_key = ""
        callback_value = ""
        map = IoTHubMap(map_callback_ok)
        map.add("key", "value")
        self.assertEqual(len(map.get_internals()), 1)
        self.assertEqual(callback_key, "key")
        self.assertEqual(callback_value, "value")
        callback_key = ""
        callback_value = ""
        # check if second filter is refused
        with self.assertRaises(Exception):
            map2 = IoTHubMap(map_callback_reject)
        # clear ok filter
        map = IoTHubMap()
        # setup reject filter
        map = IoTHubMap(map_callback_reject)
        with self.assertRaises(IoTHubMapError):
            map.add("key", "value")
        self.assertEqual(len(map.get_internals()), 0)
        self.assertEqual(callback_key, "key")
        self.assertEqual(callback_value, "value")

    def test_IoTHubMessage(self):
        # constructor
        messageString = "myMessage"
        with self.assertRaises(Exception):
            message = IoTHubMessage()
        with self.assertRaises(Exception):
            message = IoTHubMessage(1)
        with self.assertRaises(Exception):
            message = IoTHubMessage(buffer(messageString))
        message = IoTHubMessage(messageString)
        self.assertIsInstance(message, IoTHubMessage)
        # get_bytearray
        message = IoTHubMessage(bytearray(messageString, "utf8"))
        self.assertIsInstance(message, IoTHubMessage)
        with self.assertRaises(AttributeError):
            message.GetByteArray()
        with self.assertRaises(Exception):
            message.get_bytearray(1)
        with self.assertRaises(Exception):
            message.get_bytearray("key")
        with self.assertRaises(Exception):
            message.get_bytearray(["key", "value"])
        result = message.get_bytearray()
        self.assertEqual(result, b"myMessage")
        # get_string
        message = IoTHubMessage(messageString)
        self.assertIsInstance(message, IoTHubMessage)
        with self.assertRaises(AttributeError):
            message.GetString()
        with self.assertRaises(Exception):
            message.get_string(1)
        with self.assertRaises(Exception):
            message.get_string("key")
        with self.assertRaises(Exception):
            message.get_string(["key", "value"])
        result = message.get_string()
        self.assertEqual(result, "myMessage")
        # get_content_type
        with self.assertRaises(AttributeError):
            message.GetContentType()
        with self.assertRaises(Exception):
            message.get_content_type(1)
        with self.assertRaises(Exception):
            message.get_content_type("key")
        with self.assertRaises(Exception):
            message.get_content_type(["key", "value"])
        message = IoTHubMessage(messageString)
        result = message.get_content_type()
        self.assertEqual(result, IoTHubMessageContent.STRING)
        message = IoTHubMessage(bytearray(messageString, "utf8"))
        result = message.get_content_type()
        self.assertEqual(result, IoTHubMessageContent.BYTEARRAY)

        # get_content_type_system_property
        with self.assertRaises(AttributeError):
            message.GetContentTypeSystemProperty()
        with self.assertRaises(Exception):
            message.get_content_type_system_property(1)
        with self.assertRaises(Exception):
            message.get_content_type_system_property("key")
        with self.assertRaises(Exception):
            message.get_content_type_system_property(["key", "value"])
        message = IoTHubMessage(messageString)
        result = message.get_content_type_system_property()
        self.assertEqual(result, "myMessage")

        # set_content_type_system_property
        with self.assertRaises(AttributeError):
            message.SetContentTypeSystemProperty()
        with self.assertRaises(Exception):
            message.set_content_type_system_property()
        result = message.set_content_type_system_property("property")
        self.assertEqual(result, 0)

        # get_content_encoding_system_property
        with self.assertRaises(AttributeError):
            message.GetContentEncodingSystemProperty()
        with self.assertRaises(Exception):
            message.get_content_encoding_system_property(1)
        result = message.get_content_encoding_system_property()
        with self.assertRaises(Exception):
            message.get_content_type_system_property(["key", "value"])
        message = IoTHubMessage(messageString)
        result = message.get_content_type_system_property()
        self.assertEqual(result, "myMessage")
        
        # set_content_encoding_system_property
        with self.assertRaises(AttributeError):
            message.SetContentEncodingSystemProperty()
        with self.assertRaises(Exception):
            message.set_content_encoding_system_property()
        result = message.set_content_type_system_property("property")
        self.assertEqual(result, 0)

        # get_diagnostic_property_data
        with self.assertRaises(AttributeError):
            message.GetDiagnosticPropertyData()
        with self.assertRaises(Exception):
            message.get_diagnostic_property_data(1)
        result = message.get_content_encoding_system_property()
        message = IoTHubMessage(messageString)
        result = message.get_diagnostic_property_data()
        self.assertIsNone(result)

        # set_diagnostic_property_data
        with self.assertRaises(AttributeError):
            message.SetDiagnosticPropertyData()
        with self.assertRaises(Exception):
            message.set_diagnostic_property_data()
        with self.assertRaises(Exception):
            message.set_diagnostic_property_data("data")
        data = IoTHubMessageDiagnosticPropertyData("diagId", "diagTime")
        result = message.set_diagnostic_property_data(data)
        self.assertEqual(result, 0)

        # properties
        with self.assertRaises(AttributeError):
            message.Properties()
        with self.assertRaises(Exception):
            message.properties(1)
        with self.assertRaises(Exception):
            message.properties("key")
        with self.assertRaises(Exception):
            message.properties(["key", "value"])
        map = message.properties()
        self.assertIsInstance(map, IoTHubMap)
        keymap = map.get_internals()
        # get message_id
        with self.assertRaises(AttributeError):
            message.GetMessageId()
        with self.assertRaises(Exception):
            result = message.message_id()
        with self.assertRaises(Exception):
            result = message.message_id("key")
        with self.assertRaises(Exception):
            result = message.message_id(["key", "value"])
        result = message.message_id
        self.assertEqual(result, None)
        #  set message_id
        with self.assertRaises(AttributeError):
            message.SetMessageId()
        with self.assertRaises(Exception):
            message.message_id()
        with self.assertRaises(Exception):
            message.message_id = 1
        with self.assertRaises(Exception):
            message.message_id = ["key", "value"]
        result = message.message_id = "messageId"
        self.assertEqual(result, "messageId")
        # get message_id & set message_id
        result = message.message_id = "xyz"
        self.assertEqual(result, "xyz")
        result = message.message_id
        self.assertEqual(result, "xyz")
        # get correlation_id
        with self.assertRaises(AttributeError):
            message.GetCorrelationId()
        with self.assertRaises(Exception):
            result = message.correlation_id(1)
        with self.assertRaises(Exception):
            result = message.correlation_id("key")
        with self.assertRaises(Exception):
            result = message.correlation_id(["key", "value"])
        result = message.correlation_id
        self.assertIsNone(result)
        # set correlation_id
        with self.assertRaises(AttributeError):
            message.SetCorrelationId()
        with self.assertRaises(Exception):
            message.correlation_id()
        with self.assertRaises(Exception):
            message.correlation_id(1)
        with self.assertRaises(Exception):
            message.correlation_id(["key", "value"])
        result = message.correlation_id = "correlation_id"
        self.assertEqual(result, "correlation_id")
        # get & set correlation_id
        result = message.correlation_id = "xyz"
        self.assertEqual(result, "xyz")
        result = message.correlation_id
        self.assertEqual(result, "xyz")
        # input_name / output_name / connection_device_id / connection_module_id do not have set operations
        # test them against the hard-coded string that the mocked C layer returns
        result = message.input_name
        self.assertEqual(result, "python-testmockInput")
        result = message.output_name
        self.assertEqual(result, "python-testmockOutput")
        result = message.connection_device_id
        self.assertEqual(result, "python-testmockConnectionDeviceId")
        result = message.connection_module_id
        self.assertEqual(result, "python-testmockConnectionModuleId")

    def test_DeviceMethodReturnValue(self):
        # constructor
        deviceMethodReturnValue = DeviceMethodReturnValue()
        self.assertIsInstance(deviceMethodReturnValue, DeviceMethodReturnValue)

    def test_IoTHubConfig(self):
        # constructor
        ioTHubConfig = IoTHubConfig(IoTHubTransportProvider.AMQP, "aaa", "bbb", "ccc", "ddd", "eee", "fff")
        self.assertIsInstance(ioTHubConfig, IoTHubConfig)

    def test_IoTHubTransport(self):
        # constructor
        ioTHubTransport = IoTHubTransport(IoTHubTransportProvider.AMQP, "aaa", "bbb")
        self.assertIsInstance(ioTHubTransport, IoTHubTransport)

    def test_IoTHubClient(self):
        # constructor
        with self.assertRaises(Exception):
            client = IoTHubClient()
        with self.assertRaises(Exception):
            client = IoTHubClient(1)
        with self.assertRaises(Exception):
            client = IoTHubClient(connection_str)
        with self.assertRaises(Exception):
            client = IoTHubClient(connection_str, 1)
        with self.assertRaises(Exception):
            client = IoTHubClient(uri_str, uri_str)
        with self.assertRaises(Exception):
            client = IoTHubClient(uri_str, uri_str, 1)

        ioTHubTransport = IoTHubTransport(IoTHubTransportProvider.AMQP, "aaa", "bbb")
        self.assertIsInstance(ioTHubTransport, IoTHubTransport)
        ioTHubConfig = IoTHubConfig(IoTHubTransportProvider.AMQP, "aaa", "bbb", "ccc", "ddd", "eee", "fff")
        self.assertIsInstance(ioTHubConfig, IoTHubConfig)
        client = IoTHubClient(ioTHubTransport, ioTHubConfig)
        self.assertIsInstance(client, IoTHubClient)

        module = IoTHubModuleClient(ioTHubTransport, ioTHubConfig)

        if hasattr(IoTHubTransportProvider, "HTTP"):
            client = IoTHubClient(connection_str, IoTHubTransportProvider.HTTP)
            self.assertIsInstance(client, IoTHubClient)
            self.assertEqual(client.protocol, IoTHubTransportProvider.HTTP)
            with self.assertRaises(AttributeError):
                client.protocol = IoTHubTransportProvider.AMQP

            #When we are building for Mac there is no ProvisioningClient included in the C build and the classes below are not exts
            if not platform_is_mac:
                client = IoTHubClient(uri_str, device_id, IoTHubSecurityType.SAS, IoTHubTransportProvider.HTTP)
                self.assertIsInstance(client, IoTHubClient)
                self.assertEqual(client.protocol, IoTHubTransportProvider.HTTP)
                with self.assertRaises(AttributeError):
                    client.protocol = IoTHubTransportProvider.AMQP

        if hasattr(IoTHubTransportProvider, "AMQP"):
            client = IoTHubClient(connection_str, IoTHubTransportProvider.AMQP)
            self.assertIsInstance(client, IoTHubClient)
            self.assertEqual(client.protocol, IoTHubTransportProvider.AMQP)
            with self.assertRaises(AttributeError):
                client.protocol = IoTHubTransportProvider.AMQP

            #When we are building for Mac there is no ProvisioningClient included in the C build and the classes below are not exts
            if not platform_is_mac:
                client = IoTHubClient(uri_str, device_id, IoTHubSecurityType.X509, IoTHubTransportProvider.AMQP)
                self.assertIsInstance(client, IoTHubClient)
                self.assertEqual(client.protocol, IoTHubTransportProvider.AMQP)
                with self.assertRaises(AttributeError):
                    client.protocol = IoTHubTransportProvider.AMQP

        if hasattr(IoTHubTransportProvider, "MQTT"):
            client = IoTHubClient(connection_str, IoTHubTransportProvider.MQTT)
            self.assertIsInstance(client, IoTHubClient)
            self.assertEqual(client.protocol, IoTHubTransportProvider.MQTT)
            with self.assertRaises(AttributeError):
                client.protocol = IoTHubTransportProvider.AMQP

            #When we are building for Mac there is no ProvisioningClient included in the C build and the classes below are not exts
            if not platform_is_mac:
                client = IoTHubClient(uri_str, device_id, IoTHubSecurityType.SAS, IoTHubTransportProvider.MQTT)
                self.assertIsInstance(client, IoTHubClient)
                self.assertEqual(client.protocol, IoTHubTransportProvider.MQTT)
                with self.assertRaises(AttributeError):
                    client.protocol = IoTHubTransportProvider.AMQP

        if hasattr(IoTHubTransportProvider, "AMQP_WS"):
            client = IoTHubClient(connection_str, IoTHubTransportProvider.AMQP_WS)
            self.assertIsInstance(client, IoTHubClient)
            self.assertEqual(client.protocol, IoTHubTransportProvider.AMQP_WS)
            with self.assertRaises(AttributeError):
                client.protocol = IoTHubTransportProvider.AMQP

            #When we are building for Mac there is no ProvisioningClient included in the C build and the classes below are not exts
            if not platform_is_mac:
                client = IoTHubClient(uri_str, device_id, IoTHubSecurityType.X509, IoTHubTransportProvider.AMQP_WS)
                self.assertIsInstance(client, IoTHubClient)
                self.assertEqual(client.protocol, IoTHubTransportProvider.AMQP_WS)
                with self.assertRaises(AttributeError):
                    client.protocol = IoTHubTransportProvider.AMQP

        if hasattr(IoTHubTransportProvider, "MQTT_WS"):
            client = IoTHubClient(connection_str, IoTHubTransportProvider.MQTT_WS)
            self.assertIsInstance(client, IoTHubClient)
            self.assertEqual(client.protocol, IoTHubTransportProvider.MQTT_WS)
            with self.assertRaises(AttributeError):
                client.protocol = IoTHubTransportProvider.AMQP

            #When we are building for Mac there is no ProvisioningClient included in the C build and the classes below are not exts
            if not platform_is_mac:
                client = IoTHubClient(uri_str, device_id, IoTHubSecurityType.SAS, IoTHubTransportProvider.MQTT_WS)
                self.assertIsInstance(client, IoTHubClient)
                self.assertEqual(client.protocol, IoTHubTransportProvider.MQTT_WS)
                with self.assertRaises(AttributeError):
                    client.protocol = IoTHubTransportProvider.AMQP

        with self.assertRaises(AttributeError):
            client.protocol = IoTHubTransportProvider.AMQP
        with self.assertRaises(AttributeError):
            client.protocol = 1

        # set_message_callback
        counter = 1
        context = {"a": "b"}
        with self.assertRaises(AttributeError):
            client.SetMessageCallback()
        with self.assertRaises(Exception):
            client.set_message_callback()
        with self.assertRaises(Exception):
            client.set_message_callback(receive_message_callback)
        with self.assertRaises(Exception):
            client.set_message_callback(counter, receive_message_callback)
        with self.assertRaises(Exception):
            client.set_message_callback(
                receive_message_callback, counter, context)
        result = client.set_message_callback(receive_message_callback, counter)
        self.assertIsNone(result)
        result = client.set_message_callback(receive_message_callback, context)
        self.assertIsNone(result)

        # set_message_callback when using an input name
        inputName = "inputName"
        with self.assertRaises(Exception):
            module.set_message_callback(receive_message_callback, inputName, context)
        result = module.set_message_callback(inputName, receive_message_callback, context)

        # send_event_async
        counter = 1
        message = IoTHubMessage("myMessage")
        with self.assertRaises(AttributeError):
            client.SendEventAsync()
        with self.assertRaises(Exception):
            client.send_event_async()
        with self.assertRaises(Exception):
            client.send_event_async(send_confirmation_callback)
        with self.assertRaises(Exception):
            client.send_event_async(message, send_confirmation_callback)
        with self.assertRaises(Exception):
            client.send_event_async(
                send_confirmation_callback, message, counter)
        result = client.send_event_async(
            message, send_confirmation_callback, counter)
        self.assertIsNone(result)

        # send_event_async with output name
        outputName = "output_name"
        with self.assertRaises(Exception):
            result = module.send_event_async(
                message, outputName, send_confirmation_callback, counter)
        result = module.send_event_async(
            outputName, message, send_confirmation_callback, counter)
        self.assertIsNone(result)

        # create_from_environment
        module_from_env = IoTHubModuleClient()
        with self.assertRaises(Exception):
            result = module_from_env.create_from_environment()
        with self.assertRaises(Exception):
            result = module_from_env.create_from_environment(IoTHubTransportProvider.AMQP, "invalidParam")
        result = module_from_env.create_from_environment(IoTHubTransportProvider.AMQP)
        self.assertIsNone(result)

        # invoke_method
        timeout = 60
        with self.assertRaises(Exception):
            module.invoke_method_async();
        with self.assertRaises(Exception):
            module.invoke_method_async("testDevice");
        with self.assertRaises(Exception):
            module.invoke_method_async("testDevice", "testModule");
        with self.assertRaises(Exception):
            module.invoke_method_async("testDevice", "testModule", "methodName");
        with self.assertRaises(Exception):
            module.invoke_method_async("testDevice", "testModule", "methodName", "methodPayload");
        with self.assertRaises(Exception):
            module.invoke_method_async("testDevice", "testModule", "methodName", "methodPayload", "foo");
        with self.assertRaises(Exception):
            module.invoke_method_async("testDevice", "testModule", "methodName", "methodPayload", timeout, "foo");
        with self.assertRaises(Exception):
            module.invoke_method_async("testDevice", "testModule", "methodName", "methodPayload", timeout, invokemethod_callback);

        # testing module invoke overload
        module.invoke_method_async("testDevice", "methodName", "methodPayload", timeout, invokemethod_callback, None);
        # testing device invoke overload
        module.invoke_method_async("testDevice", "testModule", "methodName", "methodPayload", timeout, invokemethod_callback, None);

        # get_send_status
        with self.assertRaises(AttributeError):
            client.GetSendStatus()
        with self.assertRaises(Exception):
            client.get_send_status(1)
        with self.assertRaises(Exception):
            client.get_send_status(counter)
        result = client.get_send_status()
        self.assertIsNotNone(result)

        # get_last_message_receive_time
        with self.assertRaises(AttributeError):
            result = client.GetLastMessageReceiveTime()
        with self.assertRaises(Exception):
            result = client.get_last_message_receive_time(1)
        with self.assertRaises(Exception):
            client.get_last_message_receive_time(counter)
        with self.assertRaises(IoTHubClientError):
            result = client.get_last_message_receive_time()

        # set_option
        timeout = 241000
        with self.assertRaises(AttributeError):
            client.SetOption()
        with self.assertRaises(Exception):
            client.set_option(1)
        with self.assertRaises(Exception):
            client.set_option(timeout)
        with self.assertRaises(TypeError):
            client.set_option("timeout", bytearray("241000"))
        result = client.set_option("timeout", "241000")
        self.assertIsNone(result)
        result = client.set_option("timeout", timeout)
        self.assertIsNone(result)

        #set option w/ proxy
        proxy = HttpProxyOptions("127.0.0.1", 8888, "username", "password")
        result = client.set_option("proxy_data", proxy)
        self.assertIsNone(result)
        proxy = HttpProxyOptions("127.0.0.1", 8888)
        result = client.set_option("proxy_data", proxy)
        self.assertIsNone(result)

        # set_device_twin_callback
        counter = 1
        context = {"a": "b"}
        with self.assertRaises(AttributeError):
            client.SetDeviceTwinCallback()
        with self.assertRaises(Exception):
            client.set_device_twin_callback()
        with self.assertRaises(Exception):
            client.set_device_twin_callback(device_twin_callback)
        with self.assertRaises(Exception):
            client.set_device_twin_callback(counter, device_twin_callback)
        with self.assertRaises(Exception):
            client.set_device_twin_callback(
                device_twin_callback, counter, context)
        result = client.set_device_twin_callback(device_twin_callback, counter)
        self.assertIsNone(result)
        result = client.set_device_twin_callback(device_twin_callback, context)
        self.assertIsNone(result)

        # send_reported_state
        counter = 1
        reportedState = "{}"
        size = 2
        with self.assertRaises(AttributeError):
            client.SendReportedState()
        with self.assertRaises(Exception):
            client.send_reported_state()
        with self.assertRaises(Exception):
            client.send_reported_state(send_reported_state_callback)
        with self.assertRaises(Exception):
            client.send_reported_state(send_reported_state_callback, reportedState)
        with self.assertRaises(Exception):
            client.send_reported_state(send_reported_state_callback, size)
        with self.assertRaises(Exception):
            client.send_reported_state(send_reported_state_callback, reportedState, size)
        with self.assertRaises(Exception):
            client.send_reported_state(reportedState)
        with self.assertRaises(Exception):
            client.send_reported_state(reportedState, size)
        with self.assertRaises(Exception):
            client.send_reported_state(reportedState, send_reported_state_callback)
        with self.assertRaises(Exception):
            client.send_reported_state(reportedState, size, send_reported_state_callback)
        result = client.send_reported_state(
            reportedState, size, send_reported_state_callback, counter)
        self.assertIsNone(result)

        # set_device_method_callback
        counter = 1
        context = {"a": "b"}
        with self.assertRaises(AttributeError):
            client.SetDeviceMethodCallback()
        with self.assertRaises(Exception):
            client.set_device_method_callback()
        with self.assertRaises(Exception):
            client.set_device_method_callback(device_method_callback)
        with self.assertRaises(Exception):
            client.set_device_method_callback(counter, device_method_callback)
        with self.assertRaises(Exception):
            client.set_device_method_callback(
                device_method_callback, counter, context)
        result = client.set_device_method_callback(device_method_callback, counter)
        self.assertIsNone(result)
        result = client.set_device_method_callback(device_method_callback, context)
        self.assertIsNone(result)

        # set_device_method_callback_ex
        counter = 1
        context = {"a": "b"}
        with self.assertRaises(AttributeError):
            client.SetDeviceMethodCallbackEx()
        with self.assertRaises(Exception):
            client.set_device_method_callback_ex()
        with self.assertRaises(Exception):
            client.set_device_method_callback_ex(device_method_callback)
        with self.assertRaises(Exception):
            client.set_device_method_callback_ex(counter, device_method_callback)
        with self.assertRaises(Exception):
            client.set_device_method_callback_ex(
                device_method_callback, counter, context)
        result = client.set_device_method_callback_ex(device_method_callback_ex, counter)
        self.assertIsNone(result)
        result = client.set_device_method_callback_ex(device_method_callback_ex, context)
        self.assertIsNone(result)

        # device_method_response
        method_id = 42
        response = "{}"
        size = 2
        statusCode = 0
        with self.assertRaises(AttributeError):
            client.DeviceMethodResponse()
        with self.assertRaises(Exception):
            client.device_method_response()
        with self.assertRaises(Exception):
            client.device_method_response(method_id)
        with self.assertRaises(Exception):
            client.device_method_response(method_id, response)
        with self.assertRaises(Exception):
            client.device_method_response(method_id, size)
        with self.assertRaises(Exception):
            client.device_method_response(method_id, response, size)
        with self.assertRaises(Exception):
            client.device_method_response(response)
        with self.assertRaises(Exception):
            client.device_method_response(response, size)
        with self.assertRaises(Exception):
            client.device_method_response(response, statusCode)
        with self.assertRaises(Exception):
            client.device_method_response(response, size, statusCode)
        result = client.device_method_response(method_id, response, size, statusCode)
        self.assertIsNone(result)

        # set_connection_status_callback
        counter = 1
        context = {"a": "b"}
        with self.assertRaises(AttributeError):
            client.SetConnectionStatusCallback()
        with self.assertRaises(Exception):
            client.set_connection_status_callback()
        with self.assertRaises(Exception):
            client.set_connection_status_callback(connection_status_callback)
        with self.assertRaises(Exception):
            client.set_connection_status_callback(counter, connection_status_callback)
        with self.assertRaises(Exception):
            client.set_connection_status_callback(
                set_connection_status_callback, counter, context)
        result = client.set_connection_status_callback(connection_status_callback, counter)
        self.assertIsNone(result)
        result = client.set_connection_status_callback(connection_status_callback, context)

        # set_retry_policy
        timeout = 241000
        with self.assertRaises(AttributeError):
            client.SetRetryPolicy()
        with self.assertRaises(Exception):
            client.set_retry_policy(1)
        with self.assertRaises(Exception):
            client.set_retry_policy(timeout)
        with self.assertRaises(TypeError):
            client.set_retry_policy("timeout", bytearray("241000"))
        with self.assertRaises(TypeError):
            client.set_retry_policy("timeout", timeout)
        with self.assertRaises(TypeError):
            client.set_retry_policy(IoTHubClientRetryPolicy.RETRY_IMMEDIATE, "241000")
        result = client.set_retry_policy(IoTHubClientRetryPolicy.RETRY_IMMEDIATE, timeout)
        self.assertIsNone(result)

        # get_retry_policy
        timeout = 241000
        with self.assertRaises(AttributeError):
            client.GetRetryPolicy()
        with self.assertRaises(Exception):
            client.get_retry_policy(1)
        retryPolicyReturn = client.get_retry_policy()
        self.assertIsNone(result)

        # upload_blob_async
        destinationFileName = "fname"
        source = "src"
        size = 10
        with self.assertRaises(AttributeError):
            client.UploadToBlobAsync()
        with self.assertRaises(Exception):
            client.upload_blob_async(1)
        with self.assertRaises(Exception):
            client.upload_blob_async(blob_upload_callback)
        with self.assertRaises(Exception):
            client.upload_blob_async(destinationFileName, blob_upload_callback)
        with self.assertRaises(Exception):
            client.upload_blob_async(destinationFileName, source, blob_upload_callback)
        with self.assertRaises(Exception):
            client.upload_blob_async(destinationFileName, source, size, send_confirmation_callback)
        result = client.upload_blob_async(destinationFileName, source, size, send_confirmation_callback, None)
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main(verbosity=2)
