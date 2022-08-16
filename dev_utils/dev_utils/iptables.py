# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.
import logging
import subprocess
import socket
import sys

logger = logging.getLogger("e2e.{}".format(__name__))

mqtt_port = 8883
mqttws_port = 443
uninitialized = "uninitialized"
sudo_prefix = uninitialized
all_disconnect_types = ["DROP", "REJECT"]
all_transports = ["mqtt", "mqttws"]


def get_sudo_prefix():
    """
    Get the prefix for running sudo commands.  If the sudo binary doesn't exist, then
    we assume that we're running in a container or somewhere else where we don't
    need to use sudo to elevate our process.
    """
    global sudo_prefix

    # use "uninitialized" to mean uninitialized, because None and [] are both falsy and we want to set it to [], so we can't use None
    if sudo_prefix == uninitialized:
        try:
            run_shell_command("which sudo")
        except subprocess.CalledProcessError:
            sudo_prefix = ""
        else:
            sudo_prefix = "sudo -n "

    return sudo_prefix


def run_shell_command(cmd):
    """
    Run a shell command and raise an exception on error
    """
    logger.info("running [{}]".format(cmd))
    try:
        return subprocess.check_output(cmd.split(" ")).decode("utf-8").splitlines()
    except subprocess.CalledProcessError as e:
        logger.error("Error spawning {}".format(e.cmd))
        logger.error("Process returned {}".format(e.returncode))
        logger.error("process output: {}".format(e.output))
        raise


def transport_to_port(transport):
    """
    Given a transport, return the port that the transport uses.
    """
    if transport == "mqtt":
        return mqtt_port
    elif transport == "mqttws":
        return mqttws_port
    else:
        raise ValueError(
            "transport_type {} invalid.  Only mqtt and mqttws are accepted".format(transport)
        )


def disconnect_output_port(disconnect_type, transport, host):
    """
    Disconnect the port for a given transport.  disconnect_type can either be "DROP" to drop
    packets sent to that port, or it can be "REJECT" to reject packets sent to that port.
    """
    # sudo -n iptables -A OUTPUT -p tcp --dport 8883 --destination 20.21.22.23 -j DROP
    ip = get_ip(host)
    port = transport_to_port(transport)
    run_shell_command(
        "{}iptables -A OUTPUT -p tcp --dport {} --destination {} -j {}".format(
            get_sudo_prefix(), port, ip, disconnect_type
        )
    )


def reconnect_all(transport, host):
    """
    Reconnect all disconnects for this host and transport.  Effectively, clean up
    anything that this module may have done.
    """
    if not sys.platform.startswith("win"):
        ip = get_ip(host)
        port = transport_to_port(transport)
        for disconnect_type in all_disconnect_types:
            # sudo -n iptables -L OUTPUT -n -v --line-numbers
            lines = run_shell_command(
                "{}iptables -L OUTPUT -n -v --line-numbers".format(get_sudo_prefix())
            )
            # do the lines in reverse because deleting an entry changes the line numbers of all entries after that.
            lines.reverse()
            for line in lines:
                if disconnect_type in line and "dpt:{}".format(port) in line and ip in line:
                    line_number = line.split(" ")[0]
                    logger.info("Removing {} from [{}]".format(line_number, line))
                    # sudo -n iptables -D OUTPUT 1
                    run_shell_command(
                        "{}iptables -D OUTPUT {}".format(get_sudo_prefix(), line_number)
                    )


def get_ip(host):
    """
    Given a hostname, return the ip address
    """
    return socket.getaddrinfo(host, mqtt_port)[0][4][0]
