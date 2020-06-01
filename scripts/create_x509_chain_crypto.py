from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from datetime import datetime, timedelta, time
import uuid
import os
import argparse
import getpass
import base64
import shutil

"""
For using this script must have cryptography package installed in python environment.
"""

PUBLIC_EXPONENT = 65537
EXTENSION_NAME = ".pem"
COMMON_DEVICE_PASSWORD_FILE = "demoCA/private/device_key"
COMMON_DEVICE_CSR_FILE = "demoCA/newcerts/device_csr"
COMMON_DEVICE_CERT_FILE = "demoCA/newcerts/device_cert"


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


def create_certificate_chain(
    common_name,
    ca_password,
    intermediate_password,
    device_password,
    device_count=1,
    key_size=4096,
    days=3650,
):
    """
    This method will create a basic 3 layered chain certificate containing a root, t
    hen an intermediate and then some number of leaf certificates.
    This function is only used when the certificates are created from script.
    When certificates are created using the script , the root certificate is created for 1 year.
    The intermediate certificate is created for almost a month or 36 days
    and the device certificate is created for 3 days.

    :param common_name: The common name to be used in the subject. This is a single common name which would be applied to all certs created.
    Since this common name is meant for all, this common name will be prepended by the
    words "root", "inter" and "device" for root, intermediate and device certificates.
    For device certificates the common name will be further appended with the index of the device.
    :param ca_password: The password for the root certificate which is going to be referenced by the intermediate.
    :param intermediate_password: The password for the intermediate certificate
    :param device_password: The password for the device certificate
    :param device_count: The number of leaf devices for which that many number of certificates will be generated.
    :param key_size: The key size to use for encryption. The default is 4096.
    :param days: The number of days for which the certificate is valid. The default is 1 year or 365 days.
    """
    root_password_file = "demoCA/private/ca_key.pem"
    root_private_key = create_private_key(
        key_file=root_password_file, password=ca_password, key_size=key_size
    )
    root_cert = create_root_ca_cert(
        root_common_name="root" + common_name, root_private_key=root_private_key, days=days
    )

    intermediate_password_file = "demoCA/private/intermediate_key.pem"

    intermediate_private_key = create_private_key(
        key_file=intermediate_password_file, password=intermediate_password, key_size=key_size
    )

    intermediate_cert = create_intermediate_ca_cert(
        issuer_cert_subject=root_cert.subject,
        issuer_key=root_private_key,
        intermediate_common_name="inter" + common_name,
        intermediate_private_key=intermediate_private_key,
        days=days,
    )

    create_multiple_device_keys_and_certs(
        number_of_devices=device_count,
        issuer_cert_subject=intermediate_cert.subject,
        issuer_key=intermediate_private_key,
        device_common_name="device" + common_name,
        password=device_password,
        key_size=key_size,
        days=days,
    )


def create_root_ca_cert(root_common_name, root_private_key, days=365):
    """
    This method will create a root ca certificate.
    :param root_common_name: The common name for the certificate.
    :param root_private_key: The private key for the certificate.
    :param days: The number of days for which the certificate is valid. The default is 1 year or 365 days.
    :return: The root certificate.
    :rtype: :class:`x509.Certificate`
    """
    file_root_certificate = "demoCA/newcerts/ca_cert.pem"

    root_public_key = root_private_key.public_key()

    subject = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, str.encode(root_common_name).decode("utf-8"))]
    )

    builder = create_cert_builder(
        subject=subject, issuer_name=subject, public_key=root_public_key, days=days, is_ca=True
    )

    root_cert = builder.sign(
        private_key=root_private_key, algorithm=hashes.SHA256(), backend=default_backend()
    )
    with open(file_root_certificate, "wb") as f:
        f.write(root_cert.public_bytes(serialization.Encoding.PEM))

    return root_cert


