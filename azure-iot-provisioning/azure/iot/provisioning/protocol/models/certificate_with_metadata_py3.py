# coding=utf-8
# --------------------------------------------------------------------------
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class CertificateWithMetadata(Model):
    """CertificateWithMetadata.

    Variables are only populated by the server, and will be ignored when
    sending a request.

    :ivar certificate_metadata:
    :vartype certificate_metadata: ~protocol.models.CertificateMetadata
    :param certificate:
    :type certificate: str
    """

    _validation = {"certificate_metadata": {"readonly": True}}

    _attribute_map = {
        "certificate_metadata": {"key": "certificateMetadata", "type": "CertificateMetadata"},
        "certificate": {"key": "certificate", "type": "str"},
    }

    def __init__(self, *, certificate: str = None, **kwargs) -> None:
        super(CertificateWithMetadata, self).__init__(**kwargs)
        self.certificate_metadata = None
        self.certificate = certificate
