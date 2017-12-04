# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import getopt
from iothub_client import IoTHubTransportProvider, IoTHubSecurityType


class OptionError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def get_iothub_prov_opt(
        argv,
        iothub_uri,
        device_id,
        security_type=IoTHubSecurityType.SAS,
        protocol=IoTHubTransportProvider.MQTT):
    if len(argv) > 0:
        try:
            opts, args = getopt.getopt(
                argv, "hu:d:s:p:", [
                    "protocol=", "connectionstring="])
        except getopt.GetoptError as opt_error:
            raise OptionError("Error: %s" % opt_error.msg)
        for opt, arg in opts:
            if opt == '-h':
                raise OptionError("Help:")

            elif opt in ("-u", "--iothub_uri"):
                iothub_uri = arg

            elif opt in ("-d", "--sec_type"):
                device_id = arg

            elif opt in ("-s", "--security_type"):
                security_type_str = arg.lower()

                if security_type_str == "sas":
                    if hasattr(IoTHubSecurityType, "SAS"):
                        security_type = IoTHubSecurityType.SAS
                    else:
                        raise OptionError("Error: TPM security device type is not supported")
                elif security_type_str == "x509":
                    if hasattr(IoTHubSecurityType, "X509"):
                        security_type = IoTHubSecurityType.X509
                    else:
                        raise OptionError("Error: X509 security device type is not supported")
                else:
                    raise OptionError(
                        "Error: unknown security device type %s" %
                        security_type)

            elif opt in ("-p", "--protocol"):
                protocol_string = arg.lower()

                if protocol_string == "http":
                    if hasattr(IoTHubTransportProvider, "HTTP"):
                        protocol = IoTHubTransportProvider.HTTP
                    else:
                        raise OptionError("Error: HTTP protocol is not supported")

                elif protocol_string == "amqp":
                    if hasattr(IoTHubTransportProvider, "AMQP"):
                        protocol = IoTHubTransportProvider.AMQP
                    else:
                        raise OptionError("Error: AMQP protocol is not supported")

                elif protocol_string == "amqp_ws":
                    if hasattr(IoTHubTransportProvider, "AMQP_WS"):
                        protocol = IoTHubTransportProvider.AMQP_WS
                    else:
                        raise OptionError("Error: AMQP_WS protocol is not supported")

                elif protocol_string == "mqtt":
                    if hasattr(IoTHubTransportProvider, "MQTT"):
                        protocol = IoTHubTransportProvider.MQTT
                    else:
                        raise OptionError("Error: MQTT protocol is not supported")

                elif hasattr(IoTHubTransportProvider, "MQTT_WS"):
                    if hasattr(IoTHubTransportProvider, "MQTT_WS"):
                        protocol = IoTHubTransportProvider.MQTT_WS
                    else:
                        raise OptionError("Error: MQTT_WS protocol is not supported")
                else:
                    raise OptionError(
                        "Error: unknown protocol %s" %
                        protocol_string)

    return iothub_uri, device_id, security_type, protocol
