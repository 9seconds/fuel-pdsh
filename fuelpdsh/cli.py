# -*- coding: utf-8 -*-


import argparse
import atexit
import functools
import logging
import os
import re
import threading

import fuelpdsh
import fuelpdsh.pdsh
import fuelpdsh.cp
import fuelpdsh.utils


LOG = fuelpdsh.logger(__name__)
"""Logger."""

DEFAULT_CONCURRENCY = 4
"""How many hosts we have to access in parallel."""


def cli(cmd_to_execute, argumenter):
    stop_ev = threading.Event()
    atexit.register(stop_ev.set)

    options = get_options(argumenter)
    configure(options)

    try:
        nodes = fuelpdsh.utils.get_nodes(options)
    except:
        return os.EX_SOFTWARE

    try:
        return cmd_to_execute(nodes, options, stop_ev)
    except:
        return os.EX_SOFTWARE


def remote_cmd_argumenter(parser):
    parser.add_argument(
        "command",
        help="Command to execute",
        nargs="+"
    )


def cp_to_remote_argumenter(parser):
    parser.add_argument(
        "src_path",
        help="Source paths to copy",
        nargs="+")
    parser.add_argument(
        "dst_path",
        help="Remote destination")


def configure(options):
    level = logging.ERROR
    log_format = "%(message)s"

    if options.verbose:
        level = logging.INFO
        log_format = "*** %(thread)d >>> %(message)s"
    elif options.debug:
        level = logging.DEBUG
        log_format = "%(thread)d | [%(levelname)-5s] (%(module)10s:%(lineno)-3d) %(asctime)-15s: %(message)s"

    for namespace in "fuelpdsh", "paramiko":
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
        "--concurrency",
        help="How many simultaneous connections should be established. "
             "By default (%(default)d), we are trying to connect to all nodes, no limits.",
        type=argtype_positive_integer,
        default=DEFAULT_CONCURRENCY
    )
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
        if not isinstance(value, basestring):
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


def argtype_positive_integer(value):
    try:
        value = int(value)
    except ValueError:
        pass
    else:
        if value >= 0:
            return value

    raise argparse.ArgumentTypeError("Value {0} has to be a positive integer".format(value))


remote_cmd = functools.partial(cli, fuelpdsh.pdsh.command, remote_cmd_argumenter)
cp_to_remote = functools.partial(cli, fuelpdsh.cp.command, cp_to_remote_argumenter)
