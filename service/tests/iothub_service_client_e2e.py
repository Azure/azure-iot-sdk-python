# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import os
import sys
import uuid
import string
import random
import time
import threading
import types
import base64

from iothub_service_client import IoTHubRegistryManager, IoTHubRegistryManagerAuthMethod
from iothub_service_client import IoTHubMessaging
from iothub_service_client import IoTHubDeviceTwin
from iothub_service_client import IoTHubDeviceMethod
from iothub_service_client import IoTHubMessage, IoTHubDevice, IoTHubDeviceStatus, IoTHubDeviceMethodResponse, IoTHubModule
from iothub_service_client import IoTHubDeviceConfigurationManager, IoTHubDeviceConfiguration

from iothub_client import IoTHubClient, IoTHubClientError, IoTHubTransportProvider, IoTHubClientResult
from iothub_client import IoTHubMessageDispositionResult, IoTHubError, DeviceMethodReturnValue

IOTHUB_CONNECTION_STRING = ""

DEVICE_CLIENT_RESPONSE = ""
DEVICE_MESSAGE_TIMEOUT = 10000
DEVICE_METHOD_TIMEOUT = 60
DEVICE_METHOD_USER_CONTEXT = 42
DEVICE_METHOD_NAME = "e2e_device_method_name"
DEVICE_METHOD_PAYLOAD = "\"I'm a happy little string for python E2E test\""
DEVICE_METHOD_RESPONSE_PREFIX = "e2e_test_response-"
DEVICE_METHOD_EVENT = threading.Event()
DEVICE_METHOD_CALLBACK_TIMEOUT = 30
TEST_MODULE_ID = "TestModuleId"

RECEIVE_CALLBACKS = 0
MESSAGING_MESSAGE = ""
MESSAGING_CONTEXT = 34
MESSAGE_RECEIVED_EVENT = threading.Event()
MESSAGE_RECEIVE_CALLBACK_TIMEOUT = 30

SLEEP_BEFORE_DEVICE_ACTION = 10

###########################################################################
# Helper functions
###########################################################################
def sleep_before_device_action():
    print ( "Sleeping for {0} seconds to give time for operation to complete".format(SLEEP_BEFORE_DEVICE_ACTION))
    time.sleep(SLEEP_BEFORE_DEVICE_ACTION)


def print_device_or_module_info(title, iothub_device_or_module, testing_modules):
    print ( title + ":" )
    print ( "  deviceId                    = {0}".format(iothub_device_or_module.deviceId) )
    if (testing_modules):
        print ( "  moduleId                  = {0}".format(iothub_device_or_module.moduleId) )
    print ( "  generationId                = {0}".format(iothub_device_or_module.generationId) )
    print ( "  eTag                        = {0}".format(iothub_device_or_module.eTag) )
    print ( "  connectionState             = {0}".format(iothub_device_or_module.connectionState) )
    print ( "  connectionStateUpdatedTime  = {0}".format(iothub_device_or_module.connectionStateUpdatedTime) )
    if (testing_modules == False):
        print ( "  status                      = {0}".format(iothub_device_or_module.status) )
        print ( "  statusReason                = {0}".format(iothub_device_or_module.statusReason) )
        print ( "  statusUpdatedTime           = {0}".format(iothub_device_or_module.statusUpdatedTime) )
        print ( "  isManaged                   = {0}".format(iothub_device_or_module.isManaged) )
        print ( "  configuration               = {0}".format(iothub_device_or_module.configuration) )
        print ( "  deviceProperties            = {0}".format(iothub_device_or_module.deviceProperties) )
        print ( "  serviceProperties           = {0}".format(iothub_device_or_module.serviceProperties) )
    print ( "  lastActivityTime            = {0}".format(iothub_device_or_module.lastActivityTime) )
    print ( "  cloudToDeviceMessageCount   = {0}".format(iothub_device_or_module.cloudToDeviceMessageCount) )
    print ( "  authMethod                  = {0}".format(iothub_device_or_module.authMethod) )
    print ( "" )

