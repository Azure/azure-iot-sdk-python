# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from subprocess import check_call, CalledProcessError

this_file_path = os.path.dirname(os.path.realpath(__file__))


def run_test_app(relative_app_name):
    absolute_app = os.path.join(this_file_path, relative_app_name)

    try:
        print("+-" * 66)
        print("Running test app: {}".format(absolute_app))
        check_call([sys.executable] + absolute_app.split())
        print("Test app {} SUCCEEDED".format(absolute_app))

    except CalledProcessError as err:
        print(err)
        print("Test app {} FAILED".format(absolute_app))
        sys.exit(1)


if __name__ == "__main__":
    run_test_app("./regression_pr1023_infinite_get_twin.py")
    run_test_app("./simple_send_message_bulk.py")
