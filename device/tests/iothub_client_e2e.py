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

sys.path.append(os.path.realpath('..\samples'))

from iothub_service_client import IoTHubRegistryManager, IoTHubRegistryManagerAuthMethod
from iothub_service_client import IoTHubMessaging
from iothub_service_client import IoTHubDeviceTwin
from iothub_service_client import IoTHubDeviceMethod
from iothub_service_client import IoTHubMessage, IoTHubDevice, IoTHubDeviceStatus

from iothub_client import IoTHubClient, IoTHubClientError, IoTHubTransportProvider, IoTHubClientResult
from iothub_client import IoTHubMessageDispositionResult, IoTHubError, DeviceMethodReturnValue

from iothub_client_cert import CERTIFICATES

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
DEVICE_METHOD_CALLBACK_COUNTER = 0

MESSAGING_MESSAGE = ""
MESSAGING_CONTEXT = 34
MESSAGE_RECEIVE_EVENT = threading.Event()
MESSAGE_RECEIVE_CALLBACK_COUNTER = 0

REPORTED_STATE_CONTEXT = 0
REPORTED_STATE_STATUS = -1
REPORTED_STATE_EVENT = threading.Event()
REPORTED_STATE_CALLBACK_COUNTER = 0

BLOB_UPLOAD_CONTEXT = 34
BLOB_UPLOAD_EVENT = threading.Event()
BLOB_UPLOAD_CALLBACK_COUNTER = 0

TWIN_CALLBACK_EVENT = threading.Event()
TWIN_CALLBACK_COUNTER = 0

HTTP_TIMEOUT = 241000
HTTP_MINIMUM_POLLING_TIME = 9

CALLBACK_TIMEOUT = 60
SLEEP_BEFORE_DEVICE_ACTION = 10

###########################################################################
# Helper functions
###########################################################################

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

def get_device_connection_string(iothub_registry_manager, iothub_connection_string, device_id, authMethod):
    iothub_device = iothub_registry_manager.get_device(device_id)
    assert isinstance(iothub_device, IoTHubDevice), 'Invalid type returned!'
    assert iothub_device != None, "iothub_device is NULL"

    primaryKey = iothub_device.primaryKey

    host_name_start = iothub_connection_string.find("HostName")
    host_name_end = iothub_connection_string.find(";", host_name_start)
    host_name = iothub_connection_string[host_name_start:host_name_end]

    if authMethod == IoTHubRegistryManagerAuthMethod.X509_THUMBPRINT:
        return host_name + ";DeviceId=" + device_id + ";" + "x509=true"
    else:
        return host_name + ";DeviceId=" + device_id + ";" + "SharedAccessKey=" + primaryKey

def open_complete_callback(context):
    print ( 'open_complete_callback called with context: {0}'.format(context) )
    print ( "" )

def send_complete_callback(context, messaging_result):
    context = 0
    print ( 'send_complete_callback called with context : {0}'.format(context) )
    print ( 'messagingResult : {0}'.format(messaging_result) )
    print ( "" )

def send_reported_state_callback(status_code, user_context):
    global REPORTED_STATE_CALLBACK_COUNTER

    print ( "Confirmation for reported state received with:" )
    print ( "   status_code = {0}".format(status_code) )
    print ( "   context = {0}".format(status_code) )
    print ( "" )
    
    REPORTED_STATE_CALLBACK_COUNTER += 1
    print ( "Total calls confirmed: {0}".format(REPORTED_STATE_CALLBACK_COUNTER) )
    print ( "" )
    REPORTED_STATE_EVENT.set()

def receive_message_callback(message, counter):
    global MESSAGE_RECEIVE_CALLBACK_COUNTER

    message_buffer = message.get_bytearray()
    size = len(message_buffer)
    messagePayload = message_buffer.decode('utf-8')

    assert messagePayload == MESSAGING_MESSAGE, "Received message is not equal to what we sent"

    print ( "Received Message {0}:".format(counter) )
    print ( "   data: <<<{0}>>> & Size={1}".format(messagePayload, size) )
    map_properties = message.properties()
    key_value_pair = map_properties.get_internals()
    print ( "   properties: {0}".format(key_value_pair) )
    counter += 1

    MESSAGE_RECEIVE_CALLBACK_COUNTER += 1
    print ( "   Total calls received: {0}".format(MESSAGE_RECEIVE_CALLBACK_COUNTER) )
    print ( "" )
    MESSAGE_RECEIVE_EVENT.set()

    return IoTHubMessageDispositionResult.ACCEPTED

