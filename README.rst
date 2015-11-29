=========
fuel-pdsh
=========

fuel-pdsh is a small utility which allows you to execute one command on
the multiple OpenStack nodes from master node (aka Fuel node) remotely
using SSH.

Basically it is just a pure Python replacement for `PDSH
<https://code.google.com/p/pdsh/>`_ which uses Nailgun API to discover
nodes. Also it supports ``pdcp`` utility for copying files to multiple
hosts in parallel.

``fuel-pdsh`` package contains 2 commandline utilities, ``fuel-pdsh``
for executing SSH command on the group of hosts and ``fuel-pdcp`` for
file copying.


Commandline options
===================

The both of ``fuel-pdsh`` and ``fuel-pdcp`` have the same options set but
different arguments.

::

    $ fuel-pdsh -h
    usage: fuel-pdsh [-h] [--concurrency CONCURRENCY] [-v | -d]
                     (-w NODE_IDS | -c CLUSTER | -i IPS | -n NAME | -s STATUS | -g GROUP_ID | -r ROLES)
                     command [command ...]

    positional arguments:
      command               Command to execute

    optional arguments:
      -h, --help            show this help message and exit
      --concurrency CONCURRENCY
                            How many simultaneous connections should be
                            established. By default (0), we are trying to connect
                            to all nodes, no limits.
      -v, --verbose         Be verbose.
      -d, --debug           Be event more verbose, for debugging.
      -w NODE_IDS, --node-ids NODE_IDS
                            Plain comma-separated list of nodes.
      -c CLUSTER, --cluster CLUSTER
                            All nodes belong to cluster.
      -i IPS, --ips IPS     Plain comma-separated list of node IPs.
      -n NAME, --name NAME  Regular expression for the node name.
      -s STATUS, --status STATUS
                            Node status.
      -g GROUP_ID, --group-id GROUP_ID
                            Group ID.
      -r ROLES, --roles ROLES
                            Node roles.

    Please contact Sergey Arkhipov <serge@aerialsounds.org> for issues.


``--concurrency``
-----------------

This flag defines how may hosts would be accessed in parallel. If you
have 40 nodes but ``--concurrency`` is set to 4, only 4 hosts will be
managed in parallel. Set ``0`` if you want to connect *all* hosts in
parallel.

In reality, please do not set this setting to high. ``fuel-pdsh``
uses `Paramiko <http://www.paramiko.org/>`_ for host access and it
has well-known issues on slowing down with multiple simultaneous
connections. You may have serious performance decrease if you connect to
all hosts instead of some limit.


``--verbose``
-------------

This flag makes utilities more verbose. By default, if you execute
``fuel-pdsh``, you will see such output:

::

    $ fuel-pdsh -n contr -- echo hello world
    node-4 :  hello world
    node-39:  hello world
    node-3 :  hello world

If you enable ``-v``, you will get something like this:

::

    $ fuel-pdsh -n contr -v -- echo hello world
    *** 140489797273344 >>> Found 3 suitable nodes
    *** 140489797273344 >>> Execute with 4 threads
    node-4 :  hello world
    node-39:  hello world
    node-3 :  hello world

So, more verbose, to understand what is going.


``--debug``
-----------

Enables maximal verbosity. Basically, if you are not me, you do not need
this level of verbosity. But I need when I debug.

So, if you met with some problems and want to issue a bug, execute
utilities with ``-d`` and send me an output.


Node selectors
--------------

``-w``, ``-i``, ``-c``, ``-n``, ``-s``, ``-g`` and ``-r`` are mutually
exclusive filters for nodes, at least 1 is required.


``-w``, ``--node-ids``
----------------------

The most simple selector, just select all nodes by given IDs. So if you want
to run a command on nodes with IDs ``2``, ``4`` and ``8``, just pass them as
a comma-separated list.

::

    $ fuel-pdsh -w 2,4,8 -- ls

Also, you may prefix them with ``node-`` prefix (as you SSH to them).
The following command is the same as previous:

::

    $ fuel-pdsh -w node-2,4,node-8 -- ls
