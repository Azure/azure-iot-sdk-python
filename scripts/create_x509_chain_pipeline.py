import os
import re
import base64
import shutil
import subprocess
import argparse
import getpass


def create_custom_config():
    """
    This function creates a custom configuration based on the already present openssl
    configuration file present in local machine. The custom configuration is needed for
    creating these certificates for sample and tests.
    NOte : For this to work the local openssl conf file path needs to be stored in an
    environment variable.
    """
    # The paths from different OS is different.
    # For example OS X path is "/usr/local/etc/openssl/openssl.cnf"
    # Windows path is "C:/Openssl/bin//openssl.cnf" etc
    # Best options is to have the location of openssl config file in an env variable
    # The openssl config file extension could be "cfg" or "cnf"

    config_path = os.getenv("OPENSSL_CONF")
    with open(config_path, "r") as openssl_config:
        config = openssl_config.read()
    lines = config.splitlines()
    policy_loose_found = False
    policy_any_found = False

    policy_any_regex = re.compile(r"\s*\[\s*policy_anything\s*\]\s*")

    # First, try to find policy_anything in the openssl config file
    for number, line in enumerate(lines):
        if re.search(policy_any_regex, line):
            policy_any_found = True
            break
    # Of not found the try the search with policy_loose
    if not policy_any_found:
        policy_loose_regex = re.compile(r"\s*\[\s*policy_loose\s*\]\s*")
        for number, line in enumerate(lines):
            if re.search(policy_loose_regex, line):
                policy_loose_found = True
                break

    list_of_lines = list()
    ca_default_regex = re.compile(r"\s*\[\s*CA_default\s*\]\s*")
    ca_default_section_found = False
    policy_regex = re.compile(r"\s*\s*(policy\s*=\s*policy_strict|policy\s*=\s*policy_match)")
    with open(config_path, "r") as change_openssl_config:
        for line in change_openssl_config:
            if not ca_default_section_found and re.search(ca_default_regex, line):
                ca_default_section_found = True
            if ca_default_section_found and re.search(policy_regex, line):
                if policy_loose_found:
                    line = policy_regex.sub("policy = policy_loose", line)
                if policy_any_found:
                    line = policy_regex.sub("policy = policy_anything", line)
            list_of_lines.append(line.strip())

    with open("demoCA/openssl.cnf", "w") as local_file:
        local_file.write("\n".join(list_of_lines) + "\n")


