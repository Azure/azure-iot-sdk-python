# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains tools for working with Shared Access Signature (SAS) Tokens"""

import abc
import asyncio
import logging
import time
import urllib.parse
from typing import Dict, List, Optional, Awaitable, Callable, cast
from .custom_typing import FunctionOrCoroutine
from .signing_mechanism import SigningMechanism


logger = logging.getLogger(__name__)

DEFAULT_TOKEN_UPDATE_MARGIN: int = 120
REQUIRED_SASTOKEN_FIELDS: List[str] = ["sr", "sig", "se"]
TOKEN_FORMAT: str = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}"


class SasTokenError(Exception):
    """Error in SasToken"""

    pass


class SasToken:
    def __init__(self, sastoken_str: str) -> None:
        """Create a SasToken object from a SAS Token string
        :param str sastoken_str: The SAS Token string

        :raises: ValueError if SAS Token string is invalid
        """
        self._token_str: str = sastoken_str
        self._token_info: Dict[str, str] = _get_sastoken_info_from_string(sastoken_str)

    def __str__(self) -> str:
        return self._token_str

    def is_expired(self):
        return time.time() >= self.expiry_time

    @property
    def expiry_time(self) -> float:
        # NOTE: Time is typically expressed in float in Python, even though a
        # SAS Token expiry time should be a whole number.
        return float(self._token_info["se"])

    @property
    def resource_uri(self) -> str:
        uri = self._token_info["sr"]
        return urllib.parse.unquote(uri)

    @property
    def signature(self) -> str:
        signature = self._token_info["sig"]
        return urllib.parse.unquote(signature)


class SasTokenGenerator(abc.ABC):
    @abc.abstractmethod
    async def generate_sastoken(self):
        pass


# TODO: SigningMechanismSasTokenGenerator?
class InternalSasTokenGenerator(SasTokenGenerator):
    def __init__(self, signing_mechanism: SigningMechanism, uri: str, ttl: int = 3600) -> None:
        """An object that can generate SasTokens using provided values

        :param str uri: The URI of the resource you are generating a tokens to access
        :param signing_mechanism: The signing mechanism that will be used to sign data
        :type signing mechanism: :class:`SigningMechanism`
        :param int ttl: Time to live for generated tokens, in seconds (default 3600)
        """
        self.signing_mechanism = signing_mechanism
        self.uri = uri
        self.ttl = ttl

    async def generate_sastoken(self) -> SasToken:
        """Generate a new SasToken

        :raises: SasTokenError if the token cannot be generated
        """
        expiry_time = int(time.time()) + self.ttl
        url_encoded_uri = urllib.parse.quote(self.uri, safe="")
        message = url_encoded_uri + "\n" + str(expiry_time)
        try:
            signature = await self.signing_mechanism.sign(message)
        except Exception as e:
            # Because of variant signing mechanisms, we don't know what error might be raised.
            # So we catch all of them.
            raise SasTokenError("Unable to generate SasToken") from e
        url_encoded_signature = urllib.parse.quote(signature, safe="")
        token_str = TOKEN_FORMAT.format(
            resource=url_encoded_uri,
            signature=url_encoded_signature,
            expiry=str(expiry_time),
        )
        return SasToken(token_str)


class ExternalSasTokenGenerator(SasTokenGenerator):
    # TODO: need more specificity in generator_fn
    def __init__(self, generator_fn: FunctionOrCoroutine):
        """An object that can generate SasTokens by invoking a provided callable.
        This callable can be a function or a coroutine function.

        :param generator_fn: A callable that takes no arguments and returns a SAS Token string
        :type generator_fn: Function or Coroutine Function which returns a string
        """
        self.generator_fn = generator_fn

    async def generate_sastoken(self) -> SasToken:
        """Generate a new SasToken

        :raises: SasTokenError if the token cannot be generated
        """
        try:
            # NOTE: the typechecker has some problems here, so we help it with a cast.
            if asyncio.iscoroutinefunction(self.generator_fn):
                generator_fn = cast(Callable[[], Awaitable[str]], self.generator_fn)
                token_str = await generator_fn()
            else:
                generator_coro_fn = cast(Callable[[], str], self.generator_fn)
                token_str = generator_coro_fn()
            return SasToken(token_str)
        except Exception as e:
            raise SasTokenError("Unable to generate SasToken") from e


