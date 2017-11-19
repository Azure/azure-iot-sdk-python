# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import os
import sys
import uuid
import string
import random
import time
import threading
import types
import base64

from provisioning_device_client import ProvisioningDeviceClient, ProvisioningTransportProvider, ProvisioningSecurityDeviceType, ProvisioningError

GLOBAL_PROV_URI = "global.azure-devices-provisioning.net"
ID_SCOPE = ""

STATUS_CALLBACKS = 0
DEVICE_CALLBACKS = 0

DEVICE_CALLBACK_EVENT = threading.Event()
DEVICE_CALLBACK_TIMEOUT = 60

REGISTRATION_OK = False

def register_status_callback(reg_status, user_context):
    global STATUS_CALLBACKS
    
    print ( "")
    print ( "Register status callback: ")
    print ( "reg_status = %s" % reg_status)
    print ( "user_context = %s" % user_context)
    print ( "")

    STATUS_CALLBACKS += 1

    return


def register_device_callback(register_result, iothub_uri, device_id, user_context):
    global DEVICE_CALLBACKS
    global REGISTRATION_OK

    print ( "")
    print ( "Register device callback: " )
    print ( "   register_result = %s" % register_result)
    print ( "   iothub_uri = %s" % iothub_uri)
    print ( "   user_context = %s" % user_context)

    if iothub_uri:
        print ( "")
        print ( "Device successfully registered!" )
        REGISTRATION_OK = True
    else:  
        print ( "")
        print ( "Device registration failed!" )

    print ( "")

    DEVICE_CALLBACKS += 1

    DEVICE_CALLBACK_EVENT.set()

    return


###########################################################################
# E2E tests
###########################################################################

def run_e2e_provisioning():
    global GLOBAL_PROV_URI
    global ID_SCOPE
    global DEVICE_CALLBACK_EVENT
    global DEVICE_CALLBACK_TIMEOUT
    global REGISTRATION_OK

    SECURITY_DEVICE_TYPE = ProvisioningSecurityDeviceType.X509
    PROTOCOL = ProvisioningTransportProvider.HTTP

    try:
        # prepare
        provisioning_client = ProvisioningDeviceClient(GLOBAL_PROV_URI, ID_SCOPE, SECURITY_DEVICE_TYPE, PROTOCOL)

        version_str = provisioning_client.get_version_string()
        print ( "\nProvisioning API Version: %s\n" % version_str )

        provisioning_client.set_option("logtrace", True)

        # act
        DEVICE_CALLBACK_EVENT.clear()
        provisioning_client.register_device(register_device_callback, None, register_status_callback, None)
        DEVICE_CALLBACK_EVENT.wait(DEVICE_CALLBACK_TIMEOUT)

        # verify
        assert STATUS_CALLBACKS > 0, "Error: status_callback callback has not been called"
        assert DEVICE_CALLBACKS > 0, "Error: device_callback callback has not been called"
        assert REGISTRATION_OK, "Error: Device registration failed"
        ###########################################################################

        retval = 0

    except Exception as e:
        print ( "" )
        print ("run_e2e_provisioning() failed with exception: {0}".format(e))
        retval = 1

    return retval

def main():
    print ("********************* provisioning_device_client E2E tests started!")

    try:
        assert run_e2e_provisioning() == 0
        print ("********************* provisioning_device_client E2E tests passed!")
        return 0
    except:
        print ("********************* provisioning_device_client E2E tests failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
