from .sync_clients import DeviceClientSync, ModuleClientSync

try:
    from .async_clients import DeviceClient, ModuleClient
except SyntaxError:
    pass  # SyncClients are not available in 2.7
from .message import Message
