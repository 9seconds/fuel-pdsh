# -*- coding: utf-8 -*-


import glob
import os
import os.path
import posixpath
import threading

import concurrent.futures

import fuelpdsh
import fuelpdsh.ssh
import fuelpdsh.utils


LOG = fuelpdsh.logger(__name__)
"""Logger."""


BUFFER_LENGTH = 100 * 1024  # kilobytes
"""How long copy buffer has to be."""


def command(hostnames, options, stop_ev):
    files_to_copy = get_local_paths(options.src_path)
    files_to_copy = get_only_files(files_to_copy)

    if not files_to_copy:
        return os.EX_OK

    concurrency = options.concurrency
    if not concurrency:
        concurrency = len(hostnames)

    LOG.info("Execute with %d threads", concurrency)

    futures = []
    copy_pool = concurrent.futures.ThreadPoolExecutor(concurrency * len(files_to_copy))

    try:
        with concurrent.futures.ThreadPoolExecutor(concurrency) as pool:
            for host in hostnames:
                future = pool.submit(cp_to_remote, host, options, files_to_copy, copy_pool, stop_ev)
                futures.append(future)

            fuelpdsh.utils.wait_for_futures(futures, stop_ev)
    finally:
        copy_pool.shutdown()
        return fuelpdsh.utils.futures_exit_code(futures)


def cp_to_remote(host, options, files_to_copy, pool, stop_ev):
    if stop_ev.is_set():
        return os.EX_OK

    LOG.info("Copy %d files to host %s", len(files_to_copy), host)

    futures = []
    host_stop_ev = threading.Event()
    with fuelpdsh.ssh.get_ssh(host) as ssh:
        for filename in files_to_copy:
            local_basename = os.path.basename(filename)
            remote_path = posixpath.join(options.dst_path, local_basename)
            future = pool.submit(copy_file, ssh, host, filename, remote_path, host_stop_ev, stop_ev)
            futures.append(future)

        fuelpdsh.utils.wait_for_futures(futures, host_stop_ev)

    return fuelpdsh.utils.futures_exit_code(futures)


def copy_file(ssh, host, local_path, remote_path, host_stop_ev, stop_ev):
    LOG.info("Copy %s to %s:%s", local_path, host, remote_path)

    with ssh.open(remote_path, "wb") as remote_fileobj:
        with open(local_path, "rb") as local_fileobj:
            copy_finished = False

            while not (host_stop_ev.is_set() or stop_ev.is_set()):
                buf = local_fileobj.read(BUFFER_LENGTH)
                if not buf:
                    copy_finished = True
                    break
                remote_fileobj.write(buf)

            if not copy_finished:
                ssh.run(["rm", "-f", remote_path], allow_error=True)
                LOG.warning("File %s was not copied to %s:%s", local_path, host, remote_path)
                return os.EX_SOFTWARE

    if copy_finished:
        LOG.info("File %s was copied to %s:%s", local_path, host, remote_path)

    return os.EX_OK


def get_local_paths(paths):
    paths = [os.path.expanduser(path) for path in paths]

    expanded_paths = []
    already_met_paths = set()
    for path in paths:
        if os.path.isdir(path):
            extracted = expand_directory(path)
        else:
            extracted = glob.glob(path)
        extracted = [os.path.realpath(path_) for path_ in extracted]
        for extracted_path in extracted:
            if extracted_path not in already_met_paths:
                already_met_paths.add(extracted_path)
                expanded_paths.append(extracted_path)

    return expanded_paths


def get_only_files(paths):
    files = []

    for path in paths:
        if not os.path.isfile(path):
            LOG.debug("Skip path %s because it is not a file", path)
            continue
        if not os.access(path, os.R_OK):
            LOG.warning("Skip file %s because it is not readable", path)
            continue
        files.append(path)

    return files


def expand_directory(directory):
    return [os.path.join(directory, path) for path in os.listdir(directory)]
