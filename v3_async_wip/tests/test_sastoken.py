# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import logging
import pytest
import sys
import time
import urllib.parse
from pytest_lazyfixture import lazy_fixture
from v3_async_wip.sastoken import (
    SasToken,
    InternalSasTokenGenerator,
    ExternalSasTokenGenerator,
    SasTokenProvider,
    SasTokenError,
    TOKEN_FORMAT,
    DEFAULT_TOKEN_UPDATE_MARGIN,
)
from v3_async_wip import sastoken as st

logging.basicConfig(level=logging.DEBUG)

FAKE_URI = "some/resource/location"
FAKE_SIGNED_DATA = "8NJRMT83CcplGrAGaUVIUM/md5914KpWVNngSVoF9/M="
FAKE_SIGNED_DATA2 = "ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI="
FAKE_CURRENT_TIME = 10000000000.0  # We living in 2286!


def token_parser(token_str):
    """helper function that parses a token string for individual values"""
    token_map = {}
    kv_string = token_str.split(" ")[1]
    kv_pairs = kv_string.split("&")
    for kv in kv_pairs:
        t = kv.split("=")
        token_map[t[0]] = t[1]
    return token_map


def get_expiry_time():
    return int(time.time()) + 3600  # One hour from right now,


@pytest.fixture
def sastoken_str():
    return TOKEN_FORMAT.format(
        resource=urllib.parse.quote(FAKE_URI, safe=""),
        signature=urllib.parse.quote(FAKE_SIGNED_DATA, safe=""),
        expiry=get_expiry_time(),
    )


@pytest.fixture
def sastoken(sastoken_str):
    return SasToken(sastoken_str)


@pytest.fixture
async def mock_signing_mechanism(mocker):
    mock_sm = mocker.AsyncMock()
    mock_sm.sign.return_value = FAKE_SIGNED_DATA
    return mock_sm


@pytest.fixture(params=["Generator Function", "Generator Coroutine Function"])
def mock_token_generator_fn(mocker, request, sastoken_str):
    if request.param == "Function":
        return mocker.MagicMock(return_value=sastoken_str)
    else:
        return mocker.AsyncMock(return_value=sastoken_str)


@pytest.fixture(params=["InternalSasTokenGenerator", "ExternalSasTokenGenerator"])
def sastoken_generator(request, mocker, mock_signing_mechanism, sastoken_str):
    if request.param == "ExternalSasTokenGenerator":
        # We don't care about the difference between sync/async generator_fns when testing
        # at this level of abstraction, so just pick one
        generator = ExternalSasTokenGenerator(mocker.MagicMock(return_value=sastoken_str))
    else:
        generator = InternalSasTokenGenerator(mock_signing_mechanism, FAKE_URI)
    mocker.spy(generator, "generate_sastoken")
    return generator


@pytest.fixture
async def sastoken_provider(sastoken_generator):
    provider = SasTokenProvider(sastoken_generator)
    await provider.start()
    # Creating from the generator invokes a call on the generator, so reset the spy mock
    # so it doesn't throw off any testing logic
    provider._generator.generate_sastoken.reset_mock()
    yield provider
    await provider.stop()


