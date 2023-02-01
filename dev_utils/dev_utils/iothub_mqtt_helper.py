# TODO: REMOVE THIS WHEN NO LONGER TESTING AT IOTHUB-MQTT LEVEL

from v3_async_wip.config import IoTHubClientConfig
from azure.iot.device.common.auth import connection_string as cs
from azure.iot.device.common.auth import sastoken as st
from azure.iot.device.common.auth import signing_mechanism as sm
import ssl
import logging

logger = logging.getLogger(__name__)


def create_client_config(cs_str):
    connection_string = cs.ConnectionString(cs_str)
    hostname = connection_string[cs.HOST_NAME]
    device_id = connection_string[cs.DEVICE_ID]
    module_id = connection_string.get(cs.MODULE_ID)
    sastoken = _create_sastoken(connection_string)
    ssl_context = _create_ssl_context()
    return IoTHubClientConfig(
        device_id=device_id,
        module_id=module_id,
        hostname=hostname,
        sastoken=sastoken,
        ssl_context=ssl_context,
    )


def _create_sastoken(connection_string, ttl=3600):
    uri = _form_sas_uri(
        hostname=connection_string[cs.HOST_NAME],
        device_id=connection_string[cs.DEVICE_ID],
        module_id=connection_string.get(cs.MODULE_ID),
    )
    signing_mechanism = sm.SymmetricKeySigningMechanism(key=connection_string[cs.SHARED_ACCESS_KEY])
    sastoken = st.RenewableSasToken(uri=uri, signing_mechanism=signing_mechanism, ttl=ttl)
    return sastoken


def _form_sas_uri(hostname, device_id, module_id=None):
    if module_id:
        return "{hostname}/devices/{device_id}/modules/{module_id}".format(
            hostname=hostname, device_id=device_id, module_id=module_id
        )
    else:
        return "{hostname}/devices/{device_id}".format(hostname=hostname, device_id=device_id)


# TODO: use this logic directly in the client later
def _create_ssl_context(server_verification_cert=None, cipher=None, x509=None) -> ssl.SSLContext:
    ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.check_hostname = True

    if server_verification_cert:
        logger.debug("Configuring SSLContext with custom server verification cert")
        ssl_context.load_verify_locations(cadata=server_verification_cert)
    else:
        logger.debug("Configuring SSLContext with default certs")
        ssl_context.load_default_certs()

    if cipher:
        logger.debug("Configuring SSLContext with cipher suites")
        ssl_context.set_ciphers(cipher)
    else:
        logger.debug("Not using cipher suites")

    if x509:
        logger.debug("Configuring SSLContext with client-side X509 certificate and key")
        ssl_context.load_cert_chain(
            x509.certificate_file,
            x509.key_file,
            x509.pass_phrase,
        )
    else:
        logger.debug("Not using X509 certificates")

    return ssl_context
