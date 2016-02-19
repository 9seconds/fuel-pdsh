# -*- coding: utf-8 -*-


import functools
import logging
import os
import re

import argparse

import fuelpdsh

from . import nailgun, pdsh, filetransfer


LOG = fuelpdsh.logger(__name__)
"""Logger."""


def cli(cmd_to_execute, argumenter):
    options = get_options(argumenter)
    configure(options)

    try:
        nodes = nailgun.get_nodes(
            cluster_id=options.cluster_id,
            node_ids=options.node_ids,
            ips=options.ips,
            name=options.name,
            status=options.status,
            group_id=options.group_id,
            roles=options.roles)
    except:
        return os.EX_SOFTWARE
    else:
        nodes = nailgun.hosts(nodes)

    try:
        cmd_to_execute(nodes, options)
    except:
        return os.EX_SOFTWARE
    else:
        return os.EX_OK


def remote_cmd_argumenter(parser):
    parser.add_argument(
        "command",
        help="Command to execute",
        nargs="+")


def fetch_cmd_argumenter(parser):
    parser.add_argument(
        "remote_path",
        help="Remote path of file to download")
    parser.add_argument(
        "local_path",
        help="Local path to store downloaded file")


def push_cmd_argumenter(parser):
    parser.add_argument(
        "local_path",
        help="Local path of file to download")
    parser.add_argument(
        "remote_path",
        help="Remote path to store uploaded file")


def configure(options):
    level = logging.ERROR
    log_format = "%(message)s"

    if options.verbose:
        level = logging.INFO
        log_format = ">>> %(message)s"
    elif options.debug:
        level = logging.DEBUG
        log_format = "[%(levelname)-5s] (%(module)10s:%(lineno)-3d) %(asctime)-15s: %(message)s"

    for namespace in "fuelpdsh", "asyncssh":
        configure_logger(namespace, level, log_format)

    LOG.debug("Options are %s", options)


def configure_logger(namespace, log_level, log_format):
    root_logger = logging.getLogger("fuelpdsh")
    root_logger.handlers = []
    root_logger.propagate = False
    root_logger.setLevel(log_level)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def get_options(argumenter):
    parser = argparse.ArgumentParser(
        epilog="Please contact Sergey Arkhipov <serge@aerialsounds.org> for issues."
    )

    parser.add_argument(
        "-V", "--version",
        help="Print version",
        action="store_true",
        default=False)
    parser.add_argument(
        "-c", "--cluster-id",
        help="Select only nodes which belong to cluster with such ID.",
        type=int)
    parser.add_argument(
        "-w", "--node-ids",
        help="Plain comma-separated list of nodes.",
        type=argtype_node_ids)
    parser.add_argument(
        "-i", "--ips",
        help="Plain comma-separated list of node IPs.",
        type=argtype_node_ips)
    parser.add_argument(
        "-n", "--name",
        help="Regular expression for the node name.",
        type=re.compile)
    parser.add_argument(
        "-s", "--status",
        help="Node status.")
    parser.add_argument(
        "-g", "--group-id",
        help="Group ID.",
        type=int)
    parser.add_argument(
        "-r", "--roles",
        help="Node roles.",
        type=argtype_roles
    )

    verbosity = parser.add_mutually_exclusive_group(required=False)
    verbosity.add_argument(
        "-v", "--verbose",
        help="Be verbose.",
        action="store_true",
        default=False
    )
    verbosity.add_argument(
        "-d", "--debug",
        help="Be event more verbose, for debugging.",
        action="store_true",
        default=False
    )

    argumenter(parser)

    return parser.parse_args()


def argtype_comma_separated_list(func):
    @functools.wraps(func)
    def decorator(value):
        if not isinstance(value, str):
            raise argparse.ArgumentTypeError("Value {0} has to be a string".format(value))
        if not value:
            value = []
        else:
            value = value.rstrip(",").split(",")

        return func(value)

    return decorator


@argtype_comma_separated_list
def argtype_roles(values):
    return values


@argtype_comma_separated_list
def argtype_node_ids(values):
    converted_values = []

    for value in values:
        if not value.startswith("node-"):
            value = "node-" + value
        converted_values.append(value)

    return converted_values


@argtype_comma_separated_list
def argtype_node_ips(values):
    failed_values = []

    ip_regex = re.compile(
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)")
    for value in values:
        if not ip_regex.match(value):
            failed_values.append(value)

    if failed_values:
        raise argparse.ArgumentTypeError(
            "Values {0} are not correct IPs".format(", ".join(failed_values)))

    return values


remote_cmd = functools.partial(cli, pdsh.execute, remote_cmd_argumenter)
fetch_cmd = functools.partial(cli, filetransfer.fetch, fetch_cmd_argumenter)
push_cmd = functools.partial(cli, filetransfer.push, push_cmd_argumenter)