def print_config_info(title, iothub_deviceconfig):
    print ( title + ":" )
    print ( "iothub_deviceconfig.targetCondition                = {0}".format(iothub_deviceconfig.targetCondition) )
    print ( "iothub_deviceconfig.schemaVersion                  = {0}".format(iothub_deviceconfig.schemaVersion) )
    print ( "iothub_deviceconfig.configurationId                = {0}".format(iothub_deviceconfig.configurationId) )
    print ( "iothub_deviceconfig.eTag                           = {0}".format(iothub_deviceconfig.eTag) )
    print ( "iothub_deviceconfig.createdTimeUtc                 = {0}".format(iothub_deviceconfig.createdTimeUtc) )
    print ( "iothub_deviceconfig.priority                       = {0}".format(iothub_deviceconfig.priority) )
    print ( "iothub_deviceconfig.content.deviceContent          = {0}".format(iothub_deviceconfig.content.deviceContent) )
    print ( "iothub_deviceconfig.content.modulesContent         = {0}".format(iothub_deviceconfig.content.modulesContent) )
    print ( "" )

def read_environment_vars():
    global IOTHUB_CONNECTION_STRING

    try:
        IOTHUB_CONNECTION_STRING = os.environ["IOTHUB_CONNECTION_STRING"]
        print ("IOTHUB_CONNECTION_STRING: {0}".format(IOTHUB_CONNECTION_STRING))
    except:
        print ("Could not get all the environment variables...")


def generate_device_name():
    postfix = ''.join([random.choice(string.ascii_letters) for n in range(12)])
    return "python_e2e_test_device-{0}".format(postfix)

def generate_configurationid_id():
    numbers = '0123456789'
    postfix = ''.join([random.choice(numbers) for n in range(12)])
    return "python_e2e_test_config-{0}".format(postfix)


def get_connection_string(iothub_registry_manager, iothub_connection_string, device_id, testing_modules):
    if (testing_modules):
        iothub_device_or_module = iothub_registry_manager.get_module(device_id, TEST_MODULE_ID)
        assert isinstance(iothub_device_or_module, IoTHubModule), 'Invalid type returned!'
    else:
        iothub_device_or_module = iothub_registry_manager.get_device(device_id)
        assert isinstance(iothub_device_or_module, IoTHubDevice), 'Invalid type returned!'
    assert iothub_device_or_module != None, "iothub_device_or_module is NULL"

    primaryKey = iothub_device_or_module.primaryKey

    host_name_start = iothub_connection_string.find("HostName")
    host_name_end = iothub_connection_string.find(";", host_name_start)
    host_name = iothub_connection_string[host_name_start:host_name_end + 1]

    connection_string = host_name + "DeviceId=" + device_id + ";" + "SharedAccessKey=" + primaryKey

    if (testing_modules):
        connection_string += ";ModuleId=" + TEST_MODULE_ID

    return connection_string


def device_method_callback(method_name, payload, user_context):
    global DEVICE_METHOD_USER_CONTEXT
    global DEVICE_CLIENT_RESPONSE

    print ( "\nMethod callback called with:\nmethodName = %s\npayload = %s\ncontext = %s" % (method_name, payload, user_context) )

    device_method_return_value = DeviceMethodReturnValue()
    if method_name == DEVICE_METHOD_NAME and user_context == DEVICE_METHOD_USER_CONTEXT:
        DEVICE_CLIENT_RESPONSE = DEVICE_METHOD_RESPONSE_PREFIX + "{0}".format(uuid.uuid4())
        device_method_return_value.response = "{ \"Response\": \"" + DEVICE_CLIENT_RESPONSE + "\" }"
        device_method_return_value.status = 200
    else:
        device_method_return_value.response = "{ \"Response\": \"\" }"
        device_method_return_value.status = 500
    print ( "" )

    DEVICE_METHOD_EVENT.set()

    return device_method_return_value


def open_complete_callback(context):
    print ( 'open_complete_callback called with context: {0}'.format(context) )
    print ( "" )


def send_complete_callback(context, messaging_result):
    context = 0
    print ( 'send_complete_callback called with context : {0}'.format(context) )
    print ( 'messagingResult : {0}'.format(messaging_result) )


