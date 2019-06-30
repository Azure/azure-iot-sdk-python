import os
import re
import argparse
import getpass


def create_custom_config():
    # This is very specific to installations in various system
    openssl_path = os.getenv("OpenSSLDir")
    config_path = openssl_path + "/bin/openssl.cfg"
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


def create_certificate_chain(common_name, ca_password, intermediate_password, device_password):
    # Results of the below commands are not same when we are outisde demoCA
    # os.system("cd demoCA")
    os.system("type nul > demoCA/index.txt")
    os.system("echo 1000 > demoCA/serial")
    os.mkdir("demoCA/private")
    # Create this folder as configuration file makes new certificates go here
    os.mkdir("demoCA/newcerts")
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
        + "-new -x509 -days 300 -sha256 -extensions v3_ca -out demoCA/newcerts/ca_cert_cn.pem -subj "
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
        + "-new -sha256 -out demoCA/newcerts/intermediate_csr_cn.pem -subj "
        + subject
    )

    print("Done generating intermediate CSR")
    os.system(
        "openssl ca -config demoCA/openssl.cnf -in demoCA/newcerts/intermediate_csr_cn.pem -out demoCA/newcerts/intermediate_cert_cn.pem -keyfile demoCA/private/ca_key.pem -cert demoCA/newcerts/ca_cert_cn.pem -passin pass:"
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
        + "-out demoCA/newcerts/device_csr_cn.pem -subj "
        + subject
    )
    print("Done generating device CSR")
    os.system(
        "openssl ca -config demoCA/openssl.cnf -in demoCA/newcerts/device_csr_cn.pem -out demoCA/newcerts/device_cert_cn.pem -keyfile demoCA/private/intermediate_key.pem -cert demoCA/newcerts/intermediate_cert_cn.pem -passin pass:"
        + intermediate_password
        + " "
        + "-extensions usr_cert -days 3 -notext -md sha256 -batch"
    )
    print("Done generating device certificate")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a certificate chain.")
    parser.add_argument("domain", help="Domain name without www.")
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
    args = parser.parse_args()
    if args.key_size:
        key_size = args.key_size
    else:
        key_size = 4096
    if args.days:
        days = args.days
    else:
        days = 30

    if args.common_name:
        common_name = args.common_name
    else:
        common_name = args.domain
    # Create the directory demoCA as that is the configuration in most openssl installation
    os.system("mkdir demoCA")

    create_custom_config()
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

    create_certificate_chain(
        common_name=args.domain,
        ca_password=ca_password,
        intermediate_password=intermediate_password,
        device_password=device_password,
    )
