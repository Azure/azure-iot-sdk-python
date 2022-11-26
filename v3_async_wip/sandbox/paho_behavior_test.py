# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import paho.mqtt.client as mqtt
from v3_async_wip import transport_helper
import datetime
import os
import logging
import time
import threading

logging.basicConfig(level=logging.DEBUG)

CONNECTION_STRING = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
HOSTNAME = transport_helper.get_hostname(CONNECTION_STRING)
TRANSPORT = "tcp"
PORT = 8883
KEEP_ALIVE = 60

# NOTE: Only wait on these if you KNOW it'll happen (or use a timeout)
CONNECTED_EVENT = threading.Event()
DISCONNECTED_EVENT = threading.Event()

# NOTE: time.sleep does ~NOT~ block paho handler threads. Feel free to use it. It will not affect paho.


def create_client(reconnect_on_failure=True):
    client_id = transport_helper.get_client_id(CONNECTION_STRING)
    username = transport_helper.get_username(CONNECTION_STRING)
    password = transport_helper.get_password(CONNECTION_STRING)

    client = mqtt.Client(
        client_id=client_id,
        clean_session=False,
        protocol=mqtt.MQTTv311,
        transport="tcp",
        reconnect_on_failure=reconnect_on_failure,
    )

    ssl_context = transport_helper.create_ssl_context()
    client.tls_set_context(context=ssl_context)
    client.username_pw_set(username, password)

    def on_connect(client, userdata, flags, rc):
        now = datetime.datetime.now().time()
        print("{} - CONNECTED! rc: {}".format(now, rc))
        CONNECTED_EVENT.set()
        CONNECTED_EVENT.clear()

    def on_disconnect(client, userdata, rc):
        now = datetime.datetime.now().time()
        print("{} - DISCONNECTED! rc: {}".format(now, rc))
        DISCONNECTED_EVENT.set()
        DISCONNECTED_EVENT.clear()

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    return client


def simple():
    client = create_client()
    print("Connect")
    client.connect(host=HOSTNAME, port=PORT, keepalive=KEEP_ALIVE)
    client.loop_start()
    CONNECTED_EVENT.wait()
    print("Disconnect")
    client.disconnect()
    DISCONNECTED_EVENT.wait()
    client.loop_stop()


def multiple_connects():
    client = create_client()
    print("Connect #1")
    client.connect(host=HOSTNAME, port=PORT, keepalive=KEEP_ALIVE)
    client.loop_start()
    CONNECTED_EVENT.wait(timeout=5)
    print("Connect #2")
    client.connect(host=HOSTNAME, port=PORT, keepalive=KEEP_ALIVE)
    CONNECTED_EVENT.wait(timeout=5)
    print("Connect #3")
    client.connect(host=HOSTNAME, port=PORT, keepalive=KEEP_ALIVE)
    CONNECTED_EVENT.wait(timeout=5)
    print("Disconnect")
    client.disconnect()
    DISCONNECTED_EVENT.wait(timeout=5)
    client.loop_stop()
    # RESULT: Nothing of note really happens here. Works fine.
    # on_connect gets called repeatedly.
    # WARNING: THIS IS ONLY TRUE IF reconnect_on_failure IS TRUE


def multiple_disconnects():
    client = create_client()
    print("Connect #1")
    client.connect(host=HOSTNAME, port=PORT, keepalive=KEEP_ALIVE)
    client.loop_start()
    CONNECTED_EVENT.wait(timeout=5)
    print("Disconnect #1")
    client.disconnect()
    print("Waiting for completion...")
    DISCONNECTED_EVENT.wait(timeout=5)
    print("Disconnect #2")
    client.disconnect()
    print("Waiting for completion...")
    DISCONNECTED_EVENT.wait(timeout=120)
    # RESULT: While it doesn't block on the invocation, the second disconnect will never
    # trigger the on_disconnect handler. Not affected by reconnect policy.


