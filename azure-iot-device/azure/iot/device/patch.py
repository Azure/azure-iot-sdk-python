# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module provides patches used to dynamically modify items from the libraries"""

import sys
import inspect
import logging

logger = logging.getLogger(__name__)


# TODO: make this work for Python 2.7 and 3.4
def add_shims_for_inherited_methods(target_class):
    """Dynamically add overriding, pass-through shim methods for all public inherited methods
    on a child class, which simply call into the parent class implementation of the same method.

    These shim methods will include the same docstrings as the method from the parent class.

    This currently only works for Python 3.5+

    :param target_class: The child class to add shim methods to
    """

    # Depending on how the method was defined, it could be either a function or a method.
    # Thus we need to find the union of the two sets.
    # Here instance methods are considered functions because they are not yet bound to an instance
    # of the class. Classmethods on the other hand, are already bound, and show up as methods.
    # It also is worth noting that async functions/methods ARE picked up by this introspection.
    class_functions = inspect.getmembers(target_class, predicate=inspect.isfunction)
    class_methods = inspect.getmembers(target_class, predicate=inspect.ismethod)
    all_methods = class_functions + class_methods

    # This list of attributes gives us a lot of information, but we only are using it to get
    # the defining class of a given method.
    class_attributes = inspect.classify_class_attrs(target_class)

    # We must alias classnames to prevent naming collisions when this fn is called multiple times
    # with classes that share a name. If we've already used this classname, add trailing underscore(s)
    classname_alias = target_class.__name__
    while classname_alias in globals():
        classname_alias += "_"

    # Import the class we're adding methods to, so that functions defined in this scope can use super()
    class_module = inspect.getmodule(target_class)
    import_cmdstr = "from {module} import {target_class} as {alias}".format(
        module=class_module.__name__, target_class=target_class.__name__, alias=classname_alias
    )
    logger.info("exec: " + import_cmdstr)
    exec(import_cmdstr, globals())

    for method in all_methods:
        method_name = method[0]
        method_obj = method[1]
        # We can index on 0 here because the list comprehension will always be exactly 1 element
        method_attribute = [att for att in class_attributes if att.name == method_name][0]
        # The object of the class where the method was originally defined.
        originating_class_obj = method_attribute.defining_class

        # Create a shim method for all public methods inherited from a parent class
        if method_name[0] != "_" and originating_class_obj != target_class:

            method_sig = inspect.signature(method_obj)
            sig_params = method_sig.parameters

            # Bound methods (e.g. classmethods) remove the first parameter (e.g. cls)
            # so we need to add it back
            if inspect.ismethod(method_obj):
                complete_params = []
                complete_params.append(
                    inspect.Parameter("cls", inspect.Parameter.POSITIONAL_OR_KEYWORD)
                )
                complete_params += list(sig_params.values())
                method_sig = method_sig.replace(parameters=complete_params)

            # Since neither "self" nor "cls" are used in invocation, we need to create a new
            # invocation signature without them
            invoke_params_list = []
            for param in sig_params.values():
                if param.name != "self" and param.name != "cls":
                    # Set the parameter to empty (since we use this in an invocation, not a signature)
                    new_param = param.replace(default=inspect.Parameter.empty)
                    invoke_params_list.append(new_param)
            invoke_params = method_sig.replace(parameters=invoke_params_list)

            # Choose syntactical variants
            if inspect.ismethod(method_obj):
                obj_or_type = "cls"  # Use 'cls' to invoke super() for classmethods
            else:
                obj_or_type = "self"  # Use 'self' to invoke super() for instance methods
            if inspect.iscoroutine(method_obj) or inspect.iscoroutinefunction(method_obj):
                def_syntax = "async def"  # Define coroutine function/method
                ret_syntax = "return await"
            else:
                def_syntax = "def"  # Define function/method
                ret_syntax = "return"

            # Dynamically define a new function, with the same name, that invokes the method of the parent class
            fn_def_cmdstr = "{def_syntax} {method_name}{signature}: {ret_syntax} super({leaf_class}, {object_or_type}).{method_name}{invocation}".format(
                def_syntax=def_syntax,
                method_name=method_name,
                signature=str(method_sig),
                ret_syntax=ret_syntax,
                leaf_class=classname_alias,
                object_or_type=obj_or_type,
                invocation=str(invoke_params),
            )
            logger.info("exec: " + fn_def_cmdstr)
            exec(fn_def_cmdstr, globals())

            # Add function to leaf/child class as a method.
            set_doc_cmdstr = "{method_name}.__doc__ = method_obj.__doc__".format(
                method_name=method_name
            )
            logger.info("exec: " + set_doc_cmdstr)
            exec(set_doc_cmdstr)

            # Add as a classmethod if the method is a classmethod
            if inspect.ismethod(method_obj):
                attach_shim_cmdstr = "setattr(target_class, method_name, classmethod({method_name}))".format(
                    method_name=method_name
                )
            # Add regularly if the method is an instance method
            else:
                attach_shim_cmdstr = "setattr(target_class, method_name, {method_name})".format(
                    method_name=method_name
                )
            logger.info("exec: " + attach_shim_cmdstr)
            exec(attach_shim_cmdstr)

    # NOTE: the __qualname__ attributes of these new shim methods point to THIS module, not the class itself.
    # This shouldn't matter, but in case it does, I am documenting that fact here.
