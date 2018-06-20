# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import sys
import unittest
import iothub_service_client_mock
from iothub_service_client_mock import *

# connnection strings for mock testing
connectionString = "HostName=mockhub.mock-devices.net;SharedAccessKeyName=mockowner;SharedAccessKey=1234567890123456789012345678901234567890ABCD"

callback_key = ""
callback_value = ""
callback_message = ""


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


def open_complete_callback(context):
    return

def send_complete_callback(context, messagingResult):
    return

def send_complete_callback(updateState, payLoad, user_context):
    return

def feedback_received_callback(context, feedbackBatch):
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

    def test_IoTHubServiceClientAuthError(self):
        error = IoTHubServiceClientAuthError()
        self.assertIsInstance(error, BaseException)
        self.assertIsInstance(error, IoTHubError)
        with self.assertRaises(BaseException):
            raise IoTHubError()
        with self.assertRaises(IoTHubError):
            raise IoTHubServiceClientAuthError()
        with self.assertRaises(IoTHubServiceClientAuthError):
            raise IoTHubServiceClientAuthError()

    def test_IoTHubServiceClientAuthErrorArg(self):
        with self.assertRaises(Exception):
            error = IoTHubServiceClientAuthErrorArg()
        error = IoTHubServiceClientAuthErrorArg("function")
        with self.assertRaises(TypeError):
            raise IoTHubServiceClientAuthErrorArg("function")

    def test_IoTHubRegistryManagerError(self):
        error = IoTHubRegistryManagerError()
        self.assertIsInstance(error, BaseException)
        self.assertIsInstance(error, IoTHubError)
        with self.assertRaises(BaseException):
            raise IoTHubError()
        with self.assertRaises(IoTHubError):
            raise IoTHubRegistryManagerError()
        with self.assertRaises(IoTHubRegistryManagerError):
            raise IoTHubRegistryManagerError()

    def test_IoTHubRegistryManagerErrorArg(self):
        with self.assertRaises(Exception):
            error = IoTHubRegistryManagerErrorArg()
        with self.assertRaises(Exception):
            error = IoTHubRegistryManagerErrorArg(__name__)
        with self.assertRaises(Exception):
            error = IoTHubRegistryManagerErrorArg(__name__, "function")
        with self.assertRaises(Exception):
            error = IoTHubRegistryManagerErrorArg(IoTHubMapResult.ERROR)
        error = IoTHubRegistryManagerErrorArg("function", IoTHubRegistryManagerResult.ERROR)
        with self.assertRaises(TypeError):
            raise IoTHubRegistryManagerErrorArg("function", IoTHubRegistryManagerResult.ERROR)

    def test_IoTHubMessagingError(self):
        error = IoTHubMessagingError()
        self.assertIsInstance(error, BaseException)
        self.assertIsInstance(error, IoTHubError)
        with self.assertRaises(BaseException):
            raise IoTHubError()
        with self.assertRaises(IoTHubError):
            raise IoTHubMessagingError()
        with self.assertRaises(IoTHubMessagingError):
            raise IoTHubMessagingError()

    def test_IoTHubMessagingErrorArg(self):
        with self.assertRaises(Exception):
            error = IoTHubMessagingErrorArg()
        with self.assertRaises(Exception):
            error = IoTHubMessagingErrorArg(__name__)
        with self.assertRaises(Exception):
            error = IoTHubMessagingErrorArg(__name__, "function")
        with self.assertRaises(Exception):
            error = IoTHubMessagingErrorArg(IoTHubMapResult.ERROR)
        error = IoTHubMessagingErrorArg("function", IoTHubMessagingResult.ERROR)
        with self.assertRaises(TypeError):
            raise IoTHubMessagingErrorArg("function", IoTHubMessagingResult.ERROR)

    def test_IoTHubDeviceMethodError(self):
        error = IoTHubDeviceMethodError()
        self.assertIsInstance(error, BaseException)
        self.assertIsInstance(error, IoTHubError)
        with self.assertRaises(BaseException):
            raise IoTHubError()
        with self.assertRaises(IoTHubError):
            raise IoTHubDeviceMethodError()
        with self.assertRaises(IoTHubDeviceMethodError):
            raise IoTHubDeviceMethodError()

    def test_IoTHubDeviceMethodErrorArg(self):
        with self.assertRaises(Exception):
            error = IoTHubDeviceMethodErrorArg()
        with self.assertRaises(Exception):
            error = IoTHubDeviceMethodErrorArg(__name__)
        with self.assertRaises(Exception):
            error = IoTHubDeviceMethodErrorArg(__name__, "function")
        with self.assertRaises(Exception):
            error = IoTHubDeviceMethodErrorArg(IoTHubDEviceMethodResult.ERROR)
        error = IoTHubDeviceMethodErrorArg("function", IoTHubDeviceMethodResult.ERROR)
        with self.assertRaises(TypeError):
            raise IoTHubDeviceMethodErrorArg("function", IoTHubDeviceMethodResult.ERROR)

    def test_IoTHubDeviceTwinError(self):
        error = IoTHubDeviceTwinError()
        self.assertIsInstance(error, BaseException)
        self.assertIsInstance(error, IoTHubError)
        with self.assertRaises(BaseException):
            raise IoTHubError()
        with self.assertRaises(IoTHubError):
            raise IoTHubDeviceTwinError()
        with self.assertRaises(IoTHubDeviceTwinError):
            raise IoTHubDeviceTwinError()

    def test_IoTHubDeviceTwinErrorArg(self):
        with self.assertRaises(Exception):
            error = IoTHubDeviceTwinErrorArg()
        with self.assertRaises(Exception):
            error = IoTHubDeviceTwinErrorArg(__name__)
        with self.assertRaises(Exception):
            error = IoTHubDeviceTwinErrorArg(__name__, "function")
        with self.assertRaises(Exception):
            error = IoTHubDeviceTwinErrorArg(IoTHubDeviceTwinResult.ERROR)
        error = IoTHubDeviceTwinErrorArg("function", IoTHubDeviceTwinResult.ERROR)
        with self.assertRaises(TypeError):
            raise IoTHubDeviceTwinErrorArg("function", IoTHubDeviceTwinResult.ERROR)

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

    def test_IoTHubRegistryManagerResult(self):
        self.assertEqual(IoTHubRegistryManagerResult.OK, 0)
        self.assertEqual(IoTHubRegistryManagerResult.INVALID_ARG, 1)
        self.assertEqual(IoTHubRegistryManagerResult.ERROR, 2)
        self.assertEqual(IoTHubRegistryManagerResult.JSON_ERROR, 3)
        self.assertEqual(IoTHubRegistryManagerResult.HTTPAPI_ERROR, 4)
        self.assertEqual(IoTHubRegistryManagerResult.HTTP_STATUS_ERROR, 5)
        self.assertEqual(IoTHubRegistryManagerResult.DEVICE_EXIST, 6)
        self.assertEqual(IoTHubRegistryManagerResult.DEVICE_NOT_EXIST, 7)
        self.assertEqual(IoTHubRegistryManagerResult.CALLBACK_NOT_SET, 8)
        lastEnum = IoTHubRegistryManagerResult.CALLBACK_NOT_SET + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(IoTHubRegistryManagerResult.ANY, 0)
        registryManagerResult = IoTHubRegistryManagerResult()
        self.assertEqual(registryManagerResult, 0)
        self.assertEqual(len(registryManagerResult.names), lastEnum)
        self.assertEqual(len(registryManagerResult.values), lastEnum)

    def test_IoTHubMessagingResult(self):
        self.assertEqual(IoTHubMessagingResult.OK, 0)
        self.assertEqual(IoTHubMessagingResult.INVALID_ARG, 1)
        self.assertEqual(IoTHubMessagingResult.ERROR, 2)
        self.assertEqual(IoTHubMessagingResult.INVALID_JSON, 3)
        self.assertEqual(IoTHubMessagingResult.DEVICE_EXIST, 4)
        self.assertEqual(IoTHubMessagingResult.CALLBACK_NOT_SET, 5)
        lastEnum = IoTHubMessagingResult.CALLBACK_NOT_SET + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(IoTHubMessagingResult.ANY, 0)
        messagingResult = IoTHubMessagingResult()
        self.assertEqual(messagingResult, 0)
        self.assertEqual(len(messagingResult.names), lastEnum)
        self.assertEqual(len(messagingResult.values), lastEnum)

    def test_IoTHubDeviceConnectionState(self):
        self.assertEqual(IoTHubDeviceConnectionState.CONNECTED, 0)
        self.assertEqual(IoTHubDeviceConnectionState.DISCONNECTED, 1)
        lastEnum = IoTHubDeviceConnectionState.DISCONNECTED + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(IoTHubDeviceConnectionState.ANY, 0)
        connectionState = IoTHubDeviceConnectionState()
        self.assertEqual(connectionState, 0)
        self.assertEqual(len(connectionState.names), lastEnum)
        self.assertEqual(len(connectionState.values), lastEnum)

    def test_IoTHubDeviceStatus(self):
        self.assertEqual(IoTHubDeviceStatus.ENABLED, 0)
        self.assertEqual(IoTHubDeviceStatus.DISABLED, 1)
        lastEnum = IoTHubDeviceStatus.DISABLED + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(IoTHubDeviceStatus.ANY, 0)
        deviceStatus = IoTHubDeviceStatus()
        self.assertEqual(deviceStatus, 0)
        self.assertEqual(len(deviceStatus.names), lastEnum)
        self.assertEqual(len(deviceStatus.values), lastEnum)

    def test_IoTHubFeedbackStatusCode(self):
        self.assertEqual(IoTHubFeedbackStatusCode.SUCCESS, 0)
        self.assertEqual(IoTHubFeedbackStatusCode.EXPIRED, 1)
        self.assertEqual(IoTHubFeedbackStatusCode.DELIVER_COUNT_EXCEEDED, 2)
        self.assertEqual(IoTHubFeedbackStatusCode.REJECTED, 3)
        self.assertEqual(IoTHubFeedbackStatusCode.UNKNOWN, 4)
        lastEnum = IoTHubFeedbackStatusCode.UNKNOWN + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(IoTHubFeedbackStatusCode.ANY, 0)
        deviceStatus = IoTHubFeedbackStatusCode()
        self.assertEqual(deviceStatus, 0)
        self.assertEqual(len(deviceStatus.names), lastEnum)
        self.assertEqual(len(deviceStatus.values), lastEnum)

    def test_IoTHubDeviceMethodResult(self):
        self.assertEqual(IoTHubDeviceMethodResult.OK, 0)
        self.assertEqual(IoTHubDeviceMethodResult.INVALID_ARG, 1)
        self.assertEqual(IoTHubDeviceMethodResult.ERROR, 2)
        self.assertEqual(IoTHubDeviceMethodResult.HTTPAPI_ERROR, 3)
        lastEnum = IoTHubDeviceMethodResult.HTTPAPI_ERROR + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(IoTHubDeviceMethodResult.ANY, 0)
        deviceMethodResult = IoTHubDeviceMethodResult()
        self.assertEqual(deviceMethodResult, 0)
        self.assertEqual(len(deviceMethodResult.names), lastEnum)
        self.assertEqual(len(deviceMethodResult.values), lastEnum)

    def test_IoTHubDeviceTwinResult(self):
        self.assertEqual(IoTHubDeviceTwinResult.OK, 0)
        self.assertEqual(IoTHubDeviceTwinResult.INVALID_ARG, 1)
        self.assertEqual(IoTHubDeviceTwinResult.ERROR, 2)
        self.assertEqual(IoTHubDeviceTwinResult.HTTPAPI_ERROR, 3)
        lastEnum = IoTHubDeviceTwinResult.HTTPAPI_ERROR + 1
        with self.assertRaises(AttributeError):
            self.assertEqual(IoTHubDeviceTwinResult.ANY, 0)
        deviceTwinResult = IoTHubDeviceTwinResult()
        self.assertEqual(deviceTwinResult, 0)
        self.assertEqual(len(deviceTwinResult.names), lastEnum)
        self.assertEqual(len(deviceTwinResult.values), lastEnum)