def create_verification_cert(
    nonce, root_verify, ca_password=None, intermediate_password=None, key_size=4096
):
    print(ca_password)
    print("Done generating verification key")
    # subject = "//C=US/CN=" + nonce
    subject = "/CN=" + nonce

    if root_verify:
        key_file = "demoCA/private/verification_root_key.pem"
        csr_file = "demoCA/newcerts/verification_root_csr.pem"
        in_key_file = "demoCA/private/ca_key.pem"
        in_cert_file = "demoCA/newcerts/ca_cert.pem"
        out_cert_file = "demoCA/newcerts/verification_root_cert.pem"
        passphrase = ca_password
    else:
        key_file = "demoCA/private/verification_inter_key.pem"
        csr_file = "demoCA/newcerts/verification_inter_csr.pem"
        in_key_file = "demoCA/private/intermediate_key.pem"
        in_cert_file = "demoCA/newcerts/intermediate_cert.pem"
        out_cert_file = "demoCA/newcerts/verification_inter_cert.pem"
        passphrase = intermediate_password

    command_verification_key = ["openssl", "genrsa", "-out", key_file, str(key_size)]

    run_verification_key = subprocess.run(
        command_verification_key,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    print_subprocess_output(run_verification_key)

    command_verification_csr = [
        "openssl",
        "req",
        "-key",
        key_file,
        "-new",
        "-out",
        csr_file,
        "-subj",
        subject,
    ]

    run_verification_csr = subprocess.run(
        command_verification_csr,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    print_subprocess_output(run_verification_csr)

    command_verification_cert = [
        "openssl",
        "x509",
        "-req",
        "-in",
        csr_file,
        "-CA",
        in_cert_file,
        "-CAkey",
        in_key_file,
        "-passin",
        "pass:" + passphrase,
        "-CAcreateserial",
        "-out",
        out_cert_file,
        "-days",
        str(30),
        "-sha256",
    ]

    run_verification_cert = subprocess.run(
        command_verification_cert,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    print_subprocess_output(run_verification_cert)

    if os.path.exists(out_cert_file):
        print("Done generating verification certificate. Upload to IoT Hub to verify")
    else:
        print("verification cert NOT generated")


def print_subprocess_output(run_command):
    print(run_command.stdout)
    print(run_command.stderr)
    print(run_command.returncode)


def create_directories_and_prereq_files(pipeline):
    """
    This function creates the necessary directories and files. This needs to be called as the first step before doing anything.
    :param pipeline: The boolean representing if function has been called from pipeline or not. True for pipeline, False for calling like a script.
    """
    os.system("mkdir demoCA")
    if pipeline:
        # This command does not work when we run locally. So we have to pass in the pipeline variable
        os.system("touch demoCA/index.txt")
        # TODO Do we need this
        # os.system("touch demoCA/index.txt.attr")
    else:
        os.system("type nul > demoCA/index.txt")
        # TODO Do we need this
        # os.system("type nul > demoCA/index.txt.attr")

    os.system("echo 1000 > demoCA/serial")
    # Create this folder as configuration file makes new keys go here
    os.mkdir("demoCA/private")
    # Create this folder as configuration file makes new certificates go here
    os.mkdir("demoCA/newcerts")


def create_root(common_name, ca_password, key_size=4096, days=3650):
    """
    This function creates the root key and the root certificate.

    :param common_name: The common name to be used in the subject.
    :param ca_password: The password for the root certificate which is going to be referenced by the intermediate.
    :param key_size: The key size to use for encryption. Default is 4096.
    :param days: The number of days for which the certificate is valid. Default is 10 years (3650 days)
    """
    command_root_key = [
        "openssl",
        "genrsa",
        "-aes256",
        "-out",
        "demoCA/private/ca_key.pem",
        "-passout",
        "pass:" + ca_password,
        str(key_size),
    ]

    run_root_key = subprocess.run(
        command_root_key, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    print_subprocess_output(run_root_key)

    if os.path.exists("demoCA/private/ca_key.pem"):
        print("Done generating root key")
    else:
        print("root key NOT generated")

    subject = "/CN=" + common_name

    command_root_cert = [
        "openssl",
        "req",
        "-config",
        "demoCA/openssl.cnf",
        "-key",
        "demoCA/private/ca_key.pem",
        "-passin",
        "pass:" + ca_password,
        "-new",
        "-x509",
        "-days",
        str(days),
        "-sha256",
        "-extensions",
        "v3_ca",
        "-out",
        "demoCA/newcerts/ca_cert.pem",
        "-subj",
        subject,
    ]

    run_root_cert = subprocess.run(
        command_root_cert, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    print_subprocess_output(run_root_cert)

    if os.path.exists("demoCA/newcerts/ca_cert.pem"):
        print("Done generating root cert")
    else:
        print("root cert NOT generated")


def create_intermediate(
    common_name, pipeline, ca_password, intermediate_password, key_size=4096, days=365
):
    """
    This method will create an intermediate key, then an intermediate certificate request and finally an intermediate certificate.
    :param common_name: The common name to be used in the subject.
    :param pipeline: A boolean variable representing whether this script is being run in Azure Dev Ops pipeline or not.
    When this function is called from Azure Dev Ops this variable is True otherwise False
    :param ca_password: The password for the root certificate which is going to be referenced by the intermediate.
    :param intermediate_password: The password for the intermediate certificate
    :param key_size: The key size to use for encryption. Default is 4096.
    :param days: The number of days for which the certificate is valid. Default is 1 year (365 days)
    """

    if pipeline:
        ca_cert = os.getenv("PROVISIONING_ROOT_CERT")
        ca_key = os.getenv("PROVISIONING_ROOT_CERT_KEY")
        in_cert_file_path = "ca_cert.pem"
        in_key_file_path = "ca_key.pem"
        with open(in_cert_file_path, "w") as out_ca_pem:
            cert = str(base64.b64decode(ca_cert), "ascii")
            out_ca_pem.write(cert)

            if os.path.exists(in_cert_file_path):
                print("root cert decoded and created")
            else:
                print("root cert NOT decoded and created")
        with open(in_key_file_path, "w") as out_ca_key:
            key = str(base64.b64decode(ca_key), "ascii")
            out_ca_key.write(key)

            if os.path.exists(in_key_file_path):
                print("root key decoded and created")
            else:
                print("root key NOT decoded and created")
    else:
        in_cert_file_path = "demoCA/newcerts/ca_cert.pem"
        in_key_file_path = "demoCA/private/ca_key.pem"

    command_intermediate_key = [
        "openssl",
        "genrsa",
        "-aes256",
        "-out",
        "demoCA/private/intermediate_key.pem",
        "-passout",
        "pass:" + intermediate_password,
        str(key_size),
    ]

    run_intermediate_key = subprocess.run(
        command_intermediate_key,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    print_subprocess_output(run_intermediate_key)

    if os.path.exists("demoCA/private/intermediate_key.pem"):
        print("Done generating intermediate key")
    else:
        print("intermediate key NOT generated")

    subject = "/CN=" + common_name
    command_intermediate_csr = [
        "openssl",
        "req",
        "-config",
        "demoCA/openssl.cnf",
        "-key",
        "demoCA/private/intermediate_key.pem",
        "-passin",
        "pass:" + intermediate_password,
        "-new",
        "-sha256",
        "-out",
        "demoCA/newcerts/intermediate_csr.pem",
        "-subj",
        subject,
    ]

    run_intermediate_csr = subprocess.run(
        command_intermediate_csr,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print_subprocess_output(run_intermediate_csr)

    if os.path.exists("demoCA/newcerts/intermediate_csr.pem"):
        print("Done generating intermediate CSR")
    else:
        print("intermediate csr NOT generated")

    command_intermediate_cert = [
        "openssl",
        "ca",
        "-config",
        "demoCA/openssl.cnf",
        "-in",
        "demoCA/newcerts/intermediate_csr.pem",
        "-out",
        "demoCA/newcerts/intermediate_cert.pem",
        "-keyfile",
        in_key_file_path,
        "-cert",
        in_cert_file_path,
        "-passin",
        "pass:" + ca_password,
        "-extensions",
        "v3_ca",
        "-days",
        str(days),
        "-notext",
        "-md",
        "sha256",
        "-batch",
    ]

    run_intermediate_cert = subprocess.run(
        command_intermediate_cert,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print_subprocess_output(run_intermediate_cert)

    if os.path.exists("demoCA/newcerts/intermediate_cert.pem"):
        print("Done generating intermediate certificate")
    else:
        print("intermediate cert NOT generated")


def create_certificate_chain(
    common_name,
    ca_password,
    intermediate_password,
    device_password,
    device_count=1,
    key_size=4096,
    days=365,
):
    """
    This method will create a basic 3 layered chain certificate containing a root, then an intermediate and then some number of leaf certificates.
    This function is only used when the certificates are created from script.

    :param common_name: The common name to be used in the subject. This is a single common name which would be applied to all certs created. Since this common name is meant for all,
    this common name will be prepended by the words "root", "inter" and "device" for root, intermediate and device certificates.
    For device certificates the common name will be further appended with the index of the device.
    :param ca_password: The password for the root certificate which is going to be referenced by the intermediate.
    :param intermediate_password: The password for the intermediate certificate
    :param device_password: The password for the device certificate
    :param device_count: The number of leaf devices for which that many number of certificates will be generated.
    :param key_size: The key size to use for encryption. The default is 4096.
    :param days: The number of days for which the certificate is valid. The default is 1 year or 365 days.
    For the root cert this value is multiplied by 10. For the device certificates this number will be divided by 10.
    """
    common_name_for_root = "root" + common_name
    create_root(common_name_for_root, ca_password=ca_password, key_size=key_size, days=days * 10)

    common_name_for_intermediate = "inter" + common_name
    create_intermediate(
        common_name_for_intermediate,
        pipeline=False,
        ca_password=ca_password,
        intermediate_password=intermediate_password,
        key_size=key_size,
        days=days,
    )

    for index in range(0, device_count):
        index = index + 1
        print("creating device certificate for " + str(index))
        common_name_for_all_device = "device" + common_name
        create_leaf_certificates(
            index,
            common_name_for_all_device,
            intermediate_password=intermediate_password,
            device_password=device_password,
            key_size=key_size,
            days=int(days / 10),
        )


def create_leaf_certificates(
    index,
    common_name_for_all_device,
    intermediate_password,
    device_password,
    key_size=4096,
    days=30,
):
    """
    This function creates leaf or device certificates for a single device within a group represented
     by the index in the group.

    :param index: The index representing the ith device in the group.
    :param common_name_for_all_device: The common name to be used in the subject. This is applicable
    of all the certificates created using this method. The common name will be appended by the
    index to create an unique common name for each certificate.
    :param intermediate_password: The password for the intermediate certificate
    :param device_password: The password for the device certificate
    :param key_size: The key size to use for encryption. The default is 4096.
    :param days: The number of days for which the certificate is valid. The default is 1 month or 30 days.
    """

    key_file_name = "device_key" + str(index) + ".pem"
    csr_file_name = "device_csr" + str(index) + ".pem"
    cert_file_name = "device_cert" + str(index) + ".pem"

    command_device_key = [
        "openssl",
        "genrsa",
        "-aes256",
        "-out",
        "demoCA/private/" + key_file_name,
        "-passout",
        "pass:" + device_password,
        str(key_size),
    ]

    run_device_key = subprocess.run(
        command_device_key, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    print(run_device_key.stdout)
    print(run_device_key.stderr)
    print(run_device_key.returncode)

    if os.path.exists("demoCA/private/" + key_file_name):
        print("Done generating device key with filename {filename}".format(filename=key_file_name))
    else:
        print("device key NOT generated")

    subject = "/CN=" + common_name_for_all_device + str(index)
    command_device_csr = [
        "openssl",
        "req",
        "-config",
        "demoCA/openssl.cnf",
        "-key",
        "demoCA/private/" + key_file_name,
        "-passin",
        "pass:" + device_password,
        "-new",
        "-sha256",
        "-out",
        "demoCA/newcerts/" + csr_file_name,
        "-subj",
        subject,
    ]

    run_device_csr = subprocess.run(
        command_device_csr, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    print(run_device_csr.stdout)
    print(run_device_csr.stderr)
    print(run_device_csr.returncode)

    if os.path.exists("demoCA/newcerts/" + csr_file_name):
        print("Done generating device CSR with filename {filename}".format(filename=csr_file_name))
    else:
        print("device CSR NOT generated")

    command_device_cert = [
        "openssl",
        "ca",
        "-config",
        "demoCA/openssl.cnf",
        "-in",
        "demoCA/newcerts/" + csr_file_name,
        "-out",
        "demoCA/newcerts/" + cert_file_name,
        "-keyfile",
        "demoCA/private/intermediate_key.pem",
        "-cert",
        "demoCA/newcerts/intermediate_cert.pem",
        "-passin",
        "pass:" + intermediate_password,
        "-extensions",
        "usr_cert",
        "-days",
        str(days),
        "-notext",
        "-md",
        "sha256",
        "-batch",
    ]

    run_device_cert = subprocess.run(
        command_device_cert, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    print(run_device_cert.stdout)
    print(run_device_cert.stderr)
    print(run_device_cert.returncode)

    if os.path.exists("demoCA/newcerts/" + cert_file_name):
        print(
            "Done generating device cert with filename {filename}".format(filename=cert_file_name)
        )
    else:
        print("device cert NOT generated")


def before_cert_creation_from_pipeline():
    """
    This function creates the required folder and files before creating certificates.
    This also copies an openssl configurtaion file to be used for the generation of this certificates.
    NOTE : This function is only applicable when called from the pipeline via E2E tests
    and need not be used when it is called as a script.
    """
    create_directories_and_prereq_files(True)

    shutil.copy("config/openssl.cnf", "demoCA/openssl.cnf")

    if os.path.exists("demoCA/openssl.cnf"):
        print("Configuration file have been copied")
    else:
        print("Configuration file have NOT been copied")


def call_intermediate_cert_creation_from_pipeline(
    common_name, ca_password, intermediate_password, key_size=4096, days=365
):
    """
    This function creates an intermediate certificate by getting called from the pipeline.
    This method will create an intermediate key, then an intermediate certificate request and finally an intermediate certificate.
    :param common_name: The common name to be used in the subject.
    :param ca_password: The password for the root certificate which is going to be referenced by the intermediate.
    :param intermediate_password: The password for the intermediate certificate
    :param key_size: The key size to use for encryption. Default is 4096.
    :param days: The number of days for which the certificate is valid. Default is 1 year (365 days)
    :param common_name: The common name of the intermediate certificate.
    :param ca_password: The password for the root ca certificate from which the intermediate certificate will be created.
    :param intermediate_password: The password for the intermediate certificate.
    :param key_size: The key size for the intermediate key. Default is 4096.
    :param days: The number of days for hich
    :return:
    """

    create_intermediate(
        common_name=common_name,
        pipeline=True,
        ca_password=ca_password,
        intermediate_password=intermediate_password,
        key_size=key_size,
        days=days,
    )


def create_device_certs(
    common_name, intermediate_password, device_password, key_size=4096, days=30, device_count=1
):
    """
    Creates device certificates from an already created intermediate certificate which exists in
    the demoCA/newcerts directory. Assumption that intermediate has already been created with the
    name 'intermediate_cert.pem' and the key file is 'intermediate_key.pem'
    Hence the intermediate password is known to whoever using this function.

    :param common_name: The common name for all device certificates. This will be appended by the
    index of the specific device for which the cert is being created.
    :param intermediate_password: The intermediate password which should be already known.
    :param device_password: The device cert password.
    :param key_size: Expected key size. Default is 4096.
    :param days: Expected days. Default is 30
    :param device_count: The count of devices for which certs needs to be created. Default is 1 device.
    """
    for index in range(0, device_count):
        index = index + 1
        print("creating device certificate for " + str(index))
        create_leaf_certificates(
            index,
            common_name_for_all_device=common_name,
            intermediate_password=intermediate_password,
            device_password=device_password,
            key_size=key_size,
            days=days,
        )


def delete_directories_certs_created_from_pipeline():
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
        "--device-count", type=str, help="Number of devices that present in a group. Default is 1."
    )

    parser.add_argument(
        "--mode",
        type=str,
        help="The mode in which certificate is created. By default non-verification mode. For verification use 'verification'",
    )
    parser.add_argument(
        "--nonce",
        type=str,
        help="thumprint generated from iot hub certificates. During verification mode if omitted it will be prompted.",
    )
    parser.add_argument(
        "--root-verify",
        type=str,
        help="The boolean value to enter in case it is the root or intermediate verification. By default it is True meaning root verifictaion. If veriication of intermediate certification is needed please enter False ",
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
        days = 30

    ca_password = None
    intermediate_password = None
    if args.mode:
        if args.mode == "verification":
            mode = "verification"
            print("in verification mode")
        else:
            raise ValueError(
                "No other mode except verification is accepted. Default is non-verification"
            )
    else:
        mode = "non-verification"

    if mode == "non-verification":
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
        print("in verification mode")
        if args.nonce:
            nonce = args.nonce
            print("got nonce")
        else:
            nonce = getpass.getpass("Enter nonce for verification mode")
        if args.root_verify:
            lower_root_verify = args.root_verify.lower()
            print("root verify is False")
            if lower_root_verify == "false":
                root_verify = False
                if args.intermediate_password:
                    intermediate_password = args.intermediate_password
                else:
                    intermediate_password = getpass.getpass(
                        "Enter pass phrase for intermediate key: "
                    )
            else:
                root_verify = True
                print("root verify is TRue")
                if args.ca_password:
                    ca_password = args.ca_password
                    print("putting ca password")
                else:
                    ca_password = getpass.getpass("Enter pass phrase for root key: ")
        else:
            root_verify = True
            print("root verify is default TRue")
            if args.ca_password:
                ca_password = args.ca_password
            else:
                ca_password = getpass.getpass("Enter pass phrase for root key: ")
            print(ca_password)

    if os.path.exists("demoCA/private/") and os.path.exists("demoCA/newcerts/"):
        print("demoCA already exists.")
    else:
        create_directories_and_prereq_files(False)
        create_custom_config()

    if mode == "verification":
        create_verification_cert(nonce, root_verify, ca_password, intermediate_password)
    else:
        create_certificate_chain(
            common_name=args.domain,
            ca_password=ca_password,
            intermediate_password=intermediate_password,
            device_password=device_password,
            device_count=int(device_count),
        )
