from base64 import b64encode, b64decode
from hashlib import sha256
from time import time
from urllib import parse
from hmac import HMAC

# For Service API token, uri is your DPS Service endpoint
# This can be found in the DPS 'Overview' blade
# e.g mydps.azure-devices-provisioning.net
uri = "<DPS Service endpoint>"

# For Service API token, paste the primary or secondary key belonging to the provisioningservice owner.
# This can be found in the DPS 'Shared access policies' blade
# under 'Primary key' or 'Secondary key'
key = "<Primary key or Secondary key>"

policy_name = "provisioningserviceowner"
expiry = 3600

ttl = time() + expiry
sign_key = "%s\n%d" % ((parse.quote_plus(uri)), int(ttl))
# print(sign_key)
signature = b64encode(HMAC(b64decode(key), sign_key.encode("utf-8"), sha256).digest())

rawtoken = {"sr": uri, "sig": signature, "se": str(int(ttl))}

if policy_name is not None:
    rawtoken["skn"] = policy_name

print("SharedAccessSignature " + parse.urlencode(rawtoken))
