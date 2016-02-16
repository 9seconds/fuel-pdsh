# -*- coding: utf-8 -*-


import functools
import contextlib
import asyncio

import asyncssh


if hasattr(asyncio, "ensure_future"):
    make_future = asyncio.ensure_future
else:
    make_future = asyncio.async


def all_futures(func, hostnames, options):
    futures = []

    for hostname in hostnames:
        future = make_future(func(hostname, options))
        futures.append(future)

    return asyncio.wait(futures)


def do_for_all_hosts(func, hostnames, options):
    try:
        with contextlib.closing(asyncio.get_event_loop()) as loop:
            futures = all_futures(func, hostnames, options)
            loop.run_until_complete(futures)
    except KeyboardInterrupt:
        pass


connect = functools.partial(asyncssh.connect, known_hosts=None)
