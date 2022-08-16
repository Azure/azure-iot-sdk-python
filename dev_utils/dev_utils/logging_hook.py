# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import functools
import inspect
import threading


# List of Paho functions to add logging to
PAHO_FUNCTIONS_TO_HOOK = {
    "connect": True,
    "disconnect": True,
    "enable_logger": True,
    "loop_start": True,
    "loop_stop": True,
    "on_connect": True,
    "on_disconnect": True,
    "on_message": True,
    "on_publish": True,
    "on_subscribe": True,
    "on_unsubscribe": True,
    "proxy_set": True,
    "publish": True,
    "reconnect_delay_set": True,
    "subscribe": True,
    "tls_set_context": True,
    "unsubscribe": True,
    "username_pw_set": False,
    "ws_set_options": True,
}


# List of device/module client functions to add logging to
DEVICE_CLIENT_FUNCTIONS_TO_HOOK = {
    "shutdown": True,
    "connect": True,
    "disconnect": True,
    "update_sastoken": True,
    "send_message": True,
    "receive_method_request": True,
    "send_method_response": True,
    "get_twin": True,
    "patch_twin_reported_properties": True,
}


# lock for synchronizing multithreaded access to call_index and indent_count
global_lock = threading.Lock()
# running count of calls that are being logged.  Included with the log output so readers can match calls and returns
call_index = 0
# count of indent levels for calls. Used to indent logs so calls and returns can be visually matched.
indent_count = 0


def _get_next_call_index():
    """
    Get an index for function calls where each function call gets a new index #. This can be used
    to correlate calls with return.
    """
    global global_lock, call_index
    with global_lock:
        call_index += 1
        return call_index


def _indent():
    """
    increment the indent and return a string that can be used for indenting logging lines.
    """
    global global_lock, indent_count
    with global_lock:
        indent_count += 1
        return "  " * indent_count


def _unindent():
    """
    decrement the indent and return a string that can be used for indenting logging lines.
    """
    global global_lock, indent_count
    with global_lock:
        ret = "  " * indent_count
        indent_count -= 1
        return ret


def add_logging_hook(obj, func_name, log_func, module_name, log_args=True):
    """
    Add a logging hook to the given method
    """

    def log_call(index, args, kwargs):
        if log_args:
            log_func(
                "{indent}{module_name}-{index}: calling {func_name} with {args}, {kwargs}".format(
                    indent=_indent(),
                    module_name=module_name,
                    index=index,
                    func_name=func_name,
                    args=args,
                    kwargs=kwargs,
                )
            )
        else:
            log_func(
                "{indent}{module_name}-{index}: calling {func_name} with <REDACTED>".format(
                    indent=_indent(), module_name=module_name, index=index, func_name=func_name
                )
            )

    def log_return(index, ret):
        log_func(
            "{indent}{module_name}-{index}: {func_name} returned {ret}".format(
                indent=_unindent(),
                module_name=module_name,
                index=index,
                func_name=func_name,
                ret=ret,
            )
        )

    def log_exception(index, e):
        log_func(
            "{indent}{module_name}-{index}: {func_name} RAISED {exc}".format(
                indent=_unindent(),
                module_name=module_name,
                index=index,
                func_name=func_name,
                exc=str(e) or type(e),
            )
        )

    func_or_coro = getattr(obj, func_name)

    if (
        inspect.isawaitable(func_or_coro)
        or inspect.iscoroutine(func_or_coro)
        or inspect.iscoroutinefunction(func_or_coro)
    ):

        @functools.wraps(func_or_coro)
        async def coro_wrapper(*args, **kwargs):
            index = _get_next_call_index()
            log_call(index, args, kwargs)
            try:
                ret = await func_or_coro(*args, **kwargs)
            except Exception as e:
                log_exception(index, e)
                raise
            else:
                log_return(index, ret)
                return ret

        setattr(obj, func_name, coro_wrapper)
    else:

        @functools.wraps(func_or_coro)
        def func_wrapper(*args, **kwargs):
            index = _get_next_call_index()
            log_call(index, args, kwargs)
            try:
                ret = func_or_coro(*args, **kwargs)
            except Exception as e:
                log_exception(index, e)
                raise
            else:
                log_return(index, ret)
                return ret

        setattr(obj, func_name, func_wrapper)


def get_paho_from_device_client(device_client):
    pipeline_root = device_client._mqtt_pipeline._pipeline
    stage = pipeline_root
    while stage.next:
        stage = stage.next
    return stage.transport._mqtt_client


def hook_device_client(device_client, log_func=print):
    """
    Add logging to the given device client object.
    """
    paho = get_paho_from_device_client(device_client)

    for name in PAHO_FUNCTIONS_TO_HOOK:
        add_logging_hook(
            obj=paho,
            func_name=name,
            log_func=log_func,
            module_name="Paho",
            log_args=PAHO_FUNCTIONS_TO_HOOK[name],
        )

    for name in DEVICE_CLIENT_FUNCTIONS_TO_HOOK:
        add_logging_hook(
            obj=device_client,
            func_name=name,
            log_func=log_func,
            module_name="device_client",
            log_args=DEVICE_CLIENT_FUNCTIONS_TO_HOOK[name],
        )
