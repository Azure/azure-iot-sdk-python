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


def provisioning_client_sample_run():
    global GLOBAL_PROV_URI
    global ID_SCOPE
    global SECURITY_DEVICE_TYPE
    global PROTOCOL

    try:
        provisioning_client = ProvisioningDeviceClient(GLOBAL_PROV_URI, ID_SCOPE, SECURITY_DEVICE_TYPE, PROTOCOL)

        version_str = provisioning_client.get_version_string()
        print ( "\nProvisioning API Version: %s\n" % version_str )

        provisioning_client.set_option("logtrace", True)

        provisioning_client.register_device(register_device_callback, None, register_status_callback, None)

        try:
            # Try Python 2.xx first
            raw_input("Press Enter to interrupt...\n")
        except:
            pass
            # Use Python 3.xx in the case of exception
            input("Press Enter to interrupt...\n")

    except ProvisioningError as provisioning_error:
        print ( "Unexpected error %s" % provisioning_error )
        return
    except KeyboardInterrupt:
        print ( "Provisioning Device Client sample stopped" )


def usage():
    print ( "Usage: provisioning_device_client_sample.py -p <protocol> -i <scope_id> -s <security_device_type>" )
    print ( "    scope_id             : <scope ID for provisioning>" )
    print ( "    security_device_type : <scope ID for provisioning>" )
    print ( "    protocol             : <http, mqtt, mqtt_ws, amqp, amqp_ws>" )


if __name__ == '__main__':
    print ( "\nPython %s" % sys.version )
    print ( "Provisioning Client for Python" )

    try:
        (ID_SCOPE, SECURITY_DEVICE_TYPE, PROTOCOL) = get_prov_client_opt(sys.argv[1:], ID_SCOPE, SECURITY_DEVICE_TYPE, PROTOCOL)
    except OptionError as option_error:
        print ( option_error )
        usage()
        sys.exit(1)

    print ( "Starting the Provisioning Client Python sample..." )
    print ( "    Scope ID=%s" % ID_SCOPE )
    print ( "    Security Device Type %s" % SECURITY_DEVICE_TYPE )
    print ( "    Protocol %s" % PROTOCOL )

    provisioning_client_sample_run()


