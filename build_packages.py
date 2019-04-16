# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""Build all packages for distribution"""

import glob
import os
import sys
from subprocess import check_call

if __name__ == "__main__":
    target_dir = "../dist"
    packages = [os.path.dirname(p) for p in glob.glob("azure*/setup.py")]
    for package_name in packages:
        command_bdist_wheel = "setup.py sdist bdist_wheel --dist-dir={} --universal".format(
            target_dir
        )
        check_call([sys.executable] + command_bdist_wheel.split(), cwd=package_name)
