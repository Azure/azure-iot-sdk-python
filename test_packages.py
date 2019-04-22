# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Run tests on all packages, and write output
"""

import glob
import os
from subprocess import check_call


if __name__ == "__main__":
    # All packages in the monorepo, except nspkg
    packages = [os.path.dirname(p) for p in glob.glob("azure*/setup.py") if "nspkg" not in p]
    for package_name in packages:
        if "nspkg" not in package_name:
            command = "pytest {} --junitxml=junit/{}-test-results.xml --cov=azure --cov-report=xml:coverage.xml --cov-report=html:coverage --cov-append".format(
                package_name, package_name
            )
            check_call(command.split())
