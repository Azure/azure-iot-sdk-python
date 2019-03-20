"""Azure IoT Hub Device SDK

This SDK provides functionality for communicating with the Azure IoT Hub
as a Device or Module.
"""

from .sync_clients import DeviceClient, ModuleClient
from .sync_inbox import InboxEmpty
from .common import Message

__all__ = ["DeviceClient", "ModuleClient", "Message", "InboxEmpty", "auth"]
