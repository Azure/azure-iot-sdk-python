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

from __builtin__ import isinstance

from iothub_service_client import IoTHubRegistryManager, IoTHubRegistryManagerAuthMethod
from iothub_service_client import IoTHubMessaging
from iothub_service_client import IoTHubDeviceTwin
from iothub_service_client import IoTHubDeviceMethod
from iothub_service_client import IoTHubMessage, IoTHubDevice, IoTHubDeviceStatus, IoTHubDeviceMethodResponse

from iothub_client import IoTHubClient, IoTHubClientError, IoTHubTransportProvider, IoTHubClientResult
from iothub_client import IoTHubMessageDispositionResult, IoTHubError, DeviceMethodReturnValue

IOTHUB_CONNECTION_STRING = ""
IOTHUB_DEVICE_LONGHAUL_DURATION_SECONDS = ""
IOTHUB_E2E_X509_CERT = ""
IOTHUB_E2E_X509_PRIVATE_KEY = ""
IOTHUB_E2E_X509_THUMBPRINT = ""
IOTHUB_EVENTHUB_CONNECTION_STRING = ""
IOTHUB_PARTITION_COUNT = ""

DEVICE_CLIENT_RESPONSE = ""
DEVICE_MESSAGE_TIMEOUT = 10000
DEVICE_METHOD_TIMEOUT = 60
DEVICE_METHOD_USER_CONTEXT = 42
DEVICE_METHOD_NAME = "e2e_device_method_name"
DEVICE_METHOD_PAYLOAD = "\"I'm a happy little string for python E2E test\""
DEVICE_METHOD_RESPONSE_PREFIX = "e2e_test_response-"
DEVICE_METHOD_EVENT = threading.Event()
DEVICE_METHOD_CALLBACK_TIMEOUT = 30

RECEIVE_CALLBACKS = 0
MESSAGING_MESSAGE = ""
MESSAGING_CONTEXT = 34
MESSAGE_RECEIVED_EVENT = threading.Event()
MESSAGE_RECEIVE_CALLBACK_TIMEOUT = 30

SLEEP_BEFORE_DEVICE_ACTION = 10

###########################################################################
# Helper functions
###########################################################################

def print_device_info(title, iothub_device):
    print ( title + ":" )
    print ( "iothubDevice.deviceId                    = {0}".format(iothub_device.deviceId) )
    print ( "iothubDevice.generationId                = {0}".format(iothub_device.generationId) )
    print ( "iothubDevice.eTag                        = {0}".format(iothub_device.eTag) )
    print ( "iothubDevice.connectionState             = {0}".format(iothub_device.connectionState) )
    print ( "iothubDevice.connectionStateUpdatedTime  = {0}".format(iothub_device.connectionStateUpdatedTime) )
    print ( "iothubDevice.status                      = {0}".format(iothub_device.status) )
    print ( "iothubDevice.statusReason                = {0}".format(iothub_device.statusReason) )
    print ( "iothubDevice.statusUpdatedTime           = {0}".format(iothub_device.statusUpdatedTime) )
    print ( "iothubDevice.lastActivityTime            = {0}".format(iothub_device.lastActivityTime) )
    print ( "iothubDevice.cloudToDeviceMessageCount   = {0}".format(iothub_device.cloudToDeviceMessageCount) )
    print ( "iothubDevice.isManaged                   = {0}".format(iothub_device.isManaged) )
    print ( "iothubDevice.configuration               = {0}".format(iothub_device.configuration) )
    print ( "iothubDevice.deviceProperties            = {0}".format(iothub_device.deviceProperties) )
    print ( "iothubDevice.serviceProperties           = {0}".format(iothub_device.serviceProperties) )
    print ( "iothubDevice.authMethod                  = {0}".format(iothub_device.authMethod) )
    print ( "" )

