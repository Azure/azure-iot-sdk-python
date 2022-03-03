# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import logging
import random
import threading
import time
from azure.iot.device.exceptions import (
    ConnectionFailedError,
    ConnectionDroppedError,
    OperationCancelled,
    NoConnectionError,
)

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

IMMEDIATE_FIRST_RETRY = True
INITIAL_DELAY = 5
MAXIMUM_DELAY = 60
FAILURE_TIMEOUT = 5 * 60
JITTER_UP_FACTOR = 0.25
JITTER_DOWN_FACTOR = 0.5


def apply_jitter(c):
    min_value = c * (1 - JITTER_DOWN_FACTOR)
    max_value = c * (1 + JITTER_UP_FACTOR)
    return random.uniform(min_value, max_value)


running_call_index = 0
running_call_index_lock = threading.Lock()

stats = {}
stats_lock = threading.Lock()


def increment_count(key):
    global stats
    with stats_lock:
        stats[key] = stats.get(key, 0) + 1


def get_type_name(obj):
    try:
        return str(type(obj)).split("'")[1]
    except Exception:
        return str(type(obj))


def reset_stats():
    global stats
    stats = {}


async def retry_exponential_backoff_with_jitter(client, func, *args, **kwargs):
    """
    wrapper function to call a function with retry.
    """
    global running_call_index, running_call_index_lock

    increment_count("retry_operation_total")
    increment_count("retry_operation_{}".format(func.__name__))

    attempt = 1
    fail_time = time.time() + FAILURE_TIMEOUT

    with running_call_index_lock:
        running_call_index += 1
        call_id = "retry_op_{}_".format(running_call_index)

    logger.info(
        "retry: call {} started, call = {}({}, {}). Connecting".format(
            call_id, str(func), str(args), str(kwargs)
        )
    )

    while True:
        try:
            # If we're not connected, we need to connect.
            if not client.connected:
                logger.info("retry: call {} reconnecting".format(call_id))
                await client.connect()

            logger.info("retry: call {} invoking".format(call_id))
            result = await func(*args, **kwargs)
            logger.info("retry: call {} successful".format(call_id))
            if attempt > 1:
                increment_count("success_after_{}_retries".format(attempt - 1))
            return result

        except (
            ConnectionFailedError,
            ConnectionDroppedError,
            OperationCancelled,
            NoConnectionError,
        ) as e:
            increment_count(get_type_name(e))
            if time.time() > fail_time:
                logger.info(
                    "retry; Call {} retry limit exceeded. Raising {}".format(
                        call_id, str(e) or type(e)
                    )
                )
                increment_count("Final-faulure-{}".format(get_type_name(e)))
                raise

            sleep_time = INITIAL_DELAY * (pow(2, attempt - 1) - 1)
            sleep_time = min(sleep_time, MAXIMUM_DELAY)
            sleep_time = apply_jitter(sleep_time)
            attempt += 1

            logger.info(
                "retry: Call {} attempt {} raised {}. Sleeping for {} and trying again".format(
                    call_id, attempt, str(e) or type(e), sleep_time
                )
            )

            await asyncio.sleep(sleep_time)
        except Exception as e:
            increment_count("Non-retry-{}".format(type(e)))
            logger.info(
                "retry: Call {} raised non-retriable error {}".format(call_id, str(e) or type(e))
            )
            raise e
