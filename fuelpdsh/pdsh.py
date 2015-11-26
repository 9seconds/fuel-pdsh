#!/usr/bin/env python
# -*- coding: utf-8 -*-


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
    elif options.roles:
        condition = lambda node: set(node["roles"]) & set(options.roles)
    else:
        condition = lambda node: node["group_id"] == options.group_id

    return sorted(
        node["hostname"] for node in client.get_all() if condition(node))