def device_twin_callback(update_state, payload, user_context):
    global TWIN_CALLBACK_COUNTER

    print ( "Twin callback called with:" )
    print ( "   update_state = {0}".format(update_state) )
    print ( "   payload = {0}".format(payload) )
    print ( "   context = {0}".format(user_context) )
    
    TWIN_CALLBACK_COUNTER += 1
    print ( "Total calls confirmed: {0}".format(TWIN_CALLBACK_COUNTER) )
    print ( "" )
    TWIN_CALLBACK_EVENT.set()

def device_method_callback(method_name, payload, user_context):
    global DEVICE_METHOD_USER_CONTEXT
    global DEVICE_CLIENT_RESPONSE
    global DEVICE_METHOD_CALLBACK_COUNTER

    print ( "Method callback called with:" )
    print ( "   methodName = {0}".format(method_name) )
    print ( "   payload = {0}".format(payload) )
    print ( "   context = {0}".format(user_context) )

    device_method_return_value = DeviceMethodReturnValue()
    if method_name == DEVICE_METHOD_NAME and user_context == DEVICE_METHOD_USER_CONTEXT:
        DEVICE_CLIENT_RESPONSE = DEVICE_METHOD_RESPONSE_PREFIX + "{0}".format(uuid.uuid4())
        device_method_return_value.response = "{ \"Response\": \"" + DEVICE_CLIENT_RESPONSE + "\" }"
        device_method_return_value.status = 200
    else:
        device_method_return_value.response = "{ \"Response\": \"\" }"
        device_method_return_value.status = 500
    print ( "" )

    DEVICE_METHOD_CALLBACK_COUNTER += 1
    print ( "Total calls received: {0}".format(DEVICE_METHOD_CALLBACK_COUNTER) )
    print ( "" )
    DEVICE_METHOD_EVENT.set()

    return device_method_return_value

def blob_upload_conf_callback(result, user_context):
    global BLOB_UPLOAD_CALLBACK_COUNTER
    print ( "Blob upload confirmation{0} received for message with result = {1}".format(user_context, result) )

    assert user_context == BLOB_UPLOAD_CONTEXT, "Invalid blob upload context"
    assert result == 0, "Blob upload failed"

    BLOB_UPLOAD_CALLBACK_COUNTER += 1
    print ( "Total calls confirmed: {0}".format(BLOB_UPLOAD_CALLBACK_COUNTER) )

    BLOB_UPLOAD_EVENT.set()


###########################################################################
# Helper functions - Service Client
###########################################################################
def sc_create_registrymanager(iothub_connection_string):
    iothub_registry_manager = IoTHubRegistryManager(iothub_connection_string)
    assert iothub_registry_manager != None, "RegistryManager creation failed"
    return iothub_registry_manager

def sc_create_device(iothub_registry_manager, device_id, auth_method):
    primary_key = ""
    secondary_key = ""
    new_device = iothub_registry_manager.create_device(device_id, primary_key, secondary_key, auth_method)
    assert new_device != None, "Device creation failed"
    return new_device

def sc_create_messaging(iothub_connection_string):
    iothub_messaging = IoTHubMessaging(iothub_connection_string)
    assert iothub_messaging != None, "iothub_messaging is NULL"
    return iothub_messaging

def sc_messaging_open(iothub_messaging):
    time.sleep(SLEEP_BEFORE_DEVICE_ACTION)
    iothub_messaging.open(open_complete_callback, MESSAGING_CONTEXT)

def sc_send_message(iothub_messaging, device_id, message):
    iothub_messaging.send_async(device_id, message, send_complete_callback, MESSAGING_CONTEXT)

def sc_messaging_close(iothub_messaging):
    iothub_messaging.close(None, None)

