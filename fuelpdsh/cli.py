# -*- coding: utf-8 -*-


import argparse
import functools
import os
import re

import fuelpdsh.pdsh


def main():
    options = get_options()
    nodes = fuelpdsh.pdsh.get_nodes(options)
    fuelpdsh.pdsh.execute(nodes, options)

    return os.EX_OK


def get_options():
    parser = argparse.ArgumentParser(
        prog="fuel-pdsh",
        description="%(prog)s allows you to execute a command on fuel nodes "
                    "in parallel. It is a pure Python replacement for pdsh "
                    "utility.",
        epilog="Please contact Sergey Arkhipov <serge@aerialsounds.org> for "
               "issues."
    )

    parser.add_argument(
        "--concurrency",
        help="How many simultaneous connections should be established. "
             "By default (%(default)d), we are trying to connect to all nodes,"
             " no limits.",
        type=argtype_positive_integer,
        default=0
    )
    parser.add_argument(
        "command",
        help="Command to execute",
        nargs="+"
    )

    node_classes = parser.add_mutually_exclusive_group(required=True)
    node_classes.add_argument(
        "-w", "--node-ids",
        help="Plain comma-separated list of nodes.",
        type=argtype_node_ids)
    node_classes.add_argument(
        "-c", "--cluster",
        help="All nodes belong to cluster.",
        type=int)
    node_classes.add_argument(
        "-i", "--ips",
        help="Plain comma-separated list of node IPs.",
        type=argtype_node_ips)
    node_classes.add_argument(
        "-n", "--name",
        help="Regular expression for the node name.",
        type=re.compile)
    node_classes.add_argument(
        "-s", "--status",
        help="Node status.")
    node_classes.add_argument(
        "-g", "--group-id",
        help="Group ID.",
        type=int)
    node_classes.add_argument(
        "-r", "--roles",
        help="Node roles.",
        type=argtype_roles
    )

    return parser.parse_args()


def argtype_comma_separated_list(func):
    @functools.wraps(func)
    def decorator(value):
        if not isinstance(value, basestring):
            raise argparse.ArgumentTypeError(
                "Value {0} has to be a string".format(value))
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
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        "(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)")
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

    raise argparse.ArgumentTypeError(
        "Value {0} has to be a positive integer".format(value))
