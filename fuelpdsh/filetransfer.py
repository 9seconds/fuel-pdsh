# -*- coding: utf-8 -*-


import asyncio
import functools
import os
import os.path

import asyncssh

from . import utils


@asyncio.coroutine
def create_get_task(host, options):
    local_path = options.local_path
    local_path = os.path.join(local_path, host)
    remote_path = options.remote_path

    try:
        os.makedirs(local_path)
    except Exception as exc:
        pass

    with (yield from utils.connect(host)) as connection:
        with (yield from connection.start_sftp_client()) as sftp:
            yield from sftp.mget(remote_path, local_path, recurse=True)

    yield from connection.wait_closed()


@asyncio.coroutine
def create_put_task(host, options):
    local_path = options.local_path
    remote_path = options.remote_path

    with (yield from utils.connect(host)) as connection:
        with (yield from connection.start_sftp_client()) as sftp:
            yield from sftp.mput(local_path, remote_path, recurse=True)

    yield from connection.wait_closed()


fetch = functools.partial(utils.do_for_all_hosts, create_get_task)
push = functools.partial(utils.do_for_all_hosts, create_put_task)
