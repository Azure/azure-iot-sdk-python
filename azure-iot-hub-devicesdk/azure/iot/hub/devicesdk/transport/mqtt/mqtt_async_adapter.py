import logging
from .mqtt_transport import MQTTTransport
from azure.iot.common import async_adapter

logger = logging.getLogger(__name__)


class MQTTTransportAsync(MQTTTransport):
    """
    Asynchronous implementation of MQTTTransport for communication via MQTT protocol.
    """

    async def connect(self):
        logger.info("async connecting to transport")
        connect_async = async_adapter.emulate_async(super().connect)

        def sync_callback():
            logger.info("async connect finished")

        callback = async_adapter.AwaitableCallback(sync_callback)

        await connect_async(callback)
        await callback.completion()

    async def disconnect(self):
        logger.info("async disconnecting from transport")
        disconnect_async = async_adapter.emulate_async(super().disconnect)

        def sync_callback():
            logger.info("async disconnect finished")

        callback = async_adapter.AwaitableCallback(sync_callback)

        await disconnect_async(callback)
        await callback.completion()

    async def send_event(self, message):
        logger.info("async sending event")
        send_event_async = async_adapter.emulate_async(super().send_event)

        def sync_callback():
            logger.info("async sending finished")

        callback = async_adapter.AwaitableCallback(sync_callback)

        await send_event_async(message, callback)
        await callback.completion()
