# coding=utf-8
# --------------------------------------------------------------------------
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class DeviceCertificateIssuancePolicy(Model):
    """DeviceCertificateIssuancePolicy.

    All required parameters must be populated in order to send to Azure.

    :param certificate_authority_name: Required. The name of the Certificate
     Authority for issuing a certificate to the device.
    :type certificate_authority_name: str
    :param validity_period: Required. The desired validity time period of the
     certificate to be issued in ISO8601 format. Example: 'P6DT5H5M'. The
     minimum period is 'P1D' (1 day) and the maximum period is 'P7D' (7 days).
    :type validity_period: str
    """

    _validation = {
        "certificate_authority_name": {"required": True},
        "validity_period": {"required": True},
    }

    _attribute_map = {
        "certificate_authority_name": {"key": "certificateAuthorityName", "type": "str"},
        "validity_period": {"key": "validityPeriod", "type": "str"},
    }

    def __init__(self, *, certificate_authority_name: str, validity_period: str, **kwargs) -> None:
        super(DeviceCertificateIssuancePolicy, self).__init__(**kwargs)
        self.certificate_authority_name = certificate_authority_name
        self.validity_period = validity_period