def receive_message_callback(message, counter):
    global RECEIVE_CALLBACKS
    message_buffer = message.get_bytearray()
    size = len(message_buffer)
    print ( "Received Message [%d]:" % counter )
    print ( "    Data: <<<%s>>> & Size=%d" % (message_buffer[:size].decode('utf-8'), size) )
    map_properties = message.properties()
    key_value_pair = map_properties.get_internals()
    print ( "    Properties: %s" % key_value_pair )
    counter += 1
    RECEIVE_CALLBACKS += 1
    print ( "    Total calls received: %d" % RECEIVE_CALLBACKS )
    print ( "" )

    MESSAGE_RECEIVED_EVENT.set()

    return IoTHubMessageDispositionResult.ACCEPTED

def get_device_info_and_verify(title, iothub_registry_manager, device_id):
    # prepare
    # act
    iothub_device = iothub_registry_manager.get_device(device_id)

    # verify
    assert isinstance(iothub_device, IoTHubDevice), 'Invalid type returned!'
    assert iothub_device != None, "iothub_device is NULL"
    assert iothub_device.primaryKey != None, "iothub_device.primaryKey is NULL"
    assert iothub_device.primaryKey != "", "iothub_device.primaryKey is empty"
    assert iothub_device.secondaryKey != None, "iothub_device.secondaryKey is NULL"
    assert iothub_device.secondaryKey != "", "iothub_device.secondaryKey is empty"
    ###########################################################################

    print_device_or_module_info(title, iothub_device, False)

def get_module_info_and_verify(title, iothub_registry_manager, device_id):
    # prepare
    # act
    iothub_module = iothub_registry_manager.get_module(device_id, TEST_MODULE_ID)

    # verify
    assert isinstance(iothub_module, IoTHubModule), 'Invalid type returned!'
    assert iothub_module != None, "iothub_module is NULL"
    assert iothub_module.primaryKey != None, "iothub_module.primaryKey is NULL"
    assert iothub_module.primaryKey != "", "iothub_module.primaryKey is empty"
    assert iothub_module.secondaryKey != None, "iothub_module.secondaryKey is NULL"
    assert iothub_module.secondaryKey != "", "iothub_module.secondaryKey is empty"
    ###########################################################################

    print_device_or_module_info(title, iothub_module, True)


###########################################################################
# E2E tests
###########################################################################

