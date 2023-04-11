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

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

# When printing leaks, how many referrer levels do we print?
max_referrer_level = 5


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


def get_printable_object_name(obj):
    """
    Get a human-readable object name for our reports. This function tries to balance useful
    information (such as the `__repr__` of an object) with the shortest display (to make reports
    visually understandable). Since this text is only read by humans, it can be any for whatsoever.
    """
    try:
        if isinstance(obj, dict):
            return "{} Dict: first-5-keys={}".format(id(obj), list(obj.keys())[:10])
        else:
            return "{} {}: {}".format(id(obj), type(obj), str(obj))
    except TypeError:
        return "{} TypeError on {}".format(id(obj), type(obj))
    except ModuleNotFoundError:
        return "{} ModuleNotFoundError on {}".format(id(obj), type(obj))


class TrackedObject(object):
    """
    Object holding details on the leak of some tracked object.
    This object uses weak references so it doesn't change the behavior
    of the garbage collector by holding a reference to these objects.
    """

    def __init__(self, obj):
        self.object_id = id(obj)
        self.object_name = get_printable_object_name(obj)
        self.object_type = type(obj)

        try:
            self.weakref = weakref.ref(obj)
        except (ValueError, TypeError):
            # Some objects (like frame and dict) can't have weak references.
            # Keep track of it, but don't keep a weak reference.
            self.weakref = None

        if isinstance(obj, dict):
            self.dict = obj
        else:
            self.dict = None

    def __repr__(self):
        return self.object_name

    def __eq__(self, obj):
        if self.weakref or obj.weakref:
            return self.weakref == obj.weakref
        else:
            return self.object_id == obj.object_id

    def __hash__(self):
        return self.object_id

    def __ne__(self, obj):
        return not self == obj

    def get_object(self):
        if self.weakref:
            return self.weakref()
        elif self.dict:
            return self.dict
        elif self.object_id:
            return [x for x in gc.get_objects() if id(x) == self.object_id][0]


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
        self.filter_callback = None

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

        if self.filter_callback:
            remaining_objects = self.filter_callback(remaining_objects)

        if len(remaining_objects):
            self.dump_leak_report(remaining_objects)
        else:
            logger.info("No leaks")

    def dump_leak_report(self, leaked_objects):
        """
        Dump a report on leaked objects, including a list of what referrers to each leaked
        object.

        This prints leaked objects and the objects that are referring to them (keeping them
                alive) underneath, up to `max_referrer_level` levels deep.
        For example:

        ```
        A = Object()
        A.B = Object()
        A.B.C = Object()
        ```

        If C is marked as a leak, This will display
        ```
        ID(C) C
          ID(B) B
            ID(A) A
        ```
        Because `B` is keeping `C` alive, and `A` is keeping `B` alive.

        """

        logger.info("-----------------------------------------------")
        logger.error("Test failure.  {} objects have leaked:".format(len(leaked_objects)))
        logger.info("(Default text format is <id(obj) type(obj): str(obj)>")
        logger.info("Printing to {} levels deep".format(max_referrer_level))

        visited = set()

        all_objects = gc.get_objects()
        leaked_object_ids = [x.object_id for x in leaked_objects]

        # This is the function that recursively displays leaks and the objets that refer
        # to them.
        def visit(object, indent):
            line = f"{'  ' * indent} {get_printable_object_name(object)}"
            if indent > max_referrer_level:
                # Stop printing at `max_referrer_level` levels deep
                print(f"{line} (reached max depth)")
                return
            if id(object) == id(all_objects):
                # all_objects has a reference to all objects.  Stop if we reach it.
                return
            elif indent > 0 and id(object) in leaked_object_ids:
                # We've hit an object at the top level, but we're not at the top level.
                # this means one of our leaked objects is referring to another of our leaked objects.
                # Stop here.
                print(f"{line} (top-level leak)")
                return
            elif id(object) in visited:
                # stop if we've previously visited this object
                print(f"{line} (previously visited)")
                return
            elif str(type(object)) in ["<class 'list'>", "<class 'list_iterator'>"]:
                # stop at list or list_iterator objects. There are too many of these and
                # they don't provide any useful information.
                return
            else:
                print(f"{'  ' * indent} {get_printable_object_name(object)}")
                visited.add(id(object))
                for referrer in gc.get_referrers(object):
                    visit(referrer, indent + 1)

        for object in leaked_objects:
            visit(object.get_object(), 0)

        assert False, "Test failure.  {} objects have leaked:".format(len(leaked_objects))
