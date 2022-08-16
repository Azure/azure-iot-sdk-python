# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from dev_utils import logging_hook
import random
import functools


"""
    def _sock_send(self, buf):
    def _sock_recv(self, buffsize):
    def _reset_sockets(self, sockpair_only=False):
    def _sock_close(self):
"""

# List of Paho functions to add logging to
PAHO_FUNCTIONS_TO_HOOK = {
    # "_sock_send": False,
    # "_sock_recv": False,
    # "_sock_close": False,
    # "_reset_sockets": False,
    "connect": False,
    "disconnect": False,
    "reconnect": False,
    "publish": False,
    "on_connect": True,
    "on_disconnect": True,
}


class MyFakeException(Exception):
    pass


def add_paho_logging_hook(device_client, log_func=print):
    """
    Add logging hooks to all the Paho functions listed in the `PAHO_FUNCTIONS_TO_HOOK`
    list
    """
    paho = logging_hook.get_paho_from_device_client(device_client)

    for name in PAHO_FUNCTIONS_TO_HOOK:
        logging_hook.add_logging_hook(
            obj=paho,
            func_name=name,
            log_func=log_func,
            module_name="Paho",
            log_args=PAHO_FUNCTIONS_TO_HOOK[name],
        )


def add_hook_drop_outgoing_until_reconnect(device_client, failure_probability, log_func=print):
    """
    Add a hook to randomly drop all outgoing messages until reconnect based on some failure
    probability. This is used to simulate a "connection drop" scenario where packets just stop
    being sent and the only way to recover is to close the socket and open a new one.
    """

    paho = logging_hook.get_paho_from_device_client(device_client)

    old_sock_send = paho._sock_send
    old_sock_close = paho._sock_close
    failed = False

    @functools.wraps(old_sock_send)
    def new_sock_send(buf):
        """
        Inside `sock_send`, we randomly decide to stop sending packets.  Once we stop sending,
        we drop all outgoing packets until `failed` gets set back to `True`
        """
        nonlocal failed
        if not failed and random.random() < failure_probability:
            log_func("-----------SOCKET FAILURE. All outgoing packets will be dropped")
            failed = True

        if failed:
            log_func("-----------DROPPING {} bytes".format(len(buf)))
            return len(buf)
        else:
            count = old_sock_send(buf)
            log_func("---------- SENT {} bytes".format(count))
            return count

    @functools.wraps(old_sock_close)
    def new_sock_close():
        """
        Inside `sock_close`, we reset the `failed` variable to `False` to simulate the connection
        being "fixed" after the socket is re-opened
        """
        nonlocal failed
        if failed:
            log_func("-----------RESTORING SOCKET behavior")
            failed = False
        return old_sock_close()

    paho._sock_send = new_sock_send
    paho._sock_close = new_sock_close


def add_hook_drop_individual_outgoing(device_client, failure_probability, log_func=print):
    """
    Add a hook to randomly drop individual outgoing messages until reconnect based on some
    probability. This is used to simulate a "unreliable network" scenario where individual
    outgoing packets get dropped, but other packets continue to flow.
    """
    paho = logging_hook.get_paho_from_device_client(device_client)

    old_sock_send = paho._sock_send

    @functools.wraps(old_sock_send)
    def new_sock_send(buf):
        """
        Inside `sock_send` we randomly drop individual outgoing packets.
        """
        if random.random() < failure_probability:
            log_func("-----------DROPPING {} bytes".format(len(buf)))
            return len(buf)
        else:
            count = old_sock_send(buf)
            log_func("---------- SENT {} bytes".format(count))
            return count

    paho._sock_send = new_sock_send


