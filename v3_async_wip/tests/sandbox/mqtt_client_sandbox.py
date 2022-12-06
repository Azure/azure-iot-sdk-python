# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from v3_async_wip import transport_helper, mqtt_client

# from dev_utils import iptables
import asyncio
import os
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

CONNECTION_STRING = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
PORT = 8883
TRANSPORT = "tcp"


async def create_client():
    client_id = transport_helper.get_client_id(CONNECTION_STRING)
    username = transport_helper.get_username(CONNECTION_STRING)
    password = transport_helper.get_password(CONNECTION_STRING)
    hostname = transport_helper.get_hostname(CONNECTION_STRING)
    ssl_context = transport_helper.create_ssl_context()

    client = mqtt_client.MQTTClient(
        client_id=client_id,
        hostname=hostname,
        port=PORT,
        transport=TRANSPORT,
        ssl_context=ssl_context,
    )

    client.set_credentials(username, password)

    return client


def set_expired_credentials(client):
    print("Updating credentials to something expired")
    username = transport_helper.get_username(CONNECTION_STRING)
    password = transport_helper.get_password(CONNECTION_STRING, ttl=-900)
    client.set_credentials(username, password)


async def main():
    client = await create_client()
    set_expired_credentials(client)
    print("Trying to connect...")
    await client.connect()
    # try:
    #     await client.connect()
    # except exceptions.ConnectionFailedError as e:
    #     print("Raised exception")
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
