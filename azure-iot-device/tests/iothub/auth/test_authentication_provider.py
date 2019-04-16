# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.device.iothub.auth.authentication_provider import AuthenticationProvider


def test_raises_exception_on_init_of_abstract_auth():
    with pytest.raises(TypeError) as error:
        AuthenticationProvider()
    msg = str(error.value)
    print(msg)
    expected_msg = "Can't instantiate abstract class AuthenticationProvider with abstract methods get_current_sas_token, parse"
    assert msg == expected_msg
