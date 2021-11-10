# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import threading
import math


class Measurements(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.peak_reconnect_time = 0
        self.peak_resident_memory_mb = 0
        self.peak_telemetry_arrival_time = 0
        self.queued_telemetry_messages = 0
        self.peak_queued_telemetry_messages = 0
        self.total_elapsed_time = 0


def round(x):
    """
    round up if the decimal part of x is >= .5, otherwise round down
    """
    return math.floor(x + 0.5)


def two_decimal_places(x):
    """
    round x to two decimal places
    """
    return round(x * 100) / 100


def print_measurements(measurements, name):
    """
    print stress measurements for logging at the end of a test run
    """
    print()
    if measurements:
        print("results for: {}".format(name))
        print(
            "    Peak telemetry arrival time:      {} seconds".format(
                two_decimal_places(measurements.peak_telemetry_arrival_time)
            )
        )
        print(
            "    Peak queued telemetry message:    {} messages".format(
                measurements.peak_queued_telemetry_messages
            )
        )
        print(
            "    Peak reconnect time:              {} seconds".format(
                two_decimal_places(measurements.peak_reconnect_time)
            )
        )
        if measurements.total_elapsed_time:
            print(
                "    Total elapsed time:               {} seconds".format(
                    two_decimal_places(measurements.total_elapsed_time)
                )
            )
        print(
            "    Peak resident memory:             {} MB".format(
                two_decimal_places(measurements.peak_resident_memory_mb)
            )
        )
    else:
        print("No results for {}".format(name))
    print()
