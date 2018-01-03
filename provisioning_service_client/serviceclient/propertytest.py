import sys
import six

try:
    raise ValueError("Old Message")
except Exception as e:

    e.args = ("hi")
    raise TypeError, "Something"
    #six.raise_from(TypeError, TypeError(str(e)))
