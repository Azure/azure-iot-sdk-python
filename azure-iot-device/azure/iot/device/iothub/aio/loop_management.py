# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains functions of managing event loops for the IoTHub client"""

import asyncio
import threading
import logging

logger = logging.getLogger(__name__)

loops = {
    "CLIENT_HANDLER_LOOP": None,
    "CLIENT_INTERNAL_LOOP": None,
    "CLIENT_HANDLER_RUNNER_LOOP": None,
}
# Janus queues bind to the first loop they use, so concurrent callers must receive the same loop.
_loop_creation_lock = threading.Lock()


def _cleanup():
    """Clear all running loops and end respective threads.
    ONLY FOR TESTING USAGE
    By using this function, you can wipe all global loops.
    Do not call while clients or inboxes are still in use.
    DO NOT USE THIS IN PRODUCTION CODE
    """
    with _loop_creation_lock:
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


def _get_or_create_loop(loop_name):
    loop = loops[loop_name]
    if loop is None:
        with _loop_creation_lock:
            # Another caller may have created the loop while this caller waited for the lock.
            loop = loops[loop_name]
            if loop is None:
                _make_new_loop(loop_name)
                loop = loops[loop_name]
    return loop


def get_client_internal_loop():
    """Return the loop for internal client operations"""
    return _get_or_create_loop("CLIENT_INTERNAL_LOOP")


def get_client_handler_runner_loop():
    """Return the loop for handler runners"""
    return _get_or_create_loop("CLIENT_HANDLER_RUNNER_LOOP")


def get_client_handler_loop():
    """Return the loop for invoking user-provided handlers on the client"""
    # TODO: Try and store the user loop somehow
    return _get_or_create_loop("CLIENT_HANDLER_LOOP")
