import os
import re
import argparse
import getpass
from sys import platform


def create_custom_config():
    # The paths from different OS is different.
    # For example OS X path is "/usr/local/etc/openssl/openssl.cnf"
    # Windows path is "C:/Openssl/bin//openssl.cnf" etc
    # Best options is to have the location of openssl config file in an env variable
    # The openssl config file extension could be "cfg" or "cnf"

    # config_path = os.getenv("OPENSSLCONFIG")
    config_path = "C:/OpenSSL-Win64/bin/openssl.cfg"
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


def create_verification_cert(nonce):
    os.system("openssl genrsa -out demoCA/private/verification_key.pem" + " " + str(key_size))
    print("Done generating verification key")
    subject = "//C=US/CN=" + nonce

    os.system(
        "openssl req -key demoCA/private/verification_key.pem"
        + " "
        + "-new -out demoCA/newcerts/verification_csr.pem -subj "
        + subject
    )
    print("Done generating verification CSR")

    os.system(
        "openssl x509 -req -in demoCA/newcerts/verification_csr.pem"
        + " "
        + "-CA demoCA/newcerts/ca_cert.pem -CAkey demoCA/private/ca_key.pem -passin pass:"
        + ca_password
        + " "
        + "-CAcreateserial -out demoCA/newcerts/verification_cert.pem -days 300 -sha256"
    )
    print("Done generating verification certificate. Upload to IoT Hub to verify")


def create_directories():
    os.system("type nul > demoCA/index.txt")
    os.system("echo 1000 > demoCA/serial")
    # Create this folder as configuration file makes new keys go here
    os.mkdir("demoCA/private")
    # Create this folder as configuration file makes new certificates go here
    os.mkdir("demoCA/newcerts")


def create_certificate_chain(common_name, ca_password, intermediate_password, device_password):
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

    subject = "//C=US/CN=root" + common_name
    os.system(
        "openssl req -config demoCA/openssl.cnf -key demoCA/private/ca_key.pem -passin pass:"
        + ca_password
        + " "
        + "-new -x509 -days 300 -sha256 -extensions v3_ca -out demoCA/newcerts/ca_cert.pem -subj "
        + subject
    )
    print("Done generating root certificate")
    os.system(
        "openssl genrsa -aes256 -out demoCA/private/intermediate_key.pem -passout pass:"
        + intermediate_password
        + " "
        + str(key_size)
    )
    print("Done generating intermediate key")
    subject = "//C=US/CN=inter" + common_name
    os.system(
        "openssl req -config demoCA/openssl.cnf -key demoCA/private/intermediate_key.pem -passin pass:"
        + intermediate_password
        + " "
        + "-new -sha256 -out demoCA/newcerts/intermediate_csr.pem -subj "
        + subject
    )

    print("Done generating intermediate CSR")
    os.system(
        "openssl ca -config demoCA/openssl.cnf -in demoCA/newcerts/intermediate_csr.pem -out demoCA/newcerts/intermediate_cert.pem -keyfile demoCA/private/ca_key.pem -cert demoCA/newcerts/ca_cert.pem -passin pass:"
        + ca_password
        + " "
        + "-extensions v3_ca -days 30 -notext -md sha256 -batch"
    )
    print("Done generating intermediate certificate")

    os.system(
        "openssl genrsa -aes256 -out demoCA/private/device_key.pem -passout pass:"
        + device_password
        + " "
        + str(key_size)
    )
    print("Done generating device key")
    subject = "//C=US/CN=device" + common_name
    os.system(
        "openssl req -config demoCA/openssl.cnf -new -sha256 -key demoCA/private/device_key.pem -passin pass:"
        + device_password
        + " "
        + "-out demoCA/newcerts/device_csr.pem -subj "
        + subject
    )
    print("Done generating device CSR")
    os.system(
        "openssl ca -config demoCA/openssl.cnf -in demoCA/newcerts/device_csr.pem -out demoCA/newcerts/device_cert.pem -keyfile demoCA/private/intermediate_key.pem -cert demoCA/newcerts/intermediate_cert.pem -passin pass:"
        + intermediate_password
        + " "
        + "-extensions usr_cert -days 3 -notext -md sha256 -batch"
    )
    print("Done generating device certificate")


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
        "-d", "--days", type=int, help="Validity time in days. Default is 30 (1 month)."
    )
    parser.add_argument("--common-name", type=str, help="Common name. Default is the domain.")
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
        "--mode",
        type=str,
        help="The mode in which certificate is created. By default non-verification mode. For verification use 'verification'",
    )
    parser.add_argument(
        "--nonce",
        type=str,
        help="thumprint generated from iot hub certificates. During verification mode if omitted it will be prompted.",
    )
    args = parser.parse_args()
    if args.key_size:
        key_size = args.key_size
    else:
        key_size = 4096
    if args.days:
        days = args.days
    else:
        days = 30

    if args.domain:
        common_name = args.domain
    else:
        common_name = "random"

    if args.ca_password:
        ca_password = args.ca_password
    else:
        ca_password = getpass.getpass("Enter pass phrase for root key: ")

    if args.mode:
        if args.mode == "verification":
            mode = "verification"
        else:
            raise ValueError(
                "No other mode except verification is accepted. Default is non-verification"
            )
    else:
        mode = "non-verification"

    # Create the directory demoCA as that is the configuration in most openssl installation
    os.system("mkdir demoCA")

    create_custom_config()

    if mode == "non-verification":
        if args.intermediate_password:
            intermediate_password = args.intermediate_password
        else:
            intermediate_password = getpass.getpass("Enter pass phrase for intermediate key: ")
        if args.device_password:
            device_password = args.device_password
        else:
            device_password = getpass.getpass("Enter pass phrase for device key: ")
    else:
        if args.nonce:
            nonce = args.nonce
        else:
            nonce = getpass.getpass("Enter nonce for verification mode")

    if mode == "verification":
        create_verification_cert(nonce)
    else:
        create_directories()
        create_certificate_chain(
            common_name=args.domain,
            ca_password=ca_password,
            intermediate_password=intermediate_password,
            device_password=device_password,
        )