@pytest.mark.describe("SasToken")
class TestSasToken:
    @pytest.mark.it("Instantiates from a valid SAS Token string")
    def test_instantiates_from_token_string(self, sastoken_str):
        s = SasToken(sastoken_str)
        assert s._token_str == sastoken_str

    @pytest.mark.it("Raises a ValueError error if instantiating from an invalid SAS Token string")
    @pytest.mark.parametrize(
        "invalid_token_str",
        [
            pytest.param(
                "sr=some%2Fresource%2Flocation&sig=ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI=&se=12321312",
                id="Incomplete token format",
            ),
            pytest.param(
                "SharedERRORSignature sr=some%2Fresource%2Flocation&sig=ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI=&se=12321312",
                id="Invalid token format",
            ),
            pytest.param(
                "SharedAccessignature sr=some%2Fresource%2Flocationsig=ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI=&se12321312",
                id="Token values incorectly formatted",
            ),
            pytest.param(
                "SharedAccessSignature sig=ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI=&se=12321312",
                id="Missing resource value",
            ),
            pytest.param(
                "SharedAccessSignature sr=some%2Fresource%2Flocation&se=12321312",
                id="Missing signature value",
            ),
            pytest.param(
                "SharedAccessSignature sr=some%2Fresource%2Flocation&sig=ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI=",
                id="Missing expiry value",
            ),
        ],
    )
    def test_raises_error_invalid_token_string(self, invalid_token_str):
        with pytest.raises(ValueError):
            SasToken(invalid_token_str)

    @pytest.mark.it("Returns the SAS token string as the string representation of the object")
    def test_str_rep(self, sastoken_str):
        sastoken = SasToken(sastoken_str)
        assert str(sastoken) == sastoken_str

    @pytest.mark.it(
        "Instantiates with the .expiry_time property corresponding to the expiry time of the given SAS Token string (as a float)"
    )
    def test_instantiates_expiry_time(self, sastoken_str):
        sastoken = SasToken(sastoken_str)
        expected_expiry_time = token_parser(sastoken_str)["se"]
        assert sastoken.expiry_time == float(expected_expiry_time)

    @pytest.mark.it("Maintains .expiry_time as a read-only property")
    def test_expiry_time_read_only(self, sastoken):
        with pytest.raises(AttributeError):
            sastoken.expiry_time = 12312312312123

    @pytest.mark.it(
        "Instantiates with the .resource_uri property corresponding to the URL decoded URI of the given SAS Token string"
    )
    def test_instantiates_resource_uri(self, sastoken_str):
        sastoken = SasToken(sastoken_str)
        resource_uri = token_parser(sastoken_str)["sr"]
        assert resource_uri != sastoken.resource_uri
        assert resource_uri == urllib.parse.quote(sastoken.resource_uri, safe="")
        assert urllib.parse.unquote(resource_uri) == sastoken.resource_uri

    @pytest.mark.it("Maintains .resource_uri as a read-only property")
    def test_resource_uri_read_only(self, sastoken):
        with pytest.raises(AttributeError):
            sastoken.resource_uri = "new%2Ffake%2Furi"

    @pytest.mark.it(
        "Instantiates with the .signature property corresponding to the URL decoded signature of the given SAS Token string"
    )
    def test_instantiates_signature(self, sastoken_str):
        sastoken = SasToken(sastoken_str)
        signature = token_parser(sastoken_str)["sig"]
        assert signature != sastoken.signature
        assert signature == urllib.parse.quote(sastoken.signature, safe="")
        assert urllib.parse.unquote(signature) == sastoken.signature

    @pytest.mark.it("Maintains .signature as a read-only property")
    def test_signature_read_only(self, sastoken):
        with pytest.raises(AttributeError):
            sastoken.signature = "asdfas"


@pytest.mark.describe("InternalSasTokenGenerator -- Instantiation")
class TestSasTokenGeneratorInstantiation:
    @pytest.mark.it("Stores the provided signing mechanism as an attribute")
    def test_signing_mechanism(self, mock_signing_mechanism):
        generator = InternalSasTokenGenerator(
            signing_mechanism=mock_signing_mechanism, uri=FAKE_URI, ttl=4700
        )
        assert generator.signing_mechanism is mock_signing_mechanism

    @pytest.mark.it("Stores the provided URI as an attribute")
    def test_uri(self, mock_signing_mechanism):
        generator = InternalSasTokenGenerator(
            signing_mechanism=mock_signing_mechanism, uri=FAKE_URI, ttl=4700
        )
        assert generator.uri == FAKE_URI

    @pytest.mark.it("Stores the provided TTL as an attribute")
    def test_ttl(self, mock_signing_mechanism):
        generator = InternalSasTokenGenerator(
            signing_mechanism=mock_signing_mechanism, uri=FAKE_URI, ttl=4700
        )
        assert generator.ttl == 4700

    @pytest.mark.it("Defaults to using 3600 as the TTL if not provided")
    def test_ttl_default(self, mock_signing_mechanism):
        generator = InternalSasTokenGenerator(
            signing_mechanism=mock_signing_mechanism, uri=FAKE_URI
        )
        assert generator.ttl == 3600


