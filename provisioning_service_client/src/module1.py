from service import DeviceProvisioningServiceServiceRuntimeClient
from service import VERSION
from sastoken import SasToken

class ProvisioningServiceClientException(Exception):
    pass

class ProvisioningServiceClient:

    def __init__(self, connection_string):

        conn_str_delimiter = ";"
        conn_str_val_separator = "="
        host_name_label = "HostName"
        shared_access_key_name_label = "SharedAccessKeyName"
        shared_access_key_label = "SharedAccessKey"
        https_prefix = "https://"

        cs_args = connection_string.split(conn_str_delimiter)

        if len(cs_args) != 3:
            raise ProvisioningServiceClientException
        if len(cs_args) > len(set(cs_args)):
            raise ProvisioningServiceClientException

        for arg in cs_args:
            tokens = arg.split(conn_str_val_separator, 1)

            if tokens[0] == host_name_label:
                self.host_name = tokens[1]
            elif tokens[0] == shared_access_key_name_label:
                self.shared_access_key_name = tokens[1]
            elif tokens[0] == shared_access_key_label:
                self.shared_access_key = tokens[1]
            else:
                raise ProvisioningServiceClientException

        self.runtime_client = DeviceProvisioningServiceServiceRuntimeClient(https_prefix + self.host_name)

    def create_or_update_individual_enrollment(self, reg_id, indv_enrollment):
        custom_headers = self._populate_custom_headers()
        return self.runtime_client.device_enrollment.create_or_update(reg_id, indv_enrollment, VERSION, indv_enrollment.etag, custom_headers)

    def get_individual_enrollment(self, reg_id):
        custom_headers = self._populate_custom_headers()
        return self.runtime_client.device_enrollment.get(reg_id, VERSION, custom_headers)

    def _populate_custom_headers(self):
        custom_headers = {}
        custom_headers["Authorization"] = SasToken(self.host_name, self.shared_access_key_name, self.shared_access_key).token

        return custom_headers

if __name__ == "__main__":

    connection_string = "[]"
    endorsement_key = ""

    sc = ProvisioningServiceClient(connection_string)

    tpm_att = sc.runtime_client.device_enrollment.models.TpmAttestation(endorsement_key, None)
    att_mech = sc.runtime_client.device_enrollment.models.AttestationMechanism("tpm", tpm_att, None)
    ie1 = sc.runtime_client.device_enrollment.models.IndividualEnrollment("python-test7", att_mech)



    res = sc.get_individual_enrollment("python-test")
    #res = sc.create_or_update_individual_enrollment(ie1.registration_id, ie1)
    res = res



#connectionString = "HostName=carter-dps-2.azure-devices-provisioning.net;SharedAccessKeyName=provisioningserviceowner;SharedAccessKey=uNqKlY3IR6fB+p78K9mck9PrDsF2uLYpt0r91Hq2gh0="
#endorsementKey = "AToAAQALAAMAsgAgg3GXZ0SEs/gakMyNRqXXJP1S124GUgtk8qHaGzMUaaoABgCAAEMAEAgAAAAAAAEAxsj2gUScTk1UjuioeTlfGYZrrimExB+bScH75adUMRIi2UOMxG1kw4y+9RW/IVoMl4e620VxZad0ARX2gUqVjYO7KPVt3dyKhZS3dkcvfBisBhP1XH9B33VqHG9SHnbnQXdBUaCgKAfxome8UmBKfe+naTsE5fkvjb/do3/dD6l4sGBwFCnKRdln4XpM03zLpoHFao8zOwt8l/uP3qUIxmCYv9A7m69Ms+5/pCkTu/rK4mRDsfhZ0QLfbzVI6zQFOKF/rwsfBtFeWlWtcuJMKlXdD8TXWElTzgh7JS4qhFzreL0c1mI0GCj+Aws0usZh7dLIVPnlgZcBhgy1SSDQMQ=="

#prov_sc = DeviceProvisioningServiceServiceRuntimeClient("https://carter-dps-2.azure-devices-provisioning.net")
##prov_sc = DeviceProvisioningServiceServiceRuntimeClient("http://localhost")



#custom_headers = {}
##custom_headers["Accept"] = "application/json"
#custom_headers["Authorization"] = "SharedAccessSignature sr=carter-dps-2.azure-devices-provisioning.net&sig=9aXaZu0aWZC7bOGWUvuJj6DVH%2buOaTLp2PvxBNUm%2b%2bg%3d&se=1513190861&skn=provisioningserviceowner"
##new_ie = prov_sc.device_enrollment.create_or_update("python-test", ie, VERSION, None, custom_headers)

#res = prov_sc.device_enrollment.get("python-test", VERSION, custom_headers)


#res = prov_sc.device_enrollment.bulk_operation(bulk_op, VERSION, custom_headers)

#res = prov_sc.device_enrollment.query(qs, VERSION, custom_headers)

##res = prov_sc.device_enrollment.delete("python-test", VERSION, "*", custom_headers)

##new_ie = new_ie
##new_ie = prov_sc.device_enrollment.create_or_update("python-test", ie, VERSION, None, custom_headers)

#res = res