def sc_create_twin(iothub_connection_string):
    iothub_device_twin = IoTHubDeviceTwin(IOTHUB_CONNECTION_STRING)
    assert iothub_device_twin != None, "iothub_device_twin is NULL"
    return iothub_device_twin

def sc_get_twin(iothub_device_twin, device_id):
    twin_info = iothub_device_twin.get_twin(device_id)
    assert twin_info != None, "twin_info is NULL"
    return twin_info

def sc_update_twin(iothub_device_twin, device_id):
    new_property_name = "telemetryInterval"
    new_property_value = "42"
    UPDATE_JSON = "{\"properties\":{\"desired\":{\"" + new_property_name + "\":" + new_property_value + "}}}"
    twin_info = iothub_device_twin.update_twin(device_id, UPDATE_JSON)
    assert twin_info != None, "twin_info is NULL"
    return twin_info

def sc_create_device_method(iothub_connection_string):
    iothub_device_method = IoTHubDeviceMethod(IOTHUB_CONNECTION_STRING)
    assert iothub_device_method != None, "iothub_device_method is NULL"
    return iothub_device_method

def sc_invoke_device_method(iothub_device_method, device_id, method_name, method_payload):
    DEVICE_METHOD_TIMEOUT = 60
    response = iothub_device_method.invoke(device_id, method_name, method_payload, DEVICE_METHOD_TIMEOUT)
    assert response != None, "response is NULL"
    return response

def sc_delete_device(iothub_registry_manager, device_id):
    iothub_registry_manager.delete_device(device_id)


###########################################################################
# E2E tests
###########################################################################

