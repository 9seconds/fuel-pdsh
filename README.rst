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


Installation
============

Before install fuel-pdsh on master node, do the following:

::

    $ yum install python-devel python-pip gcc

If you want system installation, do:

::

    $ pip install fuel-pdsh

If you want to use virtualenv:

::

    $ pip install virtualenv
    $ virtualenv -p python2.6 --system-site-packages ~/.fuelpdsh-venv
    $ source ~/.fuelpdsh-venv/bin/activate
    $ pip install fuel-pdsh


Commandline options
===================

The both of ``fuel-pdsh`` and ``fuel-pdcp`` have the same options set but
different arguments.

::

    usage: fuel-pdsh [-h] [--concurrency CONCURRENCY] [-c CLUSTER_ID]
                     [-w NODE_IDS] [-i IPS] [-n NAME] [-s STATUS] [-g GROUP_ID]
                     [-r ROLES] [-v | -d]
                     command [command ...]

    positional arguments:
      command               Command to execute

    optional arguments:
      -h, --help            show this help message and exit
      --concurrency CONCURRENCY
                            How many simultaneous connections should be
                            established. By default (4), we are trying to connect
                            to all nodes, no limits.
      -c CLUSTER_ID, --cluster-id CLUSTER_ID
                            Select only nodes which belong to cluster with such
                            ID.
      -w NODE_IDS, --node-ids NODE_IDS
                            Plain comma-separated list of nodes.
      -i IPS, --ips IPS     Plain comma-separated list of node IPs.
      -n NAME, --name NAME  Regular expression for the node name.
      -s STATUS, --status STATUS
                            Node status.
      -g GROUP_ID, --group-id GROUP_ID
                            Group ID.
      -r ROLES, --roles ROLES
                            Node roles.
      -v, --verbose         Be verbose.
      -d, --debug           Be event more verbose, for debugging.

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


``-c``, ``--cluster-id``
------------------------

Defines optional cluster ID for additional node filtering. If no cluster ID
is set, utilities will work over all accessible clusters.

::

    $ fuel-pdsh -c 1 -- ls

This will do ``ls`` on all nodes in cluster with ID ``1``.


``-w``, ``--node-ids``
----------------------

The most simple selector, just select all nodes by given IDs. So if you
want t``-c``, o run a command on nodes with IDs ``2``, ``4`` and ``8``,
just pass them as a comma-separated list.

::

    $ fuel-pdsh -w 2,4,8 -- ls

Also, you may prefix them with ``node-`` prefix (as you SSH to them).
The following command is the same as previous:

::

    $ fuel-pdsh -w node-2,4,node-8 -- ls


``-i``, ``--ips``
-----------------

Select only those nodes which have these IPs.

::

    $ fuel-pdsh -i 10.0.0.1,10.0.0.2 -- ls


``-n``, ``--name``
------------------

Filters on the node names. This parameter is just a regular expression
for the node name, so there is not point to enter the whole name, just
pass a part.

::

    $ fuel-pdsh -n contro -- ls


``-s``, ``--status``
--------------------

Filter nodes on their statuses.

::

    $ fuel-pdsh -s ready -- ls

This will ``ls`` on all nodes which have status ``ready``.


``-g``, ``--group-id``
----------------------

Filters nodes on their group ID.

::

    $ fuel-pdsh -g 10 -- ls


``-r``, ``-roles``
------------------

Filter nodes on their roles.

::

    $ fuel-pdsh -r compute -- ls


fuel-pdsh
=========

``fuel-pdsh`` is a tool to execute commands in parallel on different
hosts. Let's assume you want to restart Apache on all controllers. Then
do following:

::

    $ fuel-pdsh -r controller service apache2 restart

Sometimes you need to pass arguments to the command which may be
recognized as an arguments for ``fuel-pdsh`` itself. No worries, good
old ``--`` is supported.

::

    $ fuel-pdsh -r controller -- manage.py --noinput

Sometimes you have to invoke several commands. No worries again:

::

    $ fuel-pdsh -r controller -- sh -c "command1 && command2; command3"


fuel-pdcp
=========

``fuel-pdcp`` is a utility to copy files on multiple hosts simultaneously.

::

    $ fuel-pdcp -r controller -- zabbix.deb /tmp

This will copy Zabbix package to ``/tmp`` on all controllers. Also, you
may copy several files:

::

    $ fuel-pdcp -r controller -- zabbix.deb zabbix.conf /tmp

**Important**: destination is considered directory. So if you do following

::

    $ fuel-pdcp -r controller -- zabbix.deb /tmp/zabbix.deb

Then new directory ``/tmp/zabbix.deb/`` will be created and you file
gonna be copied in ``/tmp/zabbix.deb/zabbix.deb``. This is intentional
because to avoid ambiguaty on copying several files into one place.
Please remember about that.
