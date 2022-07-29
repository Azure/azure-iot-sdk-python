# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""Build all packages for distribution"""


import sys
from subprocess import check_call

if __name__ == "__main__":
    target_dir = "./dist"
    command_sdist = "setup.py sdist --dist-dir={}".format(target_dir)
    command_bdist_wheel = "setup.py bdist_wheel --dist-dir={}".format(target_dir)
    check_call([sys.executable] + command_sdist.split())
    check_call([sys.executable] + command_bdist_wheel.split())
