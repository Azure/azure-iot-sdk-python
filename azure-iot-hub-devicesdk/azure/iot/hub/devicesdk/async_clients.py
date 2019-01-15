import logging
from .transport.mqtt import MQTTTransportAsync
from .sync_clients import GenericClient

logger = logging.getLogger(__name__)


class GenericClientAsync(GenericClient):
    """
    A super class representing a generic asynchronous client. This class needs to be extended for specific clients.
    """

    @classmethod
    async def from_authentication_provider(cls, authentication_provider, transport_name):
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
        if transport_name == "mqtt":
            transport = MQTTTransportAsync(authentication_provider)
        else:
            raise NotImplementedError(
                "No specific transport can be instantiated based on the choice."
            )
        return cls(authentication_provider, transport)

    async def connect(self):
        """
        Connects the client to an Azure IoT Hub or Azure IoT Edge instance.  The destination is chosen
        based on the credentials passed via the auth_provider parameter that was provided when
        this object was initialized.
        """
        await self._transport.connect()

    async def disconnect(self):
        """
        Disconnect the client from the Azure IoT Hub or Azure IoT Edge instance.
        """
        await self._transport.disconnect()

    async def send_event(self, message):
        """
        Sends a message to the default events endpoint on the Azure IoT Hub or Azure IoT Edge instance.
        This is a synchronous event, meaning that this function will not return until the event
        has been sent to the service and the service has acknowledged receipt of the event.

        If the connection to the service has not previously been opened by a call to connect, this
        function will open the connection before sending the event.

        :param message: The actual message to send.
        """
        await self._transport.send_event(message)


class DeviceClient(GenericClientAsync):
    """
    An asynchronous device client that connects to an Azure IoT Hub instance.
    Intended for usage with Python 3.5+
    """

    pass


class ModuleClient(GenericClientAsync):
    """
    An asynchronous module client that connects to an Azure IoT Hub or Azure IoT Edge instance.
    Intended for usage with Python 3.5+
    """

    pass
