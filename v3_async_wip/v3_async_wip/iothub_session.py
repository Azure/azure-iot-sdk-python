# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import contextlib
import ssl
from typing import Optional, Union
from v3_async_wip import signing_mechanism as sm
from v3_async_wip import connection_string as cs
from v3_async_wip import sastoken as st
from v3_async_wip import config, models
from v3_async_wip.iothub_mqtt_client import IoTHubMQTTClient

# Just alias this for now
SasAuth = st.SasTokenProvider

# class SasAuth(st.SasTokenProvider):
#     @classmethod
#     async def from_connection_string(cls, connection_string: str):
#         cs_obj = cs.ConnectionString(connection_string)
#         signing_mechanism = sm.SymmetricKeySigningMechanism(cs_obj[cs.SHARED_ACCESS_KEY])
#         uri = "{hostname}/devices/{device_id}".format(
#             hostname=cs_obj[cs.SHARED_ACCESS_KEY],
#             device_id=cs_obj[cs.DEVICE_ID]
#         )
#         generator = st.SasTokenGenerator(signing_mechanism=signing_mechanism, uri=uri)
#         return await cls.create_from_generator(generator)


class IoTHubSession:
    def __init__(
        self,
        *,
        iothub_hostname: str,
        device_id: str,
        module_id: Optional[str] = None,
        sas_auth: Optional[SasAuth] = None,
        ssl_context: Optional[ssl.SSLContext] = None,
    ) -> None:

        cfg = config.IoTHubClientConfig(
            hostname=iothub_hostname,
            device_id=device_id,
            module_id=module_id,
            sastoken_provider=sas_auth,
            ssl_context=ssl_context,
        )
        self._mqtt_client = IoTHubMQTTClient(cfg)
        self._sas_auth = sas_auth

    async def __aenter__(self) -> "IoTHubSession":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.disconnect()
        await self.shutdown()

    @classmethod
    async def from_connection_string(cls, connection_string: str):
        cs_obj = cs.ConnectionString(connection_string)
        signing_mechanism = sm.SymmetricKeySigningMechanism(cs_obj[cs.SHARED_ACCESS_KEY])
        uri = "{hostname}/devices/{device_id}".format(
            hostname=cs_obj[cs.HOST_NAME], device_id=cs_obj[cs.DEVICE_ID]
        )
        generator = st.InternalSasTokenGenerator(signing_mechanism=signing_mechanism, uri=uri)
        provider = await st.SasTokenProvider.create_from_generator(generator)
        return cls(
            iothub_hostname=cs_obj[cs.HOST_NAME],
            device_id=cs_obj[cs.DEVICE_ID],
            sas_auth=provider,
        )

    async def connect(self):
        await self._mqtt_client.connect()

    async def disconnect(self):
        await self._mqtt_client.disconnect()

    async def shutdown(self):
        await self._mqtt_client.shutdown()
        await self._sas_auth.shutdown()

    async def send_message(self, message: Union[str, models.Message]):
        if not isinstance(message, models.Message):
            message = models.Message(message)
        await self._mqtt_client.send_message(message)

    @contextlib.asynccontextmanager
    async def messages(self):
        await self._mqtt_client.enable_c2d_message_receive()
        try:
            yield self._mqtt_client.incoming_c2d_messages
        finally:
            await self._mqtt_client.disable_c2d_message_receive()