class SasTokenProvider:
    def __init__(self, generator: SasTokenGenerator) -> None:
        """Object responsible for providing a valid SasToken.

        :param generator: A SasTokenGenerator to generate SasTokens with
        :type generator: SasTokenGenerator
        """
        # NOTE: There is no good way to invoke a coroutine from within the __init__, and since
        # the the generator's .sign() method is a coroutine, that means we can't generate an
        # initial token from it here. Thus, we have to take the initial token as a separate
        # argument.
        # However, this is inconvenient, and also prevents us from fast-failing if there's a
        # problem with the generator_fn, so a factory coroutine method has been implemented.
        self._event_loop = asyncio.get_running_loop()
        self._generator = generator
        self._token_update_margin = DEFAULT_TOKEN_UPDATE_MARGIN
        self._new_sastoken_available = asyncio.Condition()

        # Will be set upon `.start()`
        self._current_token: Optional[SasToken] = None
        self._keep_token_fresh_bg_task: Optional[asyncio.Task[None]] = None

    async def _keep_token_fresh(self):
        """Runs indefinitely and will generate a SasToken when the current one gets close to
        expiration (based on the update margin)
        """
        generate_time = self._current_token.expiry_time - self._token_update_margin
        while True:
            await _wait_until(generate_time)
            try:
                logger.debug("Updating SAS Token...")
                self._current_token = await self._generator.generate_sastoken()
                logger.debug("SAS Token update succeeded")
                # TODO: validate that this is a valid token?
                generate_time = self._current_token.expiry_time - self._token_update_margin
                async with self._new_sastoken_available:
                    self._new_sastoken_available.notify_all()
            except Exception:
                logger.error("SAS Token renewal failed. Trying again in 10 seconds")
                generate_time = time.time() + 10

    async def start(self):
        """Begin running the SasTokenProvider, ensuring that the current token is always valid"""
        if not self._keep_token_fresh_bg_task:
            logger.debug("Starting SasTokenProvider")
            initial_token = await self._generator.generate_sastoken()
            if initial_token.expiry_time < time.time():
                raise SasTokenError("Newly generated SAS Token has already expired")
            self._current_token = initial_token
            async with self._new_sastoken_available:
                self._new_sastoken_available.notify_all()
            self._keep_token_fresh_bg_task = asyncio.create_task(self._keep_token_fresh())
        else:
            logger.debug("SasTokenProvider already running, no need to start")

    async def stop(self):
        """Stop running the SasTokenProvider, clearing the current token.
        Does nothing if already stopped.
        """
        # Cancel and wait for cancellation to complete
        if self._keep_token_fresh_bg_task:
            logger.debug("Stopping SasTokenProvider")
            self._keep_token_fresh_bg_task.cancel()
            await asyncio.gather(self._keep_token_fresh_bg_task, return_exceptions=True)
            self._keep_token_fresh_bg_task = None
            # NOTE: There is an argument to be made that this value shouldn't be cleared,
            # as the SasTokenProvider may be started again while it remains valid, but for
            # now, we clear it for simplicity.
            self._current_token = None
        else:
            logger.debug("SasTokenProvider was not running, no need to stop")

    def get_current_sastoken(self) -> SasToken:
        """Return the current SasToken"""
        if self._current_token:
            return self._current_token
        else:
            raise RuntimeError("SasTokenProvider is not running")

    async def wait_for_new_sastoken(self) -> SasToken:
        """Waits for a new SasToken to become available, and return it"""
        async with self._new_sastoken_available:
            await self._new_sastoken_available.wait()
        return self.get_current_sastoken()


def _get_sastoken_info_from_string(sastoken_string: str) -> Dict[str, str]:
    """Given a SAS Token string, return a dictionary of it's keys and values"""
    pieces = sastoken_string.split("SharedAccessSignature ")
    if len(pieces) != 2:
        raise ValueError("Invalid SAS Token string: Not a SAS Token ")

    # Get sastoken info as dictionary
    try:
        # TODO: fix this typehint later, it needs some kind of cast
        sastoken_info = dict(map(str.strip, sub.split("=", 1)) for sub in pieces[1].split("&"))  # type: ignore
    except Exception as e:
        raise ValueError("Invalid SAS Token string: Incorrectly formatted") from e

    # Validate that all required fields are present
    if not all(key in sastoken_info for key in REQUIRED_SASTOKEN_FIELDS):
        raise ValueError("Invalid SAS Token string: Not all required fields present")

    # Warn if extraneous fields are present
    if not all(key in REQUIRED_SASTOKEN_FIELDS for key in sastoken_info):
        logger.warning("Unexpected fields present in SAS Token")

    return sastoken_info


# NOTE: Arguably, this doesn't really belong in this module, give it's lack of a specific
# relationship to SAS Tokens, and the fact that it needs to be unit-tested separately.
# These things suggest it should be more than just a convention-private helper, however
# its hard to justify making a separate module just for this function.
# This would be a candidate for some kind of misc utility module if other similar functions
# pop up over the course of development. Until then, it lives here.
async def _wait_until(when: float) -> None:
    """Wait until a specific time has passed (accurate within 1 second).

    :param float when: The time to wait for, in seconds, since epoch
    """
    while time.time() < when:
        await asyncio.sleep(1)
