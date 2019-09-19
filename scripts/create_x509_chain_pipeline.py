import os
import re
import base64
import logging
import shutil
import subprocess


# TODO : Do we change all print statements to logging ?
logging.basicConfig(level=logging.DEBUG)


def create_custom_config():
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


def create_verification_cert(nonce, root_verify, ca_password, intermediate_password, key_size=4096):

    print("Done generating verification key")
    subject = "//C=US/CN=" + nonce

    if not root_verify:
        os.system(
            "openssl genrsa -out demoCA/private/verification_inter_key.pem" + " " + str(key_size)
        )
        os.system(
            "openssl req -key demoCA/private/verification_inter_key.pem"
            + " "
            + "-new -out demoCA/newcerts/verification_inter_csr.pem -subj "
            + subject
        )
        print("Done generating verification CSR for intermediate")

        os.system(
            "openssl x509 -req -in demoCA/newcerts/verification_inter_csr.pem"
            + " "
            + "-CA demoCA/newcerts/intermediate_cert.pem -CAkey demoCA/private/intermediate_key.pem -passin pass:"
            + intermediate_password
            + " "
            + "-CAcreateserial -out demoCA/newcerts/verification_inter_cert.pem -days 300 -sha256"
        )
        print(
            "Done generating verification certificate for intermediate. Upload to IoT Hub to verify"
        )

    else:
        os.system(
            "openssl genrsa -out demoCA/private/verification_root_key.pem" + " " + str(key_size)
        )
        os.system(
            "openssl req -key demoCA/private/verification_root_key.pem"
            + " "
            + "-new -out demoCA/newcerts/verification_root_csr.pem -subj "
            + subject
        )
        print("Done generating verification CSR")

        os.system(
            "openssl x509 -req -in demoCA/newcerts/verification_root_csr.pem"
            + " "
            + "-CA demoCA/newcerts/ca_cert.pem -CAkey demoCA/private/ca_key.pem -passin pass:"
            + ca_password
            + " "
            + "-CAcreateserial -out demoCA/newcerts/verification_root_cert.pem -days 300 -sha256"
        )
        print("Done generating verification certificate. Upload to IoT Hub to verify")


def create_directories_and_prereq_files():
    # os.system("type nul > demoCA/index.txt")
    # os.system("type nul > demoCA/index.txt.attr")
    os.system("touch demoCA/index.txt")
    # os.system("touch demoCA/index.txt.attr")
    os.system("echo 1000 > demoCA/serial")
    # Create this folder as configuration file makes new keys go here
    os.mkdir("demoCA/private")
    # Create this folder as configuration file makes new certificates go here
    os.mkdir("demoCA/newcerts")


def create_root(common_name, ca_password, key_size=4096, days=3650):
    os.system(
        "openssl genrsa -aes256 -out demoCA/private/ca_key.pem -passout pass:"
        + ca_password
        + " "
        + str(key_size)
    )
    print("Done generating root key")
    # We need another argument like country as there is always error regarding the first argument
    # Subject Attribute /C has no known NID, skipped
    # So if the first arg is common name the error comes due to common name nad common name is not taken

    subject = "//C=US/CN=" + common_name
    os.system(
        "openssl req -config demoCA/openssl.cnf -key demoCA/private/ca_key.pem -passin pass:"
        + ca_password
        + " "
        + "-new -x509 -days "
        + str(days)
        + " -sha256 -extensions v3_ca -out demoCA/newcerts/ca_cert.pem -subj "
        + subject
    )
    print("Done generating root certificate")