@pytest.mark.describe("InternalSasTokenGenerator - .generate_sastoken()")
class TestSasTokenGeneratorGenerateSastoken:
    @pytest.fixture
    def sastoken_generator(self, mock_signing_mechanism):
        return InternalSasTokenGenerator(
            signing_mechanism=mock_signing_mechanism, uri=FAKE_URI, ttl=4700
        )

    @pytest.mark.it(
        "Returns a newly generated SasToken for the configured URI that is valid for TTL seconds"
    )
    async def test_token_expiry(self, mocker, sastoken_generator):
        # Patch time.time() to return a fake time so that it's easy to check the delta with expiry
        mocker.patch.object(time, "time", return_value=FAKE_CURRENT_TIME)
        expected_expiry = FAKE_CURRENT_TIME + sastoken_generator.ttl
        token = await sastoken_generator.generate_sastoken()
        assert isinstance(token, SasToken)
        assert token.expiry_time == expected_expiry
        assert token.resource_uri == sastoken_generator.uri
        assert token._token_info["sr"] == urllib.parse.quote(sastoken_generator.uri, safe="")
        assert token.resource_uri != token._token_info["sr"]

    @pytest.mark.it(
        "Creates the resulting SasToken's signature by using the InternalSasTokenGenerator's signing mechanism to sign a concatenation of the (URL encoded) URI and (URL encoded, int converted) desired expiry time"
    )
    async def test_token_signature(self, mocker, sastoken_generator):
        assert sastoken_generator.signing_mechanism.await_count == 0
        mocker.patch.object(time, "time", return_value=FAKE_CURRENT_TIME)
        expected_expiry = int(FAKE_CURRENT_TIME + sastoken_generator.ttl)
        expected_data_to_sign = (
            urllib.parse.quote(sastoken_generator.uri, safe="") + "\n" + str(expected_expiry)
        )

        token = await sastoken_generator.generate_sastoken()

        assert sastoken_generator.signing_mechanism.sign.await_count == 1
        assert sastoken_generator.signing_mechanism.sign.await_args == mocker.call(
            expected_data_to_sign
        )
        assert token._token_info["sig"] == urllib.parse.quote(
            sastoken_generator.signing_mechanism.sign.return_value, safe=""
        )
        assert token.signature == sastoken_generator.signing_mechanism.sign.return_value
        assert token.signature != token._token_info["sig"]

    @pytest.mark.it("Raises a SasTokenError if an exception is raised by the signing mechanism")
    async def test_signing_mechanism_raises(self, sastoken_generator, arbitrary_exception):
        sastoken_generator.signing_mechanism.sign.side_effect = arbitrary_exception

        with pytest.raises(SasTokenError) as e_info:
            await sastoken_generator.generate_sastoken()
        assert e_info.value.__cause__ is arbitrary_exception


@pytest.mark.describe("ExternalSasTokenGenerator -- Instantiation")
class TestExternalSasTokenGeneratorInstantiation:
    @pytest.mark.it("Stores the provided generator_fn callable as an attribute")
    def test_generator_fn_attribute(self, mock_token_generator_fn):
        sastoken_generator = ExternalSasTokenGenerator(mock_token_generator_fn)
        assert sastoken_generator.generator_fn is mock_token_generator_fn