def reconnect_while_connected():
    client = create_client(reconnect_on_failure=False)
    print("Connect")
    client.connect(host=HOSTNAME, port=PORT, keepalive=KEEP_ALIVE)
    client.loop_start()
    CONNECTED_EVENT.wait()
    # print("Disconnect")
    # client.disconnect()
    # DISCONNECTED_EVENT.wait()
    print("Reconnect")
    client.reconnect()
    CONNECTED_EVENT.wait(timeout=5)
    client.loop_stop()
    # RESULT: Can only reconnect without calling disconnect.
    # WARNING: THIS IS ONLY TRUE IF reconnect_on_failure IS TRUE


def reconnect_after_drop():
    pass


def use_expired_credentials():
    client = create_client(reconnect_on_failure=False)
    username = transport_helper.get_username(CONNECTION_STRING)
    # Make a password that has already expired. Using 15 mins to exceed grace period.
    password = transport_helper.get_password(CONNECTION_STRING, ttl=-900)
    client.username_pw_set(username, password)
    print("Connect")
    client.connect(host=HOSTNAME, port=PORT, keepalive=10)
    client.loop_start()
    CONNECTED_EVENT.wait(timeout=10)
    time.sleep(10)
    client.loop_stop()
    # RESULT: If the expired credential is still within the grace period, no issue.
    # However, if it is not it will return rc5 on CONNECT and ALSO an rc5 on disconnect
    # (rc5 == MQTT_ERR_CONN_REFUSED). This is to say, both on_connect AND on_disconnect
    # are triggered by this conn failure.


def wait_for_expiry():
    client = create_client(reconnect_on_failure=False)
    username = transport_helper.get_username(CONNECTION_STRING)
    password = transport_helper.get_password(CONNECTION_STRING, ttl=30)  # 30 second expiry
    client.username_pw_set(username, password)
    print("Connect")
    client.connect(host=HOSTNAME, port=PORT, keepalive=10)
    client.loop_start()
    CONNECTED_EVENT.wait()
    print("Waiting for DC... [THIS WILL TAKE ~10 MINUTES!]")
    DISCONNECTED_EVENT.wait()
    client.loop_stop()
    # RESULT: Connection will drop after a grace period granted by IoTHub (approx 10 mins)


def renew_credentials_manual_connect():
    client = create_client(reconnect_on_failure=False)
    username = transport_helper.get_username(CONNECTION_STRING)
    password = transport_helper.get_password(CONNECTION_STRING, ttl=30)  # 30 second expiry
    client.username_pw_set(username, password)
    print("Connect")
    client.connect(host=HOSTNAME, port=PORT, keepalive=10)
    client.loop_start()
    CONNECTED_EVENT.wait()
    print("Making a new, longer lasting password")
    password = transport_helper.get_password(
        CONNECTION_STRING, ttl=3600
    )  # This one is good for 1hr
    print("Setting new password even though connected...")
    client.username_pw_set(username, password)
    print("Waiting for DC... [THIS WILL TAKE ~10 MINUTES!]")
    DISCONNECTED_EVENT.wait()
    print("Connecting with new password that was previously set")
    # If this works, we know that it's a new credential, since the previous one expired!
    client.connect(host=HOSTNAME, port=PORT, keepalive=10)
    CONNECTED_EVENT.wait(timeout=30)
    print("Waiting 30s to see that connection doesn't drop")
    time.sleep(30)
    print("Manual Disconnect")
    client.disconnect()
    DISCONNECTED_EVENT.wait()
    client.loop_stop()
    # RESULT: A new username/password CAN be set even when connected.
    # It will be used on this next manual connect


