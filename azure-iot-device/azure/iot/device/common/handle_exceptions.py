# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import traceback

logger = logging.getLogger(__name__)


def handle_background_exception(e):
    """
    Function which handled exceptions that are caught in background thread.  This is
    typically called from the callback thread inside the pipeline.  These exceptions
    need special handling because callback functions are typically called inside a
    non-application thread in response to non-user-initiated actions, so there's
    nobody else to catch them.

    This function gets called from inside an arbitrary thread context, so code that
    runs from this function should be limited to the bare minimum.

    :param Error e: Exception object raised from inside a background thread
    """

    # @FUTURE: We should add a mechanism which allows applications to receive these
    # exceptions so they can respond accordingly
    logger.warning(msg="Exception caught in background thread.  Unable to handle.")
    logger.warning(traceback.format_exception_only(type(e), e))


def swallow_unraised_exception(e, log_msg=None, log_lvl="warning"):
    """Swallow and log an exception object.

    Convenience function for logging, as exceptions can only be logged correctly from within a
    except block.

    :param Exception e: Exception object to be swallowed.
    :param str log_msg: Optional message to use when logging.
    :param str log_lvl: The log level to use for logging. Default "warning".
    """
    try:
        raise e
    except Exception:
        if log_lvl == "warning":
            logger.warning(log_msg)
            logger.warning(traceback.format_exc())
        elif log_lvl == "error":
            logger.error(log_msg)
            logger.error(traceback.format_exc())
        elif log_lvl == "info":
            logger.info(log_msg)
            logger.info(traceback.format_exc())
        else:
            logger.debug(log_msg)
            logger.debug(traceback.format_exc())