@pytest.mark.describe("ExternalSasTokenGenerator -- .generate_sastoken()")
class TestExternalSasTokenGeneratorGenerateSasToken:
    @pytest.fixture
    def sastoken_generator(self, mock_token_generator_fn):
        return ExternalSasTokenGenerator(mock_token_generator_fn)

    @pytest.mark.it(
        "Generates a new SasToken from the SAS Token string returned by the configured generator_fn callable"
    )
    async def test_returns_token(self, mocker, sastoken_generator):
        if isinstance(sastoken_generator.generator_fn, mocker.AsyncMock):
            assert sastoken_generator.generator_fn.await_count == 0
        else:
            assert sastoken_generator.generator_fn.call_count == 0

        token = await sastoken_generator.generate_sastoken()
        assert isinstance(token, SasToken)

        if isinstance(sastoken_generator.generator_fn, mocker.AsyncMock):
            assert sastoken_generator.generator_fn.await_count == 1
            assert sastoken_generator.generator_fn.await_args == mocker.call()
        else:
            assert sastoken_generator.generator_fn.call_count == 1
            assert sastoken_generator.generator_fn.call_args == mocker.call()

        assert str(token) == sastoken_generator.generator_fn.return_value

    @pytest.mark.it(
        "Raises SasTokenError if an exception is raised while trying to generate a SAS Token string with the generator_fn"
    )
    async def test_generator_fn_raises(self, sastoken_generator, arbitrary_exception):
        sastoken_generator.generator_fn.side_effect = arbitrary_exception

        with pytest.raises(SasTokenError) as e_info:
            await sastoken_generator.generate_sastoken()
        assert e_info.value.__cause__ is arbitrary_exception

    @pytest.mark.it("Raises SasTokenError if the generated SAS Token string is invalid")
    async def test_invalid_token(self, sastoken_generator):
        sastoken_generator.generator_fn.return_value = "not a sastoken"

        with pytest.raises(SasTokenError) as e_info:
            await sastoken_generator.generate_sastoken()
        assert isinstance(e_info.value.__cause__, ValueError)


@pytest.mark.describe("SasTokenProvider -- Instantiation")
class TestSasTokenProviderInstantiation:
    @pytest.mark.it("Stores the provided SasTokenGenerator")
    async def test_generator_fn(self, sastoken_generator):
        provider = SasTokenProvider(sastoken_generator)
        assert provider._generator is sastoken_generator

    @pytest.mark.it("Sets the token update margin to the DEFAULT_TOKEN_UPDATE_MARGIN")
    async def test_token_update_margin(self, sastoken, sastoken_generator):
        provider = SasTokenProvider(sastoken_generator)
        assert provider._token_update_margin == DEFAULT_TOKEN_UPDATE_MARGIN

    @pytest.mark.it("Sets the current token to None")
    async def test_current_token(self, sastoken_generator):
        provider = SasTokenProvider(sastoken_generator)
        assert provider._current_token is None

    @pytest.mark.it("Sets the 'keep token fresh' background task attribute to None")
    async def test_background_task(self, sastoken_generator):
        provider = SasTokenProvider(sastoken_generator)
        assert provider._keep_token_fresh_bg_task is None


