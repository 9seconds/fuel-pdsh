#!/usr/bin/env python
# -*- coding: utf-8 -*-


import argparse
import functools
import os
import Queue
import re
import sys
import threading
import time

import concurrent.futures
import fuelclient
import spur
import spur.ssh


class QueuedStream(object):

    def __init__(self, hostname, queue):
        self.hostname = hostname
        self.queue = queue
        self.accumulator = ""

    def put(self, data):
        self.queue.put(self.hostname + ": " + data, True)

    def write(self, data):
        self.accumulator += data
        if "\n" in self.accumulator:
            lines = self.accumulator.split("\n")
            self.accumulator = lines[-1]
            for line in lines[:-1]:
                self.put(line)

    def close(self):
        self.put(self.accumulator + "\n")

    flush = close


def main():
    options = get_options()
    nodes = get_nodes(options)
    execute(nodes, options)

    return os.EX_OK


def execute(hostnames, options):
    concurrency = options.concurrency
    if not concurrency:
        concurrency = len(hostnames)

    stdout_queue, stdout_ev, stdout_thread = wrap_stream(sys.stdout)
    stderr_queue, stderr_ev, stderr_thread = wrap_stream(sys.stderr)

    try:
        with concurrent.futures.ThreadPoolExecutor(concurrency) as pool:
            result = [
                pool.submit(run_on_host,
                            host,
                            options.command,
                            QueuedStream(host, stdout_queue),
                            QueuedStream(host, stderr_queue))
                for host in hostnames]
            concurrent.futures.as_completed(result)
    finally:
        stdout_ev.set()
        stderr_ev.set()
        for thread in stdout_thread, stderr_thread:
            thread.join()


def run_on_host(host, command, stdout, stderr):
    session = spur.SshShell(host,
                            missing_host_key=spur.ssh.MissingHostKey.accept)
    with session as ssh:
        try:
            ssh.run(command, stdout=stdout, stderr=stderr)
        except spur.NoSuchCommandError:
            raise ValueError("Cannot execute '{0}' on {1}",
                             " ".join(command), host)


def wrap_stream(stream):
    queue = Queue.Queue(1000000)
    stop_event = threading.Event()

    thread = threading.Thread(target=stream_wrapper,
                              args=(stream, queue, stop_event))
    thread.daemon = True
    thread.start()

    return queue, stop_event, thread


def stream_wrapper(stream, queue, event):
    while not event.is_set():
        try:
            line = queue.get_nowait()
        except Queue.Empty:
            time.sleep(0.01)
        else:
            stream.write(line)
            stream.write("\n")


def get_nodes(options):
    client = fuelclient.get_client("node")

    if options.cluster:
        condition = lambda node: node["cluster"] == options.cluster
    elif options.node_ids:
        condition = lambda node: node["hostname"] in options.node_ids
    elif options.ips:
        condition = lambda node: node["ip"] in options.ips
    elif options.name:
        condition = lambda node: options.name.search(node["name"])
    elif options.status:
        condition = lambda node: node["status"] == options.status
    else:
        condition = lambda node: node["group_id"] == options.group_id

    return sorted(
        node["hostname"] for node in client.get_all() if condition(node))


def get_options():
    parser = argparse.ArgumentParser(
        prog="fuel-pdsh",
        description="%(prog)s allows you to execute a command on fuel nodes "
                    "in parallel. It is a pure Python replacement for pdsh "
                    "utility.",
        epilog="Please contact Sergey Arkhipov <sarkhipov@mirantis.com> for "
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


if __name__ == "__main__":
    sys.exit(main())