def run_e2e_device_client(iothub_service_client_messaging, iothub_device_method, iothub_device_twin, device_id, device_connection_string, protocol, authMethod):

    ###########################################################################
    # IoTHubClient

    # prepare
    # act
    device_client = IoTHubClient(device_connection_string, protocol)

    # verify
    assert isinstance(device_client, IoTHubClient), 'Error: Invalid type returned!'
    assert device_client != None, "Error: device_client is NULL"
    ###########################################################################

    ###########################################################################
    # set_option

    # prepare
    # act
    device_client.set_option("messageTimeout", DEVICE_MESSAGE_TIMEOUT)

    if authMethod == IoTHubRegistryManagerAuthMethod.X509_THUMBPRINT:
        device_client.set_option("x509certificate", IOTHUB_E2E_X509_CERT)
        device_client.set_option("x509privatekey", IOTHUB_E2E_X509_THUMBPRINT)

    if device_client.protocol == IoTHubTransportProvider.HTTP:
        device_client.set_option("timeout", HTTP_TIMEOUT)
        device_client.set_option("MinimumPollingTime", HTTP_MINIMUM_POLLING_TIME)

    if protocol == IoTHubTransportProvider.MQTT_WS or protocol == IoTHubTransportProvider.AMQP_WS:
        device_client.set_option("TrustedCerts", CERTIFICATES)

    # verify
    ###########################################################################

    ###########################################################################
    # set_message_callback
    
    # prepare
    # act
    device_client.set_message_callback(receive_message_callback, MESSAGING_CONTEXT)

    # verify
    ###########################################################################

    if protocol == IoTHubTransportProvider.MQTT or protocol == IoTHubTransportProvider.MQTT_WS:
        ###########################################################################
        # set_device_twin_callback
    
        # prepare
        # act
        device_client.set_device_twin_callback(device_twin_callback, MESSAGING_CONTEXT)

        # verify
        ###########################################################################

        ###########################################################################
        # set_device_method_callback
    
        # prepare
        # act
        device_client.set_device_method_callback(device_method_callback, MESSAGING_CONTEXT)

        # verify
        ###########################################################################

        ###########################################################################
        # update device twin

        # prepare
        global TWIN_CALLBACK_EVENT
        global TWIN_CALLBACK_COUNTER

        TWIN_CALLBACK_EVENT.clear()
        TWIN_CALLBACK_COUNTER = 0

        # act
        sc_update_twin(iothub_device_twin, device_id)
        TWIN_CALLBACK_EVENT.wait(CALLBACK_TIMEOUT)

        # verify
        assert TWIN_CALLBACK_COUNTER == 1, "Error: device_twin_callback callback has not been called"
        ###########################################################################

        ###########################################################################
        # call device method

        # prepare
        global DEVICE_METHOD_EVENT
        global DEVICE_METHOD_CALLBACK_COUNTER

        DEVICE_METHOD_EVENT.clear()
        DEVICE_METHOD_CALLBACK_COUNTER = 0

        method_name = "E2EMethodName"
        payload_json = "{\"method_number\":\"42\"}"

        # act
        sc_invoke_device_method(iothub_device_method, device_id, method_name, payload_json)
        DEVICE_METHOD_EVENT.wait(CALLBACK_TIMEOUT)

        # verify
        assert DEVICE_METHOD_CALLBACK_COUNTER == 1, "Error: device_twin_callback callback has not been called"
        ###########################################################################

    if protocol != IoTHubTransportProvider.AMQP \
       and protocol != IoTHubTransportProvider.AMQP_WS \
       and protocol != IoTHubTransportProvider.HTTP:
        ###########################################################################
        # send_reported_state
    
        # prepare
        global REPORTED_STATE_EVENT
        global REPORTED_STATE_CALLBACK_COUNTER

        reported_state = "{\"newState\":\"standBy\"}"
        REPORTED_STATE_EVENT.clear()
        REPORTED_STATE_CALLBACK_COUNTER = 0

        # act
        device_client.send_reported_state(reported_state, len(reported_state), send_reported_state_callback, REPORTED_STATE_CONTEXT)
        REPORTED_STATE_EVENT.wait(CALLBACK_TIMEOUT)

        # verify
        assert REPORTED_STATE_CALLBACK_COUNTER == 1, "Error: send_reported_state_callback has not been called"
        ###########################################################################


    ###########################################################################
    # send_event_async

    # prepare
    global MESSAGING_MESSAGE
    global MESSAGE_RECEIVE_EVENT
    global MESSAGE_RECEIVE_CALLBACK_COUNTER

    MESSAGING_MESSAGE = ''.join([random.choice(string.ascii_letters) for n in range(12)])
    message = IoTHubMessage(bytearray(MESSAGING_MESSAGE, 'utf8'))
    MESSAGE_RECEIVE_EVENT.clear()
    MESSAGE_RECEIVE_CALLBACK_COUNTER = 0

    # act
    sc_send_message(iothub_service_client_messaging, device_id, message)
    MESSAGE_RECEIVE_EVENT.wait(CALLBACK_TIMEOUT)

    # verify
    assert MESSAGE_RECEIVE_CALLBACK_COUNTER == 1, "Error: message has not been received"
    ###########################################################################


    ###########################################################################
    # get_send_status

    # prepare
    status_counter = 0
    status = -1;

    # act
    while status_counter < 1:
        status = device_client.get_send_status()
        print ( "Send status: {0}".format(status) )

        # verify
        assert status == 0, "get_send_status reported status is not IDLE"
        status_counter += 1
    ###########################################################################


    if protocol != IoTHubTransportProvider.AMQP \
       and protocol != IoTHubTransportProvider.AMQP_WS:
        ###########################################################################
        # get_last_message_receive_time

        # prepare
        last_receive_time = -1
        # act
        last_receive_time = device_client.get_last_message_receive_time()

        # verify
        assert last_receive_time > 0, "Error: get_last_message_receive_time failed"
        ###########################################################################


    ###########################################################################
    # upload_blob_async
    
    # prepare
    global BLOB_UPLOAD_CONTEXT
    global BLOB_UPLOAD_EVENT
    global BLOB_UPLOAD_CALLBACK_COUNTER

    destination_file_name = ''.join([random.choice(string.ascii_letters) for n in range(12)])
    source = "Blob content for file upload test!"
    size = 34
    BLOB_UPLOAD_EVENT.clear()
    BLOB_UPLOAD_CALLBACK_COUNTER = 0

    # act
    device_client.upload_blob_async(destination_file_name, source, size, blob_upload_conf_callback, BLOB_UPLOAD_CONTEXT)
    BLOB_UPLOAD_EVENT.wait(CALLBACK_TIMEOUT)

    # verify
    assert BLOB_UPLOAD_CALLBACK_COUNTER == 1, "Error: blob_upload_conf_callback callback has not been called"
    ###########################################################################

    print ("run_e2e_device_client with protocol: {0}, and authMethod: {1} finished".format(protocol, authMethod))