@pytest.mark.describe("SasTokenProvider - .start()")
class TestSasTokenProviderStart:
    @pytest.mark.it(
        "Generates a new SasToken using the stored SasTokenGenerator and sets it as the current token"
    )
    async def test_generates_current_token(self, mocker, sastoken_generator):
        provider = SasTokenProvider(sastoken_generator)
        assert sastoken_generator.generate_sastoken.await_count == 0

        await provider.start()

        assert sastoken_generator.generate_sastoken.await_count == 1
        assert sastoken_generator.generate_sastoken.await_args == mocker.call()
        assert isinstance(provider._current_token, SasToken)
        assert provider._current_token == sastoken_generator.generate_sastoken.spy_return

        # Cleanup
        await provider.stop()

    @pytest.mark.it("Sends notification of new token availability")
    async def test_notify(self, mocker, sastoken_generator):
        provider = SasTokenProvider(sastoken_generator)
        notification_spy = mocker.spy(provider._new_sastoken_available, "notify_all")
        assert notification_spy.call_count == 0

        await provider.start()

        assert notification_spy.call_count == 1

    @pytest.mark.it("Allows any exception raised while trying to generate a SasToken to propagate")
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(SasTokenError("token error"), id="SasTokenError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
        ],
    )
    async def test_generation_raises(self, sastoken_generator, exception):
        sastoken_generator.generate_sastoken.side_effect = exception
        provider = SasTokenProvider(sastoken_generator)

        with pytest.raises(type(exception)) as e_info:
            await provider.start()
        assert e_info.value is exception

    @pytest.mark.it("Raises a SasTokenError if the generated SAS Token string has already expired")
    async def test_expired_token(self, mocker, sastoken_generator):
        expired_token_str = TOKEN_FORMAT.format(
            resource=urllib.parse.quote(FAKE_URI, safe=""),
            signature=urllib.parse.quote(FAKE_SIGNED_DATA, safe=""),
            expiry=int(time.time()) - 3600,  # 1 hour ago
        )
        sastoken_generator.generate_sastoken = mocker.AsyncMock()
        sastoken_generator.generate_sastoken.return_value = SasToken(expired_token_str)
        provider = SasTokenProvider(sastoken_generator)

        with pytest.raises(SasTokenError):
            await provider.start()

    # NOTE: The contents of this coroutine are tested in a separate test suite below.
    # See TestSasTokenProviderKeepTokenFresh for more.
    @pytest.mark.it("Begins running the ._keep_token_fresh() coroutine method, storing the task")
    async def test_keep_token_fresh_running(self, sastoken_generator):
        provider = SasTokenProvider(sastoken_generator)
        assert provider._keep_token_fresh_bg_task is None

        await provider.start()

        assert isinstance(provider._keep_token_fresh_bg_task, asyncio.Task)
        assert not provider._keep_token_fresh_bg_task.done()
        if sys.version_info >= (3, 8):
            # NOTE: There isn't a way to validate the contents of a task until 3.8
            # as far as I can tell.
            task_coro = provider._keep_token_fresh_bg_task.get_coro()
            assert task_coro.__qualname__ == "SasTokenProvider._keep_token_fresh"

        # Cleanup
        await provider.stop()

    @pytest.mark.it("Does nothing if already started")
    async def test_already_started(self, sastoken_generator):
        provider = SasTokenProvider(sastoken_generator)

        # Start
        await provider.start()

        # Expected state
        assert isinstance(provider._keep_token_fresh_bg_task, asyncio.Task)
        assert not provider._keep_token_fresh_bg_task.done()
        current_keep_token_fresh_bg_task = provider._keep_token_fresh_bg_task
        assert sastoken_generator.generate_sastoken.await_count == 1

        # Start again
        await provider.start()

        # No changes
        assert provider._keep_token_fresh_bg_task is current_keep_token_fresh_bg_task
        assert not provider._keep_token_fresh_bg_task.done()
        assert sastoken_generator.generate_sastoken.await_count == 1


@pytest.mark.describe("SasTokenProvider - .stop()")
class TestSasTokenProviderShutdown:
    @pytest.mark.it("Cancels the stored ._keep_token_fresh() task and removes it, if it exists")
    async def test_cancels_keep_token_fresh(self, sastoken_provider):
        t = sastoken_provider._keep_token_fresh_bg_task
        assert isinstance(t, asyncio.Task)
        assert not t.done()

        await sastoken_provider.stop()

        assert t.done()
        assert t.cancelled()
        assert sastoken_provider._keep_token_fresh_bg_task is None

    @pytest.mark.it("Sets the current token back to None")
    async def test_current_token(self, sastoken_provider):
        assert sastoken_provider._current_token is not None

        await sastoken_provider.stop()

        assert sastoken_provider._current_token is None

    @pytest.mark.it("Does nothing if already stopped")
    async def test_already_stopped(self, sastoken_provider):
        # Currently running
        t = sastoken_provider._keep_token_fresh_bg_task
        assert not t.done()

        # Stop
        await sastoken_provider.stop()

        # Expected state
        assert t.done()
        assert t.cancelled()
        assert sastoken_provider._keep_token_fresh_bg_task is None
        assert sastoken_provider._current_token is None

        # Stop again
        await sastoken_provider.stop()

        # No changes
        assert sastoken_provider._keep_token_fresh_bg_task is None
        assert sastoken_provider._current_token is None