class TestClassDefinitions(unittest.TestCase):

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

    def test_IoTHubServiceClientAuth(self):
        # constructor
        with self.assertRaises(Exception):
            authClient = IoTHubServiceClientAuth()
        with self.assertRaises(Exception):
            authClient = IoTHubServiceClientAuth(1)
        with self.assertRaises(Exception):
            authClient = IoTHubServiceClientAuth(connectionString, 1)

        authClient = IoTHubServiceClientAuth(connectionString)
        self.assertIsInstance(authClient, IoTHubServiceClientAuth)

    def test_IoTHubRegistryManager(self):
        # constructor (connection string)
        with self.assertRaises(Exception):
            regManClient = IoTHubRegistryManager()
        with self.assertRaises(Exception):
            regManClient = IoTHubRegistryManager(1)
        with self.assertRaises(Exception):
            regManClient = IoTHubRegistryManager(connectionString, 1)

        regManClient = IoTHubRegistryManager(connectionString)
        self.assertIsInstance(regManClient, IoTHubRegistryManager)

        # constructor (auth handle)
        authClient = IoTHubServiceClientAuth(connectionString)
        regManClient = IoTHubRegistryManager(authClient)
        self.assertIsInstance(regManClient, IoTHubRegistryManager)

        # create_device
        deviceId = "deviceId"
        primaryKey = "primaryKey"
        secondaryKey = "secondaryKey"
        authMethod = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY;
        deviceCapabilities = IoTHubDeviceCapabilities()
        deviceCapabilities.iot_edge = False
        with self.assertRaises(AttributeError):
            regManClient.CreateDevice()
        with self.assertRaises(Exception):
            regManClient.create_device()
        with self.assertRaises(Exception):
            regManClient.create_device(deviceId)
        with self.assertRaises(Exception):
            regManClient.create_device(deviceId, primaryKey)
        with self.assertRaises(Exception):
            regManClient.create_device(deviceId, primaryKey, secondaryKey)
        result = regManClient.create_device(deviceId, primaryKey, secondaryKey, authMethod)
        self.assertIsInstance(result, IoTHubDevice)
        result = regManClient.create_device(deviceId, primaryKey, secondaryKey, authMethod, deviceCapabilities)
        self.assertIsInstance(result, IoTHubDevice)


        # get_device
        deviceId = "deviceId"
        with self.assertRaises(AttributeError):
            regManClient.GetDevice()
        with self.assertRaises(Exception):
            regManClient.get_device()
        result = regManClient.get_device(deviceId)
        self.assertIsInstance(result, IoTHubDevice)

        # update_device
        deviceId = "deviceId"
        primaryKey = "primaryKey"
        secondaryKey = "secondaryKey"
        status = IoTHubDeviceStatus.ENABLED
        authMethod = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY;
        deviceCapabilities = IoTHubDeviceCapabilities()
        deviceCapabilities.iot_edge = True
        with self.assertRaises(AttributeError):
            regManClient.UpdateDevice()
        with self.assertRaises(Exception):
            regManClient.update_device()
        with self.assertRaises(Exception):
            regManClient.update_device(deviceId)
        with self.assertRaises(Exception):
            regManClient.update_device(deviceId, primaryKey)
        with self.assertRaises(Exception):
            regManClient.update_device(deviceId, primaryKey, secondaryKey)
        with self.assertRaises(Exception):
            regManClient.create_device(deviceId, primaryKey, secondaryKey, status)
        regManClient.update_device(deviceId, primaryKey, secondaryKey, status, authMethod)
        regManClient.update_device(deviceId, primaryKey, secondaryKey, status, authMethod, deviceCapabilities)

        # delete_device
        deviceId = "deviceId"
        with self.assertRaises(AttributeError):
            regManClient.DeleteDevice()
        with self.assertRaises(Exception):
            regManClient.delete_device()
        regManClient.delete_device(deviceId)

        # get_device_list
        numberOfDevices = 42
        with self.assertRaises(AttributeError):
            regManClient.GetDeviceList()
        with self.assertRaises(Exception):
            regManClient.get_device_list()
        result = regManClient.get_device_list(numberOfDevices)

        # get_statistics
        with self.assertRaises(AttributeError):
            regManClient.GetStatistics()
        result = regManClient.get_statistics()
        self.assertIsInstance(result, IoTHubRegistryStatistics)

        # create_module
        deviceId = "deviceId"
        moduleId = "moduleId"
        primaryKey = "primaryKey"
        secondaryKey = "secondaryKey"
        authMethod = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY;
        with self.assertRaises(AttributeError):
            regManClient.CreateModule()
        with self.assertRaises(Exception):
            regManClient.create_module()
        with self.assertRaises(Exception):
            regManClient.create_module(deviceId)
        with self.assertRaises(Exception):
            regManClient.create_module(deviceId, primaryKey)
        with self.assertRaises(Exception):
            regManClient.create_module(deviceId, primaryKey, secondaryKey)
        with self.assertRaises(Exception):
            regManClient.create_module(deviceId, primaryKey, secondaryKey, moduleId)
        result = regManClient.create_module(deviceId, primaryKey, secondaryKey, moduleId, authMethod)
        self.assertIsInstance(result, IoTHubModule)

        # update_module
        deviceId = "deviceId"
        moduleId = "moduleId"
        primaryKey = "primaryKey"
        secondaryKey = "secondaryKey"
        status = IoTHubDeviceStatus.ENABLED
        authMethod = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY;
        with self.assertRaises(AttributeError):
            regManClient.UpdateModule()
        with self.assertRaises(Exception):
            regManClient.update_module()
        with self.assertRaises(Exception):
            regManClient.update_module(deviceId)
        with self.assertRaises(Exception):
            regManClient.update_module(deviceId, primaryKey)
        with self.assertRaises(Exception):
            regManClient.update_module(deviceId, primaryKey, secondaryKey)
        with self.assertRaises(Exception):
            regManClient.create_module(deviceId, primaryKey, secondaryKey, moduleId)
        regManClient.update_module(deviceId, primaryKey, secondaryKey, moduleId, authMethod)

        # get_module
        deviceId = "deviceId"
        moduleId = "moduleId"
        with self.assertRaises(AttributeError):
            regManClient.GetDevice()
        with self.assertRaises(Exception):
            regManClient.get_module()
        with self.assertRaises(Exception):
            regManClient.get_module(deviceId)
        result = regManClient.get_module(deviceId, moduleId)
        self.assertIsInstance(result, IoTHubModule)

        # get_module_list
        deviceId = "deviceId"
        with self.assertRaises(AttributeError):
            regManClient.GetModuleList()
        with self.assertRaises(Exception):
            regManClient.get_module_list()
        result = regManClient.get_module_list(deviceId)

        # delete_module
        deviceId = "deviceId"
        moduleId = "moduleId"
        with self.assertRaises(AttributeError):
            regManClient.DeleteModule()
        with self.assertRaises(Exception):
            regManClient.delete_module()
        with self.assertRaises(Exception):
            regManClient.delete_module(deviceId)
        regManClient.delete_module(deviceId, moduleId)

    def test_IoTHubMessaging(self):
        # constructor (connection string)
        with self.assertRaises(Exception):
            messagingClient = IoTHubMessaging()
        with self.assertRaises(Exception):
            messagingClient = IoTHubMessaging(1)
        with self.assertRaises(Exception):
            messagingClient = IoTHubMessaging(connectionString, 1)

        messagingClient = IoTHubMessaging(connectionString)
        self.assertIsInstance(messagingClient, IoTHubMessaging)

        # constructor (auth handle)
        authClient = IoTHubServiceClientAuth(connectionString)
        messagingClient = IoTHubMessaging(authClient)
        self.assertIsInstance(messagingClient, IoTHubMessaging)

        # open
        with self.assertRaises(AttributeError):
            messagingClient.Open()
        with self.assertRaises(Exception):
            messagingClient.open(1)
        with self.assertRaises(Exception):
            messagingClient.open("")
        with self.assertRaises(Exception):
            messagingClient.open(open_complete_callback)
        messagingClient.open(open_complete_callback, None)

        # close
        with self.assertRaises(AttributeError):
            messagingClient.Close()
        with self.assertRaises(Exception):
            messagingClient.close(1)
        with self.assertRaises(Exception):
            messagingClient.close("")
        messagingClient.close()

        # send_async
        deviceId = "deviceId"
        moduleId = "moduleId"
        message = IoTHubMessage(bytearray("Hello", 'utf8'))
        with self.assertRaises(AttributeError):
            messagingClient.SendAsync()
        with self.assertRaises(Exception):
            messagingClient.send_async(1)
        with self.assertRaises(Exception):
            messagingClient.send_async("")
        with self.assertRaises(Exception):
            messagingClient.send_async(deviceId, "")
        with self.assertRaises(Exception):
            messagingClient.send_async(deviceId, message)
        with self.assertRaises(Exception):
            messagingClient.send_async(deviceId, message, "")
        with self.assertRaises(Exception):
            messagingClient.send_async(deviceId, message, send_complete_callback)
        with self.assertRaises(Exception):
            messagingClient.send_async(deviceId, moduleId, message, send_complete_callback, None, "extraParam")
        # Success case with message to device
        messagingClient.send_async(deviceId, message, send_complete_callback, None)
        # Success case with message to module
        messagingClient.send_async(deviceId, moduleId, message, send_complete_callback, None)

        # set_feedback_message_callback
        with self.assertRaises(AttributeError):
            messagingClient.SetFeedbackMessageCallback()
        with self.assertRaises(Exception):
            messagingClient.set_feedback_message_callback(1)
        with self.assertRaises(Exception):
            messagingClient.set_feedback_message_callback("")
        with self.assertRaises(Exception):
            messagingClient.set_feedback_message_callback(feedback_received_callback)
        messagingClient.set_feedback_message_callback(feedback_received_callback, None)

    def test_IoTHubDeviceMethod(self):
        # constructor (connection string)
        with self.assertRaises(Exception):
            deviceMethodClient = IoTHubDeviceMethod()
        with self.assertRaises(Exception):
            deviceMethodClient = IoTHubDeviceMethod(1)
        with self.assertRaises(Exception):
            deviceMethodClient = IoTHubDeviceMethod(connectionString, 1)

        deviceMethodClient = IoTHubDeviceMethod(connectionString)
        self.assertIsInstance(deviceMethodClient, IoTHubDeviceMethod)

        # constructor (auth handle)
        authClient = IoTHubServiceClientAuth(connectionString)
        deviceMethodClient = IoTHubDeviceMethod(authClient)
        self.assertIsInstance(deviceMethodClient, IoTHubDeviceMethod)

        # invoke
        deviceId = "deviceId"
        moduleId = "moduleId"
        methodName = "methodName"
        methodPayload = "methodPayload"
        timeout = 42
        with self.assertRaises(Exception):
            deviceMethodClient.invoke()
        with self.assertRaises(Exception):
            deviceMethodClient.invoke(1)
        with self.assertRaises(Exception):
            deviceMethodClient.invoke(deviceId)
        with self.assertRaises(Exception):
            deviceMethodClient.invoke(deviceId, 1)
        with self.assertRaises(Exception):
            deviceMethodClient.invoke(deviceId, methodName)
        with self.assertRaises(Exception):
            deviceMethodClient.invoke(deviceId, methodName, 1)
        with self.assertRaises(Exception):
            deviceMethodClient.invoke(deviceId, methodName, methodPayload)
        with self.assertRaises(Exception):
            deviceMethodClient.invoke(deviceId, moduleId, methodName, methodPayload, timeout, "extraParameter")
        # Test success on invoke method on a device
        response = deviceMethodClient.invoke(deviceId, methodName, methodPayload, timeout)
        self.assertIsInstance(response, IoTHubDeviceMethodResponse)
        # Test success on invoke method on a module
        response = deviceMethodClient.invoke(deviceId, moduleId, methodName, methodPayload, timeout)
        self.assertIsInstance(response, IoTHubDeviceMethodResponse)

    def test_IoTHubDeviceTwin(self):
        # constructor (connection string)
        with self.assertRaises(Exception):
            deviceTwinClient = IoTHubDeviceTwin()
        with self.assertRaises(Exception):
            deviceTwinClient = IoTHubDeviceTwin(1)
        with self.assertRaises(Exception):
            deviceTwinClient = IoTHubDeviceTwin(connectionString, 1)

        deviceTwinClient = IoTHubDeviceTwin(connectionString)
        self.assertIsInstance(deviceTwinClient, IoTHubDeviceTwin)

        # constructor (auth handle)
        authClient = IoTHubServiceClientAuth(connectionString)
        deviceTwinClient = IoTHubDeviceTwin(authClient)
        self.assertIsInstance(deviceTwinClient, IoTHubDeviceTwin)

        # get_twin
        deviceId = "deviceId"
        moduleId = "moduleId"
        with self.assertRaises(Exception):
            deviceTwinClient.get_twin()
        with self.assertRaises(Exception):
            deviceTwinClient.get_twin(1)
        with self.assertRaises(Exception):
            deviceTwinClient.get_twin(deviceId, moduleId, 1)
        # Test success on get twin on device
        deviceTwinClient.get_twin(deviceId)
        # Test success on get twin on module
        deviceTwinClient.get_twin(deviceId, moduleId)

        # update_twin
        deviceId = "deviceId"
        moduleId = "moduleId"
        deviceTwinJson = "deviceTwinJson"
        with self.assertRaises(Exception):
            deviceTwinClient.update_twin()
        with self.assertRaises(Exception):
            deviceTwinClient.update_twin(1)
        with self.assertRaises(Exception):
            deviceTwinClient.update_twin(deviceId)
        with self.assertRaises(Exception):
            deviceTwinClient.update_twin(deviceId, 1)
        with self.assertRaises(Exception):
            deviceTwinClient.update_twin(deviceId, moduleId, 1)
        # Test success on update twin on device
        deviceTwinClient.update_twin(deviceId, deviceTwinJson)
        # Test success on update twin on module
        deviceTwinClient.update_twin(deviceId, moduleId, deviceTwinJson)

    def test_IoTHubDeviceConfiguration(self):
        # constructor (connection string)
        with self.assertRaises(Exception):
            deviceConfiguration = IoTHubDeviceConfiguration(1)

        deviceConfiguration = IoTHubDeviceConfiguration()

        # Set string type to integer properties
        with self.assertRaises(Exception):
            deviceConfiguration.priority = "setting-string-to-integer-priority"

        # Setting integer types to string properties
        with self.assertRaises(Exception):
            deviceConfiguration.schemaVersion = 123
        with self.assertRaises(Exception):
            deviceConfiguration.configurationId = 123
        with self.assertRaises(Exception):
            deviceConfiguration.targetCondition = 123
        with self.assertRaises(Exception):
            deviceConfiguration.eTag = 123
        with self.assertRaises(Exception):
            deviceConfiguration.content = 123
        with self.assertRaises(Exception):
            # Cannot set content to a string as it has properties itself.
            deviceConfiguration.content = "123"
        with self.assertRaises(Exception):
            deviceConfiguration.content.modulesContent = 123
        with self.assertRaises(Exception):
            deviceConfiguration.content.deviceContent = 123

        # Read only properties
        with self.assertRaises(Exception):
            deviceConfiguration.lastUpdatedTimeUtc = "LastUpdatedUtc"

        # Verify setting appropriate values is OK
        deviceConfiguration.priority = 1234
        deviceConfiguration.schemaVersion = "schemaVersion"
        deviceConfiguration.configurationId = "configurationId"
        deviceConfiguration.targetCondition = "targetCondition"
        deviceConfiguration.eTag = "etag"
        deviceConfiguration.content.modulesContent = "modulesContent"
        deviceConfiguration.content.deviceContent = "devicesContent"

    def test_IoTHubDeviceConfigurationManager(self):
        deviceConfiguration = IoTHubDeviceConfiguration()

        with self.assertRaises(Exception):
            deviceConfigurationManager = IoTHubDeviceConfigurationManager()
        with self.assertRaises(Exception):
            deviceConfigurationManager = IoTHubDeviceConfigurationManager("string1", "string2")

        authClient = IoTHubServiceClientAuth(connectionString)
        deviceConfigurationManager = IoTHubDeviceConfigurationManager(authClient)
        deviceConfigurationManager = IoTHubDeviceConfigurationManager(connectionString)

        # get_configuration
        with self.assertRaises(Exception):
            deviceConfigurationManager.get_configuration()
        with self.assertRaises(Exception):
            deviceConfigurationManager.get_configuration("configId1", "configId2")
        with self.assertRaises(Exception):
            deviceConfigurationManager.get_configuration(deviceConfiguration)
        deviceConfigurationManager.get_configuration("configId1")

        # add_configuration
        with self.assertRaises(Exception):
            deviceConfigurationManager.add_configuration()
        with self.assertRaises(Exception):
            deviceConfigurationManager.add_configuration("configId1")
        with self.assertRaises(Exception):
            deviceConfigurationManager.add_configuration(deviceConfiguration, "configId2")
        deviceConfigurationManager.add_configuration(deviceConfiguration)

        # update_configuration
        with self.assertRaises(Exception):
            deviceConfigurationManager.update_configuration()
        with self.assertRaises(Exception):
            deviceConfigurationManager.update_configuration("configId1")
        with self.assertRaises(Exception):
            deviceConfigurationManager.update_configuration(deviceConfiguration, "configId2")
        deviceConfigurationManager.update_configuration(deviceConfiguration)

        # update_configuration
        with self.assertRaises(Exception):
            deviceConfigurationManager.delete_configuration()
        with self.assertRaises(Exception):
            deviceConfigurationManager.delete_configuration("configId1", "configId2")
        with self.assertRaises(Exception):
            deviceConfigurationManager.delete_configuration(deviceConfiguration, "configId2")
        deviceConfigurationManager.delete_configuration("configId1")

        # get_configuration_list
        with self.assertRaises(Exception):
            deviceConfigurationManager.get_configuration_list()
        with self.assertRaises(Exception):
            deviceConfigurationManager.get_configuration_list("configId1", "configId2")
        with self.assertRaises(Exception):
            deviceConfigurationManager.get_configuration_list(deviceConfiguration, "configId2")
        with self.assertRaises(Exception):
            deviceConfigurationManager.get_configuration_list("configId1")
        deviceConfigurationManager.get_configuration_list(20)

if __name__ == '__main__':
    unittest.main(verbosity=2)
