# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import getopt
from provisioning_device_client import ProvisioningTransportProvider, ProvisioningSecurityDeviceType


class OptionError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def get_prov_client_opt(
        argv,
        id_scope,
        sec_type=ProvisioningSecurityDeviceType.X509,
        protocol=ProvisioningTransportProvider.HTTP):
    lgt = len(argv)
    if lgt > 0:
        try:
            opts, args = getopt.getopt(
                argv, "hi:s:p:", [
                    "id_scope=", "security_device_type=", "protocol="])
        except getopt.GetoptError as opt_error:
            raise OptionError("Error: %s" % opt_error.msg)
        for opt, arg in opts:
            if opt == '-h':
                raise OptionError("Help:")

            elif opt in ("-i", "--id_scope"):
                id_scope = arg

            elif opt in ("-s", "--security_device_type"):
                sec_dev_str = arg.lower()

                if sec_dev_str == "tpm":
                    if hasattr(ProvisioningSecurityDeviceType, "TPM"):
                        sec_type = ProvisioningSecurityDeviceType.TPM
                    else:
                        raise OptionError("Error: TPM security device type is not supported")
                elif sec_dev_str == "x509":
                    if hasattr(ProvisioningSecurityDeviceType, "X509"):
                        sec_type = ProvisioningSecurityDeviceType.X509
                    else:
                        raise OptionError("Error: X509 security device type is not supported")
                else:
                    raise OptionError(
                        "Error: unknown security device type %s" %
                        sec_type)

            elif opt in ("-p", "--protocol"):
                protocol_string = arg.lower()

                if protocol_string == "http":
                    if hasattr(ProvisioningTransportProvider, "HTTP"):
                        protocol = ProvisioningTransportProvider.HTTP
                    else:
                        raise OptionError("Error: HTTP protocol is not supported")

                elif protocol_string == "amqp":
                    if hasattr(ProvisioningTransportProvider, "AMQP"):
                        protocol = ProvisioningTransportProvider.AMQP
                    else:
                        raise OptionError("Error: AMQP protocol is not supported")

                elif protocol_string == "amqp_ws":
                    if hasattr(ProvisioningTransportProvider, "AMQP_WS"):
                        protocol = ProvisioningTransportProvider.AMQP_WS
                    else:
                        raise OptionError("Error: AMQP_WS protocol is not supported")

                elif protocol_string == "mqtt":
                    if hasattr(ProvisioningTransportProvider, "MQTT"):
                        protocol = ProvisioningTransportProvider.MQTT
                    else:
                        raise OptionError("Error: MQTT protocol is not supported")

                elif hasattr(ProvisioningTransportProvider, "MQTT_WS"):
                    if hasattr(ProvisioningTransportProvider, "MQTT_WS"):
                        protocol = ProvisioningTransportProvider.MQTT_WS
                    else:
                        raise OptionError("Error: MQTT_WS protocol is not supported")
                else:
                    raise OptionError(
                        "Error: unknown protocol %s" %
                        protocol_string)

    return id_scope, sec_type, protocol
