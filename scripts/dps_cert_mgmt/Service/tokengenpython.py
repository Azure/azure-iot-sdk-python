from base64 import b64encode, b64decode
from hashlib import sha256
from time import time
from urllib import parse
from hmac import HMAC

uri = "crispop-dpstb.azure-devices-provisioning.net"
key = "9YlWenX+7YO6Tzu7HTnAvApsBOiD0A3SJUmRvmdy/Yc="
policy_name = "provisioningserviceowner"
expiry = 3600

ttl = time() + expiry
sign_key = "%s\n%d" % ((parse.quote_plus(uri)), int(ttl))
print(sign_key)
signature = b64encode(HMAC(b64decode(key), sign_key.encode("utf-8"), sha256).digest())

rawtoken = {"sr": uri, "sig": signature, "se": str(int(ttl))}

if policy_name is not None:
    rawtoken["skn"] = policy_name

print("SharedAccessSignature " + parse.urlencode(rawtoken))
# return 'SharedAccessSignature ' + parse.urlencode(rawtoken)
