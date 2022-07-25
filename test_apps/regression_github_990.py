# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import logging
import functools
import ssl
from test_utils import test_env, logging_hook
from azure.iot.device.aio import IoTHubDeviceClient
import azure.iot.device.common


logging.basicConfig(level=logging.WARNING)
logging.getLogger("azure.iot").setLevel(level=logging.DEBUG)

"""
Order of events for this bug repro:
1. Customer calls send_message
2. After PUBLISH and before PUBACK, transport disconnects with rc=1
3. On reconnnect, transport.connect raised TlsExchangeAuthError(None,) caused by SSLError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed (_ssl.c:852)')
4. TlsExchangeAuthError is not transient, so reconnect fails. Since the reonnect is not user-initiated, no error is returned to the caller.
5. PUBACK never received, so send_message never completes.
"""


def workaround_github_990():
    # This is a customer workaround for github issue 990. It should not be necessary
    # but I"m leaving this here unused for reference.
    try:
        stage = azure.iot.device.common.pipeline.pipeline_stages_base.ConnectionStateStage
    except AttributeError:
        stage = azure.iot.device.common.pipeline.pipeline_stages_base.ReconnectStage

    err = azure.iot.device.common.transport_exceptions.TlsExchangeAuthError

    if err not in stage.transient_connect_errors:
        stage.transient_connect_errors.append(err)


def hack_paho_to_disconnect_after_publish(device_client, log_func=print):
    paho = logging_hook.get_paho_from_device_client(device_client)

    old_sock_send = paho._sock_send
    old_sock_recv = paho._sock_recv
    old_sock_close = paho._sock_close
    old_publish = paho.publish
    old_reconnect = paho.reconnect

    fail_sock_send_until_reconnect = False
    first_publish = True
    raise_on_next_reconnect = False
    block_next_puback = False

    @functools.wraps(old_sock_send)
    def new_sock_send(buf):
        nonlocal fail_sock_send_until_reconnect

        if fail_sock_send_until_reconnect:
            log_func("-----------DROPPING {} bytes".format(len(buf)))
            return len(buf)
        else:
            count = old_sock_send(buf)
            log_func("---------- SENT {} bytes".format(count))
            return count

    @functools.wraps(old_sock_recv)
    def new_sock_recv(buflen):
        nonlocal block_next_puback

        if block_next_puback:
            result = old_sock_recv(1024)  # flush the buffer
            log_func("---------- BLOCKING PUBACK = {} bytes dropped".format(len(result)))
            block_next_puback = False
            raise BlockingIOError()
        else:
            return old_sock_recv(buflen)

    @functools.wraps(old_sock_close)
    def new_sock_close():
        nonlocal fail_sock_send_until_reconnect

        if fail_sock_send_until_reconnect:
            log_func("-----------RESTORING SOCKET behavior")
            fail_sock_send_until_reconnect = False
        return old_sock_close()

    @functools.wraps(old_publish)
    def new_publish(*args, **kwargs):
        nonlocal fail_sock_send_until_reconnect, first_publish, raise_on_next_reconnect, block_next_puback

        if first_publish:
            block_next_puback = True
        result = old_publish(*args, **kwargs)
        if first_publish:
            log_func("-----------FIRST PUBLISH COMPLETE. Breaking socket")
            fail_sock_send_until_reconnect = True
            raise_on_next_reconnect = True
            first_publish = False
        return result

    @functools.wraps(old_reconnect)
    def new_reconnect(*args, **kwargs):
        nonlocal raise_on_next_reconnect
        if raise_on_next_reconnect:
            log_func("----------- RECONNECT CALLED. raising TlsExchangeAuthError")
            raise_on_next_reconnect = False
            err = ssl.SSLError()
            err.strerror = "CERTIFICATE_VERIFY_FAILED"
            raise err
        return old_reconnect(*args, **kwargs)

    paho._sock_send = new_sock_send
    paho._sock_recv = new_sock_recv
    paho._sock_close = new_sock_close
    paho.publish = new_publish
    paho.reconnect = new_reconnect


async def main():
    # workaround_github_990()

    # Create instance of the device client using the connection string
    device_client = IoTHubDeviceClient.create_from_connection_string(
        test_env.DEVICE_CONNECTION_STRING, keep_alive=10
    )
    logging_hook.hook_device_client(device_client)

    hack_paho_to_disconnect_after_publish(device_client)

    # Connect the device client.
    await device_client.connect()

    print("Sending message...")
    await device_client.send_message("This is a message that is being sent")
    print("Message successfully sent!")

    print("Shutting down")
    await device_client.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
