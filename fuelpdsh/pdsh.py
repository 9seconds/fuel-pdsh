# -*- coding: utf-8 -*-


import asyncio
import subprocess
import functools

import asyncssh

from . import ssh
from . import utils


@asyncio.coroutine
def create_task(host, options):
    with (yield from utils.connect(host)) as connection:
        channel, _ = yield from connection.create_session(
            lambda: ssh.SSHClientSession(connection._host),
            subprocess.list2cmdline(options.command))
        yield from channel.wait_closed()

    yield from connection.wait_closed()


execute = functools.partial(utils.do_for_all_hosts, create_task)
