#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import signal
import sys
import time

import concurrent.futures
import spur

import fuelpdsh
import fuelpdsh.ssh
import fuelpdsh.stream
import fuelpdsh.utils


LOG = fuelpdsh.logger(__name__)
"""Logger."""

GENTLE_STOP_TIMEOUT = 5
"""How long to wait before sending SIGTERM to SSH process."""


def command(hostnames, options, stop_ev):
    concurrency = options.concurrency
    if not concurrency:
        concurrency = len(hostnames)

    LOG.info("Execute with %d threads", concurrency)

    stdout_stream = fuelpdsh.stream.Stream(sys.stdout)
    stderr_stream = fuelpdsh.stream.Stream(sys.stderr)

    stdout_stream.run()
    stderr_stream.run()

    futures = []
    try:
        with concurrent.futures.ThreadPoolExecutor(concurrency) as pool:

            hostname_padding = max(len(host) for host in hostnames)
            for host in hostnames:
                stdout = stdout_stream.make_host_stream(host, hostname_padding)
                stderr = stderr_stream.make_host_stream(host, hostname_padding)
                future = pool.submit(run_on_host, host, options, stdout, stderr, stop_ev)
                futures.append(future)

            fuelpdsh.utils.wait_for_futures(futures, stop_ev)
    finally:
        stdout_stream.stop()
        stderr_stream.stop()
        for stream in stdout_stream, stderr_stream:
            stream.wait()

        return fuelpdsh.utils.futures_exit_code(futures)


def run_on_host(host, options, stdout, stderr, stop_ev):
    if stop_ev.is_set():
        return os.EX_OK

    str_command = " ".join(options.command)

    with fuelpdsh.ssh.get_ssh(host) as ssh:
        LOG.debug("Execute %s on host %s", str_command, host)

        try:
            process = ssh.spawn(options.command,
                                stdout=stdout, stderr=stderr, store_pid=True, allow_error=False)
            while process.is_running():
                if stop_ev.is_set():
                    raise KeyboardInterrupt
                time.sleep(0.5)
        except spur.NoSuchCommandError:
            LOG.error("No such command on host %s", host)
            raise
        except spur.RunProcessError as exc:
            stderr.write("\n{0}".format(exc.stderr_output))
            raise
        except KeyboardInterrupt:
            stop_ssh_process(host, process)
            raise
        except:
            LOG.exception("Problem with executing %s on host %s", str_command, host)
            raise
        else:
            return process.wait_for_result().return_code
        finally:
            stdout.flush()
            stderr.flush()


def stop_ssh_process(host, process):
    LOG.info("Stop process on host %s", host)

    LOG.debug("Send SIGTERM to host %s", host)
    process.send_signal(signal.SIGTERM)
    time.sleep(1)

    if not process.is_running():
        return

    for _ in range(GENTLE_STOP_TIMEOUT - 1):
        if not process.is_running():
            time.sleep(1)
    else:
        LOG.debug("Send SIGKILL to host %s", host)
        process.send_signal(signal.SIGKILL)
