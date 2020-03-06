# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import logging
import threading

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

        @pytest.mark.it("Initializes 'completing' attribute as False")
        def test_completing(self, cls_type, init_kwargs):
            op = cls_type(**init_kwargs)
            assert op.completing is False

        @pytest.mark.it("Initializes 'error' attribute as None")
        def test_error(self, cls_type, init_kwargs):
            op = cls_type(**init_kwargs)
            assert op.error is None

        # NOTE: this test should be overridden for operations that set this value to True
        @pytest.mark.it("Initializes 'needs_connection' attribute as False")
        def test_needs_connection(self, cls_type, init_kwargs):
            op = cls_type(**init_kwargs)
            assert op.needs_connection is False

        @pytest.mark.it("Initializes 'callback_stack' list attribute with the provided callback")
        def test_callback_added_to_list(self, cls_type, init_kwargs):
            op = cls_type(**init_kwargs)
            assert len(op.callback_stack) == 1
            assert op.callback_stack[0] is init_kwargs["callback"]

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
        @pytest.fixture(
            params=["Currently completing with no error", "Currently completing with error"]
        )
        def error(self, request, arbitrary_exception):
            if request.param == "Currently completing with no error":
                return None
            else:
                return arbitrary_exception

        @pytest.mark.it("Adds a callback to the operation's callback stack'")
        def test_adds_callback(self, mocker, op):
            # Because op was instantiated with a callback, because 'callback' is a
            # required parameter, there will already be one callback on the stack
            # before we add additional ones.
            assert len(op.callback_stack) == 1
            cb1 = mocker.MagicMock()
            op.add_callback(cb1)
            assert len(op.callback_stack) == 2
            assert op.callback_stack[1] == cb1

            cb2 = mocker.MagicMock()
            op.add_callback(cb2)
            assert len(op.callback_stack) == 3
            assert op.callback_stack[1] == cb1
            assert op.callback_stack[2] == cb2

        @pytest.mark.it(
            "Raises an OperationError if attempting to add a callback to an already-completed operation"
        )
        def test_already_completed_callback(self, mocker, op):
            op.complete()
            assert op.completed

            with pytest.raises(pipeline_exceptions.OperationError):
                op.add_callback(mocker.MagicMock())

        @pytest.mark.it(
            "Raises an OperationError if attempting to add a callback to an operation that is currently undergoing the completion process"
        )
        def test_currently_completing(self, mocker, op, error):
            mocker.spy(handle_exceptions, "handle_background_exception")

            def cb(op, error):
                with pytest.raises(pipeline_exceptions.OperationError):
                    # Add a callback during completion of the callback, i.e. while op completion is in progress
                    op.add_callback(mocker.MagicMock())

            mock_cb = mocker.MagicMock(side_effect=cb)
            op.add_callback(mock_cb)

            op.complete(error)

            assert mock_cb.call_count == 1

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
            "Returns a worker operation, which, when completed, completes the operation that spawned it with the same error status"
        )
        @pytest.mark.parametrize(
            "use_error", [pytest.param(False, id="No Error"), pytest.param(True, id="With Error")]
        )
        def test_worker_op_completes_original_op(
            self, mocker, use_error, arbitrary_exception, op, worker_op_type, worker_op_kwargs
        ):
            original_op = op

            if use_error:
                error = arbitrary_exception
            else:
                error = None

            worker_op = original_op.spawn_worker_op(worker_op_type, **worker_op_kwargs)
            assert not original_op.completed

            worker_op.complete(error=error)

            # Worker op has been completed with the given error state
            assert worker_op.completed
            assert worker_op.error is error

            # Original op is now completed with the same given error state
            assert original_op.completed
            assert original_op.error is error

        @pytest.mark.it(
            "Returns a worker operation, which, when completed, triggers the 'callback' optionally provided in the **kwargs parameter, prior to completing the operation that spawned it"
        )
        @pytest.mark.parametrize(
            "use_error", [pytest.param(False, id="No Error"), pytest.param(True, id="With Error")]
        )
        def test_worker_op_triggers_own_callback_and_then_completes_original_op(
            self, mocker, use_error, arbitrary_exception, op, worker_op_type, worker_op_kwargs
        ):
            mocker.spy(handle_exceptions, "handle_background_exception")

            original_op = op

            def callback(op, error):
                # Assert this callback is called before the original op begins the completion process
                assert not original_op.completed
                assert original_op.complete.call_count == 0

            cb_mock = mocker.MagicMock(side_effect=callback)

            worker_op_kwargs["callback"] = cb_mock

            if use_error:
                error = arbitrary_exception
            else:
                error = None

            worker_op = original_op.spawn_worker_op(worker_op_type, **worker_op_kwargs)
            assert original_op.complete.call_count == 0

            worker_op.complete(error=error)

            # Provided callback was called
            assert cb_mock.call_count == 1
            assert cb_mock.call_args == mocker.call(op=worker_op, error=error)

            # Worker op was completed
            assert worker_op.completed

            # The original op that spawned the worker is also completed
            assert original_op.completed
            assert original_op.complete.call_count == 1
            assert original_op.complete.call_args == mocker.call(error=error)

            # Because exceptions raised in callbacks are caught and sent to the background exception handler,
            # the assertions in the above callback won't be able to directly raise AssertionErrors that will
            # allow for testing normally. Instead we should check the background_exception_handler to see if
            # any of the assertions raised errors and sent them there.
            assert handle_exceptions.handle_background_exception.call_count == 0

    @pytest.mark.describe("{} - .complete()".format(op_class_under_test.__name__))
    class OperationCompleteTests(OperationTestConfigClass):
        @pytest.fixture(params=["Successful completion", "Completion with error"])
        def error(self, request, arbitrary_exception):
            if request.param == "Successful completion":
                return None
            else:
                return arbitrary_exception

        @pytest.mark.it(
            "Triggers and removes callbacks from the operation's callback stack according to LIFO order, passing the operation and any error to each callback"
        )
        def test_trigger_callbacks(self, mocker, cls_type, init_kwargs, error):
            mocker.spy(handle_exceptions, "handle_background_exception")

            # Set up callback mocks
            cb1_mock = mocker.MagicMock()
            cb2_mock = mocker.MagicMock()
            cb3_mock = mocker.MagicMock()

            def cb1(op, error):
                # All callbacks have been triggered
                assert cb1_mock.call_count == 1
                assert cb2_mock.call_count == 1
                assert cb3_mock.call_count == 1
                assert len(op.callback_stack) == 0

            def cb2(op, error):
                # Callback 3 and Callback 2 have been triggered, but Callback 1 has not
                assert cb1_mock.call_count == 0
                assert cb2_mock.call_count == 1
                assert cb3_mock.call_count == 1
                assert len(op.callback_stack) == 1

            def cb3(op, error):
                # Callback 3 has been triggered, but no others have been.
                assert cb1_mock.call_count == 0
                assert cb2_mock.call_count == 0
                assert cb3_mock.call_count == 1
                assert len(op.callback_stack) == 2

            cb1_mock.side_effect = cb1
            cb2_mock.side_effect = cb2
            cb3_mock.side_effect = cb3

            # Attach callbacks to op
            init_kwargs["callback"] = cb1_mock
            op = cls_type(**init_kwargs)
            op.add_callback(cb2_mock)
            op.add_callback(cb3_mock)
            assert len(op.callback_stack) == 3
            assert not op.completed

            # Run the completion
            op.complete(error=error)

            assert op.completed
            assert cb3_mock.call_count == 1
            assert cb3_mock.call_args == mocker.call(op=op, error=error)
            assert cb2_mock.call_count == 1
            assert cb2_mock.call_args == mocker.call(op=op, error=error)
            assert cb1_mock.call_count == 1
            assert cb1_mock.call_args == mocker.call(op=op, error=error)

            # Because exceptions raised in callbacks are caught and sent to the background exception handler,
            # the assertions in the above callbacks won't be able to directly raise AssertionErrors that will
            # allow for testing normally. Instead we should check the background_exception_handler to see if
            # any of the assertions raised errors and sent them there.
            assert handle_exceptions.handle_background_exception.call_count == 0

        @pytest.mark.it(
            "Sets the 'error' attribute to the specified error (if any) at the beginning of the completion process"
        )
        def test_sets_error(self, mocker, op, error):
            mocker.spy(handle_exceptions, "handle_background_exception")
            original_err = error

            def cb(op, error):
                # During the completion process, the 'error' attribute has been set
                assert op.error is original_err
                assert error is original_err

            cb_mock = mocker.MagicMock(side_effect=cb)
            op.add_callback(cb_mock)

            op.complete(error=error)

            # Callback was triggered during completion
            assert cb_mock.call_count == 1

            # After the completion process, the 'error' attribute is still set
            assert op.error is error

            # Because exceptions raised in callbacks are caught and sent to the background exception handler,
            # the assertion in the above callback won't be able to directly raise AssertionErrors that will
            # allow for testing normally. Instead we should check the background_exception_handler to see if
            # any of the assertions raised errors and sent them there.
            assert handle_exceptions.handle_background_exception.call_count == 0

        @pytest.mark.it(
            "Sets the 'completing' attribute to True only for the duration of the completion process"
        )
        def test_completing_set(self, mocker, op, error):
            mocker.spy(handle_exceptions, "handle_background_exception")

            def cb(op, error):
                # The operation is completing, but not completed
                assert op.completing
                assert not op.completed

            cb_mock = mocker.MagicMock(side_effect=cb)
            op.add_callback(cb_mock)

            op.complete(error)

            # Callback was called
            assert cb_mock.call_count == 1

            # Once completed, the op is no longer completing
            assert not op.completing
            assert op.completed

            # Because exceptions raised in callbacks are caught and sent to the background exception handler,
            # the assertion in the above callback won't be able to directly raise AssertionErrors that will
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
            assert len(op.callback_stack) == 3
            assert not op.completed

            # Run the completion
            op.complete(error=error)

            # Op was completed, and all callbacks triggered despite the callback raising an exception
            assert op.completed
            assert cb3_mock.call_count == 1
            assert cb2_mock.call_count == 1
            assert cb1_mock.call_count == 1
            assert len(op.callback_stack) == 0

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
            assert len(op.callback_stack) == 3

            # BaseException from callback is raised
            with pytest.raises(arbitrary_base_exception.__class__) as e_info:
                op.complete(error=error)
            assert e_info.value is arbitrary_base_exception

            # Due to the BaseException raised during CB2 propagating, CB1 is never triggered
            assert cb3_mock.call_count == 1
            assert cb2_mock.call_count == 1
            assert cb1_mock.call_count == 0

        @pytest.mark.it(
            "Halts triggering of callbacks if a callback invokes the .halt_completion() method, leaving untriggered callbacks in the operation's callback stack"
        )
        def test_halt_during_callback(self, mocker, cls_type, init_kwargs, error):
            def cb2(op, error):
                # Halt the operation completion as part of the callback
                op.halt_completion()

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
            assert len(op.callback_stack) == 3

            op.complete(error=error)

            # Callback was NOT completed
            assert not op.completed

            # Callback resolution was halted after CB2 due to the operation completion being halted
            assert cb3_mock.call_count == 1
            assert cb2_mock.call_count == 1
            assert cb1_mock.call_count == 0

            assert len(op.callback_stack) == 1
            assert op.callback_stack[0] is cb1_mock

        @pytest.mark.it(
            "Marks the operation as fully completed by setting the 'completed' attribute to True, only once all callbacks have been triggered"
        )
        def test_marks_complete(self, mocker, op, error):
            mocker.spy(handle_exceptions, "handle_background_exception")

            # Set up callback mocks
            cb1_mock = mocker.MagicMock()
            cb2_mock = mocker.MagicMock()

            def cb(op, error):
                assert not op.completed

            cb1_mock.side_effect = cb
            cb2_mock.side_effect = cb

            op.add_callback(cb1_mock)
            op.add_callback(cb2_mock)

            op.complete(error=error)
            assert op.completed

            # Callbacks were called
            assert cb1_mock.call_count == 1
            assert cb2_mock.call_count == 1

            # Because exceptions raised in callbacks are caught and sent to the background exception handler,
            # the assertion in the above callbacks won't be able to directly raise AssertionErrors that will
            # allow for testing normally. Instead we should check the background_exception_handler to see if
            # any of the assertions raised errors and sent them there.
            assert handle_exceptions.handle_background_exception.call_count == 0

        @pytest.mark.it(
            "Sends an OperationError to the background exception handler, without making any changes to the operation, if the operation has already been completed"
        )
        def test_already_complete(self, mocker, op, error):
            mocker.spy(handle_exceptions, "handle_background_exception")

            # Complete the operation
            op.complete(error=error)
            assert op.completed
            assert handle_exceptions.handle_background_exception.call_count == 0

            # Get the operation state
            original_op_err_state = op.error
            origianl_op_completion_state = op.completed

            # Attempt to complete the op again
            op.complete(error=error)

            # Results in failure
            assert handle_exceptions.handle_background_exception.call_count == 1
            assert (
                type(handle_exceptions.handle_background_exception.call_args[0][0])
                is pipeline_exceptions.OperationError
            )

            # The operation state is unchanged
            assert op.error is original_op_err_state
            assert op.completed is origianl_op_completion_state

        @pytest.mark.it(
            "Sends an OperationError to the background exception handler, without making any changes to the operation, if the operation is already in the process of completing"
        )
        def test_already_completing(self, mocker, op, error):
            mocker.spy(handle_exceptions, "handle_background_exception")

            def cb(op, error):
                # Get the operation state
                origianl_op_err_state = op.error
                original_op_completion_state = op.completed

                # Attempt to complete the operation again while it is already in the process of completing
                op.complete(error=error)

                # The operation state is unchanged
                assert op.error is origianl_op_err_state
                assert op.completed is original_op_completion_state

            cb_mock = mocker.MagicMock(side_effect=cb)

            op.add_callback(cb_mock)
            op.complete(error=error)

            # Using the above callback resulted in failure
            assert cb_mock.call_count == 1
            assert handle_exceptions.handle_background_exception.call_count == 1
            assert (
                type(handle_exceptions.handle_background_exception.call_args[0][0])
                is pipeline_exceptions.OperationError
            )

        @pytest.mark.it(
            "Sends an OperationError to the background exception handler if the operation is somehow completed while still undergoing the process of completion"
        )
        def test_invalid_complete_during_completion(self, mocker, op, error):
            # This should never happen, as this is an invalid scenario, and could only happen due
            # to a bug elsewhere in the code (e.g. manually change the boolean, as in this test)

            mocker.spy(handle_exceptions, "handle_background_exception")

            def cb(op, error):
                op.completed = True

            cb_mock = mocker.MagicMock(side_effect=cb)

            op.add_callback(cb_mock)
            op.complete(error=error)

            assert cb_mock.call_count == 1
            assert handle_exceptions.handle_background_exception.call_count == 1
            assert (
                type(handle_exceptions.handle_background_exception.call_args[0][0])
                is pipeline_exceptions.OperationError
            )

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
            assert op.error is None
            assert cb_mock.call_count == 1
            # Callback was called passing 'None' as the error
            assert cb_mock.call_args == mocker.call(op=op, error=None)

    @pytest.mark.describe("{} - .halt_completion()".format(op_class_under_test.__name__))
    class OperationHaltCompletionTests(OperationTestConfigClass):
        @pytest.fixture(
            params=["Currently completing with no error", "Currently completing with error"]
        )
        def error(self, request, arbitrary_exception):
            if request.param == "Currently completing with no error":
                return None
            else:
                return arbitrary_exception

        @pytest.mark.it(
            "Marks the operation as no longer completing by setting the 'completing' attribute to False, if the operation is currently in the process of completion"
        )
        def test_sets_completing_false(self, mocker, op, error):
            mocker.spy(handle_exceptions, "handle_background_exception")

            def cb(op, error):
                assert op.completing
                assert not op.completed
                op.halt_completion()
                assert not op.completing

            cb_mock = mocker.MagicMock(side_effect=cb)
            op.add_callback(cb_mock)

            op.complete(error=error)

            assert not op.completing
            assert not op.completed
            assert cb_mock.call_count == 1

            # Because exceptions raised in callbacks are caught and sent to the background exception handler,
            # the assertion in the above callback won't be able to directly raise AssertionErrors that will
            # allow for testing normally. Instead we should check the background_exception_handler to see if
            # any of the assertions raised errors and sent them there.
            assert handle_exceptions.handle_background_exception.call_count == 0

        @pytest.mark.it(
            "Clears the existing error in the operation's 'error' attribute, if the operation is currently in the process of completion with error"
        )
        def test_clears_error(self, mocker, op, error):
            mocker.spy(handle_exceptions, "handle_background_exception")
            completion_error = error

            def cb(op, error):
                assert op.completing
                assert op.error is completion_error
                op.halt_completion()
                assert not op.completing
                assert op.error is None

            cb_mock = mocker.MagicMock(side_effect=cb)
            op.add_callback(cb_mock)

            op.complete(error=completion_error)

            assert op.error is None
            assert cb_mock.call_count == 1

            # Because exceptions raised in callbacks are caught and sent to the background exception handler,
            # the assertion in the above callback won't be able to directly raise AssertionErrors that will
            # allow for testing normally. Instead we should check the background_exception_handler to see if
            # any of the assertions raised errors and sent them there.
            assert handle_exceptions.handle_background_exception.call_count == 0

        @pytest.mark.it(
            "Sends an OperationError to the background exception handler if the operation has already been fully completed"
        )
        def test_already_completed_op(self, mocker, op):
            mocker.spy(handle_exceptions, "handle_background_exception")

            op.complete()
            assert op.completed
            op.halt_completion()

            assert handle_exceptions.handle_background_exception.call_count == 1
            assert (
                type(handle_exceptions.handle_background_exception.call_args[0][0])
                is pipeline_exceptions.OperationError
            )

        @pytest.mark.it(
            "Sends an OperationError to the background exception handler if the operation has never been completed"
        )
        def test_never_completed_op(self, mocker, op):
            mocker.spy(handle_exceptions, "handle_background_exception")

            op.halt_completion()

            assert handle_exceptions.handle_background_exception.call_count == 1
            assert (
                type(handle_exceptions.handle_background_exception.call_args[0][0])
                is pipeline_exceptions.OperationError
            )

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
        "Test{}HaltCompletion".format(op_class_under_test.__name__),
        OperationHaltCompletionTests,
    )
    setattr(
        test_module,
        "Test{}SpawnWorkerOp".format(op_class_under_test.__name__),
        OperationSpawnWorkerOpTests,
    )