def run_e2e_registrymanager(iothub_connection_string):
    try:
        # prepare
        device_id = generate_device_name()
        assert isinstance(device_id, str), 'Invalid type returned!'

        ###########################################################################
        # IoTHubRegistryManager
    
        # prepare
        # act
        iothub_registry_manager = IoTHubRegistryManager(iothub_connection_string)

        # verify
        assert isinstance(iothub_registry_manager, IoTHubRegistryManager), 'Invalid type returned!'
        assert iothub_registry_manager != None, "iothub_registry_manager is NULL"
        ###########################################################################

        print ( "IoTHubRegistryManager is created successfully" )

        ###########################################################################
        # create_device

        # prepare
        primary_key = ""
        secondary_key = ""
        auth_method = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY

        # act
        new_device = iothub_registry_manager.create_device(device_id, primary_key, secondary_key, auth_method)

        # verify
        assert isinstance(new_device, IoTHubDevice), 'Invalid type returned!'
        assert new_device != None, "new_device is NULL"
        assert new_device.primaryKey != None, "new_device.primaryKey is NULL"
        assert new_device.primaryKey != "", "new_device.primaryKey is empty"
        assert new_device.secondaryKey != None, "new_device.secondaryKey is NULL"
        assert new_device.secondaryKey != "", "new_device.secondaryKey is empty"
        ###########################################################################

        print_device_or_module_info("CreateDevice", new_device, False)


        ###########################################################################
        # create_module_device

        # prepare
        primary_key = ""
        secondary_key = ""
        auth_method = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY

        # act
        new_module = iothub_registry_manager.create_module(device_id, primary_key, secondary_key, TEST_MODULE_ID, auth_method)

        # verify
        assert isinstance(new_module, IoTHubModule), 'Invalid type returned!'
        assert new_module != None, "new_module is NULL"
        assert new_module.primaryKey != None, "new_module.primaryKey is NULL"
        assert new_module.primaryKey != "", "new_module.primaryKey is empty"
        assert new_module.secondaryKey != None, "new_module.secondaryKey is NULL"
        assert new_module.secondaryKey != "", "new_module.secondaryKey is empty"
        ###########################################################################

        print_device_or_module_info("CreateModule", new_module, True)
        

        ###########################################################################
        # get_device
        get_device_info_and_verify("GetDevice", iothub_registry_manager, device_id)

        ###########################################################################
        # get_module
        get_module_info_and_verify("GetModule", iothub_registry_manager, device_id)


        ###########################################################################
        # update_device

        # prepare
        primary_key = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(44)])
        secondary_key = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(44)])
        status = IoTHubDeviceStatus.DISABLED
        auth_method = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY

        # act
        iothub_registry_manager.update_device(device_id, primary_key, secondary_key, status, auth_method)
    
        # verify
        get_device_info_and_verify("UpdateDevice", iothub_registry_manager, device_id)


        ###########################################################################
        # update_module

        # prepare
        primary_key = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(44)])
        secondary_key = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(44)])
        status = IoTHubDeviceStatus.DISABLED
        auth_method = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY

        # act
        iothub_registry_manager.update_module(device_id, primary_key, secondary_key, TEST_MODULE_ID, auth_method)
        
        # verify
        get_module_info_and_verify("UpdateModule", iothub_registry_manager, device_id)

        

        ###########################################################################
        # get_device_list

        # prepare
        req_number_of_devices = 10

        # act
        device_list = iothub_registry_manager.get_device_list(req_number_of_devices)

        # verify
        assert device_list != None, "device_list is NULL"
        number_of_devices = len(device_list)
        assert number_of_devices != None, "device_list is NULL"
        assert number_of_devices > 0, "number_of_devices is incorrect"
        ###########################################################################

        print ( "Number of devices                        : {0}".format(number_of_devices) )

        ###########################################################################
        # get_statistics
    
        # prepare
        # act
        iothub_registry_statistics = iothub_registry_manager.get_statistics()

        # verify
        assert iothub_registry_statistics.totalDeviceCount >= 0, "iothub_registry_statistics.totalDeviceCount is incorrect"
        sum_device_count = iothub_registry_statistics.enabledDeviceCount + iothub_registry_statistics.disabledDeviceCount
        assert sum_device_count >= 0, "iothub_registry_statistics.totalDeviceCount is incorrect"
        ###########################################################################

        print ( "GetStatistics" )
        print ( "Total device count                       : {0}".format(iothub_registry_statistics.totalDeviceCount) )
        print ( "Enabled device count                     : {0}".format(iothub_registry_statistics.enabledDeviceCount) )
        print ( "Disabled device count                    : {0}".format(iothub_registry_statistics.disabledDeviceCount) )
    
        retval = 0
    except Exception as e:
        print ( "" )
        print ("run_e2e_registrymanager() failed with exception: {0}".format(e))
        retval = 1
    finally:
        ###########################################################################
        # delete_module
        # prepare
        # act
        iothub_registry_manager.delete_module(device_id, TEST_MODULE_ID)
        # verify

        ###########################################################################
        # delete_device
 
        # prepare
        # act
        iothub_registry_manager.delete_device(device_id)
        # verify
        ###########################################################################

    return retval