def create_intermediate_ca_cert(
    issuer_cert_subject, issuer_key, intermediate_common_name, intermediate_private_key, days=365
):
    """
    This method will create a intermediate ca certificate valid for a duration of 36 days.
    :param issuer_cert_subject: The subject for the issuer certificate cert that is issuing this one.
    :param issuer_key: The key for the issuer certificate.
    :param intermediate_common_name: The common name for the certificate.
    :param intermediate_private_key: The private key for the certificate.
    :param days: The number of days for which the certificate is valid. The default is 1 year or 365 days.
    :return: The intermediate certificate.
    :rtype: :class:`x509.Certificate`
    """
    file_intermediate_certificate = "demoCA/newcerts/intermediate_cert.pem"
    file_intermediate_csr = "demoCA/newcerts/intermediate_csr.pem"

    intermediate_csr = create_csr(
        private_key=intermediate_private_key,
        csr_file=file_intermediate_csr,
        subject=intermediate_common_name,
        is_ca=True,
    )

    builder = create_cert_builder(
        subject=intermediate_csr.subject,
        issuer_name=issuer_cert_subject,
        public_key=intermediate_csr.public_key(),
        days=int(days / 10),
        is_ca=True,
    )

    intermediate_cert = builder.sign(
        private_key=issuer_key, algorithm=hashes.SHA256(), backend=default_backend()
    )
    with open(file_intermediate_certificate, "wb") as f:
        f.write(intermediate_cert.public_bytes(serialization.Encoding.PEM))

    return intermediate_cert


def create_multiple_device_keys_and_certs(
    number_of_devices,
    issuer_cert_subject,
    issuer_key,
    device_common_name,
    password,
    key_size=4096,
    days=365,
):
    """
    This method will create multiple device private keys and multiple device certificates valid for 3 days.
    :param number_of_devices: The number of devices for which the certificates are created.
    :param issuer_cert_subject: The subject for the issuer certificate cert that is issuing this one.
    :param issuer_key: The key for the issuer certificate.
    :param device_common_name: The common name for the certificate.
    :param password: The password for creating the key for the certificate.
    :param key_size: The key size to use for encryption. The default is 4096.
    :param days: The number of days for which the certificate is valid. The default is 1 year or 365 days.
    """
    for i in range(1, number_of_devices + 1):
        device_password_file = COMMON_DEVICE_PASSWORD_FILE + str(i) + EXTENSION_NAME
        device_csr_file = COMMON_DEVICE_CSR_FILE + str(i) + EXTENSION_NAME
        device_cert_file = COMMON_DEVICE_CERT_FILE + str(i) + EXTENSION_NAME
        device_private_key = create_private_key(
            key_file=device_password_file, password=password, key_size=key_size
        )
        device_csr = create_csr(
            private_key=device_private_key,
            csr_file=device_csr_file,
            subject=device_common_name + str(i),
            is_ca=False,
        )

        builder = create_cert_builder(
            subject=device_csr.subject,
            issuer_name=issuer_cert_subject,
            public_key=device_csr.public_key(),
            days=int(days / 100),
            is_ca=False,
        )

        device_cert = builder.sign(
            private_key=issuer_key, algorithm=hashes.SHA256(), backend=default_backend()
        )
        with open(device_cert_file, "wb") as f:
            f.write(device_cert.public_bytes(serialization.Encoding.PEM))


