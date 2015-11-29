#!/usr/bin/env python
# -*- coding: utf-8 -*-


import functools
import glob
import itertools
import logging
import os
import os.path
import posixpath
import shutil
import signal
import sys
import time

import concurrent.futures
import fuelclient
import spur

import fuelpdsh.ssh
import fuelpdsh.stream


LOG = logging.getLogger("fuelpdsh." + __name__)
"""Logger."""

GENTLE_STOP_TIMEOUT = 5
"""How long to wait before sending SIGTERM to SSH process."""


def execute(func, hostnames, options, stop_ev):
    concurrency = options.concurrency
    if not concurrency:
        concurrency = len(hostnames)

    LOG.info("Execute with %d threads", concurrency)

    stdout_stream = fuelpdsh.stream.Stream(sys.stdout)
    stderr_stream = fuelpdsh.stream.Stream(sys.stderr)

    stdout_stream.run()
    stderr_stream.run()

    try:
        with concurrent.futures.ThreadPoolExecutor(concurrency) as pool:
            futures = []

            hostname_padding = max(len(host) for host in hostnames)
            for host in hostnames:
                stdout = stdout_stream.make_host_stream(host, hostname_padding)
                stderr = stderr_stream.make_host_stream(host, hostname_padding)
                future = pool.submit(func, host, options, stdout, stderr, stop_ev)
                futures.append(future)

            wait_for_futures(futures, stop_ev)
    finally:
        clean_futures(futures, stop_ev)

        stdout_stream.stop()
        stderr_stream.stop()
        for stream in stdout_stream, stderr_stream:
            stream.wait()


def wait_for_futures(futures, stop_ev):
    try:
        while not all(future.done() for future in futures):
            time.sleep(1)
    except KeyboardInterrupt:
        LOG.debug("Set stop event")
        stop_ev.set()


def clean_futures(futures, stop_ev):
    stop_ev.set()
    while not all(future.done() for future in futures):
        time.sleep(0.01)


def run_on_host_func(host, options, stdout, stderr, stop_ev):
    if stop_ev.is_set():
        return os.EX_OK

    str_command = " ".join(options.command)

    with fuelpdsh.ssh.get_ssh(host) as ssh:
        LOG.debug("Execute %s on host %s", str_command, host)

        try:
            process = ssh.spawn(options.command,
                                stdout=stdout, stderr=stderr, store_pid=True, allow_error=False)
            while process.is_running():
                if stop_ev.is_set():
                    raise KeyboardInterrupt
                time.sleep(0.5)
        except spur.NoSuchCommandError:
            LOG.error("No such command on host %s", host)
            raise
        except spur.RunProcessError as exc:
            stderr.write("\n{0}".format(exc.stderr_output))
            raise
        except KeyboardInterrupt:
            stop_ssh_process(host, process)
        except:
            LOG.exception("Problem with executing %s on host %s", str_command, host)
            raise
        else:
            return process.wait_for_result().return_code
        finally:
            stdout.flush()
            stderr.flush()


def stop_ssh_process(host, process):
    LOG.info("Stop process on host %s", host)

    LOG.debug("Send SIGTERM to host %s", host)
    process.send_signal(signal.SIGTERM)
    time.sleep(1)

    if not process.is_running():
        return

    for _ in range(GENTLE_STOP_TIMEOUT - 1):
        if not process.is_running():
            time.sleep(1)
    else:
        LOG.debug("Send SIGKILL to host %s", host)
        process.send_signal(signal.SIGKILL)


def cp_to_remote_func(host, options, stdout, stderr, stop_ev):
    local_paths = itertools.chain.from_iterable(glob.glob(path) for path in options.src_path)
    local_paths = filter(lambda path: os.path.isfile(path), local_paths)

    with fuelpdsh.ssh.get_ssh(host) as ssh:
        for local_path in local_paths:
            local_basename = os.path.basename(local_path)
            remote_path = posixpath.join(options.dst_path, local_basename)

            LOG.info("Copy %s to %s:%s", local_path, host, remote_path)

            with ssh.open(remote_path, "wb") as remote_fileobj:
                with open(local_path, "rb") as local_fileobj:
                    shutil.copyfileobj(local_fileobj, remote_fileobj)


def get_nodes(options):
    client = fuelclient.get_client("node")

    if options.cluster:
        LOG.debug("Filter on cluster %s", options.cluster)
        condition = lambda node: node["cluster"] == options.cluster
    elif options.node_ids:
        LOG.debug("Filter on node IDs %s", options.node_ids)
        condition = lambda node: node["hostname"] in options.node_ids
    elif options.ips:
        LOG.debug("Filter on node IPs %s", options.ips)
        condition = lambda node: node["ip"] in options.ips
    elif options.name:
        LOG.debug("Filter on node regexp name '%s'", options.name.pattern)
        condition = lambda node: options.name.search(node["name"])
    elif options.status:
        LOG.debug("Filter on node status %s", options.status)
        condition = lambda node: node["status"] == options.status
    elif options.roles:
        LOG.debug("Filter on node roles %s", options.roles)
        condition = lambda node: set(node["roles"]) & set(options.roles)
    else:
        LOG.debug("Filter on node group ID %s", options.group_id)
        condition = lambda node: node["group_id"] == options.group_id

    try:
        nodes = client.get_all()
    except Exception as exc:
        LOG.error("Cannot fetch from Fuel: %s", exc)
        raise Exception

    nodes = sorted(node["hostname"] for node in nodes if condition(node))

    LOG.info("Found %d suitable nodes", len(nodes))
    LOG.debug("Nodes to execute on: %s", nodes)

    return nodes


remote_cmd = functools.partial(execute, run_on_host_func)
cp_to_remote = functools.partial(execute, cp_to_remote_func)
