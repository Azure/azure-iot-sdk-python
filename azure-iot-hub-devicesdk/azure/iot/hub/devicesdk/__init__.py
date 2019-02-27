"""Azure IoT Hub Device SDK

This SDK provides functionality for communicating with the Azure IoT Hub
as a Device or Module.
"""

from .sync_clients import DeviceClient, ModuleClient
from .message import Message
from .message_queue import MessageQueue

__all__ = ["DeviceClient", "ModuleClient", "Message", "MessageQueue", "auth"]