def create_verification_cert(nonce, issuer_password, root_verify=False, key_size=4096):
    """
    This method will create verification certificate for providing proof of possession.
    In this example the certificate getting verified that has already been uploaded to the Azure IoT Hub.
    :param nonce: The thumbprint generated for the certificate already in possession.
    :param issuer_password: The password for private key of the certificate already in possession.
    :param root_verify: A boolean variable to indicate whether we are verifying the root certificate or intermediate certificate.
    :param key_size: The key size to use for encryption. The default is 4096.
    """
    encoded_issuer_password = str.encode(issuer_password)

    if root_verify:
        verification_password_file = "demoCA/private/verfiication_ca_key.pem"
        verfication_csr_file = "demoCA/newcerts/verfiication_ca_csr.pem"
        verfication_cert_file = "demoCA/newcerts/verfiication_ca_cert.pem"
        issuer_key_file = "demoCA/private/ca_key.pem"
        issuer_cert_file = "demoCA/newcerts/ca_cert.pem"
    else:
        verification_password_file = "demoCA/private/verfiication_inter_key.pem"
        verfication_csr_file = "demoCA/newcerts/verfiication_inter_csr.pem"
        verfication_cert_file = "demoCA/newcerts/verfiication_inter_cert.pem"
        issuer_key_file = "demoCA/private/intermediate_key.pem"
        issuer_cert_file = "demoCA/newcerts/intermediate_cert.pem"

    with open(issuer_cert_file, "rb") as fh:
        pem_data = fh.read()
        issuer_cert = x509.load_pem_x509_certificate(pem_data, default_backend())

    with open(issuer_key_file, "rb") as key_file:
        pem_data = key_file.read()
        issuer_private_key = serialization.load_pem_private_key(
            pem_data, password=encoded_issuer_password, backend=default_backend()
        )

    verification_private_key = create_private_key(
        key_file=verification_password_file, password=None, key_size=key_size
    )
    verification_csr = create_csr(
        private_key=verification_private_key,
        csr_file=verfication_csr_file,
        subject=nonce,
        is_ca=False,
    )

    verification_builder = create_cert_builder(
        subject=verification_csr.subject,
        issuer_name=issuer_cert.subject,
        public_key=verification_csr.public_key(),
    )

    verification_cert = verification_builder.sign(
        private_key=issuer_private_key, algorithm=hashes.SHA256(), backend=default_backend()
    )
    with open(verfication_cert_file, "wb") as f:
        f.write(verification_cert.public_bytes(serialization.Encoding.PEM))


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


def create_csr(private_key, csr_file, subject, is_ca=False):
    """
    Method to create a certificate signing request.
    :param private_key: The private key to the certificate.
    :param csr_file: The file name of the certificate signing request.
    :param subject: The subject fo the certificate signing request.
    :param is_ca: Boolean to indicate if a cert is ca or non ca.
    :return: The certificate signing request.
    :rtype: :class `x509.CertificateSigningRequest`
    """
    builder = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(
            x509.Name(
                [
                    # Provide various details about who we are.
                    x509.NameAttribute(NameOID.COMMON_NAME, str.encode(subject).decode("utf-8"))
                ]
            )
        )
        .add_extension(x509.BasicConstraints(ca=is_ca, path_length=None), critical=False)
    )

    csr = builder.sign(
        private_key=private_key, algorithm=hashes.SHA256(), backend=default_backend()
    )

    with open(csr_file, "wb") as f:
        f.write(csr.public_bytes(serialization.Encoding.PEM))

    return csr


def create_directories_and_prereq_files(pipeline):
    """
    This function creates the necessary directories and files. This needs to be called as the first step before doing anything.
    :param pipeline: The boolean representing if function has been called from pipeline or not. True for pipeline, False for calling like a script.
    """
    dirPath = "demoCA"
    if os.path.exists(dirPath):
        print("demoCA exists, so will delete first")
        shutil.rmtree(dirPath)

    os.system("mkdir demoCA")
    if pipeline:
        # This command does not work when we run locally. So we have to pass in the pipeline variable
        os.system("touch demoCA/index.txt")
    else:
        os.system("type nul > demoCA/index.txt")
        # TODO Do we need this
        # os.system("type nul > demoCA/index.txt.attr")

    os.system("echo 1000 > demoCA/serial")
    # Create this folder as configuration file makes new keys go here
    os.mkdir("demoCA/private")
    # Create this folder as configuration file makes new certificates go here
    os.mkdir("demoCA/newcerts")


