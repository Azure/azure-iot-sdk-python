# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import sys
import os
from os.path import dirname as dir

# This script/module should probably not exist. Some tests require access to the "scripts"
# directory of the root, and that's not accessible from within this testing package.
# Here we forcibly adjust the path to include the "scripts" directory. As soon as this is
# no longer true, we can get rid of this file.
root_path = dir(dir(sys.path[0]))
script_path = os.path.join(root_path, "scripts")
print(script_path)
if script_path not in sys.path:
    sys.path.append(script_path)
