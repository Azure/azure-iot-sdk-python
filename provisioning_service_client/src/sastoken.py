import time
import urllib
import base64
import hmac
import hashlib

class SasTokenException(Exception):
    pass

class SasToken:

    token_valid_seconds = 60 * 60 #one hour
    encoding_type = 'utf-8'
    token_format = "SharedAccessSignature sr={}&sig={}&se={}&skn={}"

    def __init__(self, resource_uri, key_name, key):

        if type(resource_uri) != str or type(key_name) != str or type(key) != str:
            raise SasTokenException
        
        self.resource_uri = urllib.quote_plus(resource_uri) #may need to be urllib.parse.quote_plus in python 3
        self.key_name = key_name
        self.key = key
        self.expiry_time = self._calc_expiry_time()
        self.token = self._build_token()

    def _calc_expiry_time(self):
        return int(time.time() + SasToken.token_valid_seconds)

    def _build_token(self):

        message = (self.resource_uri + '\n' + str(self.expiry_time)).encode(SasToken.encoding_type)
        signing_key = base64.b64decode(self.key.encode(SasToken.encoding_type))
        signed_hmac = hmac.HMAC(signing_key, message, hashlib.sha256)
        signature = urllib.quote(base64.b64encode(signed_hmac.digest()))

        return SasToken.token_format.format(self.resource_uri, signature, str(self.expiry_time), self.key_name)
