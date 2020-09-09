from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from datetime import datetime, timedelta, time
import uuid
import argparse


"""
For using this script must have cryptography package installed in python environment.
"""

PUBLIC_EXPONENT = 65537


def create_self_signed_cert(common_name, days=365):
    password_file = "self_key.pem"
    private_key = create_private_key(key_file=password_file, key_size=4096)
    file_certificate = "self_cert.pem"

    public_key = private_key.public_key()

    subject = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, str.encode(common_name).decode("utf-8"))]
    )

    builder = create_cert_builder(
        subject=subject, issuer_name=subject, public_key=public_key, days=days, is_ca=False
    )

    self_cert = builder.sign(
        private_key=private_key, algorithm=hashes.SHA256(), backend=default_backend()
    )
    with open(file_certificate, "wb") as f:
        f.write(self_cert.public_bytes(serialization.Encoding.PEM))

    return self_cert


def create_cert_builder(subject, issuer_name, public_key, days=365, is_ca=False):
    """
    The method to create a builder for all types of certificates.
    :param subject: The subject of the certificate.
    :param issuer_name: The name of the issuer.
    :param public_key: The public key of the certificate.
    :param days: The number of days for which the certificate is valid. The default is 1 year or 365 days.
    :param is_ca: Boolean to indicate if a cert is ca or non ca.
    :return: The certificate builder.
    :rtype: :class `x509.CertificateBuilder`
    """
    builder = x509.CertificateBuilder()

    builder = builder.subject_name(subject)
    builder = builder.issuer_name(issuer_name)
    builder = builder.public_key(public_key)
    builder = builder.not_valid_before(datetime.today())

    builder = builder.not_valid_after(datetime.today() + timedelta(days=days))
    builder = builder.serial_number(int(uuid.uuid4()))
    builder = builder.add_extension(
        x509.BasicConstraints(ca=is_ca, path_length=None), critical=True
    )
    return builder


def create_private_key(key_file, password=None, key_size=4096):
    """
    Crate encrypted key for certificates.
    :param key_file: The file to store the key.
    :param password: Password for the key.
    :param key_size: The key size to use for encryption. The default is 4096.
    :return: The private key.
    """
    if password:
        encrypt_algo = serialization.BestAvailableEncryption(str.encode(password))
    else:
        encrypt_algo = serialization.NoEncryption()

    private_key = rsa.generate_private_key(
        public_exponent=PUBLIC_EXPONENT, key_size=key_size, backend=default_backend()
    )
    # Write our key to file
    with open(key_file, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=encrypt_algo,
            )
        )

    return private_key


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a certificate chain.")
    parser.add_argument("domain", help="Domain name or common name.")

    args = parser.parse_args()

    common_name = args.domain
    create_self_signed_cert(common_name)
