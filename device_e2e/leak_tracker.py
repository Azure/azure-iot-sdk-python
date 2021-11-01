# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.
import gc
import inspect
import os
import weakref
import time
import logging
import importlib
import json
import sys

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


def _run_garbage_collection():
    """
    Collect everything until there's nothing more to collect
    """
    sleep_time = 0.5
    done = False
    while not done:
        collected = gc.collect(2)
        logger.info("{} objects collected".format(collected))
        if collected:
            logger.info("Sleeping for {} seconds".format(sleep_time))
            time.sleep(sleep_time)
        else:
            done = True


class TrackedObject(object):
    """
    Object holding details on the leak of some tracked object.
    This object uses weak references so it doesn't change the behavior
    of the garbage collector by holding a reference to these objects.
    """

    def __init__(self, obj):
        self.object_name = str(obj)
        try:
            self.weakref = weakref.ref(obj)
        except ValueError:
            # Some objects (like frame and dict) can't have weak references.
            # Keep track of it, but don't keep a weak reference.
            self.weakref = None

    def __repr__(self):
        return self.object_name

    def __eq__(self, obj):
        if self.weakref or obj.weakref:
            return self.weakref == obj.weakref
        else:
            return self.object_name == obj.object_name

    def __ne__(self, obj):
        return not self == obj


class TrackedModule(object):
    """
    Object holding details for a module that we are tracking.
    """

    def __init__(self, module_name):
        self.module_name = module_name
        mod = importlib.import_module(module_name)
        self.path = os.path.dirname(inspect.getsourcefile(mod))

    def is_module_object(self, obj):
        """
        Return `True` if the given object is implemented in this module.
        """
        if not isinstance(obj, BaseException):
            try:
                c = obj.__class__
                source_file = inspect.getsourcefile(c)
            except (TypeError, AttributeError):
                pass
            else:
                if source_file and source_file.startswith(self.path):
                    return True

        return False


