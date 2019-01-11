# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from .internal_client import InternalClient
from .message import Message
from threading import Event


class ModuleClient(InternalClient):
    def send_to_output(self, message, output_name):
        """
        Sends an event/message to the given module output.
        These are outgoing events and are meant to be "output events"
        This is a synchronous event, meaning that this function will not return until the event
        has been sent to the service and the service has acknowledged receipt of the event.

        If the connection to the service has not previously been opened by a call to connect, this
        function will open the connection before sending the event.

        :param output_name: Name of the output to send the event to.
        :param message: message to send to the given output. Anything passed that is not an instance of the
        Message class will be converted to Message object.
        """
        if not isinstance(message, Message):
            message = Message(message)

        message.output_name = output_name

        send_complete = Event()

        def callback():
            send_complete.set()

        self._transport.send_output_event(message, callback)
        send_complete.wait()
