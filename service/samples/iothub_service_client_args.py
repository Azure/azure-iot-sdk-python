# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import getopt


class OptionError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def get_iothub_opt(
        argv,
        connection_string,
        device_id):
    if len(argv) > 0:
        try:
            opts, args = getopt.getopt(
                argv, "hd:c:", [
                    "connectionstring=", "deviceid="])
        except getopt.GetoptError as get_opt_error:
            raise OptionError("Error: %s" % get_opt_error.msg)
        for opt, arg in opts:
            if opt == '-h':
                raise OptionError("Help:")
            elif opt in ("-c", "--connectionstring"):
                connection_string = arg
            elif opt in ("-d", "--deviceid"):
                device_id = arg

    if connection_string.find("HostName") < 0:
        raise OptionError(
            "Error: Hostname not found, not a valid connection string")

    return connection_string, device_id