def run_e2e_twin(iothub_connection_string, testing_modules):
    try:
        # prepare
        device_id = generate_device_name()
        assert isinstance(device_id, str), 'Invalid type returned!'

        primary_key = ""
        secondary_key = ""
        auth_method = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY

        iothub_registry_manager = IoTHubRegistryManager(iothub_connection_string)
        new_device = iothub_registry_manager.create_device(device_id, primary_key, secondary_key, auth_method)

        if testing_modules == True:
            new_module = iothub_registry_manager.create_module(device_id, primary_key, secondary_key, TEST_MODULE_ID, auth_method)

        ###########################################################################
        # IoTHubDeviceTwin

        # act
        iothub_device_twin = IoTHubDeviceTwin(IOTHUB_CONNECTION_STRING)

        # verify
        assert iothub_device_twin != None, "iothub_device_twin is NULL"
        ###########################################################################

        ###########################################################################

        # Wait before get twin...
        sleep_before_device_action()

        ###########################################################################
        # get_twin

        # act
        if testing_modules == True:
            twin_info = iothub_device_twin.get_twin(device_id, TEST_MODULE_ID)
        else:
            twin_info = iothub_device_twin.get_twin(device_id)

        # verify
        assert twin_info != None, "twin_info is NULL"
        json_ok = twin_info.find("deviceId")
        assert json_ok > 0, "twin_info does not contain deviceId tag"
        json_ok = twin_info.find(device_id)
        assert json_ok > 0, "twin_info does not contain the correct device id"

        if testing_modules == True:
            json_ok = twin_info.find("moduleId")
            assert json_ok > 0, "twin_info does not contain moduleId tag"

        json_ok = twin_info.find("etag")
        assert json_ok > 0, "twin_info does not contain etag tag"
        json_ok = twin_info.find("properties")
        assert json_ok > 0, "twin_info does not contain properties tag"
        ###########################################################################

        print ( "" )
        print ( "Twin before update:" )
        print ( "{0}".format(twin_info) )

        ###########################################################################
        # update_twin

        # prepare
        new_property_name = "telemetryInterval"
        new_property_value = "42"
        UPDATE_JSON = "{\"properties\":{\"desired\":{\"" + new_property_name + "\":" + new_property_value + "}}}"

        # act
        if testing_modules == True:
            twin_info = iothub_device_twin.update_twin(device_id, TEST_MODULE_ID, UPDATE_JSON)
        else:
            twin_info = iothub_device_twin.update_twin(device_id, UPDATE_JSON)

        # verify
        assert twin_info != None, "twin_info is NULL"
        json_ok = twin_info.find("deviceId")
        assert json_ok > 0, "twin_info does not contain deviceId tag"
        json_ok = twin_info.find(device_id)
        assert json_ok > 0, "twin_info does not contain the correct device id"

        json_ok = twin_info.find("etag")
        assert json_ok > 0, "twin_info does not contain etag tag"
        json_ok = twin_info.find("properties")
        assert json_ok > 0, "twin_info does not contain properties tag"

        json_ok = twin_info.find(new_property_name)
        assert json_ok > 0, "twin_info does not contain " + new_property_name + " tag"
        json_ok = twin_info.find(new_property_value)
        assert json_ok > 0, "twin_info does not contain " + new_property_value
        ###########################################################################

        print ( "" )
        print ( "Device Twin after update:" )
        print ( "{0}".format(twin_info) )
        print ( "" )
        retval = 0
    except Exception as e:
        print ( "" )
        print ("run_e2e_twin() failed with exception: {0}".format(e))
        retval = 1
    finally:
        # clean-up
        if testing_modules == True:
            iothub_registry_manager.delete_module(device_id, TEST_MODULE_ID)

        iothub_registry_manager.delete_device(device_id)

    return retval


