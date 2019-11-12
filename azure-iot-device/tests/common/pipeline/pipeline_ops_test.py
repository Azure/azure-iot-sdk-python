# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import logging

from azure.iot.device.common.pipeline.pipeline_ops_base import PipelineOperation
from azure.iot.device.common import handle_exceptions
from azure.iot.device.common.pipeline import pipeline_exceptions

logging.basicConfig(level=logging.DEBUG)


def add_operation_tests(
    test_module,
    op_class_under_test,
    op_test_config_class,
    extended_op_instantiation_test_class=None,
):
    """
    Add shared tests for an Operation class to a testing module.
    These tests need to be done for every Operation class.

    :param test_module: A reference to the test module to add tests to
    :param op_class_under_test: A reference to the specific Operation class under test
    :param op_test_config_class: A class providing fixtures specific to the Operation class
        under test. This class must define the following fixtures:
            - "cls_type" (which returns a reference to the Operation class under test)
            - "init_kwargs" (which returns a dictionary of kwargs and associated values used to
                instantiate the class)
    :param extended_op_instantiation_test_class: A class defining instantiation tests that are
        specific to the Operation class under test, and not shared with all Operations.
        Note that you may override shared instantiation tests defined in this function within
        the provided test class (e.g. test_needs_connection)
    """

    # Extend the provided test config class
    class OperationTestConfigClass(op_test_config_class):
        @pytest.fixture
        def op(self, cls_type, init_kwargs, mocker):
            op = cls_type(**init_kwargs)
            mocker.spy(op, "complete")
            return op

    @pytest.mark.describe("{} - Instantiation".format(op_class_under_test.__name__))
    class OperationBaseInstantiationTests(OperationTestConfigClass):
        @pytest.mark.it("Initializes 'name' attribute as the classname")
        def test_name(self, cls_type, init_kwargs):
            op = cls_type(**init_kwargs)
            assert op.name == op.__class__.__name__

        @pytest.mark.it("Initializes 'completed' attribute as False")
        def test_completed(self, cls_type, init_kwargs):
            op = cls_type(**init_kwargs)
            assert op.completed is False

        # NOTE: this test should be overridden for operations that set this value to True
        @pytest.mark.it("Initializes 'needs_connection' attribute as False")
        def test_needs_connection(self, cls_type, init_kwargs):
            op = cls_type(**init_kwargs)
            assert op.needs_connection is False

        @pytest.mark.it("Initializes 'callbacks' list attribute with the provided callback")
        def test_callback_added_to_list(self, cls_type, init_kwargs):
            op = cls_type(**init_kwargs)
            assert len(op.callbacks) == 1
            assert op.callbacks[0] is init_kwargs["callback"]

    # If an extended operation instantiation test class is provided, use those tests as well.
    # By using the extended_op_instantation_test_class as the first parent class, this ensures that
    # tests from OperationBaseInstantiationTests (e.g. test_needs_connection) can be overwritten by
    # tests provided in extended_op_instantiation_test_class.
    if extended_op_instantiation_test_class:

        class OperationInstantiationTests(
            extended_op_instantiation_test_class, OperationBaseInstantiationTests
        ):
            pass

    else:

        class OperationInstantiationTests(OperationBaseInstantiationTests):
            pass

    @pytest.mark.describe("{} - .add_callback()".format(op_class_under_test.__name__))
    class OperationAddCallbackTests(OperationTestConfigClass):
        @pytest.mark.it("Adds a callback to the operation, which will be triggered upon completion")
        def test_adds_callback(self, mocker, op):
            cb = mocker.MagicMock()
            op.add_callback(cb)
            assert cb.call_count == 0
            op.complete()

            assert cb.call_count == 1

    @pytest.mark.describe("{} - .spawn_worker_op()".format(op_class_under_test.__name__))
    class OperationSpawnWorkerOpTests(OperationTestConfigClass):
        @pytest.fixture
        def worker_op_type(self):
            class SomeOperationType(PipelineOperation):
                def __init__(self, arg1, arg2, arg3, callback):
                    super(SomeOperationType, self).__init__(callback=callback)

            return SomeOperationType

        @pytest.fixture
        def worker_op_kwargs(self):
            kwargs = {"arg1": 1, "arg2": 2, "arg3": 3}
            return kwargs

        @pytest.mark.it(
            "Creates and returns an new instance of the Operation class specified in the 'worker_op_type' parameter"
        )
        def test_returns_worker_op_instance(self, op, worker_op_type, worker_op_kwargs):
            worker_op = op.spawn_worker_op(worker_op_type, **worker_op_kwargs)
            assert isinstance(worker_op, worker_op_type)

        @pytest.mark.it(
            "Instantiates the returned worker operation using the provided **kwargs parameters (not including 'callback')"
        )
        def test_creates_worker_op_with_provided_kwargs(self, mocker, op, worker_op_kwargs):
            mock_instance = mocker.MagicMock()
            mock_type = mocker.MagicMock(return_value=mock_instance)
            mock_type.__name__ = "mock type"  # this is needed for log statements
            assert "callback" not in worker_op_kwargs

            worker_op = op.spawn_worker_op(mock_type, **worker_op_kwargs)

            assert worker_op is mock_instance
            assert mock_type.call_count == 1

            # Show that all provided kwargs are used. Note that this test does NOT show that
            # ONLY the provided kwargs are used - because there ARE additional kwargs added.
            for kwarg in worker_op_kwargs:
                assert mock_type.call_args[1][kwarg] == worker_op_kwargs[kwarg]

        @pytest.mark.it(
            "Adds a secondary callback to the worker operation after instantiation, if 'callback' is included in the provided **kwargs parameters"
        )
        def test_adds_callback_to_worker_op(self, mocker, op, worker_op_kwargs):
            mock_instance = mocker.MagicMock()
            mock_type = mocker.MagicMock(return_value=mock_instance)
            mock_type.__name__ = "mock type"  # this is needed for log statements
            worker_op_kwargs["callback"] = mocker.MagicMock()

            worker_op = op.spawn_worker_op(mock_type, **worker_op_kwargs)

            assert worker_op is mock_instance
            assert mock_type.call_count == 1

            # The callback used for instantiating the worker operation is NOT the callback provided in **kwargs
            assert mock_type.call_args[1]["callback"] is not worker_op_kwargs["callback"]

            # The callback provided in **kwargs is applied after instantiation
            assert mock_instance.add_callback.call_count == 1
            assert mock_instance.add_callback.call_args == mocker.call(worker_op_kwargs["callback"])

        @pytest.mark.it(
            "Raises TypeError if the provided **kwargs parameters do not match the constructor for the class provided in the 'worker_op_type' parameter"
        )
        def test_incorrect_kwargs(self, mocker, op, worker_op_type, worker_op_kwargs):
            worker_op_kwargs["invalid_kwarg"] = "some value"

            with pytest.raises(TypeError):
                op.spawn_worker_op(worker_op_type, **worker_op_kwargs)

        @pytest.mark.it(
            "Returns a worker operation, which, when completed, completes the operation that spawned it"
        )
        @pytest.mark.parametrize(
            "use_error", [pytest.param(False, id="No Error"), pytest.param(True, id="With Error")]
        )
        def test_worker_op_completes_original_op(
            self, mocker, use_error, arbitrary_exception, op, worker_op_type, worker_op_kwargs
        ):
            if use_error:
                error = arbitrary_exception
            else:
                error = None

            worker_op = op.spawn_worker_op(worker_op_type, **worker_op_kwargs)
            assert op.complete.call_count == 0

            worker_op.complete(error=error)

            assert op.complete.call_count == 1
            assert op.complete.call_args == mocker.call(error=error)

        @pytest.mark.it(
            "Returns a worker operation, which, when completed, triggers the 'callback' optionally provided in the **kwargs parameter, prior to completing the operation that spawned it"
        )
        @pytest.mark.parametrize(
            "use_error", [pytest.param(False, id="No Error"), pytest.param(True, id="With Error")]
        )
        def test_worker_op_triggers_own_callback_and_then_completes_original_op(
            self, mocker, use_error, arbitrary_exception, op, worker_op_type, worker_op_kwargs
        ):
            def callback(this_op, this_error):
                # This assertion is only true if this callback is triggered before the op that spawned
                # the worker is completed
                assert op.complete.call_count == 0

            cb_mock = mocker.MagicMock(side_effect=callback)

            worker_op_kwargs["callback"] = cb_mock

            if use_error:
                error = arbitrary_exception
            else:
                error = None

            worker_op = op.spawn_worker_op(worker_op_type, **worker_op_kwargs)
            assert op.complete.call_count == 0

            worker_op.complete(error=error)

            # Provided callback was called
            assert cb_mock.call_count == 1
            assert cb_mock.call_args == mocker.call(worker_op, error)

            # The original op that spawned the worker is also completed
            assert op.complete.call_count == 1
            assert op.complete.call_args == mocker.call(error=error)

    @pytest.mark.describe("{} - .complete()".format(op_class_under_test.__name__))
    class OperationCompleteTests(OperationTestConfigClass):
        @pytest.fixture(params=["Successful completion", "Completion with error"])
        def error(self, request, arbitrary_exception):
            if request.param == "Successful completion":
                return None
            else:
                return arbitrary_exception

        @pytest.mark.it(
            "Marks the operation as completed by setting the 'completed' attribute to True"
        )
        def test_marks_complete(self, op, error):
            assert not op.completed
            op.complete(error=error)
            assert op.completed

        @pytest.mark.it(
            "Sends an OperationError to the background exception handler if the operation has already been completed"
        )
        def test_already_complete(self, mocker, op, error):
            mocker.spy(handle_exceptions, "handle_background_exception")
            op.complete(error=error)
            assert op.completed
            assert handle_exceptions.handle_background_exception.call_count == 0
            op.complete(error=error)
            assert handle_exceptions.handle_background_exception.call_count == 1
            assert (
                type(handle_exceptions.handle_background_exception.call_args[0][0])
                is pipeline_exceptions.OperationError
            )

        @pytest.mark.it(
            "Triggers and removes callbacks that have been added to the operation according to LIFO order"
        )
        def test_trigger_callbacks(self, mocker, cls_type, init_kwargs, error):
            mocker.spy(handle_exceptions, "handle_background_exception")

            # Set up callback mocks
            cb1_mock = mocker.MagicMock()
            cb2_mock = mocker.MagicMock()
            cb3_mock = mocker.MagicMock()

            def cb1(op_cb_param, error_cb_param):
                # Callback 2 and 3 have already been triggered
                assert cb1_mock.call_count == 1
                assert cb2_mock.call_count == 1
                assert cb3_mock.call_count == 1

                assert cb1_mock.call_args == mocker.call(op, error)

                assert len(op.callbacks) == 0

            def cb2(op_cb_param, error_cb_param):
                # Callback 3 has already been triggered, but Callback 1 has not
                assert cb1_mock.call_count == 0
                assert cb2_mock.call_count == 1
                assert cb3_mock.call_count == 1

                assert cb2_mock.call_args == mocker.call(op, error)

                assert len(op.callbacks) == 1

            def cb3(op_cb_param, error_cb_param):
                # Callback 3 has been triggered, but no others have been.
                assert cb1_mock.call_count == 0
                assert cb2_mock.call_count == 0
                assert cb3_mock.call_count == 1

                assert cb3_mock.call_args == mocker.call(op, error)

                assert len(op.callbacks) == 2

            cb1_mock.side_effect = cb1
            cb2_mock.side_effect = cb2
            cb3_mock.side_effect = cb3

            # Attach callbacks to op
            init_kwargs["callback"] = cb1_mock
            op = cls_type(**init_kwargs)
            op.add_callback(cb2_mock)
            op.add_callback(cb3_mock)
            assert len(op.callbacks) == 3
            assert not op.completed

            # Run the completion
            op.complete(error=error)

            assert op.completed

            # Because exceptions raised in callbacks are caught and sent to the background exception handler,
            # the assertions in the above callbacks won't be able to directly raise AssertionErrors that will
            # allow for testing normally. Instead we should check the background_exception_handler to see if
            # any of the assertions raised errors and sent them there.
            assert handle_exceptions.handle_background_exception.call_count == 0

        @pytest.mark.it(
            "Handles any Exceptions raised during execution of a callback by sending them to the background exception handler, and continuing on with completion"
        )
        def test_callback_raises_error(
            self, mocker, arbitrary_exception, cls_type, init_kwargs, error
        ):
            mocker.spy(handle_exceptions, "handle_background_exception")

            # Set up callback mocks
            cb1_mock = mocker.MagicMock()
            cb2_mock = mocker.MagicMock(side_effect=arbitrary_exception)
            cb3_mock = mocker.MagicMock()

            # Attach callbacks to op
            init_kwargs["callback"] = cb1_mock
            op = cls_type(**init_kwargs)
            op.add_callback(cb2_mock)
            op.add_callback(cb3_mock)
            assert len(op.callbacks) == 3
            assert not op.completed

            # Run the completion
            op.complete(error=error)

            # Op was completed, and all callbacks triggered despite the callback raising an exception
            assert op.completed
            assert len(op.callbacks) == 0

            # The exception raised by the callback was passed to the background exception handler
            assert handle_exceptions.handle_background_exception.call_count == 1
            assert handle_exceptions.handle_background_exception.call_args == mocker.call(
                arbitrary_exception
            )

        @pytest.mark.it(
            "Allows any BaseExceptions raised during execution of a callback to propagate"
        )
        def test_callback_raises_base_exception(
            self, mocker, arbitrary_base_exception, cls_type, init_kwargs, error
        ):
            # Set up callback mocks
            cb1_mock = mocker.MagicMock()
            cb2_mock = mocker.MagicMock(side_effect=arbitrary_base_exception)
            cb3_mock = mocker.MagicMock()

            # Attach callbacks to op
            init_kwargs["callback"] = cb1_mock
            op = cls_type(**init_kwargs)
            op.add_callback(cb2_mock)
            op.add_callback(cb3_mock)
            assert len(op.callbacks) == 3

            # BaseException from callback is raised
            with pytest.raises(arbitrary_base_exception.__class__) as e_info:
                op.complete(error=error)
            assert e_info.value is arbitrary_base_exception

        @pytest.mark.it(
            "Halts triggering of callbacks if a callback causes the operation to uncomplete, leaving untriggered callbacks attached to the operation, which is NOT marked as completed"
        )
        def test_uncomplete_during_callback(self, mocker, cls_type, init_kwargs, error):
            def cb2(op, error):
                # Uncomplete the operation as part of the callback
                op.uncomplete()

            # Set up callback mocks
            cb1_mock = mocker.MagicMock()
            cb2_mock = mocker.MagicMock(side_effect=cb2)
            cb3_mock = mocker.MagicMock()

            # Attach callbacks to op
            init_kwargs["callback"] = cb1_mock
            op = cls_type(**init_kwargs)
            op.add_callback(cb2_mock)
            op.add_callback(cb3_mock)
            assert not op.completed
            assert len(op.callbacks) == 3

            op.complete(error=error)

            # Callback was NOT completed
            assert not op.completed

            # Callback resolution was halted after CB2 due to the operation being uncompleted
            assert cb3_mock.call_count == 1
            assert cb2_mock.call_count == 1
            assert cb1_mock.call_count == 0

            assert len(op.callbacks) == 1
            assert op.callbacks[0] is cb1_mock

        @pytest.mark.it(
            "Completes the operation successfully (no error) by default if no error is specified"
        )
        def test_error_default(self, mocker, cls_type, init_kwargs):
            cb_mock = mocker.MagicMock()
            init_kwargs["callback"] = cb_mock
            op = cls_type(**init_kwargs)
            assert not op.completed

            op.complete()

            assert op.completed
            assert cb_mock.call_count == 1
            # Callback was called passing 'None' as the error
            assert cb_mock.call_args == mocker.call(op, None)

    @pytest.mark.describe("{} - .uncomplete()".format(op_class_under_test.__name__))
    class OperationUncompleteTests(OperationTestConfigClass):
        @pytest.mark.it(
            "Marks the operation as incomplete by setting the 'completed' attribute to False"
        )
        def test_marks_uncomplete(self, op):
            op.complete()
            assert op.completed
            op.uncomplete()
            assert not op.completed

    setattr(
        test_module,
        "Test{}Instantiation".format(op_class_under_test.__name__),
        OperationInstantiationTests,
    )
    setattr(
        test_module, "Test{}Complete".format(op_class_under_test.__name__), OperationCompleteTests
    )
    setattr(
        test_module,
        "Test{}AddCallback".format(op_class_under_test.__name__),
        OperationAddCallbackTests,
    )
    setattr(
        test_module,
        "Test{}Uncomplete".format(op_class_under_test.__name__),
        OperationUncompleteTests,
    )
    setattr(
        test_module,
        "Test{}SpawnWorkerOp".format(op_class_under_test.__name__),
        OperationSpawnWorkerOpTests,
    )
