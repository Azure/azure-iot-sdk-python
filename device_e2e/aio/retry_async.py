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

# --------------------------------------
# Parameters for our back-off and jitter
# --------------------------------------

# Retry immediately after failure, or wait until after first delay?
IMMEDIATE_FIRST_RETRY = True

# Seconds to sleep for first sleep period. The exponential back-off will use
# 2x this number for the second sleep period, then 4x this number for the third
# period, then 8x and so on.
INITIAL_DELAY = 5

# Largest number of seconds to sleep between retries (before applying jitter)
MAXIMUM_DELAY = 60

# Number of seconds before an operation is considered "failed". This period starts before
# the first attempt and includes the elapsed time waiting between any failed attempts.
FAILURE_TIMEOUT = 5 * 60

# Jitter-up factor. The time, after jitter is applied, can be up this percentage larger than the
# pre-jittered time.
JITTER_UP_FACTOR = 0.25

# Jitter-down factor. The time, after jitter is applied, can be up this percentage smaller than the
# pre-jittered time.
JITTER_DOWN_FACTOR = 0.5

# Counter to keep track of running calls. We use this to distinguish between calls in logs.
running_call_index = 0
running_call_index_lock = threading.Lock()

# Retry stats. This is a dictionary of arbitrary values that we print to stdout at the of a
# test run.
retry_stats = {}
retry_stats_lock = threading.Lock()


def apply_jitter(base):
    """
    Apply a jitter that can be `JITTER_DOWN_FACTOR` percent smaller than the base up to
    `JITTER_UP_FACTOR` larger than the base.
    """
    min_value = base * (1 - JITTER_DOWN_FACTOR)
    max_value = base * (1 + JITTER_UP_FACTOR)
    return random.uniform(min_value, max_value)


def increment_retry_stat_count(key):
    """
    Increment a counter in the retry_stats dictionary
    """

    global retry_stats
    with retry_stats_lock:
        retry_stats[key] = retry_stats.get(key, 0) + 1


def reset_retry_stats():
    """
    reset retry stats between tests
    """
    global retry_stats
    retry_stats = {}


def get_type_name(obj):
    """
    Given an object, return the name of the type of that object. If `str(type(obj))` returns
    `"<class 'threading.Thread'>"`, this function returns `"threading.Thread"`.
    """
    try:
        return str(type(obj)).split("'")[1]
    except Exception:
        return str(type(obj))


async def retry_exponential_backoff_with_jitter(client, func, *args, **kwargs):
    """
    wrapper function to call a function with retry using exponential back-off with jitter.
    """
    global running_call_index, running_call_index_lock

    increment_retry_stat_count("retry_operation_total_count")
    increment_retry_stat_count("retry_operation{}".format(func.__name__))

    with running_call_index_lock:
        running_call_index += 1
        call_id = "retry_op_{}_".format(running_call_index)

    attempt = 1
    fail_time = time.time() + FAILURE_TIMEOUT

    logger.info(
        "retry: call {} started, call = {}({}, {}). Connecting".format(
            call_id, str(func), str(args), str(kwargs)
        )
    )

    while True:
        try:
            # If we're not connected, we should try connecting.
            if not client.connected:
                logger.info("retry: call {} reconnecting".format(call_id))
                await client.connect()

            logger.info("retry: call {} invoking".format(call_id))
            result = await func(*args, **kwargs)
            logger.info("retry: call {} successful".format(call_id))

            if attempt > 1:
                increment_retry_stat_count("success_after_{}_retries".format(attempt - 1))
            return result

        except (
            ConnectionFailedError,
            ConnectionDroppedError,
            OperationCancelled,
            NoConnectionError,
        ) as e:
            # These are all "retryable errors". If we've hit our maximum time, fail. If not,
            # sleep and try again.
            increment_retry_stat_count("retryable_error_{}".format(get_type_name(e)))

            if time.time() > fail_time:
                logger.info(
                    "retry; Call {} retry limit exceeded. Raising {}".format(
                        call_id, str(e) or type(e)
                    )
                )
                increment_retry_stat_count("final_error_{}".format(get_type_name(e)))
                raise

            # calculate how long to sleep based on our jitter parameters.
            if IMMEDIATE_FIRST_RETRY:
                if attempt == 1:
                    sleep_time = 0
                else:
                    sleep_time = INITIAL_DELAY * pow(2, attempt - 1)
            else:
                sleep_time = INITIAL_DELAY * pow(2, attempt)

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
            # This a "non-retryable" error. Don't retry. Just fail.
            increment_retry_stat_count("non_retryable_error_{}".format(type(e)))
            logger.info(
                "retry: Call {} raised non-retryable error {}".format(call_id, str(e) or type(e))
            )

            raise e