def run_e2e_method(iothub_connection_string, testing_modules):
    global DEVICE_METHOD_USER_CONTEXT
    global DEVICE_METHOD_NAME
    global DEVICE_METHOD_PAYLOAD
    global DEVICE_METHOD_TIMEOUT

    try:
        # prepare
        device_id = generate_device_name()
        assert isinstance(device_id, str), 'Invalid type returned!'

        primary_key = ""
        secondary_key = ""
        auth_method = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY

        iothub_registry_manager = IoTHubRegistryManager(iothub_connection_string)
        new_device = iothub_registry_manager.create_device(device_id, primary_key, secondary_key, auth_method)

        if testing_modules == True:
            new_module = iothub_registry_manager.create_module(device_id, primary_key, secondary_key, TEST_MODULE_ID, auth_method)
            protocol = IoTHubTransportProvider.AMQP
        else:
            protocol = IoTHubTransportProvider.MQTT

        connection_string = get_connection_string(iothub_registry_manager, IOTHUB_CONNECTION_STRING, device_id, testing_modules)

        device_client = IoTHubClient(connection_string, protocol)
        assert isinstance(device_client, IoTHubClient), 'Invalid type returned!'
        assert device_client != None, "device_client is NULL"

        device_client.set_option("messageTimeout", DEVICE_MESSAGE_TIMEOUT)

        device_client.set_device_method_callback(device_method_callback, DEVICE_METHOD_USER_CONTEXT)

        ###########################################################################
        # IoTHubDeviceMethod

        # prepare
        # act
        iothub_device_method = IoTHubDeviceMethod(IOTHUB_CONNECTION_STRING)

        # verify
        assert iothub_device_method != None, "iothub_device_method is NULL"
        ###########################################################################

        # Wait before invoke...
        sleep_before_device_action()

        ############################################################################
        # invoke
        
        # prepare
        # act
        if testing_modules == True:
            response = iothub_device_method.invoke(device_id, TEST_MODULE_ID, DEVICE_METHOD_NAME, DEVICE_METHOD_PAYLOAD, DEVICE_METHOD_TIMEOUT)
        else:
            response = iothub_device_method.invoke(device_id, DEVICE_METHOD_NAME, DEVICE_METHOD_PAYLOAD, DEVICE_METHOD_TIMEOUT)

        assert response != None, "response is NULL"
        assert isinstance(response, IoTHubDeviceMethodResponse), 'Invalid type returned!'

        # verify
        response_ok = response.payload.find(DEVICE_CLIENT_RESPONSE)
        assert response_ok > 0, "response does not contain " + DEVICE_CLIENT_RESPONSE
        assert response.status == 200, "response status is : " + response.status
        DEVICE_METHOD_EVENT.wait(DEVICE_METHOD_CALLBACK_TIMEOUT)
        assert DEVICE_CLIENT_RESPONSE.find(DEVICE_METHOD_RESPONSE_PREFIX) >= 0, "Timeout expired and device method has not been called!"
        ############################################################################

        print ( "" )
        retval = 0
    except Exception as e:
        print ( "" )
        print ("run_e2e_method() failed with exception: {0}".format(e))
        retval = 1
    finally:
        # clean-up
        iothub_registry_manager.delete_device(device_id)

    return retval


def run_e2e_messaging(iothub_connection_string, testing_modules):
    global RECEIVE_CALLBACKS
    global MESSAGING_MESSAGE

    try:
        # prepare
        device_id = generate_device_name()
        assert isinstance(device_id, str), 'Invalid type returned!'

        primary_key = ""
        secondary_key = ""
        auth_method = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY

        iothub_registry_manager = IoTHubRegistryManager(iothub_connection_string)
        new_device = iothub_registry_manager.create_device(device_id, primary_key, secondary_key, auth_method)

        if testing_modules == True:
            new_module = iothub_registry_manager.create_module(device_id, primary_key, secondary_key, TEST_MODULE_ID, auth_method)
            protocol = IoTHubTransportProvider.AMQP
        else:
            protocol = IoTHubTransportProvider.MQTT

        connection_string = get_connection_string(iothub_registry_manager, IOTHUB_CONNECTION_STRING, device_id, testing_modules)

        device_client = IoTHubClient(connection_string, protocol)
        assert isinstance(device_client, IoTHubClient), 'Invalid type returned!'
        assert device_client != None, "device_client is NULL"

        device_client.set_option("messageTimeout", DEVICE_MESSAGE_TIMEOUT)

        device_client.set_message_callback(receive_message_callback, MESSAGING_CONTEXT)

        ###########################################################################
        # IoTHubMessaging

        # prepare
        # act
        iothub_messaging = IoTHubMessaging(IOTHUB_CONNECTION_STRING)

        # verify
        assert iothub_messaging != None, "iothub_messaging is NULL"
        ###########################################################################

        # Wait before open...
        sleep_before_device_action()

        ############################################################################
        # open

        # act
        iothub_messaging.open(open_complete_callback, None)
        ############################################################################

        ############################################################################
        # invoke

        # prepare
        MESSAGING_MESSAGE = ''.join([random.choice(string.ascii_letters) for n in range(12)])
        message = IoTHubMessage(bytearray(MESSAGING_MESSAGE, 'utf8'))

        # act
        if testing_modules == True:
            iothub_messaging.send_async(device_id, TEST_MODULE_ID, message, send_complete_callback, MESSAGING_CONTEXT)
        else:
            iothub_messaging.send_async(device_id, message, send_complete_callback, MESSAGING_CONTEXT)
        MESSAGE_RECEIVED_EVENT.wait(MESSAGE_RECEIVE_CALLBACK_TIMEOUT)

        # verify
        assert RECEIVE_CALLBACKS == 1, "message has not been received"
        ############################################################################

        print ( "" )
        retval = 0
    except Exception as e:
        print ( "" )
        print ("run_e2e_messaging() failed with exception: {0}".format(e))
        retval = 1
    finally:
        # clean-up
        iothub_messaging.close()
        iothub_registry_manager.delete_device(device_id)
    
    return retval

