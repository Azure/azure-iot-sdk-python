import pytest
from ..device.transport.abstract_transport import AbstractTransport


def test_raises_exception():
    with pytest.raises(TypeError) as error:
        AbstractTransport()
    msg = str(error.value)
    expected_msg = "Can't instantiate abstract class AbstractTransport with abstract methods _get_connected_state_callback, connect, disconnect, send_event"
    assert msg == expected_msg