@pytest.mark.describe("SasTokenProvider - .get_current_sastoken()")
class TestSasTokenGetCurrentSasToken:
    @pytest.mark.it("Returns the current SasToken object, if running")
    def test_returns_current_token(self, sastoken_provider):
        assert sastoken_provider._keep_token_fresh_bg_task is not None
        current_token = sastoken_provider.get_current_sastoken()
        assert current_token is sastoken_provider._current_token
        new_token_str = TOKEN_FORMAT.format(
            resource=urllib.parse.quote(FAKE_URI, safe=""),
            signature=urllib.parse.quote(FAKE_SIGNED_DATA, safe=""),
            expiry=int(time.time()) + 3600,
        )
        new_token = SasToken(new_token_str)
        sastoken_provider._current_token = new_token
        assert sastoken_provider.get_current_sastoken() is new_token

    @pytest.mark.it("Raises RuntimeError if not running (i.e. not started)")
    async def test_not_running(self, sastoken_generator):
        provider = SasTokenProvider(sastoken_generator)
        assert provider._keep_token_fresh_bg_task is None
        with pytest.raises(RuntimeError):
            provider.get_current_sastoken()


@pytest.mark.describe("SasTokenProvider - .wait_for_new_sastoken()")
class TestSasTokenWaitForNewSasToken:
    @pytest.mark.it(
        "Returns the current SasToken object once a notified of a new token being available"
    )
    async def test_returns_new_current_token(self, sastoken_provider):
        token_str_1 = TOKEN_FORMAT.format(
            resource=urllib.parse.quote(FAKE_URI, safe=""),
            signature=urllib.parse.quote(FAKE_SIGNED_DATA, safe=""),
            expiry=int(time.time()) + 3600,
        )
        token1 = SasToken(token_str_1)
        token_str_2 = TOKEN_FORMAT.format(
            resource=urllib.parse.quote(FAKE_URI, safe=""),
            signature=urllib.parse.quote(FAKE_SIGNED_DATA2, safe=""),
            expiry=int(time.time()) + 4500,
        )
        token2 = SasToken(token_str_2)

        sastoken_provider._current_token = token1
        assert sastoken_provider.get_current_sastoken() is token1

        # Waiting for new token, but one is not yet available
        task = asyncio.create_task(sastoken_provider.wait_for_new_sastoken())
        await asyncio.sleep(0.1)
        assert not task.done()

        # Update the token, but without notification, the waiting task still does not return
        sastoken_provider._current_token = token2
        await asyncio.sleep(0.1)
        assert not task.done()

        # Notify that a new token is available, and now the task will return
        async with sastoken_provider._new_sastoken_available:
            sastoken_provider._new_sastoken_available.notify_all()
        returned_token = await task

        # The task returned the new token
        assert returned_token is token2
        assert returned_token is not token1
        assert returned_token is sastoken_provider.get_current_sastoken()


