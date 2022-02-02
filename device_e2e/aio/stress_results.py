# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import threading
import math


class Measurements(object):
    """Object which defines the measurements we take durring a stress test"""

    def __init__(self):
        self.lock = threading.Lock()
        self.peak_reconnect_time = 0
        self.peak_resident_memory_mb = 0
        self.peak_telemetry_arrival_time = 0
        self.telemetry_messages_in_queue = 0
        self.peak_telemetry_messages_in_queue = 0
        self.total_elapsed_time = 0
        self.test_exception = None


def print_measurements(measurements, name):
    """
    print stress measurements for logging at the end of a test run
    """
    print()
    if measurements:
        print("results for: {}".format(name))
        if measurements.test_exception:
            print(
                "    RESULT:                           FAILED ({})".format(
                    measurements.test_exception
                )
            )
        else:
            print("    RESULT:                           PASSED")
        print(
            "    Peak telemetry arrival time:      {} seconds".format(
                round(measurements.peak_telemetry_arrival_time, 2)
            )
        )
        print(
            "    Peak telemetry messages in queue: {} messages".format(
                measurements.peak_telemetry_messages_in_queue
            )
        )
        print(
            "    Peak reconnect time:              {} seconds".format(
                round(measurements.peak_reconnect_time, 2)
            )
        )
        if measurements.total_elapsed_time:
            print(
                "    Total elapsed time:               {} seconds".format(
                    round(measurements.total_elapsed_time, 2)
                )
            )
        print(
            "    Peak resident memory:             {} MB".format(
                round(measurements.peak_resident_memory_mb, 2)
            )
        )
    else:
        print("No results for {}".format(name))
    print()
