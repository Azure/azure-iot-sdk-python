# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from threading import Thread, Event
import time


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
        Will invoke the Alarm's given function at the given alarm time.
        """
        interval = self.alarm_time - time.time()
        self.finished.wait(interval)
        if not self.finished.is_set():
            self.function(*self.args, **self.kwargs)
        self.finished.set()
