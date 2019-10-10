# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import weakref


class CallableWeakMethod(object):
    """
    Object which makes a weak reference to a method call.  Similar to weakref.WeakMethod,
    but works on Python 2.7 and returns an object which is callable.

    This objet is used primarily for callbacks and it prevents circular references in the
    garbage collector.  It is used specifically in the scenario where object holds a
    refernce to object b and b holds a callback into a (which creates a rererence
    back into a)

    By default, method references are _strong_, and we end up with  we have a situation
    where a has a _strong) reference to b and b has a _strong_ reference to a.

    The Python 3.4+ garbage collectors handle this circular reference just fine, but the
    2.7 garbage collector fails, but only when one of the objects has a finalizer method.

    '''
    # example of bad (strong) circular dependency:
    class A(object):
        def --init__(self):
            self.b = B()            # A objects now have a strong refernce to B objects
            b.handler = a.method()  # and B object have a strong reference back into A objects
        def method(self):
            pass
    '''

    In the example above, if a or B has a finalizer, that object will be considered uncollectable
    (on 2.7) and both objects will leak

    However, if we use this object, a will a _strong_ reference to b, and b will have a _weak_
    reference =back to a, and the circular depenency chain is broken.

    ```
    # example of better (weak) circular dependency:
    class A(object):
        def --init__(self):
            self.b = B()                                    # A objects now have a strong refernce to B objects
            b.handler = CallableWeakMethod(a, "method")     # and B objects have a WEAK reference back into A objects
        def method(self):
            pass
    ```

    In this example, there is no circular reference, and the Python 2.7 garbage collector is able
    to collect both objects, even if one of them has a finalizer.

    When we reach the point where all supported interpreters implement PEP 442, we will
    no longer need this object

    ref: https://www.python.org/dev/peps/pep-0442/
    """

    def __init__(self, object, method_name):
        self.object_weakref = weakref.ref(object)
        self.method_name = method_name

    def _get_method(self):
        return getattr(self.object_weakref(), self.method_name)

    def __call__(self, *args, **kwargs):
        return self._get_method()(*args, **kwargs)

    def __eq__(self, other):
        return self._get_method() == other

    def __repr__(self):
        if self.object_weakref():
            return "CallableWeakMethod for {}".format(self._get_method())
        else:
            return "CallableWeakMethod for {} (DEAD)".format(self.method_name)