# NOTE: This test suite assumes the correct implementation of ._wait_until() for critical
# requirements. Find it tested in a separate suite below (TestWaitUntil)
@pytest.mark.describe("SasTokenProvider - BG TASK: ._keep_token_fresh")
class TestSasTokenProviderKeepTokenFresh:
    @pytest.fixture(autouse=True)
    def spy_time(self, mocker):
        """Spy on the time module so that we can find out last time that was returned"""
        spy_time = mocker.spy(time, "time")
        return spy_time

    # NOTE: This is an autouse fixture to ensure that it gets called first, since we want to make sure
    # this mock is running when the SasTokenProvider is created.
    @pytest.fixture(autouse=True)
    def mock_wait_until(self, mocker):
        """Mock out the wait_until function so these tests aren't dependent on real time passing"""
        mock_wait_until = mocker.patch.object(st, "_wait_until")
        mock_wait_until._allow_proceed = asyncio.Event()

        # Fake implementation that will wait for an explicit trigger to proceed, rather than the
        # passage of time
        async def fake_wait_until(when):
            await mock_wait_until._allow_proceed.wait()

        mock_wait_until.side_effect = fake_wait_until

        # Define a mechanism that will allow an explicit trigger to let the mocked coroutine return
        def proceed():
            mock_wait_until._allow_proceed.set()
            mock_wait_until._allow_proceed = asyncio.Event()

        mock_wait_until.proceed = proceed

        return mock_wait_until

    @pytest.mark.it(
        "Waits until the configured update margin number of seconds before current SasToken expiry to generate a new SasToken"
    )
    async def test_wait_to_generate(self, mocker, mock_wait_until, sastoken_provider):
        original_token = sastoken_provider.get_current_sastoken()
        assert sastoken_provider._generator.generate_sastoken.await_count == 0
        await asyncio.sleep(0.1)
        # We are waiting the expected amount of time
        expected_update_time = original_token.expiry_time - sastoken_provider._token_update_margin
        assert mock_wait_until.await_count == 1
        assert mock_wait_until.await_args == mocker.call(expected_update_time)
        # Allow the waiting to end, and a new token to be generated
        mock_wait_until.proceed()
        await asyncio.sleep(0.1)
        assert sastoken_provider._generator.generate_sastoken.await_count == 1
        assert sastoken_provider._generator.generate_sastoken.await_args == mocker.call()

    @pytest.mark.it(
        "Sets the newly generated SasToken as the new current SasToken and sends notification of its availability"
    )
    async def test_replace_token_and_notify(self, mocker, sastoken_provider, mock_wait_until):
        notification_spy = mocker.spy(sastoken_provider._new_sastoken_available, "notify_all")
        # We have the original token, as we have not yet generated a new one
        original_token = sastoken_provider.get_current_sastoken()
        assert sastoken_provider._generator.generate_sastoken.await_count == 0
        assert notification_spy.call_count == 0
        # Allow waiting to proceed, and a new token to be generated
        mock_wait_until.proceed()
        await asyncio.sleep(0.1)
        # A new token has now been generated
        assert sastoken_provider._generator.generate_sastoken.await_count == 1
        # The current token is now the token that was just generated
        current_token = sastoken_provider.get_current_sastoken()
        assert current_token is sastoken_provider._generator.generate_sastoken.spy_return
        # This token is not the same as the original token
        assert current_token is not original_token
        # A notification was sent about the new token
        assert notification_spy.call_count == 1

    @pytest.mark.it(
        "Waits until the configured update margin number of seconds before the NEW current SasToken expiry, after each time a new SasToken is generated, before once again generating a new SasToken"
    )
    async def test_wait_to_generate_again_and_again(
        self, mocker, mock_wait_until, sastoken_provider
    ):
        # Current token is the original, we have not yet generated a new one
        original_token = sastoken_provider.get_current_sastoken()
        assert sastoken_provider._generator.generate_sastoken.await_count == 0
        await asyncio.sleep(0.1)
        # We are waiting based on the original token's expiry time
        expected_update_time = original_token.expiry_time - sastoken_provider._token_update_margin
        assert mock_wait_until.await_count == 1
        assert mock_wait_until.await_args == mocker.call(expected_update_time)
        # Allow the waiting to end, and a new token to be generated
        mock_wait_until.proceed()
        await asyncio.sleep(0.1)
        assert sastoken_provider._generator.generate_sastoken.await_count == 1
        assert sastoken_provider._generator.generate_sastoken.await_args == mocker.call()
        # New token is the one that was just generated
        new_token = sastoken_provider.get_current_sastoken()
        assert new_token is sastoken_provider._generator.generate_sastoken.spy_return
        assert new_token is not original_token
        # We are once again waiting, this time based on the new token's expiry time
        expected_update_time = new_token.expiry_time - sastoken_provider._token_update_margin
        assert mock_wait_until.await_count == 2
        assert mock_wait_until.await_args == mocker.call(expected_update_time)
        # Allow the waiting to end and another new token to be generated
        mock_wait_until.proceed()
        await asyncio.sleep(0.1)
        assert sastoken_provider._generator.generate_sastoken.await_count == 2
        assert sastoken_provider._generator.generate_sastoken.await_args == mocker.call()
        # Newest token is the one that was just generated
        newest_token = sastoken_provider.get_current_sastoken()
        assert newest_token is sastoken_provider._generator.generate_sastoken.spy_return
        assert newest_token is not original_token
        assert newest_token is not new_token
        # We are once again waiting, this time based on the newest token's expiry time
        expected_update_time = newest_token.expiry_time - sastoken_provider._token_update_margin
        assert mock_wait_until.await_count == 3
        assert mock_wait_until.await_args == mocker.call(expected_update_time)
        # And so on and so forth to infinity...

    @pytest.mark.it(
        "Sets the newly generated SasToken as the new current SasToken and sends notification of its availability each time a new token is generated"
    )
    async def test_replace_token_and_notify_each_time(
        self, mocker, sastoken_provider, mock_wait_until
    ):
        notification_spy = mocker.spy(sastoken_provider._new_sastoken_available, "notify_all")
        # We have the original token, as we have not yet generated a new one
        original_token = sastoken_provider.get_current_sastoken()
        assert sastoken_provider._generator.generate_sastoken.await_count == 0
        assert notification_spy.call_count == 0
        # Allow waiting to proceed, and a new token to be generated
        mock_wait_until.proceed()
        await asyncio.sleep(0.1)
        # A new token has now been generated
        assert sastoken_provider._generator.generate_sastoken.await_count == 1
        # The current token is now the token that was just generated
        second_token = sastoken_provider.get_current_sastoken()
        assert second_token is sastoken_provider._generator.generate_sastoken.spy_return
        # This token is not the same as the original token
        assert second_token is not original_token
        # A notification was sent about the new token
        assert notification_spy.call_count == 1
        # Allow waiting to proceed and another new token to be generated
        mock_wait_until.proceed()
        await asyncio.sleep(0.1)
        # Another new token has now been generated
        assert sastoken_provider._generator.generate_sastoken.await_count == 2
        # The current token is now the token that was just generated
        third_token = sastoken_provider.get_current_sastoken()
        assert third_token is sastoken_provider._generator.generate_sastoken.spy_return
        # This token is not the same as any previous token
        assert third_token is not original_token
        assert third_token is not second_token
        # A notification was sent about the new token
        assert notification_spy.call_count == 2
        # And so on and so forth to infinity...

    @pytest.mark.it("Tries to generate again in 10 seconds if SasToken generation fails")
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(SasTokenError("Some error in SAS"), id="SasTokenError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
        ],
    )
    async def test_generation_failure(
        self, mocker, sastoken_provider, exception, mock_wait_until, spy_time
    ):
        # Set token generation to raise exception
        sastoken_provider._generator.generate_sastoken.side_effect = exception
        # Token generation has not yet happened
        assert sastoken_provider._generator.generate_sastoken.await_count == 0
        # Allow waiting to proceed, and a new token to be generated
        assert mock_wait_until.await_count == 1
        mock_wait_until.proceed()
        await asyncio.sleep(0.1)
        # Waits 10 seconds past the current time
        expected_generate_time = spy_time.spy_return + 10
        assert mock_wait_until.await_count == 2
        assert mock_wait_until.await_args == mocker.call(expected_generate_time)


