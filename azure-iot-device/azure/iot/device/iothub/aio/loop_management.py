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
    # Store whatever loop the user has on their thread the client was created in.
    # We can use this to schedule tasks for their handler/callback code so that any
    # poor performance in their provided code doesn't slow down the client.
    # TODO: store the user loop somehow
    "USER_LOOP": None,
    "CLIENT_INTERNAL_LOOP": None,
    "CLIENT_HANDLER_RUNNER_LOOP": None,
}


def _cleanup():
    """Clear all running loops and end respective threads.
    Does not clear the USER_LOOP.
    ONLY FOR TESTING USAGE
    By using this function, you can wipe all global loops.
    DO NOT USE THIS IN PRODUCTION CODE
    """
    for loop_name, loop in loops.items():
        if loop_name == "USER_LOOP":
            # Do not clean up the USER_LOOP since it wasn't made by us
            # TODO: there may be something necessary here once user loops are in play
            continue
        elif loop is not None:
            loop.call_soon_threadsafe(loop.stop())
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