def read_environment_vars():
    global IOTHUB_CONNECTION_STRING
    global IOTHUB_DEVICE_LONGHAUL_DURATION_SECONDS
    global IOTHUB_E2E_X509_CERT
    global IOTHUB_E2E_X509_PRIVATE_KEY
    global IOTHUB_E2E_X509_THUMBPRINT
    global IOTHUB_EVENTHUB_CONNECTION_STRING
    global IOTHUB_PARTITION_COUNT

    try:
        IOTHUB_CONNECTION_STRING = os.environ["IOTHUB_CONNECTION_STRING"]
        IOTHUB_DEVICE_LONGHAUL_DURATION_SECONDS = os.environ["IOTHUB_DEVICE_LONGHAUL_DURATION_SECONDS"]
        IOTHUB_E2E_X509_CERT = os.environ["IOTHUB_E2E_X509_CERT"]
        IOTHUB_E2E_X509_PRIVATE_KEY = os.environ["IOTHUB_E2E_X509_PRIVATE_KEY"]
        IOTHUB_E2E_X509_THUMBPRINT = os.environ["IOTHUB_E2E_X509_THUMBPRINT"]
        IOTHUB_EVENTHUB_CONNECTION_STRING = os.environ["IOTHUB_EVENTHUB_CONNECTION_STRING"]
        IOTHUB_PARTITION_COUNT = os.environ["IOTHUB_PARTITION_COUNT"]

        print ("IOTHUB_CONNECTION_STRING: {0}".format(IOTHUB_CONNECTION_STRING))
        print ("IOTHUB_DEVICE_LONGHAUL_DURATION_SECONDS: {0}".format(IOTHUB_DEVICE_LONGHAUL_DURATION_SECONDS))
        print ("IOTHUB_E2E_X509_CERT: {0}".format(IOTHUB_E2E_X509_CERT))
        print ("IOTHUB_E2E_X509_PRIVATE_KEY: {0}".format(IOTHUB_E2E_X509_PRIVATE_KEY))
        print ("IOTHUB_E2E_X509_THUMBPRINT: {0}".format(IOTHUB_E2E_X509_THUMBPRINT))
        print ("IOTHUB_EVENTHUB_CONNECTION_STRING: {0}".format(IOTHUB_EVENTHUB_CONNECTION_STRING))
        print ("IOTHUB_PARTITION_COUNT: {0}".format(IOTHUB_PARTITION_COUNT))
    except:
        print ("Could not get environment variables...")

def generate_device_name():
    postfix = ''.join([random.choice(string.ascii_letters) for n in range(12)])
    return "python_e2e_test_device-{0}".format(postfix)

def get_device_connection_string(iothub_registry_manager, iothub_connection_string, device_id):
    iothub_device = iothub_registry_manager.get_device(device_id)
    assert isinstance(iothub_device, IoTHubDevice), 'Invalid type returned!'
    assert iothub_device != None, "iothub_device is NULL"

    primaryKey = iothub_device.primaryKey

    host_name_start = iothub_connection_string.find("HostName")
    host_name_end = iothub_connection_string.find(";", host_name_start)
    host_name = iothub_connection_string[host_name_start:host_name_end + 1]

    return host_name + "DeviceId=" + device_id + ";" + "SharedAccessKey=" + primaryKey

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

        print_device_info("CreateDevice", new_device)

        ###########################################################################
        # get_device

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

        print_device_info("GetDevice", iothub_device)

        ###########################################################################
        # update_device

        # prepare
        primary_key = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(44)])
        secondary_key = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(44)])
        status = IoTHubDeviceStatus.DISABLED
        auth_method = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY

        # act
        iothub_registry_manager.update_device(device_id, primary_key, secondary_key, status, auth_method)
        updated_device = iothub_registry_manager.get_device(device_id)
    
        # verify
        assert isinstance(updated_device, IoTHubDevice), 'Invalid type returned!'
        assert updated_device != None, "updated_device is NULL"
        assert updated_device.primaryKey == primary_key, "updated_device.primaryKey is not updated"
        assert updated_device.secondaryKey == secondary_key, "updated_device.secondaryKey is not updated"
        assert updated_device.authMethod == auth_method, "updated_device.authMethod is not updated"
        assert updated_device.status == status, "updated_device.status is not updated"
        ###########################################################################

        print_device_info("UpdateDevice", updated_device)

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
        print ("run_e2e_devicetwin() failed with exception: {0}".format(e))
        retval = 1
    finally:
        ###########################################################################
        # delete_device
 
        # prepare
        # act
        iothub_registry_manager.delete_device(device_id)
        # verify
        ###########################################################################

    return retval