# NOTE: We don't normally test convention-private helpers directly, but in this case, the
# complexity is high enough, and the function is critical enough, that it makes more sense
# to isolate rather than attempting to indirectly test.
@pytest.mark.describe("._wait_until()")
class TestWaitUntil:
    @pytest.mark.it(
        "Repeatedly does 1 second asyncio sleeps until the current time is greater than the provided 'when' parameter"
    )
    @pytest.mark.parametrize(
        "time_from_now",
        [
            pytest.param(5, id="5 seconds from now"),
            pytest.param(60, id="1 minute from now"),
            pytest.param(3600, id="1 hour from now"),
        ],
    )
    async def test_sleep(self, mocker, time_from_now):
        # Mock out the sleep coroutine so that we aren't waiting around forever on this test
        mock_sleep = mocker.patch.object(asyncio, "sleep")

        # mock out time
        def fake_time():
            """Fake time implementation that will return a time float that is 1 larger
            than the previous time it was called"""
            fake_time_return = FAKE_CURRENT_TIME
            while True:
                yield fake_time_return
                fake_time_return += 1

        fake_time_gen = fake_time()
        mock_time = mocker.patch.object(time, "time", side_effect=fake_time_gen)

        desired_time = FAKE_CURRENT_TIME + time_from_now

        await st._wait_until(desired_time)

        assert mock_sleep.await_count == time_from_now
        for call in mock_sleep.await_args_list:
            assert call == mocker.call(1)
        assert mock_time.call_count == time_from_now + 1
        for call in mock_time.call_args_list:
            assert call == mocker.call()
