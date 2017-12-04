#!/usr/bin/env python

# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import random
import time
import sys
from provisioning_device_client import ProvisioningDeviceClient, ProvisioningTransportProvider, ProvisioningSecurityDeviceType, ProvisioningError, ProvisioningHttpProxyOptions
from provisioning_device_client_args import get_prov_client_opt, OptionError

GLOBAL_PROV_URI = "global.azure-devices-provisioning.net"
ID_SCOPE = ""
SECURITY_DEVICE_TYPE = ProvisioningSecurityDeviceType.X509
PROTOCOL = ProvisioningTransportProvider.HTTP

def register_status_callback(reg_status, user_context):
    print ( "")
    print ( "Register status callback: ")
    print ( "reg_status = %s" % reg_status)
    print ( "user_context = %s" % user_context)
    print ( "")
    return


def register_device_callback(register_result, iothub_uri, device_id, user_context):
    print ( "")
    print ( "Register device callback: " )
    print ( "   register_result = %s" % register_result)
    print ( "   iothub_uri = %s" % iothub_uri)
    print ( "   user_context = %s" % user_context)

    if iothub_uri:
        print ( "")
        print ( "Device successfully registered!" )
    else:  
        print ( "")
        print ( "Device registration failed!" )

    print ( "")
    return


class ProvisioningManager(object):

    def __init__(
            self,
            global_prov_uri,
            id_scope,
            security_device_type=ProvisioningSecurityDeviceType.X509,
            protocol=ProvisioningTransportProvider.HTTP):

        self.client_protocol = protocol
        self.client = ProvisioningDeviceClient(global_prov_uri, id_scope, security_device_type, protocol)
        self.version_str = self.client.get_version_string()

    def set_option(self, option_name, option_value):
        try:
            self.client.set_option(option_name, option_value)
        except ProvisioningError as provisioning_error:
            print ( "set_option failed (%s)" % provisioning_error )

    def register_device(self, register_device_callback, user_context, register_status_callback, user_status_context):
        try:
            self.client.register_device(register_device_callback, user_context, register_status_callback, user_status_context)
        except ProvisioningError as provisioning_error:
            print ( "register_device failed (%s)" % provisioning_error )

def main(global_prov_uri, id_scope, security_device_type, protocol):
    try:
        print ( "\nPython %s\n" % sys.version )
        print ( "Provisioning Device Client for Python" )

        provisioning_manager = ProvisioningManager(global_prov_uri, id_scope, security_device_type, protocol)

        print ( "Starting the Provisioning Device Client Python sample using protocol %s..." % provisioning_manager.client_protocol )

        provisioning_manager.set_option("logtrace", True)

        provisioning_manager.register_device(register_device_callback, None, register_status_callback, None)

        try:
            # Try Python 2.xx first
            raw_input("Press Enter to interrupt...\n")
        except:
            pass
            # Use Python 3.xx in the case of exception
            input("Press Enter to interrupt...\n")

    except ProvisioningError as provisioning_error:
        print ( "Unexpected error %s " % provisioning_error )
        return
    except KeyboardInterrupt:
        print ( "Provisioning Device Client sample stopped" )


def usage():
    print ( "Usage: provisioning_device_client_sample.py -i <id_scope> -s <security_device_type> -p <protocol>" )
    print ( "    id_scope             : <scope ID for provisioning>" )
    print ( "    security_device_type : <TPM or X509>" )
    print ( "    protocol             : <http, mqtt, mqtt_ws, amqp, amqp_ws>" )

if __name__ == '__main__':
    try:
        (ID_SCOPE, SECURITY_DEVICE_TYPE, PROTOCOL) = get_prov_client_opt(sys.argv[1:], ID_SCOPE, SECURITY_DEVICE_TYPE, PROTOCOL)
    except OptionError as option_error:
        print ( option_error )
        usage()
        sys.exit(1)

    main(GLOBAL_PROV_URI, ID_SCOPE, SECURITY_DEVICE_TYPE, PROTOCOL)
