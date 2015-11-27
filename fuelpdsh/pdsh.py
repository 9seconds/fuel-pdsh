#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging
import Queue
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


def execute(hostnames, options):
    concurrency = options.concurrency
    if not concurrency:
        concurrency = len(hostnames)

    logging.info("Execute with %d threads", concurrency)

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
            logging.info("Waiting for %d tasks to be completed",
                         len(hostnames))
            concurrent.futures.as_completed(result)
    except Exception as exc:
        logging.exception("Cannot execute tasks: %s", exc)
    finally:
        stdout_ev.set()
        stderr_ev.set()

        logging.debug("Waiting for stdout thread to be finished")
        stdout_thread.join()

        logging.debug("Waiting for stderr thread to be finished")
        stderr_thread.join()


def run_on_host(host, command, stdout, stderr):
    str_command = " ".join(command)
    session = spur.SshShell(host,
                            missing_host_key=spur.ssh.MissingHostKey.accept)

    with session as ssh:
        try:
            logging.debug("Execute %s on host %s", str_command, host)
            ssh.run(command, stdout=stdout, stderr=stderr)
        except spur.NoSuchCommandError:
            logging.error("No such command on host %s", host)
            raise ValueError("Cannot execute '{0}' on {1}",
                             str_command, host)
        except:
            logging.exception("Problem with executing %s on host %s",
                              str_command, host)


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
        logging.debug("Filter on cluster %s", options.cluster)
        condition = lambda node: node["cluster"] == options.cluster
    elif options.node_ids:
        logging.debug("Filter on node IDs %s", options.node_ids)
        condition = lambda node: node["hostname"] in options.node_ids
    elif options.ips:
        logging.debug("Filter on node IPs %s", options.ips)
        condition = lambda node: node["ip"] in options.ips
    elif options.name:
        logging.debug("Filter on node regexp name '%s'", options.name.pattern)
        condition = lambda node: options.name.search(node["name"])
    elif options.status:
        logging.debug("Filter on node status %s", options.status)
        condition = lambda node: node["status"] == options.status
    elif options.roles:
        logging.debug("Filter on node roles %s", options.roles)
        condition = lambda node: set(node["roles"]) & set(options.roles)
    else:
        logging.debug("Filter on node group ID %s", options.group_id)
        condition = lambda node: node["group_id"] == options.group_id

    try:
        nodes = client.get_all()
    except Exception as exc:
        logging.error("Cannot fetch from Fuel: %s", exc)
        raise Exception

    nodes = sorted(node["hostname"] for node in nodes if condition(node))

    logging.info("Found %d suitable nodes", len(nodes))
    logging.debug("Nodes to execute on: %s", nodes)

    return nodes
