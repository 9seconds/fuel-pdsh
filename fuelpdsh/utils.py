# -*- coding: utf-8 -*-


import os
import time

import concurrent.futures
import fuelclient

import fuelpdsh


LOG = fuelpdsh.logger(__name__)
"""Logger."""


def wait_for_futures(futures, stop_ev):
    try:
        while not all(future.done() for future in futures):
            time.sleep(1)
    except KeyboardInterrupt:
        LOG.debug("Set stop event")
    finally:
        stop_ev.set()
        while not all(future.done() for future in futures):
            time.sleep(0.01)


def futures_exit_code(futures):
    exit_code = os.EX_OK

    for future in futures:
        try:
            result = future.result()
        except concurrent.futures.CancelledError:
            result = os.EX_SOFTWARE
        finally:
            if not isinstance(result, int):
                result = os.EX_SOFTWARE
            exit_code = max(exit_code, result)

    return exit_code


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