MODULE_CONTENT = '''{"sunny": {"properties.desired": {"temperature": 69,"humidity": 30}}, 
                                      "goolily": {"properties.desired": {"elevation": 45,"orientation": "NE"}}, 
                                      "$edgeAgent": {"properties.desired": {"schemaVersion": "1.0","runtime": {"type": "docker","settings": {"minDockerVersion": "1.5","loggingOptions": ""}},"systemModules": 
                                                {"edgeAgent": {"type": "docker","settings": {"image": "edgeAgent","createOptions": ""},"configuration": {"id": "configurationapplyedgeagentreportinge2etestcit-config-a9ed4811-1b57-48bf-8af2-02319a38de01"}}, 
                                                "edgeHub": {"type": "docker","status": "running","restartPolicy": "always","settings": {"image": "edgeHub","createOptions": ""},"configuration": {"id": "configurationapplyedgeagentreportinge2etestcit-config-a9ed4811-1b57-48bf-8af2-02319a38de01"}}}, 
                                                    "modules": {"sunny": {"version": "1.0","type": "docker","status": "running","restartPolicy": "on-failure","settings": {"image": "mongo","createOptions": ""},"configuration": {"id": "configurationapplyedgeagentreportinge2etestcit-config-a9ed4811-1b57-48bf-8af2-02319a38de01"}}, 
                                                    "goolily": {"version": "1.0","type": "docker","status": "running","restartPolicy": "on-failure","settings": {"image": "asa","createOptions": ""},"configuration": {"id": "configurationapplyedgeagentreportinge2etestcit-config-a9ed4811-1b57-48bf-8af2-02319a38de01"}}}}}, 
                                      "$edgeHub": {"properties.desired": {"schemaVersion": "1.0","routes": {"route1": "from * INTO $upstream"},"storeAndForwardConfiguration": {"timeToLiveSecs": 20}}}}'''

def strip_spaces(str):
    return ''.join(str.split())

