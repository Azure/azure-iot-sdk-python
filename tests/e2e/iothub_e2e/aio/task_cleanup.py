# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import logging

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


async def cleanup_tasks(task_list):
    """
    Go through a task list and retrieve all task results.  This prevents any "Task result was
    never retrieved" errors, especially when a test fails and the test script doesn't get a
    chance to gather all the task results.
    """

    tasks_left = len(task_list)
    logger.info("-------------------------")
    logger.info("Cleaning up {} tasks".format(tasks_left))
    logger.info("-------------------------")

    for task_result in asyncio.as_completed(task_list, timeout=600):
        try:
            await task_result
            tasks_left -= 1
        except asyncio.TimeoutError:
            logger.error(
                "Task cleanup timeout with {} tasks remaining incomplete".format(tasks_left)
            )
            raise
        except Exception as e:
            logger.error("Cleaning up task that failed with [{}]".format(str(e) or type(e)))
            tasks_left -= 1

    logger.info("-------------------------")
    logger.info("Done cleaning up tasks")
    logger.info("-------------------------")
