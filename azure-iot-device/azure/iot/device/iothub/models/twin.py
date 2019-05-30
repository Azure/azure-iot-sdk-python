# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains classes related to device twin and module twin functionality
"""


class Twin(object):
    """Represents a device twin or module twin

    :ivar desired_properties: The desired properties for the Twin.  These are properties
      which are sent _to_ the device or module to indicate the _desired_ state of the device
      or module
    :type desired_properties: dict, str, int, float, bool, or None (JSON compatible values)
    :ivar reported_properties: The reported properties for the Twin.  These are properties
      which are sent _from_ the device or module to indicate the _actual_ state of the device.
    :type reported_properties: dict, str, int, float, bool, or None (JSON compatible values)
    """

    # OPEN QUESTION: can desired_properties and reported_properties only be dict, or can they be any JSON-compatible value?

    def __init__(self):
        """Initializer for a Twin object
        """
        self.desiried_properties = None
        self.reported_properties = None
