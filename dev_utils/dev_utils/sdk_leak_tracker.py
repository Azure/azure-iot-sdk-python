# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

from .leak_tracker import LeakTracker

TRACKED_MODULES = ("azure.iot.device", "paho")


def create_tracker(filter_callback=None):
    tracker = LeakTracker()
    for module_name in TRACKED_MODULES:
        tracker.track_module(module_name)
    tracker.filter_callback = filter_callback
    return tracker
