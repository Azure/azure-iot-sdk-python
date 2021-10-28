# ref.inCopyright (c) Microsoft. All rights reserved.
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


def _dump_referrers(obj):
    referrers = gc.get_leaks_with_referrers(obj.weakref())
    for referrer in referrers:
        if isinstance(referrer, dict):
            print("  dict: {}".format(referrer))
            for sub_referrer in gc.get_leaks_with_referrers(referrer):
                if sub_referrer != referrers:
                    if not inspect.ismodule(sub_referrer):
                        print("    used by: {}:{}".format(type(sub_referrer), sub_referrer))
        elif not isinstance(referrer, type) and not inspect.ismodule(referrer):
            print("  used by: {}:{}".format(type(referrer), referrer))


class RefObject(object):
    """
    Object holding details on the leak of some tracked object
    """

    def __init__(self, obj):
        self.value = str(obj)
        self.weakref = weakref.ref(obj)

    def __repr__(self):
        return self.value

    def __eq__(self, obj):
        return self.weakref == obj.weakref

    def __ne__(self, obj):
        return not self == obj


class TrackedModule(object):
    def __init__(self, module_name):
        self.module_name = module_name
        mod = importlib.import_module(module_name)
        self.path = os.path.dirname(inspect.getsourcefile(mod))

    def is_module_object(self, obj):
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
    def __init__(self):
        self.tracked_modules = []
        self.baseline_objects = []

    def add_tracked_module(self, module_name):
        module = TrackedModule(module_name)
        logger.info("Tracking {} at path {}".format(module_name, module.path))
        self.tracked_modules.append(module)

    def _get_all_tracked_objects(self):
        """
        Query the garbage collector for a a list of all objects that
        are implemented in tracked libraries
        """
        all = []
        for obj in gc.get_objects():
            if any([mod.is_module_object(obj) for mod in self.tracked_modules]):
                source_file = inspect.getsourcefile(obj.__class__)
                try:
                    all.append(RefObject(obj))
                except TypeError:
                    logger.warning(
                        "Could not add {} from {} to leak list".format(obj.__class__, source_file)
                    )
        return all

    def set_baseline(self):
        self.baseline_objects = self._get_all_tracked_objects()

    def _remove_baseline_objects(self, all):
        """
        Return a filtered leak list with baseline objects are removed
        """

        new_list = []
        for obj in all:
            if obj not in self.baseline_objects:
                new_list.append(obj)

        return new_list

    def get_leaks(self):
        """
        Return a list of objects that are not part of the baseline
        """
        _run_garbage_collection()

        remaining_objects = self._get_all_tracked_objects()
        remaining_objects = self._remove_baseline_objects(remaining_objects)

        return remaining_objects

    def check_for_new_leaks(self):
        """
        Get all tracked objects from the garbage collector.  If any objects remain, list
        them and assert so the test fails.
        """
        remaining_objects = self.get_leaks()
        if len(remaining_objects):
            logger.error("Test failure.  {} objects have leaked:".format(len(remaining_objects)))
            leaks_with_referrers = self.get_leaks_with_referrers(remaining_objects)  # noqa: F841
            self.dump_leak_report(leaks_with_referrers)
            assert False
        else:
            logger.info("No leaks")

    def dump_leak_report(self, leaks_with_referrers):

        id_to_name_map = {}
        index = 0

        for leak in leaks_with_referrers:
            index = leak["index"]
            object_type = str(type(leak["obj"].weakref()))
            object_id = id(leak["obj"].weakref())
            id_to_name_map[object_id] = "Tracked object: {} (index={})".format(object_type, index)
            if hasattr(leak["obj"].weakref(), "__dict__"):
                dict_id = id(leak["obj"].weakref().__dict__)
                id_to_name_map[dict_id] = "Tracked object __dict__: {} (index={})".format(
                    object_type, index
                )

        for module_name, module in dict(sys.modules).items():
            object_id = id(sys.modules[module_name])
            dict_id = id(module.__dict__)
            id_to_name_map[object_id] = "Module: {}".format(module_name)
            id_to_name_map[dict_id] = "Module __dict__: {}".format(module_name)

        for obj in gc.get_objects():
            if hasattr(obj, "__dict__"):
                dict_id = id(obj.__dict__)
                if dict_id not in id_to_name_map:
                    id_to_name_map[dict_id] = "Untracked_object: {}.__dict__".format(type(obj))

        for leak in leaks_with_referrers:
            logger.info("object: {}".format(leak["obj"]))
            for referrer in leak["referrers"]:
                if isinstance(referrer, RefObject):
                    object_id = id(referrer.weakref())
                else:
                    object_id = id(referrer)
                if object_id in id_to_name_map:
                    logger.info("    {}".format(id_to_name_map[object_id]))
                else:
                    logger.info("    Non-object: {}".format(referrer))

    def get_leaks_with_referrers(self, objects):
        """
        Get all referrers for all objects as a way to see why objects are leaking.
        Meant to be run inside a debugger, probably using pprint on the output
        """
        leaks = []
        index = 0
        for obj in objects:
            referrers = []
            for ref in gc.get_referrers(obj.weakref()):
                if type(ref) in [dict]:
                    referrers.append(ref)
                else:
                    try:
                        referrers.append(RefObject(ref))
                    except TypeError:
                        referrers.append(str(ref))
            leaks.append({"index": index, "obj": obj, "referrers": referrers})
            index += 1
        return leaks
