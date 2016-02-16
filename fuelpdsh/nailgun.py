# -*- coding: utf-8 -*-


import json
import os.path
import subprocess

import fuelpdsh

from . import cache


DEFAULT_NODE_CACHE_FILE = os.path.join(fuelpdsh.DIR_APP, "fuelnodes.pickle.gz")
"""Default cache file path for fuel nodes."""


@cache.cached(DEFAULT_NODE_CACHE_FILE)
def get_all_nodes():
    output = subprocess.check_output(
        ["fuel", "node", "--list", "--all", "--json"],
        universal_newlines=True)
    converted_output = json.loads(output)

    return converted_output


def get_nodes(cluster_id=None, node_ids=None, ips=None, name=None, status=None,
              group_id=None, roles=None, online=None):
    nodes = get_all_nodes()

    if cluster_id:
        nodes = filter(lambda node: node["cluster"] == cluster_id, nodes)
    if group_id:
        nodes = filter(lambda node: node["group_id"] == group_id, nodes)
    if ips:
        nodes = filter(lambda node: node["ip"] in ips, nodes)
    if name:
        nodes = filter(lambda node: name.search(node["name"]), nodes)
    if status:
        nodes = filter(lambda node: node["status"].lower() == status.lower(),
                       nodes)
    if node_ids is not None:
        nodes = filter(lambda node: node["hostname"] in node_ids, nodes)
    if roles is not None:
        def filterfunc(node):
            node_roles = [role.strip() for role in node["roles"].split(",")]
            return set(node_roles) & set(roles)
        nodes = filter(filterfunc, nodes)
    if online is not None:
        nodes = filter(lambda node: node["online"] == online, nodes)

    nodes = sorted(nodes, key=lambda node: node["hostname"])

    return nodes


def hosts(nodes):
    return [node["hostname"] for node in nodes]
