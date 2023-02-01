# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""Temporary module used to help set up transport for manual testing"""
# TODO: remove this when not testing at MQTT level
import ssl
import logging
import urllib
from azure.iot.device.common.auth import connection_string as cs
from azure.iot.device.common.auth import sastoken as st
from azure.iot.device.common.auth import signing_mechanism as sm

logger = logging.getLogger(__name__)

WS_PATH = "/$iothub/websocket"
IOTHUB_API_VERSION = "2019-10-01"


def get_client_id(connection_string):
    connection_string = cs.ConnectionString(connection_string)
    return connection_string[cs.DEVICE_ID]


def get_hostname(connection_string):
    connection_string = cs.ConnectionString(connection_string)
    return connection_string[cs.HOST_NAME]


def get_username(connection_string):
    connection_string = cs.ConnectionString(connection_string)

    query_param_seq = []
    query_param_seq.append(("api-version", IOTHUB_API_VERSION))
    # query_param_seq.append(
    #     ("DeviceClientType", user_agent.get_iothub_user_agent())
    # )

    username = "{hostname}/{client_id}/?{query_params}".format(
        hostname=connection_string[cs.HOST_NAME],
        client_id=get_client_id(str(connection_string)),
        query_params=urllib.parse.urlencode(query_param_seq, quote_via=urllib.parse.quote),
    )
    return username


def get_password(connection_string, ttl=3600):
    connection_string = cs.ConnectionString(connection_string)
    uri = _form_sas_uri(
        hostname=connection_string[cs.HOST_NAME],
        device_id=connection_string[cs.DEVICE_ID],
        module_id=connection_string.get(cs.MODULE_ID),
    )
    signing_mechanism = sm.SymmetricKeySigningMechanism(key=connection_string[cs.SHARED_ACCESS_KEY])
    sastoken = st.RenewableSasToken(uri, signing_mechanism, ttl=ttl)
    return str(sastoken)


def create_ssl_context(server_verification_cert=None, cipher=None, x509_cert=None):
    """
    This method creates the SSLContext object used by Paho to authenticate the connection.
    """
    logger.debug("creating a SSL context")
    ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)

    if server_verification_cert:
        logger.debug("configuring SSL context with custom server verification cert")
        ssl_context.load_verify_locations(cadata=server_verification_cert)
    else:
        logger.debug("configuring SSL context with default certs")
        ssl_context.load_default_certs()

    if cipher:
        try:
            logger.debug("configuring SSL context with cipher suites")
            ssl_context.set_ciphers(cipher)
        except ssl.SSLError as e:
            # TODO: custom error with more detail?
            raise e

    if x509_cert is not None:
        logger.debug("configuring SSL context with client-side certificate and key")
        ssl_context.load_cert_chain(
            x509_cert.certificate_file,
            x509_cert.key_file,
            x509_cert.pass_phrase,
        )

    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.check_hostname = True

    return ssl_context


def _form_sas_uri(hostname, device_id, module_id=None):
    if module_id:
        return "{hostname}/devices/{device_id}/modules/{module_id}".format(
            hostname=hostname, device_id=device_id, module_id=module_id
        )
    else:
        return "{hostname}/devices/{device_id}".format(hostname=hostname, device_id=device_id)
