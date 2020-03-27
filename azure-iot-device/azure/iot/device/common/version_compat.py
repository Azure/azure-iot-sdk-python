# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module defines functions intended for providing compatibility between
different versions of Python"""

from six.moves import urllib


def urlencode(query, quote_via=urllib.parse.quote_plus, safe=""):
    """ Custom implementation of urllib.parse.urlencode().

    This is necessary because prior to Python 3.5, urlencode() always encodes via
    quote_plus() rather than quote(). This is generally not desirable for MQTT, as
    it will translate ' ' into '+' rather than '%20', and '+' is not allowed in the
    topic strings for MQTT publish.

    Starting in 3.5, the included library function for urlencode() allows you to specify
    which style of encoding you want, however this feature is not available in 2.7 and so
    we must implement it ourselves.
    """
    if isinstance(query, list):
        encoded = "&".join(
            ["{}={}".format(quote_via(k, safe=safe), quote_via(v, safe=safe)) for (k, v) in query]
        )
    elif isinstance(query, dict):
        encoded = "&".join(
            [
                "{}={}".format(quote_via(k, safe=safe), quote_via(v, safe=safe))
                for k, v in query.items()
            ]
        )
    else:
        raise TypeError("Invalid type for 'query'")
    return encoded