'''

def verify_expected_device_configuration(expectedConfig, actualConfig):
    assert actualConfig != None, "Returned configuration object is NULL"

    assert expectedConfig.targetCondition == actualConfig.targetCondition, "targetCondition doesn't match"
    assert expectedConfig.configurationId == actualConfig.configurationId, "configurationId doesn't match"
    # assert expectedConfig.priority == actualConfig.priority, "priority doesn't match"
    assert strip_spaces(expectedConfig.content.deviceContent) == strip_spaces(actualConfig.content.deviceContent), "deviceContent doesn't match"
    assert strip_spaces(expectedConfig.content.modulesContent) == strip_spaces(actualConfig.content.modulesContent), "modulesContent doesn't match"
    assert expectedConfig.labels["label1"] == actualConfig.labels["label1"], "Labels[label1] doesn't match"
    assert expectedConfig.labels["label2"] == actualConfig.labels["label2"], "Labels[label2] doesn't match"

def run_e2e_deviceconfiguration(iothub_connection_string):

    try:
        # prepare
        configuration_id = generate_configurationid_id()
        assert isinstance(configuration_id, str), 'Invalid type returned!'
        print(configuration_id)

        iothub_deviceconfiguration = IoTHubDeviceConfiguration()
        assert iothub_deviceconfiguration != None, "iothub_deviceconfiguration is NULL"

        print ("Creating configuration object for {0}".format(configuration_id))        
        iothub_deviceconfiguration.targetCondition = "tags.UniqueTag='configurationapplyedgeagentreportinge2etestcita5b4e2b7f6464fe9988feea7d887584a' and tags.Environment='test'"
        iothub_deviceconfiguration.configurationId =  configuration_id
        iothub_deviceconfiguration.priority = 10
        iothub_deviceconfiguration.content.deviceContent = ""
        iothub_deviceconfiguration.content.modulesContent = MODULE_CONTENT
        iothub_deviceconfiguration.labels["label1"] = "value1"
        iothub_deviceconfiguration.labels["label2"] = "value2"

        # add_configuration
        print ("Adding configuration for {0}".format(configuration_id))
        iothub_deviceconfiguration_manager = IoTHubDeviceConfigurationManager(iothub_connection_string)

        iothub_deviceconfig_added = iothub_deviceconfiguration_manager.add_configuration(iothub_deviceconfiguration)
        verify_expected_device_configuration(iothub_deviceconfiguration, iothub_deviceconfig_added)

        # get_configuration
        print ("Getting configuration for {0}".format(configuration_id))
        iothub_deviceconfig_get = iothub_deviceconfiguration_manager.get_configuration(configuration_id)
        verify_expected_device_configuration(iothub_deviceconfig_get, iothub_deviceconfig_added)

        # update_configuration
        print ("Updating configuration for {0}".format(configuration_id))
        iothub_deviceconfig_added.targetCondition = "tags.UniqueTag='configurationapplyedgeagentreportinge2etestcita5b4e2b7f6464fe9988feea7d887584a' and tags.Environment='test2'"
        iothub_deviceconfig_updated = iothub_deviceconfiguration_manager.update_configuration(iothub_deviceconfig_added)
        verify_expected_device_configuration(iothub_deviceconfig_updated, iothub_deviceconfig_added)

        # get_configuration_list
        print ("Retrieving configuration list")
        number_of_configurations = 20
        configuration_list = iothub_deviceconfiguration_manager.get_configuration_list(number_of_configurations)
        assert len(configuration_list) > 0, "No configurations were returned"
        assert len(configuration_list) <= number_of_configurations, "More configurations were returned than specified max"

        retval = 0

    except Exception as e:
        print ( "" )
        print ("run_e2e_deviceconfiguration() failed with exception: {0}".format(e))
        retval = 1
    finally:
        if (iothub_deviceconfiguration is not None):
            print ("Deleting configuration for {0}".format(configuration_id))
            iothub_deviceconfiguration_manager.delete_configuration(configuration_id)

    return retval
'''

def main():
    print ("********************* iothub_service_client E2E tests started!")

    read_environment_vars()
   
    try:
        assert run_e2e_registrymanager(IOTHUB_CONNECTION_STRING) == 0
        assert run_e2e_twin(IOTHUB_CONNECTION_STRING, False) == 0
        assert run_e2e_twin(IOTHUB_CONNECTION_STRING, True) == 0
        assert run_e2e_method(IOTHUB_CONNECTION_STRING, False) == 0
        assert run_e2e_method(IOTHUB_CONNECTION_STRING, True) == 0
        assert run_e2e_messaging(IOTHUB_CONNECTION_STRING, False) == 0
        assert run_e2e_messaging(IOTHUB_CONNECTION_STRING, True) == 0
        # assert run_e2e_deviceconfiguration(IOTHUB_CONNECTION_STRING) == 0
        print ("********************* iothub_service_client E2E tests passed!")
        return 0
    except Exception as e:
        print ("********************* iothub_service_client E2E tests failed!")
        print ("Exception = {0}".format(e))
        return 1


if __name__ == '__main__':
    sys.exit(main())
