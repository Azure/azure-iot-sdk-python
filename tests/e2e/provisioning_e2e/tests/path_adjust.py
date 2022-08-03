# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import sys
from os.path import dirname as dir

print("ADJUSTING PATH...")

root = dir(dir(sys.path[0]))
scripts = root + "\\scripts"
print(scripts)
sys.path.append(scripts)
# print("PATH: {}".format(sys.path))

# print("Attempting to import scripts...")
# #import scripts
# import create_x509_chain_crypto
