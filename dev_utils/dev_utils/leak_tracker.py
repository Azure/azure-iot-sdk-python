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
            return "Dict ID={}: first-5-keys={}".format(id(obj), list(obj.keys())[:10])
        else:
            return "{}: {}".format(type(obj), str(obj))
    except TypeError:
        return "Foreign object (raised TypeError): {}, ID={}".format(type(obj), id(obj))
    except ModuleNotFoundError:
        return "Foreign object (raised ModuleNotFoundError): {}, ID={}".format(type(obj), id(obj))


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
        else:
            return self.dict


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

        This means that `a` has a reference to `b`, which means that `b` will not be collected
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
        referring to `b`.

        Phew.
        """

        logger.info("-----------------------------------------------")
        logger.error("Test failure.  {} objects have leaked:".format(len(leaked_objects)))
        logger.info("(Default text format is <type(obj): str(obj)>")

        id_to_name_map = {}

        # first, map IDs for leaked objects.  We display these slightly differently because it
        # makes tracking inter-leak references a little easier.
        for leak in leaked_objects:
            id_to_name_map[leak.object_id] = leak

            # if the object has a `__dict__` attribute, then map the ID of that dictionary
            # back to the object also.
            if leak.get_object() and hasattr(leak.get_object(), "__dict__"):
                dict_id = id(leak.get_object().__dict__)
                id_to_name_map[dict_id] = leak

        # Second, go through all objects and map IDs for those (unless we've done them already).
        # In this step, we add mappings for objects and their `__dict__` attributes, but we
        # don't add `dict` objects yet. This is because we don't know if any `dict` is a user-
        # created dictionary or if it's a `__dict__`.  If it's a `__dict__`, we add it here and
        # point it to the owning object.  If it's just a `dict`, we add it in the last loop
        # through
        for obj in gc.get_objects():
            object_id = id(obj)

            if not isinstance(obj, dict):
                if object_id not in id_to_name_map:
                    id_to_name_map[object_id] = TrackedObject(obj)

                if hasattr(obj, "__dict__"):
                    dict_id = id(obj.__dict__)
                    if dict_id not in id_to_name_map:
                        id_to_name_map[dict_id] = id_to_name_map[object_id]

        # Third, map IDs for all dicts that we haven't done yet.
        for obj in gc.get_objects():
            object_id = id(obj)

            if isinstance(obj, dict):
                if object_id not in id_to_name_map:
                    id_to_name_map[object_id] = TrackedObject(obj)

        already_reported = set()
        objects_to_report = leaked_objects.copy()

        # keep track of all 3 generations in handy local variables.  These are here
        # for developers who might be looking at leaks inside of pdb.
        gen0 = []
        gen1 = []
        gen2 = []

        for generation_storage, generation_name in [
            (gen0, "generation 0: objects that leaked"),
            (gen1, "generation 1: objects that refer to leaked objects"),
            (gen2, "generation 2: objects that refer to generation 1"),
        ]:
            next_set_of_objects_to_report = set()
            if len(objects_to_report):
                logger.info("-----------------------------------------------")
                logger.info(generation_name)

                # Add our objects to our generation-specific list. This helps
                # developers looking at bugs inside pdb because they can just look
                # at `gen0[0].get_object()` to see the first leaked object, etc.
                generation_storage.extend(objects_to_report)

                for obj in objects_to_report:
                    if obj in already_reported:
                        logger.info("already reported: {}".format(obj.object_name))
                    else:
                        logger.info("object: {}".format(obj.object_name))
                        if not obj.get_object():
                            logger.info("    not recursing")
                        else:
                            for referrer in gc.get_referrers(obj.get_object()):
                                if (
                                    isinstance(referrer, dict)
                                    and referrer.get("dict", None) == obj.get_object()
                                ):
                                    # This is the dict from a TrackedObject object.  Skip it.
                                    pass
                                else:
                                    object_id = id(referrer)
                                    if object_id in id_to_name_map:
                                        logger.info(
                                            "    referred by: {}".format(id_to_name_map[object_id])
                                        )
                                        next_set_of_objects_to_report.add(id_to_name_map[object_id])
                                    else:
                                        logger.info(
                                            "    referred by Non-object: {}".format(
                                                get_printable_object_name(referrer)
                                            )
                                        )
                        already_reported.add(obj)

                logger.info(
                    "Total: {} objects, referred to by {} objects".format(
                        len(objects_to_report), len(next_set_of_objects_to_report)
                    )
                )
                objects_to_report = next_set_of_objects_to_report

        logger.info("-----------------------------------------------")
        logger.info("Leaked objects are available in local variables: gen0, gen1, and gen2")
        logger.info("for the 3 generations of leaks. Use the get_object method to retrieve")
        logger.info("the actual objects")
        logger.info("eg: us gen0[0].get_object() to get the first leaked object")
        logger.info("-----------------------------------------------")
        assert False, "Test failure.  {} objects have leaked:".format(len(leaked_objects))
