# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import functools
import logging
import threading
import traceback
from multiprocessing.pool import ThreadPool
from concurrent.futures import ThreadPoolExecutor
from azure.iot.device.common import handle_exceptions

logger = logging.getLogger(__name__)

"""
This module contains decorators that are used to marshal code into pipeline and
callback threads and to assert that code is being called in the correct thread.

The intention of these decorators is to ensure the following:

1. All pipeline functions execute in a single thread, known as the "pipeline
  thread".  The `invoke_on_pipeline_thread` and `invoke_on_pipeline_thread_nowait`
  decorators cause the decorated function to run on the pipeline thread.

2. If the pipeline thread is busy running a different function, the invoke
  decorators will wait until that function is complete before invoking another
  function on that thread.

3. There is a different thread which is used for callbacks into user code, known
  as the the "callback thread".  This is not meant for callbacks into pipeline
  code.  Those callbacks should still execute on the pipeline thread.  The
  `invoke_on_callback_thread_nowait` decorator is used to ensure that callbacks
  execute on the callback thread.

4. Decorators which cause thread switches are used only when necessary.  The
  pipeline thread is only entered in places where we know that external code is
  calling into the pipeline (such as a client API call or a callback from a
  third-party library).  Likewise, the callback thread is only entered in places
  where we know that the pipeline is calling back into client code.

5. Exceptions raised from the pipeline thread are still able to be caught by
  the function which entered the pipeline thread.

5. Calls into the pipeline thread can either block or not block.  Blocking is used
  for cases where the caller needs a return value from the pipeline or is
  expecting to handle any errors raised from the pipeline thread.  Blocking is
  not used when the code calling into the pipeline is not waiting for a response
  and is not expecting to handle any exceptions, such as protocol library
  handlers which call into the pipeline to deliver protocol messages.

6. Calls into the callback thread could theoretically block, but we currently
  only have decorators which enter the callback thread without blocking.  This
  is done to ensure that client code does not execute on the pipeline thread and
  also to ensure that the pipline thread is not blocked while waiting for client
  code to execute.

These decorators use concurrent.futures.Future and the ThreadPoolExecutor because:

1. The thread pooling with a pool size of 1 gives us a single thread to run all
  pipeline operations and a different (single) thread to run all callbacks.  If
  the code attempts to run a second pipeline operation (or callback) while a
  different one is running, the ThreadPoolExecutor will queue the code until the
  first call is completed.

2. The concurent.futures.Future object properly handles both Exception and
  BaseException errors, re-raising them when the Future.result method is called.
  threading.Thread.get() was not an option because it doesn't re-raise
  BaseException errors when Thread.get is called.

3. concurrent.futures is available as a backport to 2.7.

"""

_executors = {}


def _get_named_executor(thread_name):
    """
    Get a ThreadPoolExecutor object with the given name.  If no such executor exists,
    this function will create on with a single worker and assign it to the provided
    name.
    """
    global _executors
    if thread_name not in _executors:
        logger.debug("Creating {} executor".format(thread_name))
        _executors[thread_name] = ThreadPoolExecutor(max_workers=1)
    return _executors[thread_name]


def _invoke_on_executor_thread(func, thread_name, block=True):
    """
    Return wrapper to run the function on a given thread.  If block==False,
    the call returns immediately without waiting for the decorated function to complete.
    If block==True, the call waits for the decorated function to complete before returning.
    """

    # Mocks on py27 don't have a __name__ attribute.  Use str() if you can't use __name__
    try:
        function_name = func.__name__
        function_has_name = True
    except AttributeError:
        function_name = str(func)
        function_has_name = False

    def wrapper(*args, **kwargs):
        if threading.current_thread().name is not thread_name:
            logger.debug("Starting {} in {} thread".format(function_name, thread_name))

            def thread_proc():
                threading.current_thread().name = thread_name
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if not block:
                        handle_exceptions.handle_background_exception(e)
                    else:
                        raise
                except BaseException:
                    if not block:
                        logger.error("Unhandled exception in background thread")
                        logger.error(
                            "This may cause the background thread to abort and may result in system instability."
                        )
                        traceback.print_exc()
                    raise

            # TODO: add a timeout here and throw exception on failure
            future = _get_named_executor(thread_name).submit(thread_proc)
            if block:
                return future.result()
            else:
                return future
        else:
            logger.debug("Already in {} thread for {}".format(thread_name, function_name))
            return func(*args, **kwargs)

    # Silly hack:  On 2.7, we can't use @functools.wraps on callables don't have a __name__ attribute
    # attribute(like MagicMock object), so we only do it when we have a name.  functools.update_wrapper
    # below is the same as using the @functools.wraps(func) decorator on the wrapper function above.
    if function_has_name:
        return functools.update_wrapper(wrapped=func, wrapper=wrapper)
    else:
        wrapper.__wrapped__ = func  # needed by tests
        return wrapper


def invoke_on_pipeline_thread(func):
    """
    Run the decorated function on the pipeline thread.
    """
    return _invoke_on_executor_thread(func=func, thread_name="pipeline")


def invoke_on_pipeline_thread_nowait(func):
    """
    Run the decorated function on the pipeline thread, but don't wait for it to complete
    """
    return _invoke_on_executor_thread(func=func, thread_name="pipeline", block=False)


def invoke_on_callback_thread_nowait(func):
    """
    Run the decorated function on the callback thread, but don't wait for it to complete
    """
    return _invoke_on_executor_thread(func=func, thread_name="callback", block=False)


def invoke_on_http_thread_nowait(func):
    """
    Run the decorated function on the callback thread, but don't wait for it to complete
    """
    # TODO: Refactor this since this is not in the pipeline thread anymore, so we need to pull this into common.
    # Also, the max workers eventually needs to be a bigger number, so that needs to be fixed to allow for more than one HTTP Request a a time.
    return _invoke_on_executor_thread(func=func, thread_name="azure_iot_http", block=False)


def _assert_executor_thread(func, thread_name):
    """
    Decorator which asserts that the given function only gets called inside the given
    thread.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):

        assert (
            threading.current_thread().name == thread_name
        ), """
            Function {function_name} is not running inside {thread_name} thread.
            It should be. You should use invoke_on_{thread_name}_thread(_nowait) to enter the
            {thread_name} thread before calling this function.  If you're hitting this from
            inside a test function, you may need to add the fake_pipeline_thread fixture to
            your test.  (generally applied on the global pytestmark in a module) """.format(
            function_name=func.__name__, thread_name=thread_name
        )

        return func(*args, **kwargs)

    return wrapper


def runs_on_pipeline_thread(func):
    """
    Decorator which marks a function as only running inside the pipeline thread.
    """
    return _assert_executor_thread(func=func, thread_name="pipeline")


def runs_on_http_thread(func):
    """
    Decorator which marks a function as only running inside the http thread.
    """
    return _assert_executor_thread(func=func, thread_name="azure_iot_http")
