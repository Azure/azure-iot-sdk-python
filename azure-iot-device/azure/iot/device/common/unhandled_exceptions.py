# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging

logger = logging.getLogger(__name__)


def exception_caught_in_background_thread(e):
    """
    Function which handled exceptions that are caught in background thread.  This is
    typically called from the callback thread inside the pipeline.  These exceptions
    need special handling because callback functions are typically called inside a
    non-application thread in response to non-user-initiated actions, so there's
    nobody else to catch them.

    This function gets called from inside an arbitrary thread context, so code that
    runs from this function should be limited to the bare minumum.

    :param Error e: Exception object raised from inside a background thread
    """

    # @FUTURE: We should add a mechanism which allows applications to receive these
    # exceptions so they can respond accordingly
    logger.error(msg="Exception caught in background thread.  Unable to handle.", exc_info=e)