def run_e2e_devicetwin(iothub_connection_string):
    try:
        # prepare
        device_id = generate_device_name()
        assert isinstance(device_id, str), 'Invalid type returned!'

        primary_key = ""
        secondary_key = ""
        auth_method = IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY

        iothub_registry_manager = IoTHubRegistryManager(iothub_connection_string)
        new_device = iothub_registry_manager.create_device(device_id, primary_key, secondary_key, auth_method)

        ###########################################################################
        # IoTHubDeviceTwin

        # act
        iothub_device_twin = IoTHubDeviceTwin(IOTHUB_CONNECTION_STRING)

        # verify
        assert iothub_device_twin != None, "iothub_device_twin is NULL"
        ###########################################################################

        ###########################################################################

        # Wait before get twin...
        time.sleep(SLEEP_BEFORE_DEVICE_ACTION)

        ###########################################################################
        # get_twin

        # act
        twin_info = iothub_device_twin.get_twin(device_id)

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
        ###########################################################################

        print ( "" )
        print ( "Device Twin before update:" )
        print ( "{0}".format(twin_info) )

        ###########################################################################
        # update_twin

        # prepare
        new_property_name = "telemetryInterval"
        new_property_value = "42"
        UPDATE_JSON = "{\"properties\":{\"desired\":{\"" + new_property_name + "\":" + new_property_value + "}}}"

        # act
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
        print ("run_e2e_devicetwin() failed with exception: {0}".format(e))
        retval = 1
    finally:
        # clean-up
        iothub_registry_manager.delete_device(device_id)

    return retval


def run_e2e_devicemethod(iothub_connection_string):
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

        device_connection_string = get_device_connection_string(iothub_registry_manager, IOTHUB_CONNECTION_STRING, device_id)


        device_client = IoTHubClient(device_connection_string, IoTHubTransportProvider.MQTT)
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
        time.sleep(SLEEP_BEFORE_DEVICE_ACTION)

        ############################################################################
        # invoke
        
        # prepare
        # act
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
        print ("run_e2e_devicemethod() failed with exception: {0}".format(e))
        retval = 1
    finally:
        # clean-up
        iothub_registry_manager.delete_device(device_id)

    return retval


def run_e2e_messaging(iothub_connection_string):
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

        device_connection_string = get_device_connection_string(iothub_registry_manager, IOTHUB_CONNECTION_STRING, device_id)

        device_client = IoTHubClient(device_connection_string, IoTHubTransportProvider.MQTT)
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
        time.sleep(SLEEP_BEFORE_DEVICE_ACTION)

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
        iothub_registry_manager.delete_device(device_id)
    
    return retval


if __name__ == '__main__':
    print ("iothub_service_client E2E tests started!")

    read_environment_vars()
   
    try:
        assert run_e2e_registrymanager(IOTHUB_CONNECTION_STRING) == 0
        assert run_e2e_devicetwin(IOTHUB_CONNECTION_STRING) == 0
        assert run_e2e_devicemethod(IOTHUB_CONNECTION_STRING) == 0
        assert run_e2e_messaging(IOTHUB_CONNECTION_STRING) == 0
        print ("iothub_service_client E2E tests passed!")
    except:
        print ("iothub_service_client E2E tests failed!")
