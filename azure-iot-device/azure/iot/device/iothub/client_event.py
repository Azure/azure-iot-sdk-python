# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

NEW_SASTOKEN_REQUIRED = "NEW_SASTOKEN_REQUIRED"
CONNECTION_STATE_CHANGE = "CONNECTION_STATE_CHANGE"
BACKGROUND_EXCEPTION = "BACKGROUND_EXCEPTION"


class ClientEvent(object):
    def __init__(self, name, values_for_user=[]):
        self.name = name
        self.values_for_user = values_for_user
