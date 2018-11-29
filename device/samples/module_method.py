import time
import iothub_client

from iothub_client import IoTHubModuleClient, IoTHubTransportProvider, DeviceMethodReturnValue

# Create a a module client object
client = IoTHubModuleClient()

# Use the configuration provided by the container
client.create_from_environment(IoTHubTransportProvider.MQTT)

# This function will be called every time a method request is received
def method_callback(method_name, payload, user_context):
    print('received method call:')
    print('\tmethod name:', method_name)
    print('\tpayload:', str(payload))
    retval = DeviceMethodReturnValue()
    retval.status = 200
    retval.response = "{\"key\":\"value\"}"
    return retval

print('subscribing to method calls')
# Register the callback with the client
client.set_module_method_callback(method_callback, 0)

# Loop forever
while True:
    time.sleep(5)
