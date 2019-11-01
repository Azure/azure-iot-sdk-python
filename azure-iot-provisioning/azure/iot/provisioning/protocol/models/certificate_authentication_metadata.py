# coding=utf-8
# --------------------------------------------------------------------------
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from .authentication_metadata import AuthenticationMetadata


class CertificateAuthenticationMetadata(AuthenticationMetadata):
    """CertificateAuthenticationMetadata.

    Variables are only populated by the server, and will be ignored when
    sending a request.

    All required parameters must be populated in order to send to Azure.

    :param authentication_metadata_type: Required. Constant filled by server.
    :type authentication_metadata_type: str
    :ivar device_certificate_metadata: Device certificate metadata.
    :vartype device_certificate_metadata: ~protocol.models.CertificateMetadata
    :ivar certificate_authority_metadata: Certificate authority metadata.
    :vartype certificate_authority_metadata:
     ~protocol.models.CertificateMetadata
    """

    _validation = {
        "authentication_metadata_type": {"required": True},
        "device_certificate_metadata": {"readonly": True},
        "certificate_authority_metadata": {"readonly": True},
    }

    _attribute_map = {
        "authentication_metadata_type": {"key": "authenticationMetadataType", "type": "str"},
        "device_certificate_metadata": {
            "key": "deviceCertificateMetadata",
            "type": "CertificateMetadata",
        },
        "certificate_authority_metadata": {
            "key": "certificateAuthorityMetadata",
            "type": "CertificateMetadata",
        },
    }

    def __init__(self, **kwargs):
        super(CertificateAuthenticationMetadata, self).__init__(**kwargs)
        self.device_certificate_metadata = None
        self.certificate_authority_metadata = None
        self.authentication_metadata_type = "CertificateAuthenticationMetadata"
