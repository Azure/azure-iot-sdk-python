# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import sys
import os
from os.path import dirname as dir

print("ADJUSTING PATH...")

root_path = dir(dir(sys.path[0]))
script_path = os.path.join(root_path, "scripts")
print(script_path)
if script_path not in sys.path:
    sys.path.append(script_path)
print("PATH: {}".format(sys.path))