def add_hook_drop_incoming_until_reconnect(device_client, failure_probability, log_func=print):
    """
    Add a hook to randomly drop all incoming messages until reconnect based on some failure
    probability. This is used to simulate a "connection drop" scenario where packets just stop
    being sent and the only way to recover is to close the socket and open a new one.
    """
    paho = logging_hook.get_paho_from_device_client(device_client)

    old_sock_recv = paho._sock_recv
    old_sock_close = paho._sock_close
    failed = False

    @functools.wraps(old_sock_recv)
    def new_sock_recv(buffsize):
        """
        Inside `sock_recv`, we randomly decide to stop receiving packets.  Once we stop receiving,
        we drop all incoming bytes until `failed` gets set back to `True`

        Note: `sock_send` gets called on a packet-by-packet basis, sending hundreds of bytes
        per call, and `sock_recv` gets called on a byte-by-byte basis, receiving a single byte
        at a time, the `failure_probability` value passed to this function needs to be much
        smaller than the `failure_probability` that might be used when fuzzing `sock_send`.
        """
        nonlocal failed
        if not failed and random.random() < failure_probability:
            log_func("-----------SOCKET FAILURE. All incoming packets will be dropped")
            failed = True

        buf = old_sock_recv(buffsize)

        if failed:
            log_func("-----------DROPPING {} bytes".format(len(buf)))
            raise BlockingIOError
        else:
            log_func("---------- RECEIVED {} bytes".format(len(buf)))
            return buf

    @functools.wraps(old_sock_close)
    def new_sock_close():
        """
        Inside `sock_close`, we reset the `failed` variable to `False` to simulate the connection
        being "fixed" after the socket is re-opened
        """
        nonlocal failed
        if failed:
            log_func("-----------RESTORING SOCKET behavior")
            failed = False
        return old_sock_close()

    paho._sock_recv = new_sock_recv
    paho._sock_close = new_sock_close


def add_hook_drop_individual_incoming(device_client, failure_probability, log_func=print):
    """
    Add a hook to randomly drop individual incoming messages until reconnect based on some
    failure probability. This is used to simulate a "unreliable network" scenario where individual
    outgoing packets get dropped, but other packets continue to flow.  Since we don't know what
    an "individual message" is when we're receiving, we just flush the incoming byte queue and
    assume that is good enough.
    """
    paho = logging_hook.get_paho_from_device_client(device_client)

    old_sock_recv = paho._sock_recv

    @functools.wraps(old_sock_recv)
    def new_sock_recv(buffsize):
        """
        Inside `sock_recv` we randomly flush the incoming packet queue to simulate dropping of
        a single packet, (or a small number of incoming packets depending on how quickly the
        incoming queue is handled).
        """
        if random.random() < failure_probability:
            buf = old_sock_recv(2048)
            log_func("---------- DROPPED {} bytes".format(len(buf)))
            raise BlockingIOError
        else:
            buf = old_sock_recv(buffsize)
            log_func("---------- RECEIVED {} bytes".format(len(buf)))
            return buf

    paho._sock_recv = new_sock_recv


def add_hook_raise_send_exception(device_client, failure_probability, log_func=print):
    """
    Add a hook to randomly raise an exception when sending based on some failure probability. This
    is used to simulate an exception inside Paho when sending.
    """
    paho = logging_hook.get_paho_from_device_client(device_client)

    old_sock_send = paho._sock_send

    @functools.wraps(old_sock_send)
    def new_sock_send(buf):
        if random.random() < failure_probability:
            log_func("---------- RAISING EXCEPTION")
            raise MyFakeException("Forced Send Failure")
        else:
            count = old_sock_send(buf)
            log_func("---------- SENT {} bytes".format(count))
            return count

    paho._sock_send = new_sock_send


def add_hook_raise_receive_exception(device_client, failure_probability, log_func=print):
    """
    Add a hook to randomly raise an exception when receiving based on some failure probability. This
    is used to simulate an exception inside Paho when receiving.
    """
    paho = logging_hook.get_paho_from_device_client(device_client)

    old_sock_recv = paho._sock_recv

    @functools.wraps(old_sock_recv)
    def new_sock_recv(buffsize):
        if random.random() < failure_probability:
            log_func("---------- RAISING EXCEPTION")
            raise MyFakeException("Forced Receive Failure")
        else:
            buf = old_sock_recv(buffsize)
            log_func("---------- RECEIVED {} bytes".format(len(buf)))
            return buf

    paho._sock_recv = new_sock_recv
