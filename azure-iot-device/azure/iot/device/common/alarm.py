# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from threading import Thread, Event
import time


# class Alarm(Thread):
#     """Call a function at a specified time"""

#     def __init__(self, alarm_time, function, args=None, kwargs=None):
#         Thread.__init__(self)
#         self.alarm_time = alarm_time
#         self.function = function
#         self.args = args if args is not None else []
#         self.kwargs = kwargs if kwargs is not None else {}
#         self.finished = Event()

#     def cancel(self):
#         """Stop the alarm if it hasn't finished yet."""
#         self.finished.set()

#     #     def run(self):
#     #         """Method representing the thread's activity.
#     #         Overrides the method inherited from Thread.
#     #         Will invoke the Alarm's given function at the given alarm time.
#     #         """
#     #         while not self.finished.is_set():
#     #             curr_time = time.time()
#     #             if curr_time >= self.alarm_time:
#     #                 self.function(*self.args, **self.kwargs)
#     #                 self.finished.set()
#     #                 break
#     #             else:
#     #                 time.sleep(1)

#     # def run(self):
#     #     """Method representing the thread's activity.
#     #     Overrides the method inherited from Thread.
#     #     Will invoke the Alarm's given function at the given alarm time.
#     #     """
#     #     interval = self.alarm_time - time.time()
#     #     self.finished.wait(interval)
#     #     if not self.finished.is_set():
#     #         self.function(*self.args, **self.kwargs)
#     #     self.finished.set()


class Alarm(Thread):
    """Call a function after a specified number of seconds:

            t = Timer(30.0, f, args=None, kwargs=None)
            t.start()
            t.cancel()     # stop the timer's action if it's still waiting

    """

    def __init__(self, interval, function, args=None, kwargs=None):
        Thread.__init__(self)
        self.interval = interval
        self.function = function
        self.args = args if args is not None else []
        self.kwargs = kwargs if kwargs is not None else {}
        self.finished = Event()

    def cancel(self):
        """Stop the timer if it hasn't finished yet."""
        self.finished.set()

    def run(self):
        self.finished.wait(self.interval)
        if not self.finished.is_set():
            self.function(*self.args, **self.kwargs)
        self.finished.set()