def run_e2e(iothub_registry_manager, iothub_service_client_messaging, iothub_device_method, iothub_device_twin, protocol, authMethod):
    global IOTHUB_CONNECTION_STRING

    print ("********************* run_e2e({0}, {1}) E2E test started".format(protocol, authMethod))
    try:
        device_id = generate_device_name()

        device = sc_create_device(iothub_registry_manager, device_id, authMethod)
        device_connection_string = get_device_connection_string(iothub_registry_manager, IOTHUB_CONNECTION_STRING, device_id, authMethod)

        run_e2e_device_client(iothub_service_client_messaging, iothub_device_method, iothub_device_twin, device_id, device_connection_string, protocol, authMethod)

        retval = 0
    except Exception as e:
        print ("run_e2e({0}, {1}) E2E test failed with exception: {2}".format(protocol, authMethod, e))
        retval = 1
    finally:
        iothub_registry_manager.delete_device(device_id)

    print ("********************* run_e2e({0}, {1}) E2E test finished".format(protocol, authMethod))
    return retval


if __name__ == '__main__':
    print ("iothub_service_client E2E tests started!")

    read_environment_vars()
    iothub_registry_manager = sc_create_registrymanager(IOTHUB_CONNECTION_STRING)
    iothub_service_client_messaging = sc_create_messaging(IOTHUB_CONNECTION_STRING)
    iothub_device_method = sc_create_device_method(IOTHUB_CONNECTION_STRING)
    iothub_device_twin = sc_create_twin(IOTHUB_CONNECTION_STRING)

    sc_messaging_open(iothub_service_client_messaging)

    try:
        assert run_e2e(iothub_registry_manager, iothub_service_client_messaging, iothub_device_method, iothub_device_twin, IoTHubTransportProvider.MQTT, IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY) == 0
        assert run_e2e(iothub_registry_manager, iothub_service_client_messaging, iothub_device_method, iothub_device_twin, IoTHubTransportProvider.MQTT, IoTHubRegistryManagerAuthMethod.X509_THUMBPRINT) == 0

        assert run_e2e(iothub_registry_manager, iothub_service_client_messaging, iothub_device_method, iothub_device_twin, IoTHubTransportProvider.AMQP, IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY) == 0
        assert run_e2e(iothub_registry_manager, iothub_service_client_messaging, iothub_device_method, iothub_device_twin, IoTHubTransportProvider.AMQP, IoTHubRegistryManagerAuthMethod.X509_THUMBPRINT) == 0

        assert run_e2e(iothub_registry_manager, iothub_service_client_messaging, iothub_device_method, iothub_device_twin, IoTHubTransportProvider.HTTP, IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY) == 0
        assert run_e2e(iothub_registry_manager, iothub_service_client_messaging, iothub_device_method, iothub_device_twin, IoTHubTransportProvider.HTTP, IoTHubRegistryManagerAuthMethod.X509_THUMBPRINT) == 0

        assert run_e2e(iothub_registry_manager, iothub_service_client_messaging, iothub_device_method, iothub_device_twin, IoTHubTransportProvider.MQTT_WS, IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY) == 0
        assert run_e2e(iothub_registry_manager, iothub_service_client_messaging, iothub_device_method, iothub_device_twin, IoTHubTransportProvider.MQTT_WS, IoTHubRegistryManagerAuthMethod.X509_THUMBPRINT) == 0

        assert run_e2e(iothub_registry_manager, iothub_service_client_messaging, iothub_device_method, iothub_device_twin, IoTHubTransportProvider.AMQP_WS, IoTHubRegistryManagerAuthMethod.SHARED_PRIVATE_KEY) == 0
        assert run_e2e(iothub_registry_manager, iothub_service_client_messaging, iothub_device_method, iothub_device_twin, IoTHubTransportProvider.AMQP_WS, IoTHubRegistryManagerAuthMethod.X509_THUMBPRINT) == 0

        print ("iothub_device_client E2E tests passed!")
    except:
        print ("iothub_device_client E2E tests failed!")
