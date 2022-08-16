# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from subprocess import check_call

this_file_path = os.path.dirname(os.path.realpath(__file__))

failures = []


def run_test_app(relative_app_name, timeout):
    absolute_app = os.path.join(this_file_path, relative_app_name)

    try:
        print("+-" * 66)
        print()
        print("Running test app: {}".format(absolute_app))
        check_call([sys.executable] + absolute_app.split(), timeout=timeout)
        print("Test app {} SUCCEEDED".format(absolute_app))

    except Exception as err:
        print(err)
        print("Test app {} FAILED".format(absolute_app))
        failures.push("{} failed with {}".format(relative_app_name, str(err) or type(err)))

    print()
    print("+-" * 66)
    print()
    print()


if __name__ == "__main__":
    run_test_app("./simple_stress/simple_send_message_bulk.py", timeout=600)
    run_test_app("./regressions/regression_pr_1023_infinite_get_twin.py", timeout=600)
    run_test_app("./regressions/regression_issue_990_exception_after_publish.py", timeout=600)
    run_test_app("./fuzzing/fuzz_send_message.py 1", timeout=600)
    run_test_app("./fuzzing/fuzz_send_message.py 3", timeout=600)

    # individual dropped PUBLISH messages don't get retried until after reconnect, so these 2 are
    # currently commented out.

    # run_test_app("./fuzzing/fuzz_send_message.py 2", timeout=600)
    # run_test_app("./fuzzing/fuzz_send_message.py 4", timeout=600)

    # exceptions in the Paho thread aren't caught and handled, so these 2 are currently commented out.

    # run_test_app("./fuzzing/fuzz_send_message.py 5", timeout=600)
    # run_test_app("./fuzzing/fuzz_send_message.py 6", timeout=600)

    print("+-" * 66)
    print()
    print("FINAL RESULT: {}".format("FAILED" if len(failures) else "SUCCEEDED"))
    if len(failures):
        print()
        for failure in failures:
            print(failure)
    print()
    print("+-" * 66)

    sys.exit(len(failures))
