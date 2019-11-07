# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import logging

logging.basicConfig(level=logging.DEBUG)

base_operation_defaults = {"needs_connection": False}

# def add_shared_operation_tests(
#     cls, module, default_attributes={}, positional_arguments=["callback"], keyword_arguments={}
# ):


def _add_complete_tests(cls, module):
    @pytest.fixture
    def op(self):
        pass

    @pytest.mark.describe("{} - .add_callback()".format(cls.__name__))
    class AddCallbackTests(object):
        pass

    @pytest.mark.describe("{} - .complete()".format(cls.__name__))
    class CompleteTests(object):
        pass

    @pytest.mark.describe("{} - .uncomplete()".format(cls.__name__))
    class UncompleteTests(object):
        pass

    setattr(module, "Test{}AddCallback".format(cls.__name__), AddCallbackTests)
    setattr(module, "Test{}Complete".format(cls.__name__), CompleteTests)
    setattr(module, "Test{}Uncomplete".format(cls.__name__), UncompleteTests)
