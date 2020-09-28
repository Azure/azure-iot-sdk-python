# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
""" This module contains functions of managing event loops for the IoTHub client
"""
import asyncio
import threading
import logging
from azure.iot.device.common import asyncio_compat

logger = logging.getLogger(__name__)

loops = {
    "CLIENT_HANDLER_LOOP": None,
    "CLIENT_INTERNAL_LOOP": None,
    "CLIENT_HANDLER_RUNNER_LOOP": None,
}


def _cleanup():
    """Clear all running loops and end respective threads.
    ONLY FOR TESTING USAGE
    By using this function, you can wipe all global loops.
    DO NOT USE THIS IN PRODUCTION CODE
    """
    for loop_name, loop in loops.items():
        if loop is not None:
            logger.debug("Stopping event loop - {}".format(loop_name))
            loop.call_soon_threadsafe(loop.stop)
            # NOTE: Stopping the loop will also end the thread, because the only thing keeping
            # the thread alive was the loop running
            loops[loop_name] = None


def _make_new_loop(loop_name):
    logger.debug("Creating new event loop - {}".format(loop_name))
    # Create the loop on a new Thread
    new_loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=new_loop.run_forever)
    # Make the Thread a daemon so it will not block program exit
    loop_thread.daemon = True
    loop_thread.start()
    # Store the loop
    loops[loop_name] = new_loop


def get_client_internal_loop():
    """Return the loop for internal client operations"""
    if loops["CLIENT_INTERNAL_LOOP"] is None:
        _make_new_loop("CLIENT_INTERNAL_LOOP")
    return loops["CLIENT_INTERNAL_LOOP"]


def get_client_handler_runner_loop():
    """Return the loop for handler runners"""
    if loops["CLIENT_HANDLER_RUNNER_LOOP"] is None:
        _make_new_loop("CLIENT_HANDLER_RUNNER_LOOP")
    return loops["CLIENT_HANDLER_RUNNER_LOOP"]


def get_client_handler_loop():
    """Return the loop for invoking user-provided handlers on the client"""
    # TODO: Try and store the user loop somehow
    if loops["CLIENT_HANDLER_LOOP"] is None:
        _make_new_loop("CLIENT_HANDLER_LOOP")
    return loops["CLIENT_HANDLER_LOOP"]
