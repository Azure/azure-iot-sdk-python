import paho.mqtt.client as mqtt
from v3_async_wip import transport_helper
from dev_utils import iptables
import asyncio
import os
import datetime

CONNECTION_STRING = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
HOSTNAME = transport_helper.get_hostname(CONNECTION_STRING)
PORT = 8883
TRANSPORT = "tcp"
KEEPALIVE = 5

LOOP = None

"""
FINDINGS REGARDING STATE

New client -> NEW
CONNACK Received -> CONNECTED
Manual disconnect initiated (while connected) -> DISCONNECTING
Manual disconnect initiated (while disconnected) -> DISCONNECTING
Unexpected disconnect -> No change to state (CONNECTED)


"""


def drop_packets():
    iptables.disconnect_output_port("DROP", "mqtt", HOSTNAME)


def restore_packets():
    iptables.reconnect_all("mqtt", HOSTNAME)


def log_paho_state(state_num):
    if state_num == 0:
        msg = "NEW"
    elif state_num == 1:
        msg = "CONNECTED"
    elif state_num == 2:
        msg = "DISCONNECTING"
    elif state_num == 3:
        msg = "CONNECT_ASYNC"
    else:
        msg = "UNKNOWN"
    print("    Current time: {}".format(datetime.datetime.now().time()))
    print("    Client state: {} - {}".format(state_num, msg))


def create_client(reconnect_on_failure=False):
    client_id = transport_helper.get_client_id(CONNECTION_STRING)
    username = transport_helper.get_username(CONNECTION_STRING)
    password = transport_helper.get_password(CONNECTION_STRING)

    client = mqtt.Client(
        client_id=client_id,
        clean_session=False,
        protocol=mqtt.MQTTv311,
        transport=TRANSPORT,
        reconnect_on_failure=reconnect_on_failure,
    )

    ssl_context = transport_helper.create_ssl_context()
    client.tls_set_context(context=ssl_context)
    client.username_pw_set(username, password)

    def on_connect(client, userdata, flags, rc):
        if client.is_connected():
            print("Connected! rc - {}".format(rc))
        else:
            print("Connection Failed! rc - {}".format(rc))
        log_paho_state(client._state)

    def on_disconnect(client, userdata, rc):
        print("Disconnected! rc - {}".format(rc))
        log_paho_state(client._state)

        async def stop_network_loop():
            print("Loop stop...")
            client.loop_stop()
            log_paho_state(client._state)

        asyncio.run_coroutine_threadsafe(stop_network_loop(), LOOP)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    print("Client created!")
    log_paho_state(client._state)

    return client


def set_expired_credentials(client):
    print("Updating credentials to something expired")
    username = transport_helper.get_username(CONNECTION_STRING)
    password = transport_helper.get_password(CONNECTION_STRING, ttl=-900)
    client.username_pw_set(username, password)
    log_paho_state(client._state)


async def connect(client):
    print("Connecting...")
    client.connect(host=HOSTNAME, port=PORT, keepalive=KEEPALIVE)
    log_paho_state(client._state)
    client.loop_start()
    while not client.is_connected():
        await asyncio.sleep(0.5)
    await asyncio.sleep(0.1)


async def disconnect(client):
    print("Disconnecting...")
    rc = client.disconnect()
    log_paho_state(client._state)
    print("    rc: {}".format(rc))
    while client.is_connected():
        await asyncio.sleep(0.5)
    await asyncio.sleep(0.1)


async def unexpected_disconnect(client):
    print("Dropping...")
    log_paho_state(client._state)
    drop_packets()
    await asyncio.sleep(KEEPALIVE * 2)
    log_paho_state(client._state)
    # while client.is_connected():
    #     await asyncio.sleep(0.5)
    # await asyncio.sleep(0.1)
    restore_packets()


async def run_test(client):
    # set_expired_credentials(client)
    drop_packets()
    await disconnect(client)


async def main():
    restore_packets()
    global LOOP
    LOOP = asyncio.get_running_loop()
    client = create_client()

    await run_test(client)

    print("Waiting to exit...")
    await asyncio.sleep(1)
    log_paho_state(client._state)
    restore_packets()

    # Bad credential - conn and disconn 5


if __name__ == "__main__":
    asyncio.run(main())
