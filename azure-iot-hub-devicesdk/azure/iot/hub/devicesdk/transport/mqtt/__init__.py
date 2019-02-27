"""Azure IoT Hub Device SDK MQTT Transport

This package provides the MQTT transport for use with the Azure IoT Hub Device SDK.
INTERNAL USAGE ONLY
"""

from .mqtt_transport import MQTTTransport

try:
    from .mqtt_async_adapter import MQTTTransportAsync
except SyntaxError:
    pass
