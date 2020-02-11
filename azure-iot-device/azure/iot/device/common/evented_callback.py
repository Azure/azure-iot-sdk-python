# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import threading
import logging
import six
import traceback

logger = logging.getLogger(__name__)


class EventedCallback(object):
    """
    A sync callback whose completion can be waited upon.
    """

    def __init__(self, return_arg_name=None):
        """
        Creates an instance of an EventedCallback.

        """
        # LBYL because this mistake doesn't cause an exception until the callback
        # which is much later and very difficult to trace back to here.
        if return_arg_name and not isinstance(return_arg_name, six.string_types):
            raise TypeError("internal error: return_arg_name must be a string")

        self.completion_event = threading.Event()
        self.exception = None
        self.result = None

        def wrapping_callback(*args, **kwargs):
            if "error" in kwargs and kwargs["error"]:
                self.exception = kwargs["error"]
            elif return_arg_name:
                if return_arg_name in kwargs:
                    self.result = kwargs[return_arg_name]
                else:
                    raise TypeError(
                        "internal error: excepected argument with name '{}', did not get".format(
                            return_arg_name
                        )
                    )

            if self.exception:
                # Do not use exc_info parameter on logger.error.  This casuses pytest to save the traceback which saves stack frames which shows up as a leak
                logger.error("Callback completed with error {}".format(self.exception))
                logger.error(traceback.format_exc())
            else:
                logger.debug("Callback completed with result {}".format(self.result))

            self.completion_event.set()

        self.callback = wrapping_callback

    def __call__(self, *args, **kwargs):
        """
        Calls the callback.
        """
        self.callback(*args, **kwargs)

    def wait_for_completion(self, *args, **kwargs):
        """
        Wait for the callback to be called, and return the results.
        """
        self.completion_event.wait(*args, **kwargs)

        if self.exception:
            raise self.exception
        else:
            return self.result