def delete_directories_certs_created_from_pipeline():
    """
    Function deletes all the directories and files which were created for the certificates.
    """
    dirPath = "demoCA"
    try:
        shutil.rmtree(dirPath)
    except Exception:
        print("Error while deleting directory")
    if os.path.exists("out_ca_cert.pem"):
        os.remove("out_ca_cert.pem")
    else:
        print("The file does not exist")
    if os.path.exists("out_ca_key.pem"):
        os.remove("out_ca_key.pem")
    else:
        print("The file does not exist")
    if os.path.exists(".rnd"):
        os.remove(".rnd")
    else:
        print("The file does not exist")


def before_cert_creation_from_pipeline():
    """
    This function creates the required folder and files before creating certificates.
    This also copies an openssl configurations file to be used for the generation of this certificates.
    NOTE : This function is only applicable when called from the pipeline via E2E tests
    and need not be used when it is called as a script.
    """
    create_directories_and_prereq_files(True)


def call_intermediate_cert_and_device_cert_creation_from_pipeline(
    intermediate_common_name,
    device_common_name,
    ca_password,
    intermediate_password,
    device_password,
    device_count,
    key_size=4096,
    days=365,
):
    """
    This function creates an intermediate certificate by getting called from the pipeline.
    This method will create an intermediate key, then an intermediate certificate request and finally an intermediate certificate.
    :param intermediate_common_name: The common name to be used in the subject for the intermediate certificate.
    :param device_common_name: The common name to be used in the subject for the device certificate.
    :param ca_password: The password for the root certificate which is going to be referenced by the intermediate.
    :param intermediate_password: The password for the intermediate certificate
    :param device_password: The password for the device certificate
    :param device_count: The number of devices for which the certificates are created.
    :param key_size: The key size to use for encryption. Default is 4096.
    :param days: The number of days for which the certificate is valid. Default is 1 year (365 days)
    """

    ca_cert = os.getenv("PROVISIONING_ROOT_CERT")
    ca_key = os.getenv("PROVISIONING_ROOT_CERT_KEY")
    in_cert_file_path = "ca_cert.pem"
    in_key_file_path = "ca_key.pem"
    with open(in_cert_file_path, "w") as out_ca_pem:
        cert_pem_data = str(base64.b64decode(ca_cert), "ascii")
        out_ca_pem.write(cert_pem_data)
        encoded_cert_pem_data = str.encode(cert_pem_data)
        root_cert = x509.load_pem_x509_certificate(encoded_cert_pem_data, default_backend())

        if os.path.exists(in_cert_file_path):
            print("root cert decoded and created")
        else:
            print("root cert NOT decoded and created")

    with open(in_key_file_path, "w") as out_ca_key:
        key_pem_data = str(base64.b64decode(ca_key), "ascii")
        out_ca_key.write(key_pem_data)
        encoded_key_pem_data = str.encode(key_pem_data)
        root_private_key = serialization.load_pem_private_key(
            encoded_key_pem_data, password=str.encode(ca_password), backend=default_backend()
        )

        if os.path.exists(in_key_file_path):
            print("root key decoded and created")
        else:
            print("root key NOT decoded and created")

    intermediate_password_file = "demoCA/private/intermediate_key.pem"

    intermediate_private_key = create_private_key(
        key_file=intermediate_password_file, password=intermediate_password, key_size=key_size
    )

    intermediate_cert = create_intermediate_ca_cert(
        issuer_cert_subject=root_cert.subject,
        issuer_key=root_private_key,
        intermediate_common_name=intermediate_common_name,
        intermediate_private_key=intermediate_private_key,
        days=days,
    )

    create_multiple_device_keys_and_certs(
        number_of_devices=device_count,
        issuer_cert_subject=intermediate_cert.subject,
        issuer_key=intermediate_private_key,
        device_common_name=device_common_name,
        password=device_password,
        key_size=key_size,
        days=days,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a certificate chain.")
    parser.add_argument("domain", help="Domain name or common name.")
    parser.add_argument(
        "-s",
        "--key-size",
        type=int,
        help="Size of the key in bits. 2048 bit is quite common. "
        + "4096 bit is more secure and the default.",
    )
    parser.add_argument(
        "-d",
        "--days",
        type=int,
        help="Validity time in days. Default is 10 years for root , 1 year for intermediate and 1 month for leaf",
    )
    parser.add_argument(
        "--ca-password", type=str, help="CA key password. If omitted it will be prompted."
    )
    parser.add_argument(
        "--intermediate-password",
        type=str,
        help="intermediate key password. If omitted it will be prompted.",
    )
    parser.add_argument(
        "--device-password", type=str, help="device key password. If omitted it will be prompted."
    )

    parser.add_argument(
        "--issuer-password",
        type=str,
        help="The passphrase for the issuer needed only during verification. "
        "If omitted it will be prompted.",
    )

    parser.add_argument(
        "--device-count", type=str, help="Number of devices that present in a group. Default is 1."
    )

    parser.add_argument(
        "--mode",
        type=str,
        help="The mode in which certificate is created. "
        "By default non-verification mode. For verification use 'verification'",
    )
    parser.add_argument(
        "--nonce",
        type=str,
        help="Thumbprint generated from IoT Hub or DPS certificates for performing proof of possession. "
        "During verification mode if omitted it will be prompted.",
    )
    parser.add_argument(
        "--root-verify",
        type=str,
        help="The boolean value to enter to mean either the root or intermediate verification. "
        "By default it is True meaning root verifictaion. "
        "If veriication of intermediate certification is needed please enter False.",
    )
    args = parser.parse_args()

    common_name = args.domain

    if args.key_size:
        key_size = args.key_size
    else:
        key_size = 4096
    if args.days:
        days = args.days
    else:
        days = 365

    ca_password = None
    intermediate_password = None
    if args.mode:
        if args.mode == "verification":
            mode = "verification"
        else:
            raise ValueError(
                "No other mode except verification is accepted. Default is non-verification"
            )
    else:
        mode = "non-verification"

    if mode == "non-verification":
        print("In non-verification mode...........")
        if args.ca_password:
            ca_password = args.ca_password
        else:
            ca_password = getpass.getpass("Enter pass phrase for root key: ")
        if args.intermediate_password:
            intermediate_password = args.intermediate_password
        else:
            intermediate_password = getpass.getpass("Enter pass phrase for intermediate key: ")
        if args.device_password:
            device_password = args.device_password
        else:
            device_password = getpass.getpass("Enter pass phrase for device key: ")
        if args.device_count:
            device_count = args.device_count
        else:
            device_count = 1
    else:
        print("In verification mode...........")
        if args.nonce:
            nonce = args.nonce
            print("Received nonce")
        else:
            nonce = getpass.getpass("Enter nonce for verification mode")
        if args.root_verify:
            lower_root_verify = args.root_verify.lower()

            if lower_root_verify == "false":
                root_verify = False
                print("Root verify is False. So will be verifying intermediate certificate")
            else:
                root_verify = True
                print("Root verify is True. So will be verifying root certificate")
        else:
            print("Root verify will be by default False.")
            root_verify = False

        if args.issuer_password:
            issuer_password = args.issuer_password
        else:
            issuer_password = getpass.getpass(
                "Enter pass phrase for issuer certificate verification: "
            )

    create_directories_and_prereq_files(False)

    if mode == "verification":
        create_verification_cert(nonce, issuer_password, root_verify, key_size=4096)
    else:
        create_certificate_chain(
            common_name=args.domain,
            ca_password=ca_password,
            intermediate_password=intermediate_password,
            device_password=device_password,
            device_count=int(device_count),
        )