def renew_credentials_auto_reconnect():
    client = create_client(reconnect_on_failure=True)
    username = transport_helper.get_username(CONNECTION_STRING)
    password = transport_helper.get_password(CONNECTION_STRING, ttl=30)  # 30 second expiry
    client.username_pw_set(username, password)
    print("Connect")
    client.connect(host=HOSTNAME, port=PORT, keepalive=10)
    client.loop_start()
    CONNECTED_EVENT.wait()
    print("Making a new, longer lasting password")
    password = transport_helper.get_password(
        CONNECTION_STRING, ttl=3600
    )  # This one is good for 1hr
    print("Setting new password even though connected...")
    client.username_pw_set(username, password)
    print("Waiting for DC... [THIS WILL TAKE ~10 MINUTES!]")
    DISCONNECTED_EVENT.wait()
    print("Waiting for auto-reconnect with new password that was previously set")
    # If this works, we know that it's a new credential, since the previous one expired!
    CONNECTED_EVENT.wait(timeout=30)
    print("Waiting 30s to see that connection doesn't drop")
    time.sleep(30)
    print("Manual Disconnect")
    client.disconnect()
    DISCONNECTED_EVENT.wait()
    client.loop_stop()
    # RESULT: A new username/password CAN be set even when connected.
    # It will be used on this next auto connect


def renew_credentials_without_drop():
    client = create_client(
        reconnect_on_failure=True
    )  # This needs to be true to connect while connected
    username = transport_helper.get_username(CONNECTION_STRING)
    password = transport_helper.get_password(CONNECTION_STRING, ttl=30)  # 30 second expiry
    client.username_pw_set(username, password)
    print("Connect")
    client.connect(host=HOSTNAME, port=PORT, keepalive=10)
    client.loop_start()
    CONNECTED_EVENT.wait()
    print("Making a new, longer lasting password")
    password = transport_helper.get_password(
        CONNECTION_STRING, ttl=3600
    )  # This one is good for 1hr
    print("Setting new password even though connected...")
    client.username_pw_set(username, password)
    print("Attempting to connect again with new credential (already connected)")
    client.connect(host=HOSTNAME, port=PORT, keepalive=10)
    CONNECTED_EVENT.wait()
    print("Waiting 15 minutes to see that no disconnect happens...")
    # Disconnect would normally be expected after ~10 mins
    time.sleep(900)
    print("Still connected after 15 minutes")
    print("Manual Disconnect")
    client.disconnect()
    DISCONNECTED_EVENT.wait()
    client.loop_stop()
    # RESULT: Client stayed connected because the second connect updated the credentials.


def conn_failure_auto_reconnect():
    client = create_client(reconnect_on_failure=True)
    username = transport_helper.get_username(CONNECTION_STRING)
    # Make a password that has already expired. Using 15 mins to exceed grace period.
    password = transport_helper.get_password(CONNECTION_STRING, ttl=-900)
    client.username_pw_set(username, password)
    print("Connect #1 (Failure expected)")
    client.connect(host=HOSTNAME, port=PORT, keepalive=KEEP_ALIVE)
    client.loop_start()
    time.sleep(60)
    client.loop_stop()
    # RESULT: Keeps retrying the failed connect (rc5). There is a backoff on the interval.


"""
~~~~ SUMMARY OF RESULTS ~~~~

If reconnect_on_failure is enabled in Paho, credentials can be updated without a connection drop
by just calling .username_pw_set() and then a manual connect before any drop happens.
Or, you could just wait for the drop due to expiration, and then let the reconnect process handle it.

If reconnect_on_failure is disabled in Paho, then you must wait for a drop, and manually connect.
However, you can still call .username_pw_set() anytime before the drop.

However, with reconnect_on_failure enabled, a failed manual .connect() will still trigger indefinite
reconnection attempts, unless there is some kind of socket failure (e.g. no internet connection on Windows)

Lastly, if reconnect_on_failure is disabled, you need to be careful about multiple calls to .connect().
The on_connect handler/callback will never trigger unless reconnect_on_failure is enabled.
This is pretty reasonable behavior in a vacuum, but given that it CAN trigger multiple times when
reconnect_on_failure is enabled, that's kinda weird.
"""

# TODO: does reconnect() help any of the above problems?
# TODO: does the CONACK not coming through mean the password wasn't updated for the connection though?

if __name__ == "__main__":
    pass
