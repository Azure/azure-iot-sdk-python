# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest

fake_count = 0


def get_next_fake_value():
    """
    return a new "unique" fake value that can be used to test that attributes
    are set correctly.  Even if we expect a particular attribute to hold something
    besides a string (like an array or an object), we can still test using a string,
    so we do.
    """
    global fake_count
    fake_count = fake_count + 1
    return "__fake_value_{}__".format(fake_count)


base_operation_defaults = {"needs_connection": False, "error": None}
base_event_defaults = {}


def add_operation_test(
    obj, module, extra_defaults={}, positional_arguments=[], keyword_arguments={}
):
    """
    Add a test class to test the given PipelineOperation class.  The class that
    we're testing is passed in the obj parameter, and the different initialization
    constants are passed with the named arguments that follow.
    """
    all_extra_defaults = extra_defaults.copy()
    all_extra_defaults.update(name=obj.__name__)

    _add_data_object_test(
        obj=obj,
        module=module,
        base_defaults=base_operation_defaults,
        extra_defaults=all_extra_defaults,
        positional_arguments=positional_arguments,
        keyword_arguments=keyword_arguments,
    )


def add_event_test(obj, module, extra_defaults={}, positional_arguments=[], keyword_arguments={}):
    """
    Add a test class to test the given PipelineOperation class.  The class that
    we're testing is passed in the obj parameter, and the different initialization
    constants are passed with the named arguments that follow.
    """
    all_extra_defaults = extra_defaults.copy()
    all_extra_defaults.update(name=obj.__name__)

    _add_data_object_test(
        obj=obj,
        module=module,
        base_defaults=base_event_defaults,
        extra_defaults=all_extra_defaults,
        positional_arguments=positional_arguments,
        keyword_arguments=keyword_arguments,
    )


def _add_data_object_test(
    obj, module, base_defaults, extra_defaults={}, positional_arguments=[], keyword_arguments={}
):
    """
    internal function that takes the class and attribute details and adds a test class which
    validates that the given class properly implements the given attributes.
    """

    # `defaults` contains an array of object attributes that should be set when
    # we call the initializer will all of the required positional arguments
    # and none of the optional keyword arguments.

    defaults = base_defaults.copy()
    for key in extra_defaults:
        defaults[key] = extra_defaults[key]
    for key in keyword_arguments:
        defaults[key] = keyword_arguments[key]

    # `args` contains an array of positional argument that we are passing to test that they
    # get assigned to the correct attribute.
    args = [get_next_fake_value() for i in range(len(positional_arguments))]

    # `kwargs` contains a dictionary of all keyword arguments, which includes required positional
    # arguments and optional keyword arguments.
    kwargs = {}
    for key in positional_arguments:
        kwargs[key] = get_next_fake_value()
    for key in keyword_arguments:
        kwargs[key] = get_next_fake_value()

    # LocalTestObject is a local class which tests the object that was passed in.  pytest doesn't test
    # against this local object, but it does test against it when we put it into the module namespace
    # for the module that was passed in.
    @pytest.mark.describe("{} - Instantiation".format(obj.__name__))
    class LocalTestObject(object):
        @pytest.mark.it(
            "Accepts {} positional arguments that get assigned to attributes of the same name: {}".format(
                len(positional_arguments), ", ".join(positional_arguments)
            )
            if len(positional_arguments)
            else "Accepts no positional arguments"
        )
        def test_positional_arguments(self):
            instance = obj(*args)
            for i in range(len(args)):
                assert getattr(instance, positional_arguments[i]) == args[i]

        @pytest.mark.it(
            "Accepts the following keyword arguments that get assigned to attributes of the same name: {}".format(
                ", ".join(kwargs.keys()) if len(kwargs) else "None"
            )
        )
        def test_keyword_arguments(self):
            instance = obj(**kwargs)
            for key in kwargs:
                assert getattr(instance, key) == kwargs[key]

        @pytest.mark.it(
            "Has the following default attributes: {}".format(
                ", ".join(["{}={}".format(key, repr(defaults[key])) for key in defaults])
            )
        )
        def test_defaults(self):
            instance = obj(*args)
            for key in defaults:
                assert getattr(instance, key) == defaults[key]

    # Adding this object to the namespace of the module that was passed in (using a name that starts with "Test")
    # will cause pytest to pick it up.
    setattr(module, "Test{}Instantiation".format(obj.__name__), LocalTestObject)
