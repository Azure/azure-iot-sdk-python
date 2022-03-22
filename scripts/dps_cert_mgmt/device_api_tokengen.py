from base64 import b64encode, b64decode
from hashlib import sha256
from time import time
from urllib import parse
from hmac import HMAC

# For Device API token, paste your DPS ID Scope here.
# This can be found in the DPS 'Overview' blade
id_scope = "<idscope>"

# For Device API token, paste the registration ID of the enrollment here.
# This can be found in the DPS -> Manage enrollments -> Individual enrollments -> <Registration ID>
registration_id = "<registration id>"

# For Device API token, paste the primary or secondary key belonging to the individual enrollment.
# This can be found in the DPS -> Manage enrollments -> Individual enrollments -> <Registration ID>
# under 'Primary key' or 'Secondary key'
# If using a symmetric key-based enrollment group, you'll need to first generate a device symmetric
# key using the enrollment group key. Use the enrollment group primary or secondary key to compute
# an HMAC-SHA256 of the registration ID for the device. The result is then converted into Base64
# format to obtain the derived device key. To view code examples, see
# https://docs.microsoft.com/en-us/azure/iot-dps/how-to-legacy-device-symm-key
key = "<Primary key or Secondary key>"

uri = id_scope + "/registrations/" + registration_id
policy_name = "registration"
expiry = 3600

ttl = time() + expiry
sign_key = "%s\n%d" % ((parse.quote_plus(uri)), int(ttl))
# print(sign_key)
signature = b64encode(HMAC(b64decode(key), sign_key.encode("utf-8"), sha256).digest())

rawtoken = {"sr": uri, "sig": signature, "se": str(int(ttl))}

if policy_name is not None:
    rawtoken["skn"] = policy_name

print("SharedAccessSignature " + parse.urlencode(rawtoken))
