import logging
import six
import weakref
from threading import Event
from .transport.mqtt import MQTTTransport
from .message import Message
from .message_queue import MessageQueueManager

logger = logging.getLogger(__name__)


class GenericClient(object):
    """
    A super class representing a generic client. This class needs to be extended for specific clients.
    """

    def __init__(self, transport):
        """
        Constructor for instantiating an generic client.  This initializer should not be called
        directly.  Instead, the class method `from_authentication_provider` should be used to
        create a client object.

        :param auth_provider: The authentication provider
        :param transport: The transport that the client will use.
        """
        self._transport = transport
        self._transport.on_transport_connected = self._state_change
        self._transport.on_transport_disconnected = self._state_change
        self.state = "initial"

    def _state_change(self, new_state):
        self.state = new_state
        logger.info("Connection State - {}".format(self.state))


class GenericClientSync(GenericClient):
    """
    A super class representing a generic synchronous client. This class needs to be extended for specific clients.
    """

    def __init__(self, transport):
        super(GenericClientSync, self).__init__(transport)
        self._queue_manager = MessageQueueManager(
            transport.enable_feature, transport.disable_feature
        )

    @classmethod
    def from_authentication_provider(cls, authentication_provider, transport_name):
        """
        Creates a device client with the specified authentication provider and transport

        When creating the client, you need to pass in an authorization provider and a transport_name

        The authentication_provider parameter is an object created using the authentication_provider_factory
        module.  It knows where to connect (a network address), how to authenticate with the service
        (a set of credentials), and, if necessary, the protocol gateway to use when communicating
        with the service.

        The transport_name is a string which defines the name of the transport to use when connecting
        with the service or the protocol gateway.

        Currently "mqtt" is the only supported transport.

        :param authentication_provider: The authentication provider
        :param transport_name: The name of the transport that the client will use.
        """
        transport_name = transport_name.lower()
        if transport_name == "mqtt":
            transport = MQTTTransport(authentication_provider)
        elif transport_name == "amqp" or transport_name == "http":
            raise NotImplementedError("This transport has not yet been implemented")
        else:
            raise ValueError("No specific transport can be instantiated based on the choice.")
        return cls(transport)

    def connect(self):
        """
        Connects the client to an Azure IoT Hub or Azure IoT Edge instance.  The destination is chosen
        based on the credentials passed via the auth_provider parameter that was provided when
        this object was initialized.

        This is a synchronous call, meaning that this function will not return until the connection
        to the service has been completely established.
        """
        logger.info("connecting to transport")

        connect_complete = Event()

        def callback():
            connect_complete.set()

        self._transport.connect(callback)
        connect_complete.wait()

    def disconnect(self):
        """
        Disconnect the client from the Azure IoT Hub or Azure IoT Edge instance.

        This is a synchronous call, meaning that this function will not return until the connection
        to the service has been completely closed.
        """
        logger.info("disconnecting from transport")

        disconnect_complete = Event()

        def callback():
            disconnect_complete.set()

        self._transport.disconnect(callback)
        disconnect_complete.wait()

    def send_event(self, message):
        """
        Sends a message to the default events endpoint on the Azure IoT Hub or Azure IoT Edge instance.
        This is a synchronous event, meaning that this function will not return until the event
        has been sent to the service and the service has acknowledged receipt of the event.

        If the connection to the service has not previously been opened by a call to connect, this
        function will open the connection before sending the event.

        :param message: The actual message to send. Anything passed that is not an instance of the
        Message class will be converted to Message object.
        """
        if not isinstance(message, Message):
            message = Message(message)

        send_complete = Event()

        def callback():
            send_complete.set()

        self._transport.send_event(message, callback)
        send_complete.wait()


class DeviceClient(GenericClientSync):
    """
    A synchronous device client that connects to an Azure IoT Hub instance.
    Intended for usage with Python 2.7 or compatibility scenarios for Python 3.5+.
    """

    def __init__(self, transport):
        super(DeviceClient, self).__init__(transport)
        self._transport.on_transport_c2d_message_received = self._queue_manager.route_c2d_message

    def get_c2d_message_queue(self):
        return self._queue_manager.get_c2d_message_queue()


class ModuleClient(GenericClientSync):
    """
    A synchronous module client that connects to an Azure IoT Hub or Azure IoT Edge instance.
    Intended for usage with Python 2.7 or compatibility scenarios for Python 3.5+.
    """

    def __init__(self, transport):
        super(ModuleClient, self).__init__(transport)
        self._transport.on_transport_input_message_received = (
            self._queue_manager.route_input_message
        )

    def get_input_message_queue(self, input_name):
        return self._queue_manager.get_input_message_queue(input_name)

    def send_to_output(self, message, output_name):
        """
        Sends an event/message to the given module output.
        These are outgoing events and are meant to be "output events"
        This is a synchronous event, meaning that this function will not return until the event
        has been sent to the service and the service has acknowledged receipt of the event.

        If the connection to the service has not previously been opened by a call to connect, this
        function will open the connection before sending the event.

        :param message: message to send to the given output. Anything passed that is not an instance of the
        Message class will be converted to Message object.
        :param output_name: Name of the output to send the event to.
        """
        if not isinstance(message, Message):
            message = Message(message)

        message.output_name = output_name

        send_complete = Event()

        def callback():
            send_complete.set()

        self._transport.send_output_event(message, callback)
        send_complete.wait()