class LeakTracker(object):
    """
    Object which tracks leaked objects by recoding an "initial set of objects" at some point in
    time and then comparing this to the "current set of objects" at a later point in time.
    """

    def __init__(self):
        self.tracked_modules = []
        self.initial_set_of_objects = []

    def track_module(self, module_name):
        """
        Add a module with objects that we want to track.  If a module name is not
        passed as a "tracked module", then objects implemented in that module will
        not be tracked.
        """
        module = TrackedModule(module_name)
        logger.info("Tracking {} at path {}".format(module_name, module.path))
        self.tracked_modules.append(module)

    def _get_all_tracked_objects(self):
        """
        Query the garbage collector for a a list of all objects that
        are implemented in tracked modules
        """
        all = []
        for obj in gc.get_objects():
            if any([mod.is_module_object(obj) for mod in self.tracked_modules]):
                all.append(TrackedObject(obj))
        return all

    def set_initial_object_list(self):
        self.initial_set_of_objects = self._get_all_tracked_objects()

    def _remove_initial_objects_from_list(self, all):
        """
        Return a filtered leak list with baseline objects are removed
        """

        new_list = []
        for obj in all:
            if obj not in self.initial_set_of_objects:
                new_list.append(obj)

        return new_list

    def get_leaks(self):
        """
        Return a list of objects that are not part of the baseline
        """
        _run_garbage_collection()

        remaining_objects = self._get_all_tracked_objects()
        remaining_objects = self._remove_initial_objects_from_list(remaining_objects)

        return remaining_objects

    def check_for_leaks(self):
        """
        Get all tracked objects from the garbage collector.  If any objects remain, list
        them and assert so the test fails.
        """
        remaining_objects = self.get_leaks()
        if len(remaining_objects):
            logger.error("Test failure.  {} objects have leaked:".format(len(remaining_objects)))
            self.dump_leak_report(remaining_objects)
            assert False
        else:
            logger.info("No leaks")

    def dump_leak_report(self, leaked_objects):
        """
        Dump a report on leaked objects, including a list of what referrers to each leaked
        object.

        In order to display useful information on referrers, we need to do some ID-to-object
        mapping.  This is necessary because of the way the garbage collector keeps track of
        references between objects.

        To explain this, if we have object `a` that refers to object `b`:
            ```
            >>> class Object(object):
            ...   pass
            ...
            >>> a = Object()
            >>> b = Object()
            ```

        And `a` has a reference to `b`:
            ```
            >>> a.something = b
            ```

        This means that `a` has a reference to `b`, which meanms that `b` will not be collected
        until _after_ `a` is collected.  In other words. `a` is keeping `b` alive.

        You can see this by using `gc.get_referrers(b)` to see who refers to `b`.  But, If you do
        this, it will tell you that `a` does _not_ refer to `b`. Instead, it is `a.__dict__`
        that refers to `b`.

            ```
            >>> a in gc.get_referrers(b)
            False
            >>> a.__dict__ in gc.get_referrers(b)
            True
            ```

        This feels counterintuitive because, from your viewpoint, `a` does refer to `b`.
        However, from the garage collector's viewpoint, `a` refers to `a.__dict__` and `a.__dict__`
        refers to `b`.  In effect, `a` does refer to `b`, but it does so indirectly through
        `a.__dict__`:

            ```
            >>> a.__dict__ in gc.get_referrers(b)
            True
            >>> a in gc.get_referrers(a.__dict__)
            True
            ```

        If, however, object `a` uses `__slots__` to refer to `b`, then object `a` will refer
        to object `b` and `a.___dict__` will not exist.`

            ```
            >>> class ObjectWithSlots(object):
            ...     __slots__ = ["something"]
            ...
            >>> a = ObjectWithSlots()
            >>> b = Object()
            >>> a.something = b
            >>> a in gc.get_referrers(b)
            True
            >>> a.__dict__ in gc.get_referrers(b)
            Traceback (most recent call last):
              File "<stdin>", line 1, in <module>
            AttributeError: 'ObjectWithSlots' object has no attribute '__dict<'
            ```

        This can be complicated to keep track of.  So, to dump useful information, we use
        `id_to_name_map` to keep track of the relationship between `a` and `a.__dict__`.
        In effect:

            ```
            id_to_name_map[id(a)] = str(a)
            id_to_name_map[id(a.__dict__)] = str(a)
            ```

        With this mapping, we can show that `a` refers to `b`, even when it is `a.__dict__` that is
        refering to `b`.

        Phew.
        """

        id_to_name_map = {}
        index = 0

        # first, map IDs for leaked objects.  We display these slightly differently because it
        # makes tracking inter-leak references a little easier.
        for leak in leaked_objects:
            object_name = leak.object_name

            object_id = id(leak.weakref())
            id_to_name_map[object_id] = "Tracked object: {} (index={})".format(object_name, index)

            if hasattr(leak.weakref(), "__dict__"):
                dict_id = id(leak.weakref().__dict__)
                id_to_name_map[dict_id] = "Tracked object __dict__: {} (index={})".format(
                    object_name, index
                )

            index += 1

        # Second, map IDs for all other objects (unless we've mapped them already).  This might
        # be overkill, but it gives us the most information.
        for obj in gc.get_objects():
            object_id = id(obj)
            if object_id not in id_to_name_map:
                id_to_name_map[object_id] = "Untracked_object: {}".format(type(obj))

            if hasattr(obj, "__dict__"):
                dict_id = id(obj.__dict__)
                if dict_id not in id_to_name_map:
                    id_to_name_map[dict_id] = "Untracked_object: {}.__dict__".format(type(obj))

        for leak in leaked_objects:
            logger.info("object: {}".format(leak.object_name))
            for referrer in gc.get_referrers(leak):
                object_id = id(referrer)
                if object_id in id_to_name_map:
                    logger.info("    referred by: {}".format(id_to_name_map[object_id]))
                else:
                    logger.info("    referred by Non-object: {}".format(referrer))
