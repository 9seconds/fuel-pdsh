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

    conditions = []
    if options.node_ids:
        LOG.debug("Filter on node IDs %s", options.node_ids)
        conditions.append(lambda node: node["hostname"] in options.node_ids)
    if options.ips:
        LOG.debug("Filter on node IPs %s", options.ips)
        conditions.append(lambda node: node["ip"] in options.ips)
    if options.name:
        LOG.debug("Filter on node regexp name '%s'", options.name.pattern)
        conditions.append(lambda node: options.name.search(node["name"]))
    if options.status:
        LOG.debug("Filter on node status %s", options.status)
        conditions.append(lambda node: node["status"] == options.status)
    if options.roles:
        LOG.debug("Filter on node roles %s", options.roles)
        conditions.append(lambda node: set(node["roles"]) & set(options.roles))
    if options.group_id:
        LOG.debug("Filter on node group ID %s", options.group_id)
        conditions.append(lambda node: node["group_id"] == options.group_id)

    try:
        nodes = client.get_all(options.cluster_id)
    except Exception as exc:
        LOG.error("Cannot fetch from Fuel: %s", exc)
        raise Exception

    nodes = sorted(node["hostname"] for node in nodes if all(cond(node) for cond in conditions))

    LOG.info("Found %d suitable nodes", len(nodes))
    LOG.debug("Nodes to execute on: %s", nodes)

    return nodes
