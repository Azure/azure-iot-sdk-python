# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from threading import Thread, Event
import time

# NOTE: The Alarm class is very similar, but fundamentally different from threading.Timer.
# Beyond just the input format difference (a specific time for Alarm vs. an interval for Timer),
# the manner in which they keep time is different. A Timer will only tick towards its interval
# while the system is running, but an Alarm will go off at a specific time, so system sleep will
# not throw off the timekeeping. In the case that the Alarm time occurs while the system is asleep
# the Alarm will trigger upon system wake.


class Alarm(Thread):
    """Call a function at a specified time"""

    def __init__(self, alarm_time, function, args=None, kwargs=None):
        Thread.__init__(self)
        self.alarm_time = alarm_time
        self.function = function
        self.args = args if args is not None else []
        self.kwargs = kwargs if kwargs is not None else {}
        self.finished = Event()

    def cancel(self):
        """Stop the alarm if it hasn't finished yet."""
        self.finished.set()

    def run(self):
        """Method representing the thread's activity.
        Overrides the method inherited from Thread.
        Will invoke the Alarm's given function at the given alarm time (accurate within 1 second)
        """
        while not self.finished.is_set() and time.time() < self.alarm_time:
            self.finished.wait(1)

        if not self.finished.is_set():
            self.function(*self.args, **self.kwargs)
        self.finished.set()
