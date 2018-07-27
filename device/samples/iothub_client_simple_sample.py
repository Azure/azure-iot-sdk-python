from iothub_client import IoTHubClient, IoTHubTransportProvider, IoTHubMessage

CONNECTION_STRING = "<YOUR DEVICE CONNECTION STRING HERE>"
PROTOCOL = IoTHubTransportProvider.MQTT


def send_confirmation_callback(message, result, user_context):
    print("Confirmation received for message with result = %s" % (result))


if __name__ == '__main__':
    client = IoTHubClient(CONNECTION_STRING, PROTOCOL)
    message = IoTHubMessage("test message")
    client.send_event_async(message, send_confirmation_callback, None)
    print("Message transmitted to IoT Hub")