def create_intermediate(
    common_name, pipeline, ca_password, intermediate_password, key_size=4096, days=365
):

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

    os.system(
        "openssl genrsa -aes256 -out demoCA/private/intermediate_key.pem -passout pass:"
        + intermediate_password
        + " "
        + str(key_size)
    )
    if os.path.exists("demoCA/private/intermediate_key.pem"):
        print("Done generating intermediate key")
    else:
        print("intermediate key NOT generated")

    subject = "/CN=" + common_name
    os.system(
        "openssl req -config demoCA/openssl.cnf -key demoCA/private/intermediate_key.pem -passin pass:"
        + intermediate_password
        + " "
        + "-new -sha256 -out demoCA/newcerts/intermediate_csr.pem -subj "
        + subject
    )

    if os.path.exists("demoCA/newcerts/intermediate_csr.pem"):
        print("Done generating intermediate CSR")
    else:
        print("intermediate csr NOT generated")

    command = [
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

    cp = subprocess.run(
        command, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    print(cp.stdout)
    print(cp.stderr)
    print(cp.returncode)

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
    pipeline=False,
    key_size=4096,
    days=365,
):
    common_name_for_root = "root" + common_name
    create_root(common_name_for_root, ca_password=ca_password, key_size=key_size, days=days * 10)

    common_name_for_intermediate = "root" + common_name
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
            days=days,
        )


def create_leaf_certificates(
    index,
    common_name_for_all_device,
    intermediate_password,
    device_password,
    key_size=4096,
    days=365,
):

    key_file_name = "device_key" + str(index) + ".pem"
    csr_file_name = "device_csr" + str(index) + ".pem"
    cert_file_name = "device_cert" + str(index) + ".pem"

    os.system(
        "openssl genrsa -aes256 -out demoCA/private/"
        + key_file_name
        + " -passout pass:"
        + device_password
        + " "
        + str(key_size)
    )
    if os.path.exists("demoCA/private/" + key_file_name):
        print("Done generating device key with filename {filename}".format(filename=key_file_name))
        logging.debug(
            "Done generating device key with filename {filename}".format(filename=key_file_name)
        )
    else:
        print("device key NOT generated")

    subject = "//C=US/CN=" + common_name_for_all_device + str(index)
    os.system(
        "openssl req -config demoCA/openssl.cnf -new -sha256 -key demoCA/private/"
        + key_file_name
        + " -passin pass:"
        + device_password
        + " "
        + "-out demoCA/newcerts/"
        + csr_file_name
        + " -subj "
        + subject
    )
    if os.path.exists("demoCA/newcerts/" + csr_file_name):
        print("Done generating device CSR with filename {filename}".format(filename=csr_file_name))
        logging.debug(
            "Done generating device CSR with filename {filename}".format(filename=csr_file_name)
        )
    else:
        print("device CSR NOT generated")

    os.system(
        "openssl ca -config demoCA/openssl.cnf -in demoCA/newcerts/"
        + csr_file_name
        + " -out demoCA/newcerts/"
        + cert_file_name
        + " -keyfile demoCA/private/intermediate_key.pem -cert demoCA/newcerts/intermediate_cert.pem -passin pass:"
        + intermediate_password
        + " "
        + "-extensions usr_cert -days "
        + str(days)
        + " -notext -md sha256 -batch"
    )

    if os.path.exists("demoCA/newcerts/" + cert_file_name):
        print(
            "Done generating device cert with filename {filename}".format(filename=cert_file_name)
        )
        logging.debug(
            "Done generating device cert with filename {filename}".format(filename=cert_file_name)
        )
    else:
        print("device cert NOT generated")


def call_intermediate_cert_creation_from_pipeline(
    common_name, ca_password, intermediate_password, key_size=4096, days=30
):
    os.system("mkdir demoCA")
    create_directories_and_prereq_files()

    shutil.copy("config/openssl.cnf", "demoCA/openssl.cnf")

    if os.path.exists("demoCA/openssl.cnf"):
        print("Configuration file have been copied")
    else:
        print("Configuration file have NOT been copied")

    print("ca_password={ca_password}".format(ca_password=ca_password))
    print(
        "intermediate_password={intermediate_password}".format(
            intermediate_password=intermediate_password
        )
    )

    create_intermediate(
        common_name=common_name,
        pipeline=True,
        ca_password=ca_password,
        intermediate_password=intermediate_password,
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


def call_device_cert_creation_from_pipeline(
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
