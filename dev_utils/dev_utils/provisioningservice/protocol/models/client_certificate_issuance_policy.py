# coding=utf-8
# --------------------------------------------------------------------------
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class ClientCertificateIssuancePolicy(Model):
    """The device enrollment record.

    Variables are only populated by the server, and will be ignored when
    sending a request.

    All required parameters must be populated in order to send to Azure.

    param certificateAuthorityName: The certificate authority name
    :type certificateAuthorityName: str
    """

    _validation = {"certificate_authority_name": {"required": True}}

    _attribute_map = {
        "certificate_authority_name": {"key": "certificateAuthorityName", "type": "str"},
    }

    def __init__(self, **kwargs):
        super(ClientCertificateIssuancePolicy, self).__init__(**kwargs)
        self.certificate_authority_name = kwargs.get("certificate_authority_name", None)